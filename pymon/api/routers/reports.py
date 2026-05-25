import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from pymon.api.deps import get_db
from pymon.auth import User, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/server/{server_id}")
async def generate_server_report(server_id: int, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        server = conn.execute("SELECT name, host FROM servers WHERE id = ?", (server_id,)).fetchone()
        if not server: raise HTTPException(status_code=404, detail="Server not found")

        history = conn.execute("""
            SELECT timestamp, cpu_percent, memory_percent 
            FROM metrics_history 
            WHERE server_id = ? AND timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp ASC
        """, (server_id,)).fetchall()

        labels = [row[0] for row in history]
        cpu_data = [row[1] for row in history]
        mem_data = [row[2] for row in history]

        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Infrastructure Report - {server['name']}</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body {{ font-family: 'Outfit', sans-serif; padding: 40px; background: #fff; color: #1e293b; max-width: 1000px; margin: 0 auto; }}
                    .card {{ border: 1px solid #e2e8f0; padding: 40px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
                    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #f1f5f9; padding-bottom: 20px; }}
                    h1 {{ margin: 0; color: #0f172a; font-size: 2rem; }}
                    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }}
                    .stat-box {{ background: #f8fafc; padding: 20px; border-radius: 12px; }}
                    .label {{ color: #64748b; font-size: 0.8rem; text-transform: uppercase; font-weight: 600; }}
                    .value {{ font-size: 1.2rem; font-weight: 700; color: #0f172a; }}
                    .chart-container {{ height: 400px; margin-top: 40px; }}
                    .btn-print {{ background: #0f172a; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
                    @media print {{ .btn-print {{ display: none; }} body {{ padding: 0; }} .card {{ border: none; box-shadow: none; }} }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="header">
                        <div>
                            <h1>System Performance Report</h1>
                            <p style="color: #64748b;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                        </div>
                        <button class="btn-print" onclick="window.print()">Download PDF</button>
                    </div>
                    
                    <div class="info-grid">
                        <div class="stat-box">
                            <div class="label">Server Identifier</div>
                            <div class="value">{server['name']}</div>
                        </div>
                        <div class="stat-box">
                            <div class="label">Network Address</div>
                            <div class="value">{server['host']}</div>
                        </div>
                    </div>

                    <h3 style="margin-top: 40px;">24-Hour Performance Trend</h3>
                    <div class="chart-container">
                        <canvas id="reportChart"></canvas>
                    </div>
                </div>

                <script>
                    const ctx = document.getElementById('reportChart').getContext('2d');
                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(labels)},
                            datasets: [
                                {{
                                    label: 'CPU Usage (%)',
                                    data: {json.dumps(cpu_data)},
                                    borderColor: '#f97316',
                                    backgroundColor: 'rgba(249, 115, 22, 0.1)',
                                    fill: true,
                                    tension: 0.4,
                                    borderWidth: 3
                                }},
                                {{
                                    label: 'Memory Usage (%)',
                                    data: {json.dumps(mem_data)},
                                    borderColor: '#3b82f6',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    fill: true,
                                    tension: 0.4,
                                    borderWidth: 3
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{ legend: {{ position: 'top' }} }},
                            scales: {{ 
                                y: {{ beginAtZero: true, max: 100 }},
                                x: {{ ticks: {{ maxRotation: 45, autoSkip: true, maxTicksLimit: 12 }} }}
                            }}
                        }}
                    }});
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html)
    finally:
        conn.close()
