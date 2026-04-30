"""Network Monitor Component - Extracted from PyMon Dashboard"""

import json


def get_network_monitor_html(network_data: dict) -> str:
    """Generate network usage chart HTML for a given set of server data.

    Args:
        network_data: Dictionary containing 'servers' list with network_rx,
                    network_tx, etc.

    Returns:
        HTML string containing the Chart.js visualization
    """
    if not network_data.get("servers"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No network data available</div>"
        )

    servers = network_data.get("servers") or []

    # Calculate average network usage across all servers
    total_rx = sum(s.get("network_rx", 0) for s in servers if s.get("last_status") == "up")
    total_tx = sum(s.get("network_tx", 0) for s in servers if s.get("last_status") == "up")
    active_servers = len([s for s in servers if s.get("last_status") == "up"])

    avg_rx = (total_rx / active_servers).toFixed(2) if active_servers else 0
    avg_tx = (total_tx / active_servers).toFixed(2) if active_servers else 0

    # Generate color gradient based on network load
    network_color = _get_network_color(avg_rx, avg_tx)

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Network Traffic</h3>
        <span style="background: {network_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_rx:.1f} MB/s RX / {avg_tx:.1f} MB/s TX avg</span>
    </div>

    <svg viewBox="0 0 800 250" style="width: 100%; height: auto; max-height: 250px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="250" fill="url(#grid)"/>

        <!-- Network bars -->
        {"".join(_generate_network_bar(s, i) for i, s in enumerate(servers[:6]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0 MB/s</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{avg_rx:.0f} MB/s</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">500 MB/s</text>
        <text x="-10" y="205" text-anchor="end" fill="#64748b" font-size="10">1 GB/s</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_server_info(s, i) for i, s in enumerate(servers[:6]))}
    </div>
</div>"""


def _get_network_color(rx: float, tx: float) -> str:
    """Generate a color based on network load balance."""
    total = rx + tx or 1
    ratio = min(1.0, max(0.5, (rx / total)))

    if ratio < 0.3:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif ratio < 0.5:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif ratio < 0.7:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_network_bar(server: dict, index: int) -> str:
    """Generate a single network bar element."""
    rx = server.get("network_rx", 0) or 0
    tx = server.get("network_tx", 0) or 0

    # Bar height scales with network usage (max 210px for 1 GB/s)
    max_bandwidth = 1024 * 1.5  # 1.5 GB/s in MB/s
    bar_height_rx = min(210, rx * 2.1)
    bar_height_tx = min(210, tx * 2.1)

    return f'''<g transform="translate({40 + index * 160}, 25)">
        <!-- RX Bar -->
        <rect x="0" y="{230 - bar_height_rx}" width="70" height="{bar_height_rx}" rx="4"
            fill={_get_network_color(rx, tx)} stroke="#1e293b" stroke-width="2"/>
        <!-- TX Bar -->
        <rect x="80" y="{230 - bar_height_tx}" width="70" height="{bar_height_tx}" rx="4"
            fill={_get_network_color(tx, rx)} stroke="#1e293b" stroke-width="2"/>
        <!-- Labels -->
        <text x="35" y="-15" text-anchor="middle" fill="#f8fafc" font-size="10">RX</text>
        <text x="125" y="-15" text-anchor="middle" fill="#f8fafc" font-size="10">TX</text>
    </g>'''


def _generate_server_info(server: dict, index: int) -> str:
    """Generate server info badge."""
    status = "●" if server.get("last_status") == "up" else "○"
    hostname = server.get("hostname", f"server-{index}") or "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 8px; padding: 8px 16px; display: flex; align-items: center; gap: 8px;">
        <span style="color: {"#10b981" if server.get("last_status") == "up" else "#64748b"}">
            {status}
        </span>
        <span style="color: #e2e8f0; font-size: 13px;">{hostname[:20]}</span>
    </div>"""


def get_network_summary(network_data: dict) -> dict:
    """Generate a summary object for network metrics."""

    servers = network_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]

    total_rx = sum(s.get("network_rx", 0) for s in active_servers)
    total_tx = sum(s.get("network_tx", 0) for s in active_servers)

    avg_rx = (total_rx / len(active_servers)) if active_servers else 0
    avg_tx = (total_tx / len(active_servers)) if active_servers else 0

    # Calculate network health score
    rx_health_score = min(1.0, max(0, 1 - (avg_rx / 512)))  # Cap at 512 MB/s
    tx_health_score = min(1.0, max(0, 1 - (avg_tx / 512)))

    overall_status = (
        "critical" if avg_rx > 900 or avg_tx > 900
        else ("warning" if avg_rx > 600 or avg_tx > 600)
        else "healthy"
    )

    return {
        "total_rx": total_rx,
        "total_tx": total_tx,
        "avg_rx": avg_rx,
        "avg_tx": avg_tx,
        "active_servers": len(active_servers),
        "rx_health_score": rx_health_score * 100,
        "tx_health_score": tx_health_score * 100,
        "overall_status": overall_status,
    }


def get_network_trend_html(trend_data: dict) -> str:
    """Generate HTML for network usage trend chart."""

    history = trend_data.get("history", []) or []

    if not history:
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No network trend data available</div>"
        )

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Network Trend (Last {len(history)} samples)</h3>

    <svg viewBox="0 0 600 250" style="width: 100%; height: auto; max-height: 250px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="600" height="250" fill="url(#grid)"/>

        <!-- X-axis -->
        <line x1="0" y1="230" x2="590" y2="230" stroke="#334155" stroke-width="1"/>
        <line x1="0" y1="0" x2="0" y2="230" stroke="#334155" stroke-width="1"/>

        <!-- Network trend line -->
        {"".join(_generate_trend_point(h, i) for i, h in enumerate(history))}

        <!-- Y-axis labels -->
        <text x="-5" y="220" text-anchor="end" fill="#64748b" font-size="9">0 MB/s</text>
        <text x="-5" y="185" text-anchor="end" fill="#64748b" font-size="9">{(max(h.get("network_rx", 0) for h in history) / 2):.0f} MB/s</text>
        <text x="-5" y="145" text-anchor="end" fill="#64748b" font-size="9">1 GB/s</text>

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

    rx = point.get("network_rx", 0) or 0
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"

    # Determine color based on RX load
    max_rx = max(h.get("network_rx", 0) for h in history) or 1024
    y_position = min(230, max(0, (rx / max_rx * 230)))

    return f'''<circle cx="{280 + index * 7}" cy="{y_position}" r="6"
        fill={_get_trend_color(rx, rx)} stroke="#fff" stroke-width="2"
        class="trend-point">
        <title>{timestamp}: RX {rx:.1f} MB/s</title>
    </circle>'''


def _get_trend_color(value: float, max_value: float) -> str:
    """Get trend color based on value ratio."""
    if value / max_value < 0.3:
        return "#10b981"
    elif value / max_value < 0.6:
        return "#f59e0b"
    else:
        return "#ef4444"


def _generate_trend_info(point: dict, index: int) -> str:
    """Generate trend info badge."""

    rx = point.get("network_rx", 0) or 0
    timestamp = (point.get("checked_at") or "").replace("T", " ").split(".")[0] if point.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{point.get("name", "Network")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{rx:.1f} MB/s RX</div>
    </div>"""


def get_network_alerts_html(alert_data: dict) -> str:
    """Generate HTML for network-related alerts."""

    if not alert_data or not alert_data.get("alerts"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No network alerts configured</div>"
        )

    alerts = alert_data.get("alerts", []) or []
    active_alerts = [a for a in alerts if a.get("enabled", True)]

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Network Alerts</h3>

    <div style="display: grid; gap: 12px;">
        {"".join(_generate_network_alert(a) for a in active_alerts)}
    </div>

    <style>
        .alert-card {padding: 12px 16px; border-radius: 8px; display: flex; align-items: center; gap: 12px;}
        .alert-icon {flex - shrink: 0; font-size: 18px;}
    </style>
</div>"""


def _generate_network_alert(alert: dict) -> str:
    """Generate a single network alert card."""

    name = alert.get("name", "Unnamed Alert")[:35]
    threshold = (
        f"{alert.get('threshold', 0):.1f} MB/s"
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
            <div style="color: #94a3b8; font-size: 12px;">Alerts when network > {threshold} MB/s</div>
        </div>
        <span style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 11px;">
            {severity.upper()}
        </span>
    </div>"""


def get_network_recommendations_html(network_data: dict) -> str:
    """Generate HTML for network optimization recommendations."""

    summary = get_network_summary(network_data)

    if summary["overall_status"] == "healthy":
        recommendation = "🟢 Network traffic is healthy. Consider reviewing your bandwidth allocation and considering load balancing to distribute traffic more evenly."
    elif summary["overall_status"] == "warning":
        recommendation = "🟡 Network traffic is elevated. Review high-bandwidth applications, consider upgrading network infrastructure or implementing traffic shaping."
    else:
        recommendation = "🔴 Critical network pressure detected! Immediate action required - investigate bandwidth-intensive processes, optimize data transfer, or scale network capacity."

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 12px;">Network Optimization Tips</h3>

    {recommendation}

    <div style="margin-top: 16px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; display: flex; gap: 12px;">
        <span>📊</span>
        <div style="color: #cbd5e1; font-size: 13px;">
            Average network throughput across monitored servers: RX {summary["avg_rx"]:.1f} MB/s / TX {summary["avg_tx"]:.1f} MB/s (Status: {summary["overall_status"].upper()})
        </div>
    </div>
</div>"""


def get_latency_monitor_html(latency_data: dict) -> str:
    """Generate latency monitoring chart HTML."""

    if not latency_data or not latency_data.get("latencies"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No latency data available</div>"
        )

    latencies = latency_data.get("latencies", []) or []

    # Calculate average and max latency
    avg_latency = (sum(l.get("latency_ms", 0) for l in latencies) / len(latencies)) if latencies else 0
    max_latency = max((l.get("latency_ms", 0) for l in latencies), default=0)

    # Generate color gradient based on latency load
    latency_color = _get_latency_color(avg_latency)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Network Latency</h3>
        <span style="background: {latency_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_latency:.1f} ms avg / {max_latency:.1f} ms max</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Latency points -->
        {"".join(_generate_latency_point(l, i) for i, l in enumerate(latencies[:8]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0 ms</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(max_latency / 2):.0f} ms</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">200 ms</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_latency_info(l, i) for i, l in enumerate(latencies[:8]))}
    </div>
</div>"""


def _get_latency_color(avg_latency: float) -> str:
    """Generate a color based on latency level."""
    if avg_latency < 50:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_latency < 100:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    elif avg_latency < 200:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_latency_point(latency: dict, index: int) -> str:
    """Generate a single latency point element."""

    ms = latency.get("latency_ms", 0) or 0
    timestamp = (latency.get("checked_at") or "").replace("T", " ").split(".")[0] if latency.get("checked_at") else "-"

    y_position = min(180, max(0, ms * 1.7))

    return f'''<circle cx="{340 + index * 8}" cy="{y_position}" r="5"
        fill={_get_latency_color(ms)} stroke="#fff" stroke-width="2">
        <title>{timestamp}: {ms:.1f} ms</title>
    </circle>'''


def _generate_latency_info(latency: dict, index: int) -> str:
    """Generate latency info badge."""

    ms = (latency.get("latency_ms", 0) or 0).toFixed(2)
    timestamp = (latency.get("checked_at") or "").replace("T", " ").split(".")[0] if latency.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{latency.get("name", "Latency")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{ms} ms</div>
    </div>"""


def get_jitter_monitor_html(jitter_data: dict) -> str:
    """Generate jitter monitoring chart HTML."""

    if not jitter_data or not jitter_data.get("jitters"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No jitter data available</div>"
        )

    jitters = jitter_data.get("jitters", []) or []

    # Calculate average and max jitter
    avg_jitter = (sum(j.get("jitter_ms", 0) for j in jitters) / len(jitters)) if jitters else 0
    max_jitter = max((j.get("jitter_ms", 0) for j in jitters), default=0)

    # Generate color gradient based on jitter load
    jitter_color = _get_jitter_color(avg_jitter)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Network Jitter</h3>
        <span style="background: {jitter_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_jitter:.2f} ms avg / {max_jitter:.2f} ms max</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Jitter points -->
        {"".join(_generate_jitter_point(j, i) for i, j in enumerate(jitters[:10]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0 ms</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(max_jitter / 2):.1f} ms</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">20 ms</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_jitter_info(j, i) for i, j in enumerate(jitters[:10]))}
    </div>
</div>"""


def _get_jitter_color(avg_jitter: float) -> str:
    """Generate a color based on jitter level."""
    if avg_jitter < 5:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_jitter < 10:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_jitter_point(jitter: dict, index: int) -> str:
    """Generate a single jitter point element."""

    ms = jitter.get("jitter_ms", 0) or 0
    timestamp = (jitter.get("checked_at") or "").replace("T", " ").split(".")[0] if jitter.get("checked_at") else "-"

    y_position = min(180, max(0, ms * 9))

    return f'''<circle cx="{350 + index * 6}" cy="{y_position}" r="4"
        fill={_get_jitter_color(ms)} stroke="#fff" stroke-width="2">
        <title>{timestamp}: {ms:.2f} ms</title>
    </circle>'''


def _generate_jitter_info(jitter: dict, index: int) -> str:
    """Generate jitter info badge."""

    ms = (jitter.get("jitter_ms", 0) or 0).toFixed(3)
    timestamp = (jitter.get("checked_at") or "").replace("T", " ").split(".")[0] if jitter.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{jitter.get("name", "Jitter")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{ms} ms</div>
    </div>"""


def get_packet_loss_monitor_html(packet_data: dict) -> str:
    """Generate packet loss monitoring chart HTML."""

    if not packet_data or not packet_data.get("packets"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No packet loss data available</div>"
        )

    packets = packet_data.get("packets", []) or []

    # Calculate average and max packet loss
    avg_loss = (sum(p.get("loss_percent", 0) for p in packets) / len(packets)) if packets else 0
    max_loss = max((p.get("loss_percent", 0) for p in packets), default=0)

    # Generate color gradient based on packet loss load
    loss_color = _get_loss_color(avg_loss)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Packet Loss</h3>
        <span style="background: {loss_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_loss:.2f}% avg / {max_loss:.2f}% max</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Packet loss points -->
        {"".join(_generate_loss_point(p, i) for i, p in enumerate(packets[:15]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0%</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(max_loss / 2):.0f}%</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">5%</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_loss_info(p, i) for i, p in enumerate(packets[:15]))}
    </div>
</div>"""


def _get_loss_color(avg_loss: float) -> str:
    """Generate a color based on packet loss level."""
    if avg_loss < 0.1:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_loss < 0.5:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_loss_point(loss: dict, index: int) -> str:
    """Generate a single packet loss point element."""

    pct = loss.get("loss_percent", 0) or 0
    timestamp = (loss.get("checked_at") or "").replace("T", " ").split(".")[0] if loss.get("checked_at") else "-"

    y_position = min(180, max(0, pct * 3.6))

    return f'''<circle cx="{45 + index * 6}" cy="{y_position}" r="5"
        fill={_get_loss_color(pct)} stroke="#fff" stroke-width="2">
        <title>{timestamp}: {pct:.2f}% loss</title>
    </circle>'''


def _generate_loss_info(loss: dict, index: int) -> str:
    """Generate packet loss info badge."""

    pct = (loss.get("loss_percent", 0) or 0).toFixed(3)
    timestamp = (loss.get("checked_at") or "").replace("T", " ").split(".")[0] if loss.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{loss.get("name", "Packet Loss")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{pct}%</div>
    </div>"""


def get_bandwidth_monitor_html(bandwidth_data: dict) -> str:
    """Generate bandwidth usage monitoring chart HTML."""

    if not bandwidth_data or not bandwidth_data.get("bandwidth"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No bandwidth data available</div>"
        )

    bandwidth_list = bandwidth_data.get("bandwidth", []) or []

    # Calculate average and max bandwidth
    avg_bw = (sum(bw.get("bandwidth_mbps", 0) for bw in bandwidth_list) / len(bandwidth_list)) if bandwidth_list else 0
    max_bw = max((bw.get("bandwidth_mbps", 0) for bw in bandwidth_list), default=0)

    # Generate color gradient based on bandwidth load
    bw_color = _get_bandwidth_color(avg_bw)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Bandwidth Usage</h3>
        <span style="background: {bw_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;">{avg_bw:.1f} Mbps avg / {max_bw:.1f} Mbps max</span>
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Bandwidth bars -->
        {"".join(_generate_bandwidth_bar(bw, i) for i, bw in enumerate(bandwidth_list[:10]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0 Mbps</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(max_bw / 2):.0f} Mbps</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">2 Gbps</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_bandwidth_info(bw, i) for i, bw in enumerate(bandwidth_list[:10]))}
    </div>
</div>"""


def _get_bandwidth_color(avg_bw: float) -> str:
    """Generate a color based on bandwidth level."""
    if avg_bw < 100:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_bw < 500:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    else:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"


def _generate_bandwidth_bar(bandwidth: dict, index: int) -> str:
    """Generate a single bandwidth bar element."""

    mbps = bandwidth.get("bandwidth_mbps", 0) or 0
    timestamp = (bandwidth.get("checked_at") or "").replace("T", " ").split(".")[0] if bandwidth.get("checked_at") else "-"

    # Bar height scales with bandwidth (max 180px for 2 Gbps)
    bar_height = min(180, mbps * 0.9)

    return f'''<g transform="translate({40 + index * 150}, 25)">
        <rect x="0" y="{180 - bar_height}" width="150" height="{bar_height}" rx="4"
            fill={_get_bandwidth_color(mbps)} stroke="#1e293b" stroke-width="2"/>
        <!-- Value text -->
        <text x="75" y="-28" text-anchor="middle" fill="#f8fafc" font-size="10">
            {mbps:.1f} Mbps
        </text>
    </g>'''


def _generate_bandwidth_info(bandwidth: dict, index: int) -> str:
    """Generate bandwidth info badge."""

    mbps = (bandwidth.get("bandwidth_mbps", 0) or 0).toFixed(2)
    timestamp = (bandwidth.get("checked_at") or "").replace("T", " ").split(".")[0] if bandwidth.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{bandwidth.get("name", "Bandwidth")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{mbps} Mbps</div>
    </div>"""


def get_ssl_monitor_html(ssl_data: dict) -> str:
    """Generate SSL/TLS monitoring chart HTML."""

    if not ssl_data or not ssl_data.get("certificates"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No SSL certificate data available</div>"
        )

    certificates = ssl_data.get("certificates", []) or []

    # Calculate average days until expiry
    avg_expiry = (sum(c.get("days_until_expiry", 999) for c in certificates if c.get("expires") != "expired") /
                 len([c for c in certificates if c.get("expires") != "expired"])) if any(c.get("expires") != "expired" for c in certificates) else 0
    critical_count = len([c for c in certificates if c.get("days_until_expiry", 999) < 30])

    # Generate color based on expiry risk
    ssl_color = _get_ssl_color(avg_expiry, critical_count)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">SSL/TLS Certificates</h3>

    <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        {"".join(_generate_ssl_badge(c, i) for i, c in enumerate(certificates[:5]))}
    </div>

    <svg viewBox="0 0 800 200" style="width: 100%; height: auto; max-height: 200px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="200" fill="url(#grid)"/>

        <!-- Certificate bars -->
        {"".join(_generate_ssl_bar(c, i) for i, c in enumerate(certificates[:5]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0 days</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(avg_expiry / 2):.0f} days</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">365 days</text>

    </svg>

    <div style="margin-top: 12px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px;">
        {f"<span style='color: #cbd5e1; font-size: 13px;'>Average days until expiry: {avg_expiry:.1f} (Critical: {critical_count} certificates)</span>" if avg_expiry > 0 else "<span style='color: #94a3b8; font-size: 13px;'>No valid certificates to monitor</span>"}
    </div>
</div>"""


def _get_ssl_color(avg_days: float, critical_count: int) -> str:
    """Generate a color based on SSL expiry risk."""

    if avg_days > 180 or not critical_count:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_days > 90 or critical_count < 3:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_ssl_badge(certificate: dict, index: int) -> str:
    """Generate a single SSL certificate badge."""

    expires = certificate.get("expires", "N/A")
    days = certificate.get("days_until_expiry", 999) or 999
    status = "●" if expires != "expired" and days > 0 else "○"

    color = "#10b981" if days > 30 else ("#f59e0b" if days > 7 else "#ef4444")

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 8px; padding: 8px 16px; display: flex; align-items: center; gap: 8px;">
        <span style="color: {color}">
            {status}
        </span>
        <div style="flex: 1;">
            <div style="color: #e2e8f0; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                title="{certificate.get("name", f"Cert-{index}")}">
                {certificate.get("domain", "N/A")[:35]}
            </div>
        </div>
        <span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px; font-size: 11px;">
            {days}d
        </span>
    </div>"""


def _generate_ssl_bar(certificate: dict, index: int) -> str:
    """Generate a single SSL certificate bar element."""

    days = (certificate.get("days_until_expiry", 999) or 999).toFixed(0) if certificate.get("expires") != "expired" else "-"

    # Bar height scales with expiry days (max 180px for 365 days)
    bar_height = min(180, max(2, days * 0.47))

    return f'''<g transform="translate({40 + index * 150}, 25)">
        <rect x="0" y="{180 - bar_height}" width="150" height="{bar_height}" rx="4"
            fill={_get_ssl_color(days, days)} stroke="#1e293b" stroke-width="2"/>
        <!-- Value text -->
        <text x="75" y="-28" text-anchor="middle" fill="#f8fafc" font-size="10">
            {days}d
        </text>
    </g>'''


def get_connection_monitor_html(connection_data: dict) -> str:
    """Generate connection monitoring chart HTML."""

    if not connection_data or not connection_data.get("connections"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            'border-radius: 12px; background: rgba(15, 23, 42, 0.5);'
            ">No connection data available</div>"
        )

    connections = connection_data.get("connections", []) or []

    # Calculate average and max active connections
    avg_connections = (sum(c.get("active_connections", 0) for c in connections) / len(connections)) if connections else 0
    max_connections = max((c.get("active_connections", 0) for c in connections), default=0)

    # Generate color gradient based on connection load
    conn_color = _get_connection_color(avg_connections)

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Active Connections</h3>

    <svg viewBox="0 0 800 250" style="width: 100%; height: auto; max-height: 250px;">
        <!-- Grid lines -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="250" fill="url(#grid)"/>

        <!-- Connection points -->
        {"".join(_generate_connection_point(c, i) for i, c in enumerate(connections[:12]))}

        <!-- Y-axis labels -->
        <text x="-10" y="40" text-anchor="end" fill="#64748b" font-size="10">0</text>
        <text x="-10" y="95" text-anchor="end" fill="#64748b" font-size="10">{(max_connections / 2):.0f}</text>
        <text x="-10" y="150" text-anchor="end" fill="#64748b" font-size="10">5k</text>

    </svg>

    <div style="margin-top: 12px; display: flex; gap: 16px; flex-wrap: wrap;">
        {"".join(_generate_connection_info(c, i) for i, c in enumerate(connections[:12]))}
    </div>

    <style>
        .connection-point {cursor: pointer;}
        .connection-label {fill: #94a3b8; font-size: 10px;}
    </style>
</div>"""


def _get_connection_color(avg_conns: float) -> str:
    """Generate a color based on connection load."""

    if avg_conns < 500:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    elif avg_conns < 2000:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    else:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"


def _generate_connection_point(connection: dict, index: int) -> str:
    """Generate a single connection point element."""

    conns = connection.get("active_connections", 0) or 0
    timestamp = (connection.get("checked_at") or "").replace("T", " ").split(".")[0] if connection.get("checked_at") else "-"

    y_position = min(230, max(0, conns * 1.9))

    return f'''<circle cx="{45 + index * 6}" cy="{y_position}" r="5"
        fill={_get_connection_color(conns)} stroke="#fff" stroke-width="2"
        class="connection-point">
        <title>{timestamp}: {conns} connections</title>
    </circle>'''


def _generate_connection_info(connection: dict, index: int) -> str:
    """Generate connection info badge."""

    conns = (connection.get("active_connections", 0) or 0).toFixed(2)
    timestamp = (connection.get("checked_at") or "").replace("T", " ").split(".")[0] if connection.get("checked_at") else "-"

    return f"""<div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155;
                     border-radius: 6px; padding: 8px 12px;">
        <div style="color: #f8fafc; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            title="{connection.get("name", "Connections")}">
            {timestamp}
        </div>
        <div style="color: #cbd5e1; font-size: 12px;">{conns}</div>
    </div>"""


def get_network_health_summary(network_data: dict) -> dict:
    """Generate a comprehensive health summary for network monitoring."""

    servers = network_data.get("servers", []) or []
    active_servers = [s for s in servers if s.get("last_status") == "up"]

    # Get network data from first server (or aggregate if multiple)
    total_rx = sum(s.get("network_rx", 0) for s in active_servers)
    total_tx = sum(s.get("network_tx", 0) for s in active_servers)

    # Calculate overall network health
    avg_rx_per_server = (total_rx / len(active_servers)) if active_servers else 0
    avg_tx_per_server = (total_tx / len(active_servers)) if active_servers else 0

    # Determine overall status based on multiple factors
    rx_load = min(1.0, max(0, avg_rx_per_server / 512))
    tx_load = min(1.0, max(0, avg_tx_per_server / 512))

    critical_factors = [
        any(s.get("network_error", 0) > 100 for s in active_servers),
        any(s.get("packet_loss", 0) > 1 for s in active_servers),
        any(s.get("latency_ms", 0) > 200 for s in active_servers),
    ]

    overall_status = (
        "critical" if any(critical_factors) or rx_load > 0.8 or tx_load > 0.8
        else ("warning" if rx_load > 0.5 or tx_load > 0.5 or len(active_servers) < 1)
        else "healthy"
    )

    return {
        "overall_status": overall_status,
        "total_rx": total_rx,
        "total_tx": total_tx,
        "avg_rx_per_server": avg_rx_per_server,
        "avg_tx_per_server": avg_tx_per_server,
        "active_servers": len(active_servers),
        "critical_factors": critical_factors,
    }
