import asyncio
import sqlite3
import time
import aiohttp
from datetime import datetime
from pymon.api.deps import get_db

class ScrapeManager:
    """
    Scrape Manager for collecting metrics from agents
    """
    def __init__(self):
        self.interval = 15  # seconds
        self.running = False
        self._scrape_tasks = {}
        
    def start(self):
        self.running = True
        asyncio.run(self._scrape_loop())
    
    def stop(self):
        self.running = False
    
    async def _scrape_loop(self):
        """Background loop to scrape all enabled servers"""
        while self.running:
            try:
                await self.scrape_all()
                await asyncio.sleep(self.interval)
            except Exception as e:
                print(f"[ERROR] Scrape loop: {e}")
                await asyncio.sleep(10)
    
    async def scrape_all(self):
        """Scrape all configured enabled servers"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, host, port, os_type, enabled FROM servers WHERE enabled=1")
        servers = cursor.fetchall()
        
        if not servers:
            conn.close()
            return
        
        print(f"[*] ScrapeManager: Scrapping {len(servers)} servers...")
        
        # Build scrape tasks
        tasks = []
        for s in servers:
            server_id, name, host, port, os_type, enabled = s
            # Scrape the agent endpoint
            tasks.append(self.scrape_server(name, host, port, os_type))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes
            success = sum(1 for r in results if not isinstance(r, Exception))
            if success > 0:
                print(f"[*] ScrapeManager: Collected metrics from {success}/{len(servers)} servers\n")
            else:
                print(f"[*] ScrapeManager: No metrics collected, all servers unreachable\n")
        
        conn.close()

    def scrape_server(self, name: str, host: str, port: int, os_type: str):
        """Create async task for scraping a single server's agent"""
        import aiohttp
        
        async def _task():
            # Scrape agent endpoint (default port for node_exporter is 9100)
            # For custom agents, the port is configured in the server record
            agent_port = port
            scrape_url = f"http://{host}:{agent_port}/metrics"
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Set headers for common user agents
                    headers = {
                        'User-Agent': 'PyMon/1.0',
                        'Accept': 'text/plain'
                    }
                    
                    async with session.get(scrape_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            
                            # Parse Prometheus text format
                            metrics = self.parse_prometheus_metrics(text)
                            
                            if metrics:
                                # Store each metric point
                                timestamp = datetime.now().isoformat()
                                
                                for metric in metrics:
                                    # Parse metric name and value
                                    metric_name = metric['name']
                                    metric_value = metric['value']
                                    
                                    # Skip empty values
                                    if metric_value is None or metric_value == '':
                                        continue
                                    
                                    # Insert into metrics_history
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute(
                                            """INSERT OR REPLACE INTO metrics_history 
                                               (timestamp, server_id, cpu_percent, memory_percent, 
                                                disk_percent, network_rx, network_tx, disk_info)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (
                                                timestamp,
                                                0,  # Use 0 or pass server_id properly
                                                metric_value,  # Store in cpu_percent column for now
                                                0.0, 0.0, 0.0, '{"parsed": True}'
                                            )
                                        )
                                        conn.commit()
                                    except Exception as insert_err:
                                        print(f"  ✗ Error storing {metric_name}: {insert_err}")
                                
                                print(f"  ✓ {name}: {len(metrics)} metrics collected")
                                
                        elif resp.status == 503:
                            # Agent not running
                            pass
                        else:
                            print(f"    {name}: Server returned {resp.status}")
                            
            except aiohttp.ClientError as ce:
                print(f"    {name}: Network error - {type(ce).__name__}")
            except Exception as e:
                print(f"    {name}: Unexpected error - {type(e).__name__}")
        
        return _task()
    
    def parse_prometheus_metrics(self, text: str):
        """
        Parse Prometheus text format metrics
        Returns list of dict with 'name', 'value'
        """
        metrics = []
        
        for line in text.splitlines():
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse metric line
            # Example: node_cpu_cpu_seconds_total{mode="idle"} 12345.678
            parts = line.rsplit(None, 1)  # Split from the right
            if len(parts) != 2:
                continue
            
            metric_str, value_str = parts
            
            # Extract metric name (before any {)
            if '{' in metric_str:
                metric_name = metric_str.split('{')[0]
            else:
                metric_name = metric_str.strip()
            
            # Parse value (remove braces if present)
            value_str = value_str.strip('{}')
            
            try:
                value = float(value_str)
            except ValueError:
                continue
            
            # Skip internal metrics and those ending with _total
            if metric_name.endswith('_total'):
                continue
            
            # Only keep unique metric names
            unique_name = metric_name.replace('_total', '').split('_')[-1]
            
            metrics.append({
                'name': unique_name,
                'value': value
            })
        
        return metrics

# Singleton instance to be used globally
scraper = ScrapeManager()

def get_scraper():
    """Get the global scraper instance"""
    return scraper

async def start_scraper():
    """Start the scraper asynchronously"""
    scraper.start()

# Call from __main__.py after server initialization