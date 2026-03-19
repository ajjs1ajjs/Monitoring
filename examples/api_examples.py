#!/usr/bin/env python3
"""
PyMon API Examples

This script demonstrates how to use the PyMon API for:
- Authentication
- Server management
- Metrics retrieval
- Data export
- Dashboard operations

Requirements:
    pip install requests

Usage:
    python api_examples.py
"""

import json
from datetime import datetime

import requests

# Configuration
BASE_URL = "http://localhost:8090"
USERNAME = "admin"
PASSWORD = "admin"


class PyMonClient:
    """PyMon API Client"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def login(self, username=USERNAME, password=PASSWORD):
        """Authenticate and get JWT token"""
        print(f"🔐 Logging in as {username}...")

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login", json={"username": username, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print(f"✅ Login successful! Token: {self.token[:50]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False

    # ========================================================================
    # Server Management
    # ========================================================================

    def list_servers(self):
        """Get list of all servers"""
        print("\n📋 Listing all servers...")

        response = self.session.get(f"{self.base_url}/api/servers")

        if response.status_code == 200:
            servers = response.json().get("servers", [])
            print(f"✅ Found {len(servers)} servers:")
            for server in servers:
                status_icon = "🟢" if server.get("last_status") == "up" else "🔴"
                print(
                    f"   {status_icon} {server['name']} ({server['host']}:{server['agent_port']}) - {server.get('os_type')}"
                )
            return servers
        else:
            print(f"❌ Failed: {response.status_code}")
            return []

    def add_server(self, name, host, os_type="linux", agent_port=9100):
        """Add a new server"""
        print(f"\n➕ Adding server: {name}...")

        response = self.session.post(
            f"{self.base_url}/api/servers",
            json={"name": name, "host": host, "os_type": os_type, "agent_port": agent_port},
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server added with ID: {data.get('id')}")
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    def delete_server(self, server_id):
        """Delete a server"""
        print(f"\n🗑️  Deleting server {server_id}...")

        response = self.session.delete(f"{self.base_url}/api/servers/{server_id}")

        if response.status_code == 200:
            print(f"✅ Server deleted")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False

    def scrape_server(self, server_id):
        """Trigger manual scrape for a server"""
        print(f"\n🔄 Triggering scrape for server {server_id}...")

        response = self.session.post(f"{self.base_url}/api/servers/{server_id}/scrape")

        if response.status_code == 200:
            print(f"✅ Scrape triggered")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False

    # ========================================================================
    # Enhanced Dashboard APIs
    # ========================================================================

    def get_metrics_history(self, range="1h", metric=None, server_id=None):
        """Get historical metrics for charts"""
        print(f"\n📊 Getting metrics history (range={range}, metric={metric})...")

        params = {"range": range}
        if metric:
            params["metric"] = metric
        if server_id:
            params["server_id"] = server_id

        response = self.session.get(f"{self.base_url}/api/servers/metrics-history", params=params)

        if response.status_code == 200:
            data = response.json()
            labels = data.get("labels", [])
            datasets = data.get("datasets", [])
            print(f"✅ Got {len(labels)} data points, {len(datasets)} datasets")

            # Print last value from each dataset
            for ds in datasets:
                if ds.get("data"):
                    last_val = ds["data"][-1]
                    print(f"   {ds['label']}: {last_val:.1f}")

            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    def get_disk_breakdown(self, server_id):
        """Get per-disk usage for a server"""
        print(f"\n💾 Getting disk breakdown for server {server_id}...")

        response = self.session.get(f"{self.base_url}/api/servers/{server_id}/disk-breakdown")

        if response.status_code == 200:
            data = response.json()
            disks = data.get("disks", [])
            print(f"✅ Found {len(disks)} disks:")
            for disk in disks:
                percent = disk.get("percent", 0)
                color = "🟢" if percent < 60 else "🟡" if percent < 80 else "🔴"
                print(f"   {color} {disk['volume']}: {disk.get('used_gb')}GB / {disk.get('size_gb')}GB ({percent}%)")
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    def get_uptime_timeline(self, server_id, days=7):
        """Get uptime timeline for a server"""
        print(f"\n⏱️  Getting uptime timeline for server {server_id} ({days} days)...")

        response = self.session.get(f"{self.base_url}/api/servers/{server_id}/uptime-timeline", params={"days": days})

        if response.status_code == 200:
            data = response.json()
            uptime = data.get("uptime_percent", 0)
            timeline = data.get("timeline", [])

            # Count incidents
            incidents = 0
            for i in range(1, len(timeline)):
                if timeline[i]["status"] == "down" and timeline[i - 1]["status"] == "up":
                    incidents += 1

            color = "🟢" if uptime >= 99 else "🟡" if uptime >= 95 else "🔴"
            print(f"✅ Uptime: {color} {uptime}% ({incidents} incidents in {days} days)")
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    def export_data(self, server_id, format="json", range="24h"):
        """Export server metrics data"""
        print(f"\n📤 Exporting data for server {server_id} (format={format}, range={range})...")

        response = self.session.get(
            f"{self.base_url}/api/servers/{server_id}/export", params={"format": format, "range": range}
        )

        if response.status_code == 200:
            if format == "json":
                data = response.json()
                records = data.get("data", [])
                print(f"✅ Exported {len(records)} records")
                return data
            else:
                # CSV
                filename = f"server_{server_id}_{range}.{format}"
                with open(filename, "w") as f:
                    f.write(response.text)
                print(f"✅ Exported to {filename}")
                return response.text
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    def compare_ranges(self, metric="cpu", range="1h", server_id=None):
        """Compare current vs previous period"""
        print(f"\n📈 Comparing {metric} metrics (range={range})...")

        params = {"metric": metric, "range": range}
        if server_id:
            params["server_id"] = server_id

        response = self.session.get(f"{self.base_url}/api/servers/compare", params=params)

        if response.status_code == 200:
            data = response.json()
            current = data.get("current", 0)
            previous = data.get("previous", 0)
            delta = data.get("delta", 0)
            delta_percent = data.get("delta_percent", 0)
            trend = data.get("trend", "stable")

            trend_icon = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"
            print(f"✅ {trend_icon} Current: {current}, Previous: {previous}")
            print(f"   Delta: {delta:+.2f} ({delta_percent:+.2f}%)")
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None

    # ========================================================================
    # Health & System
    # ========================================================================

    def health_check(self):
        """Check API health"""
        print("\n🏥 Checking API health...")

        response = self.session.get(f"{self.base_url}/api/health")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status')}")
            return data
        else:
            print(f"❌ Failed: {response.status_code}")
            return None


def main():
    """Main demonstration function"""
    print("=" * 60)
    print("PyMon API Examples")
    print("=" * 60)

    # Initialize client
    client = PyMonClient()

    # Login
    if not client.login():
        print("Failed to login. Exiting.")
        return

    # Health check
    client.health_check()

    # List servers
    servers = client.list_servers()

    if servers:
        server_id = servers[0]["id"]

        # Get metrics history
        client.get_metrics_history(range="1h", metric="cpu")
        client.get_metrics_history(range="1h")  # All metrics

        # Get disk breakdown
        client.get_disk_breakdown(server_id)

        # Get uptime timeline
        client.get_uptime_timeline(server_id, days=7)

        # Export data
        client.export_data(server_id, format="json", range="24h")
        # client.export_data(server_id, format="csv", range="24h")

        # Compare ranges
        client.compare_ranges(metric="cpu", range="1h")
        client.compare_ranges(metric="memory", range="6h")

    # Add a test server (commented out by default)
    # client.add_server("Test Server", "192.168.1.200", os_type="linux")

    # Delete a test server (commented out by default)
    # client.delete_server(999)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
