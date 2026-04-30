"""Alerts Panel Component - Extracted from PyMon Dashboard"""

import json


def get_alerts_panel_html(alerts_data: dict) -> str:
    """Generate alerts panel HTML for a given set of alert data.

    Args:
        alerts_data: Dictionary containing 'alerts' list with name, severity,
                     metric, condition, threshold, etc.

    Returns:
        HTML string containing the alerts panel with Chart.js visualization
    """
    if not alerts_data.get("alerts"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            '">No alerts configured</div>'
        )

    alerts = alerts_data.get("alerts", []) or []
    active_alerts = [a for a in alerts if a.get("enabled", True)]

    return f"""<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600;">Active Alerts</h3>
        <span class="badge" style="background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%); color: white; padding: 6px 16px; border-radius: 9999px; font-size: 13px; font-weight: 500;">
            {len(active_alerts)} active
        </span>
    </div>

    <style>
        .badge {display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500; color: white;}
        .critical {background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%); }
        .warning {background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%); }
        .info {background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%); }
    </style>

    <div style="display: grid; gap: 12px;">
        {"".join(_generate_alert_card(a) for a in active_alerts)}
    </div>

    <div style="margin-top: 16px; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; display: flex; gap: 12px;">
        <span style="color: #fbbf24">⚠️</span>
        <span style="color: #cbd5e1; font-size: 13px;">Pro tip: Configure alert thresholds based on your service SLA requirements.</span>
    </div>
</div>"""


def _generate_alert_card(alert: dict) -> str:
    """Generate a single alert card element."""

    name = alert.get("name", "Unnamed Alert")[:40]
    metric = alert.get("metric", "N/A")
    condition = alert.get("condition", ">").upper()
    threshold = (
        f"{alert.get('threshold', 0):.1f}%"
        if isinstance(alert.get("threshold"), float)
        else str(alert.get("threshold", 0))
    )
    severity = alert.get("severity", "info")

    # Get color based on severity
    colors = {"critical": "#ef4444", "warning": "#f59e0b", "info": "#3b82f6", "low": "#10b981"}

    color = colors.get(severity, "#64748b")

    return f"""<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 8px;">
        <div style="flex: 1;">
            <div style="font-weight: 600; color: #f8fafc; font-size: 14px; margin-bottom: 4px;">
                {name}
            </div>
            <div style="color: #94a3b8; font-size: 12px; display: flex; gap: 8px; align-items: center;">
                <span>{metric}</span>
                <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; font-family: monospace;">
                    {condition} {threshold}
                </span>
            </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge {severity}" style="text-transform: capitalize;">{severity}</span>
            <button onclick="Alerts.delete({alert.get("id")})"
                style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;"
                title="Delete alert">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    </div>"""


def get_alerts_summary(alerts_data: dict) -> dict:
    """Generate a summary object for alerts metrics."""

    alerts = alerts_data.get("alerts", []) or []
    active_alerts = [a for a in alerts if a.get("enabled", True)]

    # Categorize by severity
    critical_count = len([a for a in active_alerts if a.get("severity") == "critical"])
    warning_count = len([a for a in active_alerts if a.get("severity") == "warning"])

    # Get metrics covered by alerts
    metrics_list = sorted(set(a.get("metric", "") for a in active_alerts))

    return {
        "total_alerts": len(alerts),
        "active_alerts": len(active_alerts),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "metrics_covered": metrics_list[:10],  # Limit to top 10
        "status": "normal" if active_alerts == [] else ("alerting" if critical_count > 3 else "warnings"),
    }


def generate_alert_rules_html() -> str:
    """Generate HTML for alert rules creation form."""

    return f"""<div style="padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; font-weight: 600; margin-bottom: 16px;">Create Alert Rule</h3>

    <div id="alert-form" class="space-y-6">
        <div>
            <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Alert Name</label>
            <input type="text" id="alert-name" placeholder="e.g., High CPU Usage Alert"
                class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all"
                style="width: 100%; padding: 12px; background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; color: #f8fafc; border-radius: 8px;">
        </div>

        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
            <div>
                <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Metric</label>
                <select id="alert-metric" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                    <option value="cpu_percent">CPU Usage (%)</option>
                    <option value="memory_percent">Memory Usage (%)</option>
                    <option value="disk_percent">Disk Usage (%)</option>
                    <option value="network_tx">Network TX (MB/s)</option>
                    <option value="network_rx">Network RX (MB/s)</option>
                </select>
            </div>

            <div>
                <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Condition</label>
                <select id="alert-condition" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                    <option value="&gt;" selected>&gt;</option>
                    <option value="&lt;">&lt;</option>
                    <option value="=&amp;gt;">&gt;=</option>
                    <option value="&lt;=">&lt;=</option>
                </select>
            </div>

            <div>
                <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Threshold (%)</label>
                <input type="number" id="alert-threshold" placeholder="e.g., 80"
                    class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all"
                    style="width: 100%; padding: 12px; background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; color: #f8fafc; border-radius: 8px;">
            </div>

            <div>
                <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Severity</label>
                <select id="alert-severity" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                    <option value="critical">Critical 🔴</option>
                    <option value="warning" selected>Warning 🟡</option>
                    <option value="info">Info 🟢</option>
                </select>
            </div>
        </div>

        <div>
            <label style="display: block; color: #94a3b8; margin-bottom: 6px; font-weight: 500;">Description (optional)</label>
            <textarea id="alert-description" rows="2" placeholder="Describe what this alert means and how to resolve it..."
                class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all resize-vertical">
            </textarea>
        </div>

        <button type="submit" id="create-alert-btn"
            style="width: 100%; padding: 12px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; transition: transform 0.2s;">
            Create Alert Rule
        </button>
    </div>

    <style>
        .space-y-6 > * {margin - bottom: 1rem; }
    </style>
</div>"""


def get_alert_rules_list_html(alerts_data: dict) -> str:
    """Generate HTML for list of alert rules."""

    alerts = alerts_data.get("alerts", []) or []
    if not alerts:
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            '">No alert rules configured</div>'
        )

    return f"""<div style="display: grid; gap: 12px;">
    {"".join(_generate_alert_rule_item(a) for a in alerts)}
</div>"""


def _generate_alert_rule_item(alert: dict) -> str:
    """Generate a single alert rule item."""

    name = alert.get("name", "Unnamed")[:40]
    metric = alert.get("metric", "N/A").replace("_", " ")
    condition = (
        f"{alert.get('condition', '>')} {alert.get('threshold', 0)}%"
        if isinstance(alert.get("threshold"), float)
        else f"{alert.get('condition', '>')} {alert.get('threshold', 0)}"
    )

    return f"""<div style="padding: 12px; border-bottom: 1px solid rgba(51,65,85,0.5); display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div style="font-weight: 600; color: #f8fafc; margin-bottom: 4px;">{name}</div>
            <div style="color: #94a3b8; font-size: 12px;">{metric} {condition}</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge" style="{_get_badge_style(alert.get("severity", "info"))};">{alert.get("severity", "info")}</span>
            <button onclick="Settings.deleteApiKey({alert.get("id")})"
                style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; padding: 4px 8px; border-radius: 4px; cursor: pointer;"
                title="Delete rule">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    </div>"""


def _get_badge_style(severity: str) -> str:
    """Get badge style based on severity."""

    styles = {
        "critical": "background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);",
        "warning": "background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);",
        "info": "background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);",
    }

    return f'style="{styles.get(severity.lower(), "background: rgba(51,65,85,0.5);")}"'


def get_alert_history_html(history_data: dict) -> str:
    """Generate HTML for alert history timeline."""

    if not history_data or not history_data.get("history"):
        return (
            '<div class="empty-state" style='
            "padding: 40px; text-align: center; color: #94a3b8;"
            "border-radius: 12px; background: rgba(15, 23, 42, 0.5);"
            '">No alert history available</div>'
        )

    history = history_data.get("history", []) or []

    return f"""<div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
    <h3 style="color: #f8fafc; font-size: 18px; margin-bottom: 16px;">Alert History</h3>

    <div style="display: flex; gap: 4px; margin-bottom: 20px;">
        {"".join(_generate_timeline_item(h) for h in history)}
    </div>

    <div style="padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; text-align: center;">
        <span style="color: #cbd5e1; font-size: 13px;">Showing last {len(history)} alerts</span>
    </div>

    <style>
        .timeline-item {padding: 8px; background: rgba(15, 23, 42, 0.6); border-radius: 6px; display: flex; align-items: center; gap: 12px; }
        .dot {width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    </style>
</div>"""


def _generate_timeline_item(item: dict) -> str:
    """Generate a single timeline item."""

    timestamp = item.get("checked_at", "").replace("T", " ").split(".")[0] if item.get("checked_at") else "-"
    status = item.get("status", "unknown")
    severity_colors = {"critical": "#ef4444", "warning": "#f59e0b", "info": "#3b82f6"}

    color = severity_colors.get(status, "#64748b")

    return f"""<div class="timeline-item">
        <span style="{_get_dot_style(color)}"></span>
        <div style="flex: 1;">
            <div style="color: #f8fafc; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                title="{item.get("name", "Alert")}">
                {item.get("name", "")[:40]}
            </div>
            <div style="color: #94a3b8; font-size: 11px;">{timestamp}</div>
        </div>
    </div>"""


def _get_dot_style(color: str) -> str:
    """Get dot style based on color."""

    return f"background: {color}; box-shadow: 0 0 8px {color};"
