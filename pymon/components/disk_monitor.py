"""Disk Monitor Component - Extracted from PyMon Dashboard"""

import json


def get_disk_monitor_html(disk_data: dict) -> str:
    """Generate disk usage chart HTML for a given set of server data.

    Args:
        disk_data: Dictionary containing 'servers' list with disk_percent,
                  last_status, etc.

    Returns:
        HTML string containing the Chart.js visualization
    """
    if not disk_data.get("servers"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No disk data available</div>"
        )

    servers = disk_data.get("servers") or []

    # Calculate average disk usage across all servers
    total_disk = sum(s.get("disk_percent", 0) for s in servers if s.get("last_status") == "up")
    active_servers = len([s for s in servers if s.get("last_status") == "up"])

    avg_disk = round(total_disk / active_servers, 1) if active_servers else 0

    # Generate color gradient based on disk load
    disk_color = _get_disk_color(avg_disk)

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Disk Usage</h3>
        <span style="background: {disk_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_disk}% average</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Disk bars -->
        {"".join(_generate_disk_bar(s, i) for i, s in enumerate(servers[:5]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0%</text>
        <text x="-10" y="90" text-anchor="end" fill="#64748b" font-size="10">{avg_disk}%</text>
        <text x="-10" y="140" text-anchor="end" fill="#64748b" font-size="10">100%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_server_info(s, i) for i, s in enumerate(servers[:5]))}
    </div>
</div>"""


def _get_disk_color(disk_percent: float) -> str:
    """Generate a color based on disk usage level."""
    if disk_percent < 30:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif disk_percent < 50:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif disk_percent < 75:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_disk_bar(server: dict, index: int) -> str:
    """Generate a single disk bar element."""
    disk = server.get("disk_percent", 0)
    status = "up" if server.get("last_status") == "up" else "down"

    # Bar height scales with disk usage (max 150px for 100% disk)
    bar_height = min(150, disk * 1.5)

    return f'''<g transform="translate({40 + index * 160}, 20)">
        <rect x="0" y="{180 - bar_height}" width="160" height="{bar_height}" rx="4"
            fill={_get_disk_color(disk)} stroke="#1e293b" stroke-width="2"/>
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


def get_disk_summary(disk_data: dict) -> dict:
    """Generate a summary object for disk metrics."""

    servers = disk_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]
    total_disk = sum(s.get("disk_percent", 0) for s in active_servers)
    avg_disk = round(total_disk / len(active_servers), 2) if active_servers else 0

    # Categorize server disk states
    low_disk = [s for s in active_servers if s.get("disk_percent", 0) < 30]
    medium_disk = [s for s in active_servers if s.get("disk_percent", 0) < 50 and not s in low_disk]
    high_disk = [s for s in active_servers if s.get("disk_percent", 0) >= 50 and not s in medium_disk]

    # Estimate optimal disk threshold (90th percentile of normal servers)
    disk_values = sorted([s.get("disk_percent", 0) for s in active_servers])
    if len(disk_values) > 1:
        optimal_threshold = disk_values[int(len(disk_values) * 0.9)]
    else:
        optimal_threshold = 85

    return {
        "total_disk": total_disk,
        "avg_disk": avg_disk,
        "active_servers": len(active_servers),
        "low_disk_count": len(low_disk),
        "medium_disk_count": len(medium_disk),
        "high_disk_count": len(high_disk),
        "optimal_threshold": optimal_threshold,
        "status": "healthy" if avg_disk < 70 else ("warning" if avg_disk < 90 else "critical"),
    }


def get_disk_trend_html(trend_data: dict) -> str:
    """Generate HTML for disk usage trend chart."""

    history = trend_data.get("history", []) or []

    if not history:
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No disk trend data available</div>"
        )

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Disk Trend (Last {len(history)} samples)</h3>

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

        <!-- Disk trend line -->
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

    disk = point.get("disk_percent", 0)
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"
    color = _get_disk_color(disk)

    y_position = max(0, min(180, disk * 1.5))

    return f'''<circle cx="{320 + index * 10}" cy="{y_position}" r="6" fill={color} stroke="#fff" stroke-width="2"
        class="trend-point">
        <title>{timestamp}: {disk:.1f}%</title>
    </circle>'''


def _generate_trend_info(point: dict, index: int) -> str:
    """Generate trend info badge."""

    disk = point.get("disk_percent", 0)
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{point.get("name", "Disk")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{disk:.1f}% disk</div>
    </div>"""


def get_disk_alerts_html(alert_data: dict) -> str:
    """Generate HTML for disk-related alerts."""

    if not alert_data or not alert_data.get("alerts"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No disk alerts configured</div>"
        )

    alerts = alert_data.get("alerts", []) or []
    active_alerts = [a for a in alerts if a.get("enabled", True)]

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Disk Alerts</h3>

    <div style="display: grid; gap: 12px;">
        {"".join(_generate_disk_alert(a) for a in active_alerts)}
    </div>

    <style>
        .alert-card {padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; gap: 12px;}
        .alert-icon {flex - shrink: 0; font-size: 18px;}
    </style>
</div>"""


def _generate_disk_alert(alert: dict) -> str:
    """Generate a single disk alert card."""

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
            <div style="color: #94a3b8; font-size: 12px;">Alerts when disk > {threshold}</div>
        </div>
        <span style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 11px;">
            {severity.upper()}
        </span>
    </div>"""


def get_disk_recommendations_html(disk_data: dict) -> str:
    """Generate HTML for disk optimization recommendations."""

    summary = get_disk_summary(disk_data)

    if summary["status"] == "healthy":
        recommendation = "🟢 Disk usage is healthy. Consider reviewing your storage allocation and considering SSD upgrades for performance improvements."
    elif summary["status"] == "warning":
        recommendation = "🟡 Disk usage is elevated. Review large files, consider archiving old data, or expanding storage capacity before it becomes critical."
    else:
        recommendation = "🔴 Critical disk pressure detected! Immediate action required - investigate large unused files, archive old data, or expand storage immediately."

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 12px;">Disk Optimization Tips</h3>

    {recommendation}

    <div style="margin-top: 16px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; display: flex; gap: 12px;">
        <span>📊</span>
        <div style="color: #cbd5e1; font-size: 13px;">
            Average disk usage across monitored servers: {summary["avg_disk"]:.1f}% (Threshold: {summary["optimal_threshold"]:.0f}%)
        </div>
    </div>
</div>"""


def get_partition_monitor_html(partition_data: dict) -> str:
    """Generate partition usage chart HTML for a given set of server data.

    Args:
        partition_data: Dictionary containing 'partitions' list with use_percent,
                       mount_point, file_system, etc.

    Returns:
        HTML string containing the Chart.js visualization
    """
    if not partition_data.get("partitions"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No partition data available</div>"
        )

    partitions = partition_data.get("partitions") or []

    # Sort by usage percentage descending
    sorted_partitions = sorted(partitions, key=lambda p: p.get("use_percent", 0), reverse=True)

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Partition Usage</h3>
        <span class="badge" style="{_get_partition_badge_style(sorted_partitions[0].get("status", "healthy"))}">
            Top {len(sorted_partitions)} partitions
        </span>
    </div>

    <svg viewBox="0 0 800 250" style="width: 100%; height: auto; max-height: 250px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="250" fill="url(#grid)"/>

        <!-- Partition bars -->
        {"".join(_generate_partition_bar(p, i) for i, p in enumerate(sorted_partitions[:7]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0%</text>
        <text x="-10" y="90" text-anchor="end" fill="#64748b" font-size="10">50%</text>
        <text x="-10" y="140" text-anchor="end" fill="#64748b" font-size="10">75%</text>
        <text x="-10" y="190" text-anchor="end" fill="#64748b" font-size="10">100%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_partition_info(p, i) for i, p in enumerate(sorted_partitions[:7]))}
    </div>

    <style>
        .badge {display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500; color: white;}
        .healthy {background: linear-gradient(90deg, #10b981 0%, #059669 100%);}
        .warning {background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);}
        .critical {background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);}
    </style>
</div>"""


def _get_partition_badge_status(partition: dict) -> str:
    """Get partition status string."""
    use = partition.get("use_percent", 0)
    if use < 30:
        return "healthy"
    elif use < 60:
        return "warning"
    else:
        return "critical"


def _get_partition_badge_style(status: str) -> str:
    """Get badge style based on status."""

    styles = {
        "healthy": 'background: linear-gradient(90deg, #10b981 0%, #059669 100%);',
        "warning": 'background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);',
        "critical": 'background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);',
    }

    return styles.get(status.lower(), "background: rgba(51,65,85,0.5);")


def _generate_partition_bar(partition: dict, index: int) -> str:
    """Generate a single partition bar element."""
    use = partition.get("use_percent", 0)
    status = "healthy" if partition.get("status") == "up" else "down"

    # Bar height scales with usage (max 210px for 100% usage)
    bar_height = min(210, use * 2.1)

    return f'''<g transform="translate({40 + index * 160}, 25)">
        <rect x="0" y="{230 - bar_height}" width="160" height="{bar_height}" rx="4"
            fill={_get_partition_color(use)} stroke="#1e293b" stroke-width="2"/>
        <text x="80" y="-25" text-anchor="middle" fill="#f8fafc" font-size="11">
            {partition.get("mount_point", f"/dev/{index}")[:6]}
        </text>
    </g>'''


def _get_partition_color(use: float) -> str:
    """Generate a color based on partition usage level."""
    if use < 30:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif use < 50:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif use < 75:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_partition_info(partition: dict, index: int) -> str:
    """Generate partition info badge."""

    mount_point = (partition.get("mount_point", f"/dev/{index}").lstrip("/")).replace("/", " /")[:25]
    use = float(partition.get("use_percent", 0) or 0)
    size = partition.get("size_gb", "N/A") or "-"
    badge_style = _get_partition_badge_style(_get_partition_badge_status(partition))

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 8px; padding: 8px 16px; display: flex; align-items: center; gap: 8px;">
        <span style="{badge_style} color: white; font-size: 12px; font-weight: 500; padding: 2px 6px; border-radius: 9999px;">
            {use:.1f}%
        </span>
        <div style="flex: 1;">
            <div style="color: #e2e8f0; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {mount_point}
            </div>
            <div style="color: #64748b; font-size: 11px;">{size} GB</div>
        </div>
    </div>"""


def get_disk_space_html(space_data: dict) -> str:
    """Generate disk space availability chart HTML."""

    if not space_data or not space_data.get("space"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No disk space data available</div>"
        )

    space = space_data.get("space", []) or []

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Available Disk Space</h3>

    <div style="display: grid; gap: 12px;">
        {"".join(_generate_space_row(s, i) for i, s in enumerate(space[:5]))}
    </div>

    <style>
        .space-row {padding: 12px 16px; background: rgba(15, 23, 42, 0.6); border-radius: 8px;}
        .progress-bar {height: 8px; background: rgba(51,65,85,0.5); border-radius: 9999px; overflow: hidden;}
        .progress-fill {height: 100%; border-radius: 9999px;}
    </style>
</div>"""


def _generate_space_row(space: dict, index: int) -> str:
    """Generate a single disk space row."""

    mount = (space.get("mount_point", f"/dev/{index}").lstrip("/")).replace("/", " /")[:30] if space.get("mount_point") else "-"
    free = space.get("free_gb", 0) or 0
    total = space.get("total_gb", 1) or 1
    used_percent = round((total - free) / total * 100, 2)

    return f"""<div class="space-row">
        <div style="color: #f8fafc; font-size: 13px; margin-bottom: 4px;">{mount}</div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="color: #94a3b8; font-size: 12px;">Free:</span>
            <span style="color: #f8fafc; font-size: 13px;">{free:.1f} GB</span>
        </div>
        <div class="progress-bar" style="flex: 1; margin-left: auto;">
            <div class="progress-fill" style="{_get_fill_style(used_percent)}"
                title="{used_percent}% used, {free:.1f} GB free">
            </div>
        </div>
    </div>"""


def _get_fill_style(percent: float) -> str:
    """Get progress bar fill style based on usage."""

    colors = {
        "healthy": "#10b981",
        "warning": "#f59e0b",
        "critical": "#ef4444",
    }

    status = (
        "healthy" if percent < 30
        else "warning" if percent < 70
        else "critical"
    )

    width = max(1, min(100, percent))

    return f'background: linear-gradient(90deg, {colors[status]} 0%, #059669 100%); width: {width}%;'


def get_disk_health_summary(disk_data: dict) -> dict:
    """Generate a comprehensive health summary for disk monitoring."""

    servers = disk_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]

    # Get partition data from first server (or aggregate if multiple)
    partitions = []
    if active_servers and "partitions" in active_servers[0]:
        partitions = sorted(active_servers[0].get("partitions", []) or [], key=lambda p: p.get("use_percent", 0), reverse=True)[:5]

    # Calculate overall disk health
    total_partitions = len(partitions) if partitions else 0
    critical_partitions = len([p for p in partitions if p.get("use_percent", 0) >= 85])
    warning_partitions = len([p for p in partitions if 70 <= p.get("use_percent", 0) < 85])

    overall_status = (
        "critical"
        if critical_partitions > 0
        else "warning"
        if warning_partitions > 1 or any(p.get("use_percent", 0) >= 60 for p in partitions)
        else "healthy"
    )

    return {
        "overall_status": overall_status,
        "total_servers": len(active_servers),
        "active_servers": len([s for s in active_servers if s.get("partitions")]),
        "critical_partitions": critical_partitions,
        "warning_partitions": warning_partitions,
        "top_partitions": partitions[:5],
    }
