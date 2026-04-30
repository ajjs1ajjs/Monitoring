"""CPU Chart Component - Extracted from PyMon Dashboard"""

import os


def get_cpu_chart_html(servers_data: dict) -> str:
    """Generate CPU usage chart HTML for a given set of server data.

    Args:
        servers_data: Dictionary containing 'servers' list with cpu_percent,
                     last_status, etc.

    Returns:
        HTML string containing the Chart.js visualization
    """
    if not servers_data.get("servers"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            ">No CPU data available</div>"
        )

    servers = servers_data["servers"] or []

    # Calculate average CPU usage across all servers
    total_cpu = sum(s.get("cpu_percent", 0) for s in servers if s.get("last_status") == "up")
    active_servers = len([s for s in servers if s.get("last_status") == "up"])

    avg_cpu = (total_cpu / active_servers * 100).toFixed(1) if active_servers else 0

    # Generate color gradient based on CPU load
    cpu_color = _get_cpu_color(avg_cpu)

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">CPU Usage</h3>
        <span style="background: {cpu_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_cpu}% average</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- CPU bars -->
        {"".join(_generate_cpu_bar(s, i) for i, s in enumerate(servers[:5]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0%</text>
        <text x="-10" y="90" text-anchor="end" fill="#64748b" font-size="10">{avg_cpu}%</text>
        <text x="-10" y="140" text-anchor="end" fill="#64748b" font-size="10">100%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_server_info(s, i) for i, s in enumerate(servers[:5]))}
    </div>
</div>"""


def _get_cpu_color(cpu_percent: float) -> str:
    """Generate a color based on CPU usage level."""
    if cpu_percent < 30:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif cpu_percent < 60:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif cpu_percent < 85:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"
    else:
        return "linear-gradient(90deg, #7f1d1d 0%, #450a0a 100%)"


def _generate_cpu_bar(server: dict, index: int) -> str:
    """Generate a single CPU bar element."""
    cpu = server.get("cpu_percent", 0)
    status = "up" if server.get("last_status") == "up" else "down"

    # Bar height scales with CPU usage (max 150px for 100% CPU)
    bar_height = min(150, cpu * 1.5)

    return f'''<g transform="translate({40 + index * 160}, 20)">
        <rect x="0" y="{180 - bar_height}" width="160" height="{bar_height}" rx="4"
            fill={_get_cpu_color(cpu)} stroke="#1e293b" stroke-width="2"/>
        <text x="80" y="-10" text-anchor="middle" fill="#f8fafc" font-size="11">
            {server.get("name", f"Server-{index}")[:8]}
        </text>
    </g>'''


def _generate_server_info(server: dict, index: int) -> str:
    """Generate server info badge."""
    status = "●" if server.get("last_status") == "up" else "○"
    os_type = server.get("os_type", "linux").capitalize()

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 8px; padding: 8px 16px; display: flex; align-items: center; gap: 8px;">
        <span style="color: {"#10b981" if server.get("last_status") == "up" else "#64748b"}">
            {status}
        </span>
        <span style="color: #e2e8f0; font-size: 13px;">{server.get("name", f"Server-{index}")[:15]}</span>
        <span style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 11px;">
            {os_type}
        </span>
    </div>"""


def get_cpu_summary(servers_data: dict) -> dict:
    """Generate a summary object for CPU metrics."""

    servers = servers_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]
    total_cpu = sum(s.get("cpu_percent", 0) for s in active_servers)
    avg_cpu = (total_cpu / len(active_servers) * 100).toFixed(2) if active_servers else 0

    # Categorize server CPU states
    low_cpu = [s for s in active_servers if s.get("cpu_percent", 0) < 30]
    medium_cpu = [s for s in active_servers if s.get("cpu_percent", 0) < 60 and not s in low_cpu]
    high_cpu = [s for s in active_servers if s.get("cpu_percent", 0) >= 60 and not s in medium_cpu]

    # Estimate optimal CPU threshold (90th percentile of normal servers)
    cpu_values = sorted([s.get("cpu_percent", 0) for s in active_servers])
    if len(cpu_values) > 1:
        optimal_threshold = cpu_values[int(len(cpu_values) * 0.9)]
    else:
        optimal_threshold = 80

    return {
        "total_cpu": total_cpu,
        "avg_cpu": avg_cpu,
        "active_servers": len(active_servers),
        "low_cpu_count": len(low_cpu),
        "medium_cpu_count": len(medium_cpu),
        "high_cpu_count": len(high_cpu),
        "optimal_threshold": optimal_threshold,
        "status": "healthy" if avg_cpu < 70 else ("warning" if avg_cpu < 90 else "critical"),
    }
