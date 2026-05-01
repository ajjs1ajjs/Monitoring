"""
Monitoring Dashboard - FastAPI Application

Features:
- RESTful API endpoints for metrics, graphs, and system info
- WebSockets support for real-time updates (optional)
- Interactive charts with Chart.js integration
- Dark/Light theme support via API responses
- Responsive design ready
"""

import hashlib
import json
import random
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ========================================
# APP SETUP
# ========================================

app = FastAPI(
    title="Monitoring Dashboard API",
    description="Interactive monitoring dashboard with real-time charts and metrics",
    version="1.0.0",
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="../monitoring/static"), name="static")

# Mount templates directory
templates = Jinja2Templates(directory="../monitoring/templates")

# ========================================
# DATABASE MODELS & REPOSITORIES (Mock for demo)
# ========================================


class MetricRepository:
    """In-memory repository with realistic mock data"""

    def __init__(self):
        self.metrics = {}

    def register_metric(self, name: str, unit: str, min_val: float, max_val: float):
        self.metrics[name] = {
            "name": name,
            "unit": unit,
            "min": min_val,
            "max": max_val,
            "history": [],
            "current": None,
        }

    def add_data_point(self, metric_name: str, timestamp: float, value: float):
        if metric_name in self.metrics:
            self.metrics[metric_name]["history"].append({"timestamp": timestamp, "value": value})
            # Keep only last 100 points for memory efficiency
            if len(self.metrics[metric_name]["history"]) > 100:
                self.metrics[metric_name]["history"] = self.metrics[metric_name]["history"][-100:]

    def get_latest_value(self, metric_name: str) -> Optional[float]:
        return self.metrics.get(metric_name, {}).get("current") if metric_name in self.metrics else None

    def get_history(self, metric_name: str, hours: int = 24) -> List[dict]:
        """Get historical data points for a specific time range"""
        if metric_name not in self.metrics:
            return []

        now = datetime.utcnow()
        cutoff_time = (now - timedelta(hours=hours)).timestamp()

        history_points = [point for point in self.metrics[metric_name]["history"] if point["timestamp"] >= cutoff_time]

        # Sort by timestamp and return as list of dicts
        return sorted(history_points, key=lambda x: x["timestamp"])

    def generate_mock_data(self) -> dict:
        """Generate realistic mock data for demo purposes"""
        now = datetime.utcnow()

        metrics_data = {
            "cpu_usage": MetricRepository.__generate_cpu_data(hours=24),
            "memory_usage": MetricRepository.__generate_memory_data(hours=24),
            "disk_io": MetricRepository.__generate_disk_io_data(hours=12),
            "network_in": MetricRepository.__generate_network_data("in", hours=6),
            "network_out": MetricRepository.__generate_network_data("out", hours=6),
            "request_rate": MetricRepository.__generate_request_data(hours=4),
        }

        # Convert to format for Chart.js
        chart_data = {}
        for metric_name, data_points in metrics_data.items():
            labels = []
            datasets = [
                {
                    "label": f"{metric_name.replace('_', ' ').title()}",
                    "data": [],
                    "borderColor": MetricRepository.__get_color(metric_name),
                    "fill": False,
                }
            ]

            for point in data_points:
                labels.append(point["timestamp"].strftime("%H:%M"))
                datasets[0]["data"].append({"x": point["timestamp"], "y": round(point["value"], 2)})

            chart_data[metric_name] = {"labels": labels, "datasets": datasets}

        return chart_data

    @staticmethod
    def __generate_cpu_data(hours: int = 24) -> List[dict]:
        """Generate CPU usage data with realistic patterns"""
        data = []
        cpu_base = random.uniform(35, 50)
        cycle_duration = timedelta(hours=8)

        start_time = datetime.utcnow() - (cycle_duration * hours // 2)

        while start_time <= datetime.utcnow():
            # CPU usage follows daily patterns with some noise
            hour_of_day = start_time.hour + start_time.minute / 60

            # Base pattern: lower during night, higher during work hours
            if 8 <= hour_of_day <= 18:
                base = random.uniform(45, 70)
            else:
                base = random.uniform(20, 35)

            # Add some noise
            noise = random.gauss(0, 5)
            cpu_value = max(base + noise, 10)

            data.append({"timestamp": start_time, "value": round(cpu_value, 2)})

            start_time += timedelta(minutes=30)

        return data

    @staticmethod
    def __generate_memory_data(hours: int = 24) -> List[dict]:
        """Generate memory usage with gradual increase and spikes"""
        data = []
        memory_base = random.uniform(55, 70)

        start_time = datetime.utcnow() - timedelta(hours=hours)

        while start_time <= datetime.utcnow():
            # Memory slowly increases over time
            base_growth = hours * 0.5 / (24 * 60)  # ~1% per hour

            memory_value = memory_base + (start_time.hour + start_time.minute / 60) * base_growth

            # Add occasional spikes
            if random.random() < 0.05:  # 5% chance of spike
                memory_value += random.uniform(5, 15)

            # Clamp to realistic values
            memory_value = max(memory_value, 45)
            memory_value = min(memory_value, 92)

            data.append({"timestamp": start_time, "value": round(memory_value, 2)})

            start_time += timedelta(minutes=30)

        return data

    @staticmethod
    def __generate_disk_io_data(hours: int = 12) -> List[dict]:
        """Generate disk I/O throughput with burst patterns"""
        data = []

        # Burst every 15-30 minutes for realism
        start_time = datetime.utcnow() - timedelta(hours=hours)

        while start_time <= datetime.utcnow():
            # Generate random bursts
            base_throughput = random.uniform(20, 80)

            if random.random() < 0.1:  # 10% chance of burst
                burst_factor = random.uniform(2, 4)
                throughput = base_throughput * burst_factor
            else:
                throughput = base_throughput

            data.append({"timestamp": start_time, "value": round(throughput, 2)})

            start_time += timedelta(minutes=15)

        return data

    @staticmethod
    def __generate_network_data(direction: str, hours: int = 6) -> List[dict]:
        """Generate network traffic with realistic patterns"""
        data = []

        # Network has more consistent baseline with occasional spikes
        base_mbps = random.uniform(10, 50) if direction == "in" else random.uniform(5, 25)

        start_time = datetime.utcnow() - timedelta(hours=hours)

        while start_time <= datetime.utcnow():
            # Base traffic with small variations
            base_traffic = base_mbps + random.gauss(0, base_mbps * 0.15)

            # Add occasional large transfers (files, backups)
            if random.random() < 0.02:  # 2% chance
                spike = random.uniform(80, 200)
                traffic = max(base_traffic, spike)
            else:
                traffic = base_traffic

            # Ensure realistic values
            traffic = max(traffic, 5)
            traffic = min(traffic, 300)

            data.append({"timestamp": start_time, "value": round(traffic, 2)})

            start_time += timedelta(minutes=10)

        return data

    @staticmethod
    def __generate_request_data(hours: int = 4) -> List[dict]:
        """Generate request rate per second with burst patterns"""
        data = []

        # Requests typically follow daily user patterns
        start_time = datetime.utcnow() - timedelta(hours=hours)

        while start_time <= datetime.utcnow():
            hour_of_day = start_time.hour + start_time.minute / 60

            if 9 <= hour_of_day <= 17:  # Business hours
                base_requests = random.uniform(200, 500)
            elif 8 <= hour_of_day < 9 or 17 <= hour_of_day < 20:
                base_requests = random.uniform(100, 300)
            else:
                base_requests = random.uniform(20, 100)

            # Add burst patterns (API calls, batch jobs)
            if random.random() < 0.08:
                requests = base_requests * random.uniform(3, 5)
            else:
                requests = base_requests

            data.append({"timestamp": start_time, "value": round(requests, 2)})

            start_time += timedelta(minutes=15)

        return data

    @staticmethod
    def __get_color(metric_name: str) -> str:
        """Get consistent color for each metric"""
        colors = {
            "cpu_usage": "#e17055",  # Orange-red
            "memory_usage": "#fdcb6e",  # Yellow-orange
            "disk_io": "#00b894",  # Teal
            "network_in": "#74b9ff",  # Blue
            "network_out": "#a29bfe",  # Purple
            "request_rate": "#0984e3",  # Bright blue
        }
        return colors.get(metric_name, "#667eea")


# ========================================
# API ENDPOINTS
# ========================================

repo = MetricRepository()


# Initialize with some mock data at startup
@app.on_event("startup")
async def init_data():
    """Initialize repository with realistic mock data"""
    repo.register_metric("cpu_usage", "%", 0, 100)
    repo.register_metric("memory_usage", "%", 0, 100)
    repo.register_metric("disk_io", "MB/s", 0, 500)
    repo.register_metric("network_in", "Mbps", 0, 300)
    repo.register_metric("network_out", "Mbps", 0, 200)
    repo.register_metric("request_rate", "req/sec", 0, 1000)

    # Add some historical data to make charts look realistic
    for _ in range(10):
        mock_data = repo.generate_mock_data()
        for metric_name, chart_data in mock_data.items():
            for point in chart_data["labels"]:
                if hasattr(point, "timestamp"):
                    pass  # Already processed


# ========================================
# DASHBOARD ENDPOINTS
# ========================================


@app.get("/", response_class=Response)
async def index(request: Request):
    """Main dashboard page with interactive charts"""

    # Generate fresh chart data
    chart_data = repo.generate_mock_data()

    return templates.TemplateResponse(
        "index.html", {"request": request, "chart_data": json.dumps(chart_data), "app_version": app.version}
    )


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics values"""

    metrics = {}
    for metric_name in ["cpu_usage", "memory_usage", "disk_io", "network_in", "network_out", "request_rate"]:
        value = (
            repo.generate_mock_data()[metric_name]["datasets"][0]["data"][-1]["y"] if repo.generate_mock_data() else 0
        )
        metrics[metric_name] = {
            "name": metric_name.replace("_", " ").title(),
            "value": round(value, 2),
            "unit": repo.metrics.get(metric_name, {}).get("unit", ""),
        }

    return {"metrics": metrics}


@app.get("/api/metrics/history/{metric_name}", response_model=List[dict])
async def get_metric_history(metric_name: str = "cpu_usage", hours: int = Query(default=24, ge=1, le=720)):
    """Get historical data for a specific metric"""

    # Generate realistic history based on the requested time range
    now = datetime.utcnow()
    cutoff_time = (now - timedelta(hours=hours)).timestamp()

    history_points = []
    base_value = random.uniform(20, 60) if metric_name == "cpu_usage" else random.uniform(45, 80)

    # Generate data points every 15 minutes
    for i in range(hours * 4):
        timestamp = now - timedelta(minutes=hours * 60 - (i * 15))

        if metric_name == "cpu_usage":
            value = max(20, min(95, base_value + random.gauss(0, 8)))
        elif metric_name == "memory_usage":
            # Memory gradually increases
            growth_per_hour = (hours * 1) / 24
            value = min(90, base_value + i * (growth_per_hour / 4))
            if random.random() < 0.03:  # Occasional spike
                value += random.uniform(5, 15)
        elif metric_name == "disk_io":
            value = max(10, min(200, base_value * (1 + random.gauss(0, 0.3))))
        else:
            # Generic pattern
            value = max(5, min(150, base_value + random.gauss(0, 10)))

        history_points.append({"timestamp": timestamp.strftime("%H:%M"), "value": round(value, 2)})

    return {"metric": metric_name, "hours": hours, "data": history_points}


@app.get("/api/system")
async def get_system_info():
    """Get system information and uptime"""

    return {
        "hostname": hashlib.md5(secrets.token_hex(8)).hexdigest()[:12],
        "uptime_seconds": random.randint(86400, 31536000),
        "memory_total_mb": 16384,
        "memory_free_mb": round(random.uniform(2048, 8192), 2),
        "cpu_cores": 8,
        "os_version": "Windows Server",
        "python_version": "3.11.x",
    }


@app.get("/api/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z", "version": app.version}


# ========================================
# ERROR HANDLERS & MIDDLEWARE (Optional Enhancements)
# ========================================


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Custom error handler with proper HTTP status codes"""
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=500, content={"detail": str(exc), "timestamp": datetime.utcnow().isoformat() + "Z"})


# Add CORS middleware (if needed for cross-origin requests)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# ROUTING & LIFESPAN (Optional Advanced Features)
# ========================================


@app.get("/api/dashboard")
async def get_dashboard_data():
    """Get complete dashboard data for the main page"""

    chart_data = repo.generate_mock_data()
    system_info = await get_system_info()
    metrics_snapshot = await get_metrics()

    return {"charts": chart_data, "system": system_info, "metrics": metrics_snapshot["metrics"]}


# Export app for testing and deployment
__all__ = ["app", "repo"]
