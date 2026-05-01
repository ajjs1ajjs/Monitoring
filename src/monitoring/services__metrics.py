from monitoring.dto__models import ServerCreate

"""Business logic services for Monitoring."""

from datetime import timedelta, datetime, timezone
from typing import Any, Dict, List, Optional


class MetricsService:  # noqa: D101, ANN204
    """Core metrics aggregation and caching service."""

    def __init__(self):
        self.cache_prefix = "metrics_"
    
    async def get_cached_metrics(
        self, server_id: Optional[int], metric: str, range: str  # noqa: D103
    ) -> Optional[Dict[str, Any]]:
        """Check cache before querying DB."""
        try:
            import asyncio
            
            loop = asyncio.new_event_loop()
            try:
                key = f"{self.cache_prefix}{server_id}:{metric}:{range}"
                cached = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: cache_client.get(key)
                )
                if cached and isinstance(cached, dict):
                    return cached
            except Exception:
                pass
            
            loop.close()
        except Exception:
            pass
        
        # Return from DB if not in cache
        return await self._get_metrics_from_db(server_id, metric, range)

    async def _get_metrics_from_db(  # noqa: D103
        self, server_id: Optional[int], metric: str, range: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch metrics from database."""
        if not self.db_client._db_path:
            return None
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_client._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT timestamp, {metric} as value FROM metrics_history "
                f"WHERE server_id=? AND timestamp > datetime('now', ?) ORDER BY timestamp",
                (server_id or 0,),
            )
            
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                return None
            
            result = {
                "server_id": server_id,
                "metric": metric,
                "values": [float(r["value"]) for r in rows],
                "timestamps": [r["timestamp"] for r in rows],
            }
            
            # Cache the result
            key = f"{self.cache_prefix}{server_id}:{metric}:{range}"
            try:
                import asyncio
                
                loop = asyncio.new_event_loop()
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: cache_client.set(key, str(result), 600)
                )
            except Exception:
                pass
            
            conn.close()
            return result
        
        except Exception as e:
            # Log error but don't fail the API request
            print(f"MetricsService error for server_id={server_id}, metric={metric}: {e}")
            return None

    async def get_multi_metrics(  # noqa: D103, ANN002
        self, 
        servers: List[int], 
        metrics: List[str] = None
    ) -> Dict[int, Dict[str, Any]]:
        """Get multiple metrics for multiple servers using asyncio.gather."""
        
        async def fetch_for_server(
            sid: int, metric: str
        ) -> Optional[Dict[str, Any]]:  # noqa: D103
            return await self.get_cached_metrics(sid, metric, "24h")
        
        if not metrics:
            all_metrics = ["cpu_percent", "memory_percent", "disk_percent"]
        else:
            all_metrics = metrics
        
        results: Dict[int, Dict[str, Any]] = {}
        
        for sid in servers:
            server_results: Dict[str, Optional[Dict[str, Any]]] = {}
            for metric in all_metrics:
                result = await fetch_for_server(sid, metric)
                if result:
                    server_results[metric] = result.get("values", [])
            
            results[sid] = server_results

    async def aggregate_trends(  # noqa: D103
        self, server_id: int, days: int = 7, granularity: str = "hourly"
    ) -> Optional[Dict[str, Any]]:
        """Aggregate trends over time period."""
        
        if not self.db_client._db_path:
            return None
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_client._db_path)
            cursor = conn.execute(
                f"""
                SELECT 
                    strftime('%Y-%m-%d {granularity}', timestamp) as period,
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    MIN(cpu_percent) as min_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as max_memory,
                    AVG(disk_percent) as avg_disk,
                    SUM(network_rx) as total_rx,
                    SUM(network_tx) as total_tx
                FROM metrics_history
                WHERE server_id = ? 
                  AND timestamp > datetime('now', '-{days} days')
                GROUP BY period
                ORDER BY period
            """, (server_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return {
                "periods": [r[0] for r in rows],
                "avg_cpu": [float(r[1]) if r[1] else None for r in rows],
                "max_memory": [float(r[5]) if r[5] else None for r in rows],
            }
        
        except Exception as e:
            print(f"AggregateTrends error for server_id={server_id}, days={days}: {e}")
            return None


# Global service instance
metrics_service = MetricsService()
