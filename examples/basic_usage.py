#!/usr/bin/env python3
"""
PyMon Basic Usage Examples

This script shows how to:
- Monitor servers
- Check metrics
- Create alerts
- Export reports

Requirements:
    pip install requests

Usage:
    python basic_usage.py
"""

import time
from datetime import datetime

import requests

BASE_URL = "http://localhost:8090"
USERNAME = "admin"
PASSWORD = "admin"


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def get_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def example_1_list_servers(token):
    """Example 1: List all servers"""
    print_header("Example 1: List All Servers")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/servers", headers=headers)

    if response.status_code == 200:
        servers = response.json().get("servers", [])

        if not servers:
            print("No servers configured yet.")
            return []

        print(f"Total servers: {len(servers)}\n")

        for i, server in enumerate(servers, 1):
            status = "🟢 UP" if server.get("last_status") == "up" else "🔴 DOWN"
            print(f"{i}. {server['name']}")
            print(f"   Host: {server['host']}:{server['agent_port']}")
            print(f"   OS: {server['os_type']}")
            print(f"   Status: {status}")
            print(f"   CPU: {server.get('cpu_percent', 0):.1f}%")
            print(f"   Memory: {server.get('memory_percent', 0):.1f}%")
            print(f"   Disk: {server.get('disk_percent', 0):.1f}%")
            print()

        return servers
    else:
        print(f"Error: {response.status_code}")
        return []


def example_2_get_metrics(token, server_id):
    """Example 2: Get historical metrics"""
    print_header("Example 2: Get Historical Metrics")

    headers = {"Authorization": f"Bearer {token}"}

    # Get CPU history
    print("CPU Usage (last hour):")
    response = requests.get(
        f"{BASE_URL}/api/servers/metrics-history", headers=headers, params={"range": "1h", "metric": "cpu"}
    )

    if response.status_code == 200:
        data = response.json()
        labels = data.get("labels", [])
        datasets = data.get("datasets", [])

        if datasets:
            values = datasets[0].get("data", [])
            avg = sum(values) / len(values) if values else 0
            min_val = min(values) if values else 0
            max_val = max(values) if values else 0

            print(f"  Data points: {len(values)}")
            print(f"  Average: {avg:.1f}%")
            print(f"  Min: {min_val:.1f}%")
            print(f"  Max: {max_val:.1f}%")
    else:
        print("  No data available")


def example_3_disk_breakdown(token, server_id):
    """Example 3: Get disk breakdown"""
    print_header("Example 3: Disk Breakdown")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/servers/{server_id}/disk-breakdown", headers=headers)

    if response.status_code == 200:
        data = response.json()
        disks = data.get("disks", [])

        if not disks:
            print("No disk data available")
            return

        for disk in disks:
            volume = disk.get("volume", "Unknown")
            percent = disk.get("percent", 0)
            used = disk.get("used_gb", 0)
            total = disk.get("size_gb", 0)

            # Color code
            if percent < 60:
                status = "🟢 OK"
            elif percent < 80:
                status = "🟡 Warning"
            else:
                status = "🔴 Critical"

            print(f"  {volume}: {used}GB / {total}GB ({percent}%) - {status}")
    else:
        print("Error getting disk data")


def example_4_uptime(token, server_id):
    """Example 4: Get uptime information"""
    print_header("Example 4: Uptime Timeline")

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/servers/{server_id}/uptime-timeline", headers=headers, params={"days": 7})

    if response.status_code == 200:
        data = response.json()
        uptime = data.get("uptime_percent", 0)
        timeline = data.get("timeline", [])

        # Count incidents
        incidents = sum(
            1 for i in range(1, len(timeline)) if timeline[i]["status"] == "down" and timeline[i - 1]["status"] == "up"
        )

        # Color code
        if uptime >= 99:
            status = "🟢 Excellent"
        elif uptime >= 95:
            status = "🟡 Good"
        else:
            status = "🔴 Poor"

        print(f"  Uptime (7 days): {uptime}% - {status}")
        print(f"  Incidents: {incidents}")
        print(f"  Data points: {len(timeline)}")
    else:
        print("Error getting uptime data")


def example_5_export_data(token, server_id):
    """Example 5: Export metrics data"""
    print_header("Example 5: Export Data")

    headers = {"Authorization": f"Bearer {token}"}

    # Export as JSON
    response = requests.get(
        f"{BASE_URL}/api/servers/{server_id}/export", headers=headers, params={"format": "json", "range": "24h"}
    )

    if response.status_code == 200:
        data = response.json()
        records = data.get("data", [])
        print(f"  Exported {len(records)} records (JSON)")

        if records:
            print(f"  First record: {records[0]}")
            print(f"  Last record: {records[-1]}")
    else:
        print("Error exporting data")


def example_6_compare(token, server_id=None):
    """Example 6: Compare time ranges"""
    print_header("Example 6: Time Range Comparison")

    headers = {"Authorization": f"Bearer {token}"}

    metrics = ["cpu", "memory", "disk"]

    for metric in metrics:
        response = requests.get(
            f"{BASE_URL}/api/servers/compare",
            headers=headers,
            params={"metric": metric, "range": "1h", "server_id": server_id},
        )

        if response.status_code == 200:
            data = response.json()
            current = data.get("current", 0)
            previous = data.get("previous", 0)
            delta = data.get("delta", 0)
            trend = data.get("trend", "stable")

            trend_icon = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"

            print(f"  {metric.upper()}: {current:.1f} (prev: {previous:.1f}) {trend_icon} {delta:+.1f}")
        else:
            print(f"  {metric.upper()}: No data")


def main():
    """Main function"""
    print("\n" + "█" * 60)
    print(" PyMon Basic Usage Examples")
    print("█" * 60)
    print(f"\nConnecting to: {BASE_URL}")
    print(f"User: {USERNAME}")

    # Get token
    print("\n🔐 Authenticating...")
    token = get_token()

    if not token:
        print("❌ Authentication failed! Check credentials.")
        return

    print("✅ Authentication successful!")

    # Run examples
    servers = example_1_list_servers(token)

    if servers:
        server_id = servers[0]["id"]

        example_2_get_metrics(token, server_id)
        example_3_disk_breakdown(token, server_id)
        example_4_uptime(token, server_id)
        example_5_export_data(token, server_id)
        example_6_compare(token, server_id)
    else:
        print("\n⚠️  No servers configured. Add a server first!")
        print("\nTo add a server via API:")
        print("""
    import requests

    token = "your_token_here"
    headers = {"Authorization": f"Bearer {token}"}

    requests.post(
        "http://localhost:8090/api/servers",
        headers=headers,
        json={
            "name": "My Server",
            "host": "192.168.1.100",
            "os_type": "linux",
            "agent_port": 9100
        }
    )
        """)

    print("\n" + "█" * 60)
    print(" Examples completed!")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
