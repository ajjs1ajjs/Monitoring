import platform
import psutil  # Можливо, знадобиться встановити: pip install psutil


def get_system_info():
    print("=== System Information ===")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Processor: {platform.processor()}")

    # Оперативна пам'ять
    mem = psutil.virtual_memory()
    print(f"Memory: {mem.total // (1024 ** 3)} GB (Used: {mem.percent}%)")

    # Дисковий простір
    disk = psutil.disk_usage('/')
    print(f"Disk Space: {disk.total // (1024 ** 3)} GB (Free: {disk.free // (1024 ** 3)} GB)")


if __name__ == "__main__":
    get_system_info()