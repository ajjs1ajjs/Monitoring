"""Memory Monitor Component - Extracted from PyMon Dashboard"""

import json


def get_memory_monitor_html(memory_data: dict) -> str:
    """Generate memory usage chart HTML for a given set of server data.

    Args:
        memory_data: Dictionary containing 'servers' list with memory_percent,
                    last_status, etc.

    Returns:
        HTML string containing the Chart.js visualization
    """
    if not memory_data.get("servers"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            ">No memory data available</div>"
        )

    servers = memory_data.get("servers") or []

    # Calculate average memory usage across all servers
    total_memory = sum(s.get("memory_percent", 0) for s in servers if s.get("last_status") == "up")
    active_servers = len([s for s in servers if s.get("last_status") == "up"])

    avg_memory = round(total_memory / active_servers, 1) if active_servers else 0

    # Generate color gradient based on memory load
    memory_color = _get_memory_color(avg_memory)

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Memory Usage</h3>
        <span style="background: {memory_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_memory}% average</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Memory bars -->
        {"".join(_generate_memory_bar(s, i) for i, s in enumerate(servers[:5]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0%</text>
        <text x="-10" y="90" text-anchor="end" fill="#64748b" font-size="10">{avg_memory}%</text>
        <text x="-10" y="140" text-anchor="end" fill="#64748b" font-size="10">100%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_server_info(s, i) for i, s in enumerate(servers[:5]))}
    </div>
</div>"""


def _get_memory_color(memory_percent: float) -> str:
    """Generate a color based on memory usage level."""
    if memory_percent < 30:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif memory_percent < 50:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif memory_percent < 75:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_memory_bar(server: dict, index: int) -> str:
    """Generate a single memory bar element."""
    memory = server.get("memory_percent", 0)
    status = "up" if server.get("last_status") == "up" else "down"

    # Bar height scales with memory usage (max 150px for 100% memory)
    bar_height = min(150, memory * 1.5)

    return f'''<g transform="translate({40 + index * 160}, 20)">
        <rect x="0" y="{180 - bar_height}" width="160" height="{bar_height}" rx="4"
            fill={_get_memory_color(memory)} stroke="#1e293b" stroke-width="2"/>
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


def get_memory_summary(memory_data: dict) -> dict:
    """Generate a summary object for memory metrics."""

    servers = memory_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]
    total_memory = sum(s.get("memory_percent", 0) for s in active_servers)
    avg_memory = round(total_memory / len(active_servers), 2) if active_servers else 0

    # Categorize server memory states
    low_memory = [s for s in active_servers if s.get("memory_percent", 0) < 30]
    medium_memory = [s for s in active_servers if s.get("memory_percent", 0) < 50 and not s in low_memory]
    high_memory = [s for s in active_servers if s.get("memory_percent", 0) >= 50 and not s in medium_memory]

    # Estimate optimal memory threshold (90th percentile of normal servers)
    memory_values = sorted([s.get("memory_percent", 0) for s in active_servers])
    if len(memory_values) > 1:
        optimal_threshold = memory_values[int(len(memory_values) * 0.9)]
    else:
        optimal_threshold = 75

    return {
        "total_memory": total_memory,
        "avg_memory": avg_memory,
        "active_servers": len(active_servers),
        "low_memory_count": len(low_memory),
        "medium_memory_count": len(medium_memory),
        "high_memory_count": len(high_memory),
        "optimal_threshold": optimal_threshold,
        "status": "healthy" if avg_memory < 60 else ("warning" if avg_memory < 85 else "critical"),
    }


def get_memory_trend_html(trend_data: dict) -> str:
    """Generate HTML for memory usage trend chart."""

    history = trend_data.get("history", []) or []

    if not history:
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            ">No memory trend data available</div>"
        )

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Memory Trend (Last {len(history)} samples)</h3>

    <svg viewBox="0 0 600 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="600" height="200" fill="url(#grid)"/>

        <!-- X-axis -->
        <line x1="0" y1="180" x2="590" y2="180" stroke="#334155" stroke-width="1"/>
        <line x1="0" y1="0" x2="0" y2="180" stroke="#334155" stroke-width="1"/>

        <!-- Memory trend line -->
        {"".join(_generate_trend_point(h, i) for i, h in enumerate(history))}

        <!-- Y-axis labels -->
        <text x="-5" y="170" text-anchor="end" fill="#64748b" font-size="9">0%</text>
        <text x="-5" y="130" text-anchor="end" fill="#64748b" font-size="9">50%</text>
        <text x="-5" y="90" text-anchor="end" fill="#64748b" font-size="9">75%</text>
        <text x="-5" y="50" text-anchor="end" fill="#64748b" font-size="9">100%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_trend_info(h, i) for i, h in enumerate(history[:5]))}
    </div>

    <style>
        .trend-point {cursor: pointer;}
        .trend-label {fill: #94a3b8; font-size: 10px;}
    </style>
</div>"""


def _generate_trend_point(point: dict, index: int) -> str:
    """Generate a single trend point element."""

    memory = point.get("memory_percent", 0)
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"
    color = _get_memory_color(memory)

    y_position = max(0, min(180, memory * 1.5))

    return f'''<circle cx="{320 + index * 10}" cy="{y_position}" r="6" fill={color} stroke="#fff" stroke-width="2"
        class="trend-point">
        <title>{timestamp}: {memory:.1f}%</title>
    </circle>'''


def _generate_trend_info(point: dict, index: int) -> str:
    """Generate trend info badge."""

    memory = point.get("memory_percent", 0)
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{point.get("name", "Memory")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{memory:.1f}% memory</div>
    </div>"""


def get_memory_alerts_html(alert_data: dict) -> str:
    """Generate HTML for memory-related alerts."""

    if not alert_data or not alert_data.get("alerts"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            ">No memory alerts configured</div>"
        )

    alerts = alert_data.get("alerts", []) or []
    active_alerts = [a for a in alerts if a.get("enabled", True)]

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Memory Alerts</h3>

    <div style="display: grid; gap: 12px;">
        {"".join(_generate_memory_alert(a) for a in active_alerts)}
    </div>

    <style>
        .alert-card {padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; gap: 12px;}
        .alert-icon {flex - shrink: 0; font-size: 18px;}
    </style>
</div>"""


def _generate_memory_alert(alert: dict) -> str:
    """Generate a single memory alert card."""

    name = alert.get("name", "Unnamed Alert")[:35]
    threshold = (
        f"{alert.get('threshold', 0):.1f}%"
        if isinstance(alert.get("threshold"), float)
        else str(alert.get("threshold", 0))
    )
    severity = alert.get("severity", "info").lower()

    # Get icon and color based on severity
    icons = {
        "critical": ("🔴", "#ef4444"),
        "warning": ("⚠️", "#f59e0b"),
        "info": ("ℹ️", "#3b82f6"),
    }

    icon, color = icons.get(severity, ("ℹ️", "#64748b"))

    return f"""<div class="alert-card" style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155;">
        <span class="alert-icon">{icon}</span>
        <div style="flex: 1;">
            <div style="color: #f8fafc; font-weight: 600; margin-bottom: 2px;">{name}</div>
            <div style="color: #94a3b8; font-size: 12px;">Alerts when memory > {threshold}</div>
        </div>
        <span style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 11px;">
            {severity.upper()}
        </span>
    </div>"""


def get_memory_recommendations_html(memory_data: dict) -> str:
    """Generate HTML for memory optimization recommendations."""

    summary = get_memory_summary(memory_data)

    if summary["status"] == "healthy":
        recommendation = "🟢 Memory usage is healthy. Consider reviewing your application's memory profiling to identify any potential leaks."
    elif summary["status"] == "warning":
        recommendation = "🟡 Memory usage is elevated. Review high-memory processes and consider scaling your infrastructure or optimizing resource-intensive operations."
    else:
        recommendation = "🔴 Critical memory pressure detected! Immediate action required - investigate memory leaks, increase allocation, or scale out horizontally."

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 12px;">Memory Optimization Tips</h3>

    {recommendation}

    <div style="margin-top: 16px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; display: flex; gap: 12px;">
        <span>📊</span>
        <div style="color: #cbd5e1; font-size: 13px;">
            Average memory usage across monitored servers: {summary["avg_memory"]:.1f}% (Threshold: {summary["optimal_threshold"]:.0f}%)
        </div>
    </div>
</div>"""
