"""
Асинхронний Redis кеш-менеджер для проєкту Monitoring.

Цей модуль надає:
- Базовий клас CacheManager з асинхронними методами
- Декоратори для автоматичного кешування API відповідей
- Генератор ключів кешування
- Підтримку TTL (час життя) для записів
"""

import asyncio
import hashlib
import json
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    from redis.asyncio import Redis as AsyncRedis
    from redis.asyncio.connection import ConnectionPool as AsyncConnectionPool
except ImportError:
    print("⚠️ redis (async) не встановлено. Кешування буде недоступне.")
    AsyncRedis = None  # type: ignore
    AsyncConnectionPool = None  # type: ignore


from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheConfig(BaseSettings):
    """Конфігурсація Redis кешу."""

    model_config = SettingsConfigDict(env_prefix="CACHE_", env_file=".env")

    # Підключення

    redis_url: str = "redis://localhost:6379/0"  # Default URL
    db: int = 0
    password: Optional[str] = None

    # Параметри TTL (час життя) в секундах
    default_ttl: int = 3600  # 1 година за замовчуванням
    short_ttl: int = 300  # 5 хвилин для частих даних
    long_ttl: int = 86400  # 24 години для статичних даних

    # Конфіг кешування API
    api_cache_enabled: bool = True
    max_api_cache_size: int = 1000  # Максимальна кількість записів в кеші


class CacheKeyGenerator:
    """Генератор ключів для Redis."""

    @staticmethod
    def generate_key(prefix: str, *args: Any) -> str:
        """Створює унікальний ключ на основі префіксу та аргументів."""
        parts = [prefix] + [str(arg) for arg in args if arg is not None]
        # Додаємо соль для безпеки (щоб схожі дані не потрапляли в один ключ)
        salt = "pymon-cache-v1"
        combined = ":".join(parts) + f":{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]


class CacheManager:
    """Асинхронний менеджер Redis кешу."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._redis_pool: Optional[AsyncRedis] = None
        self._initialized = False
        self._stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

    async def initialize(self) -> bool:
        """Ініціалізує підключення до Redis."""
        if self._initialized:
            return True
        if AsyncRedis is None:
            return False

        try:
            pool = AsyncConnectionPool.from_url(self.config.redis_url, decode_responses=False)
            self._redis_pool = AsyncRedis(connection_pool=pool)
            await self._redis_pool.ping()
            print(f"✅ Підключено до Redis: {self.config.redis_url}")
            return True
        except Exception as e:
            print(f"❌ Помилка ініціалізації Redis: {e}")
            self._stats["errors"] += 1
            return False

    async def close(self) -> None:
        """Закриває підключення до Redis."""
        if self._redis_pool:
            try:
                await self._redis_pool.close()
            except Exception as e:
                print(f"⚠️ Помилка закриття Redis: {e}")

    # ==================== Базові операції ====================

    async def get(self, key: str) -> Optional[Any]:
        """Отримує значення з кешу."""
        if not await self.initialize():
            return None

        try:
            value = await self._redis_pool.get(key)  # type: ignore

            # Памітати про перетворення JSON назад
            if isinstance(value, bytes):
                data = json.loads(value.decode("utf-8"))  # type: ignore
                self._stats["hits"] += 1
                return data

        except (json.JSONDecodeError, Exception) as e:  # type: ignore
            print(f"⚠️ Помилка читання кешу для ключа {key}: {e}")

        self._stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:  # type: ignore
        """Записує значення в Redis."""
        if not await self.initialize():
            return False

        try:
            # Перетворюємо Python-об'єкт у JSON
            json_value = json.dumps(value, default=str).encode("utf-8")  # type: ignore

            ttl = ttl or self.config.default_ttl
            result = await self._redis_pool.setex(key, ttl, json_value)  # type: ignore

            if not result:
                self._stats["errors"] += 1

        except Exception as e:
            print(f"⚠️ Помилка запису в Redis для ключа {key}: {e}")
            self._stats["errors"] += 1

        return True

    async def delete(self, key: str) -> bool:
        """Видаляє ключ з кешу."""
        if not await self.initialize():
            return False

        try:
            result = await self._redis_pool.delete(key)  # type: ignore
            return bool(result)  # Redis повертає кількість видалених ключів

        except Exception as e:
            print(f"⚠️ Помилка видалення ключа {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Перевіряє, чи існує ключ у кешу."""
        if not await self.initialize():
            return False

        try:
            result = await self._redis_pool.exists(key)  # type: ignore
            return bool(result)

        except Exception as e:
            print(f"⚠️ Помилка перевірки існування ключа {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1, ttl: int = None) -> Optional[int]:  # type: ignore
        """Атомарно збільшує значення (використовується для лічильників)."""
        if not await self.initialize():
            return None

        try:
            # Використовуємо SETNX + INCR для атомарності
            ttl = ttl or self.config.default_ttl
            result = await self._redis_pool.set(key, amount, nx=True, px=ttl * 1000)  # type: ignore

            if not result:
                # Ключ вже існує - інкрементуємо його
                value = await self._redis_pool.incr(key)  # type: ignore
                return int(value)
            else:
                return int(amount)

        except Exception as e:
            print(f"⚠️ Помилка інкременту для ключа {key}: {e}")
            return None

    async def expire(self, key: str, ttl: int = None) -> bool:  # type: ignore
        """Розширює час життя ключа (TTL)."""
        if not await self.initialize():
            return False

        try:
            ttl = ttl or self.config.default_ttl
            result = await self._redis_pool.expire(key, ttl)  # type: ignore
            return bool(result)  # True якщо розширення вдалося

        except Exception as e:
            print(f"⚠️ Помилка розширення TTL для ключа {key}: {e}")
            return False

    async def clear(self, prefix: str = "") -> int:
        """Видаляє всі ключі з заданим префіксом."""
        if not await self.initialize():
            return 0

        try:
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self._redis_pool.scan(cursor=cursor, match=f"{prefix}*", count=100)  # type: ignore
                for key in keys:
                    await self._redis_pool.delete(key)  # type: ignore
                    deleted_count += 1

                if cursor == 0:
                    break

            return deleted_count

        except Exception as e:
            print(f"⚠️ Помилка очищення кешу: {e}")
            return 0

    # ==================== Декоратори для кешування ====================

    def get_cached(self, key_generator: Optional[Callable] = None, ttl: int = None) -> Callable:  # type: ignore
        """Декоратор для отримання даних з кешу перед виконанням функції.

        Приклад використання:
            @cache.get_cached(ttl=300)  # TTL 5 хвилин
            async def get_server_status(server_id: int):
                await self.initialize()
                return {"status": "active", "cpu": 45}
        """

        if key_generator is None:
            key_generator = CacheKeyGenerator.generate_key

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Створюємо ключ на основі аргументів функції
                key_parts = [str(arg) for arg in args if arg is not None]
                key_parts.extend([f"{name}={value}" for name, value in kwargs.items()])
                cache_key = f"pymon:{func.__name__}:{key_generator(*key_parts)}"

                # Спробуємо отримати з кешу
                cached_data = await self.get(cache_key)

                if cached_data is not None:
                    return cached_data

                # Якщо в кеші немає, виконуємо функцію і записуємо результат
                result = await func(*args, **kwargs)
                ttl_to_use = ttl or (
                    self.config.short_ttl if "active" in str(func.__name__).lower() else self.config.default_ttl
                )

                await self.set(cache_key, result, ttl=ttl_to_use)
                return result

            return wrapper

        return decorator

    def cache_response(self, ttl: int = None, key_generator: Optional[Callable] = None) -> Callable:  # type: ignore
        """Декоратор для кешування результату функції після виконання.

        Приклад використання:
            @cache.cache_response(ttl=3600)  # TTL 1 година
            async def get_all_servers():
                await self.initialize()
                return [{"id": i, "name": f"server_{i}"} for i in range(5)]
        """

        if key_generator is None:
            key_generator = CacheKeyGenerator.generate_key

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Виконуємо функцію (не кешуємо перед виконанням)
                result = await func(*args, **kwargs)

                # Створюємо ключ для збереження
                key_parts = [str(arg) for arg in args if arg is not None]
                key_parts.extend([f"{name}={value}" for name, value in kwargs.items()])
                cache_key = f"pymon:{func.__name__}:{key_generator(*key_parts)}"

                # Записуємо результат в кеш
                ttl_to_use = ttl or (
                    self.config.long_ttl if "all" in str(func.__name__).lower() else self.config.default_ttl
                )
                await self.set(cache_key, result, ttl=ttl_to_use)

                return result

            return wrapper

        return decorator

    def cache_with_version(
        self, version: str = None, ttl: int = None, key_generator: Optional[Callable] = None  # type: ignore
    ) -> Callable:
        """Декоратор для кешування з підтримкою версій. Якщо версія змінилася, кеш очищується.

        Приклад використання:
            @cache.cache_with_version(version="1.0", ttl=3600)
            async def get_static_assets():
                await self.initialize()
                return {"css": "style.css", "js": "app.js"}
        """

        if key_generator is None:
            key_generator = CacheKeyGenerator.generate_key

        version_counter = 0  # Внутрішній лічильник версій

        def decorator(func: Callable) -> Callable:
            nonlocal version_counter

            @wraps(func)
            async def wrapper(*args, **kwargs):
                current_version = version or (getattr(wrapper.__wrapped__, "_cache_version", None))

                if current_version:
                    # Створюємо ключ з версією
                    key_parts = [str(arg) for arg in args if arg is not None]
                    key_parts.extend([f"{name}={value}" for name, value in kwargs.items()])

                    # Якщо версія змінилася або кешу немає - виконуємо функцію
                    if current_version != version:
                        cache_key = f"pymon:{func.__name__}:{key_generator(*key_parts)}:v{version}"
                        cached_data = await self.get(cache_key)

                        if cached_data is None or cached_data.get("_version") != str(version):
                            result = await func(*args, **kwargs)

                            # Записуємо з версією
                            ttl_to_use = ttl or self.config.default_ttl
                            await self.set(cache_key, {**result, "_version": version}, ttl=ttl_to_use)

                            return result

                    else:
                        cache_key = f"pymon:{func.__name__}:{key_generator(*key_parts)}:v{current_version}"
                        cached_data = await self.get(cache_key)

                        if cached_data is not None and isinstance(cached_data, dict):
                            return cached_data

                # Якщо версії немає - працюємо як звичайний кеш-декоратор
                result = await func(*args, **kwargs)
                ttl_to_use = ttl or self.config.default_ttl
                cache_key = f"pymon:{func.__name__}:{key_generator(*key_parts)}"

                if isinstance(result, dict):
                    result["_version"] = version if version else str(version_counter + 1)
                    await self.set(cache_key, result, ttl=ttl_to_use)

                return result

            # Зберігаємо версію для функції (якщо вона не задана)
            if not version:
                setattr(wrapper.__wrapped__, "_cache_version", version_counter + 1)

            return wrapper

        return decorator

    # ==================== Утиліти ====================

    def get_stats(self) -> Dict[str, Any]:
        """Повертає статистикі роботи з кешом."""
        stats = {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": self._calculate_hit_rate(),
        }
        return stats

    def _calculate_hit_rate(self) -> float:
        """Розраховує коефіцієнт хітів (accuracy)."""
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0

        hit_rate = self._stats["hits"] / total
        return round(hit_rate * 100, 2)

    # ==================== Специфічні операції для Monitoring ====================

    async def get_server_metrics(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Отримує метрики конкретного сервера з кешу (TTL: 30с)."""
        if not await self.initialize():
            return None

        key = CacheKeyGenerator.generate_key("server_metrics", server_id)
        cache_key = f"pymon:{key}"

        cached_data = await self.get(cache_key)

        if cached_data is not None:
            return cached_data  # type: ignore

        # Тут буде логіка отримання метрик від Prometheus або іншого джерела
        # Покажемо приклад структури
        metrics = {
            "server_id": server_id,
            "cpu_usage": 45.2,
            "memory_usage": 62.8,
            "disk_io_read": 1024.5,
            "disk_io_write": 512.3,
            "network_in": 10240.0,
            "network_out": 5120.0,
        }

        await self.set(cache_key, metrics, ttl=self.config.short_ttl)
        return metrics

    async def get_api_status(self) -> Optional[Dict[str, Any]]:
        """Отримує статус API з кешу (TTL: 5хв)."""
        if not await self.initialize():
            return None

        cache_key = "pymon:api_status"
        cached_data = await self.get(cache_key)

        if cached_data is not None:
            return {**cached_data, "cache_age": asyncio.get_event_loop().time() - cached_data.get("_timestamp", 0)}

        # Створити базовий статус API
        status = {
            "status": "operational",
            "version": "1.0.0",
            "endpoints": ["/api/v1/metrics", "/api/v1/alerts", "/api/v1/servers"],
            "_timestamp": asyncio.get_event_loop().time(),
        }

        await self.set(cache_key, status, ttl=self.config.short_ttl)
        return status

    async def get_uptime_data(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Отримує дані про uptime сервера з кешу (TTL: 1хв)."""
        if not await self.initialize():
            return None

        key = CacheKeyGenerator.generate_key("uptime", server_id)
        cache_key = f"pymon:{key}"

        cached_data = await self.get(cache_key)

        if cached_data is not None:
            return {**cached_data, "cache_age": asyncio.get_event_loop().time() - cached_data.get("_timestamp", 0)}

        # Показати приклад структури
        data = {
            "server_id": server_id,
            "uptime_seconds": 31536000,  # 1 рік
            "downtime_minutes": 5.2,
            "uptime_percent": 99.98,
            "_timestamp": asyncio.get_event_loop().time(),
        }

        await self.set(cache_key, data, ttl=self.config.short_ttl)
        return data

    async def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        """Отримує загальні статистику для дашборду (TTL: 1хв)."""
        if not await self.initialize():
            return None

        cache_key = "pymon:dashboard_stats"
        cached_data = await self.get(cache_key)

        if cached_data is not None:
            stats = {**cached_data, "cache_age": asyncio.get_event_loop().time() - cached_data.get("_timestamp", 0)}
            return stats

        # Показати приклад структури
        stats = {
            "total_servers": 125,
            "active_servers": 118,
            "alerts_count": 7,
            "metrics_collected": 45678,
            "last_update": asyncio.get_event_loop().time(),
        }

        await self.set(cache_key, stats, ttl=self.config.short_ttl)
        return stats


# ==================== Основні експортні функції ====================

__all__ = [
    "CacheConfig",
    "CacheKeyGenerator",
    "CacheManager",
    # Декоратори
    "get_cached",
    "cache_response",
    "cache_with_version",
]


async def main():
    """Приклад використання модулю."""
    cache = CacheManager()

    # Ініціалізація
    if await cache.initialize():
        print(f"📊 Статистика (спочатку): {cache.get_stats()}")

        # Приклад отримання з кешу
        server_metrics = await cache.get_server_metrics(1)
        if server_metrics:
            print(f"\nМетрики сервера 1: {server_metrics}")

        # Приклад використання декоратора
        @cache.get_cached(ttl=300)
        async def get_user_data(user_id: int):
            await cache.initialize()
            return {"user_id": user_id, "name": f"User_{user_id}", "active": True}

        # Викликаємо декораторований метод (перший раз з виконанням)
        user1 = await get_user_data(42)
        print(f"\nДані користувача 42: {user1}")

        # Другий виклик - має прийняти з кешу (якщо TTL ще діє)
        # user1_again = await get_user_data(42)  # Буде працювати, якщо кеш не застарів

        # Статистика після тестів
        print(f"\n📊 Статистика після тестів: {cache.get_stats()}")

        # Закриття
        await cache.close()


if __name__ == "__main__":
    asyncio.run(main())
