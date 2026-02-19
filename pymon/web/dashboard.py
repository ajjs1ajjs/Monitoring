"""Web dashboard UI"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

web = FastAPI(title="PyMon Dashboard")


class Dashboard:
    def __init__(self):
        self.panels: list[dict] = []

    def add_panel(self, title: str, query: str, chart_type: str = "line", refresh: int = 5) -> None:
        self.panels.append({"title": title, "query": query, "type": chart_type, "refresh": refresh})


dashboard = Dashboard()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PyMon Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 1rem 2rem; border-bottom: 1px solid #0f3460; }
        .header h1 { font-size: 1.5rem; color: #e94560; }
        .container { padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1.5rem; }
        .panel { background: #16213e; border-radius: 8px; padding: 1rem; border: 1px solid #0f3460; }
        .panel h3 { margin-bottom: 1rem; color: #e94560; }
        .chart-container { height: 200px; }
        .stats { display: flex; gap: 2rem; margin-bottom: 2rem; }
        .stat { background: #16213e; padding: 1.5rem; border-radius: 8px; flex: 1; border: 1px solid #0f3460; }
        .stat-value { font-size: 2rem; color: #e94560; }
        .stat-label { color: #888; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <div class="header"><h1>PyMon Dashboard</h1></div>
    <div class="container">
        <div class="stats" id="stats"></div>
        <div class="grid" id="panels"></div>
    </div>
    <script>
        const panels = {{ panels | tojson }};
        const charts = {};
        
        async function fetchMetrics(query) {
            const end = new Date();
            const start = new Date(end - 3600000);
            const res = await fetch(`/api/v1/query?query=${query}&start=${start.toISOString()}&end=${end.toISOString()}`);
            return (await res.json()).result || [];
        }
        
        function createPanel(panel, index) {
            const div = document.createElement('div');
            div.className = 'panel';
            div.innerHTML = `<h3>${panel.title}</h3><div class="chart-container"><canvas id="chart-${index}"></canvas></div>`;
            document.getElementById('panels').appendChild(div);
            
            const ctx = document.getElementById(`chart-${index}`).getContext('2d');
            charts[index] = new Chart(ctx, {
                type: panel.type,
                data: { labels: [], datasets: [{ label: panel.title, data: [], borderColor: '#e94560', backgroundColor: 'rgba(233, 69, 96, 0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, maintainAspectRatio: false, scales: { x: { display: false }, y: { grid: { color: '#0f3460' } } }, plugins: { legend: { display: false } } }
            });
        }
        
        async function updatePanel(panel, index) {
            const data = await fetchMetrics(panel.query);
            const chart = charts[index];
            chart.data.labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
            chart.data.datasets[0].data = data.map(d => d.value);
            chart.update('none');
        }
        
        panels.forEach(createPanel);
        panels.forEach((p, i) => { updatePanel(p, i); setInterval(() => updatePanel(p, i), p.refresh * 1000); });
    </script>
</body>
</html>
"""


@web.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return DASHBOARD_HTML.replace("{{ panels | tojson }}", str(dashboard.panels).replace("'", '"'))


@web.get("/api/dashboard/panels")
async def get_panels():
    return {"panels": dashboard.panels}


@web.post("/api/dashboard/panels")
async def add_panel(panel: dict):
    dashboard.add_panel(
        title=panel.get("title", "Untitled"),
        query=panel.get("query", ""),
        chart_type=panel.get("type", "line"),
        refresh=panel.get("refresh", 5),
    )
    return {"status": "ok"}
