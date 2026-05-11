import os
import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pymon.auth import User, get_current_user
from pymon.api.deps import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/notifications")
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        # Check if notifications table has a unified config or per-channel
        # The frontend expects a single object for all channels based on the saveSettings JS
        row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
        if row:
            return json.loads(row[0])
        
        # Fallback: if they are per-channel, we might need to aggregate
        rows = conn.execute("SELECT * FROM notifications").fetchall()
        config = {"enabled": True}
        for r in rows:
            if r['config']:
                cfg = json.loads(r['config'])
                config.update(cfg)
            config[f"{r['channel']}_enabled"] = bool(r['enabled'])
        return config
    finally:
        conn.close()

@router.post("/notifications")
async def save_notification_settings(data: dict, current_user: User = Depends(get_current_user)):
    conn = get_db()
    try:
        # Save as a single 'all' record for simplicity as expected by dashboard
        config_json = json.dumps(data)
        conn.execute("INSERT OR REPLACE INTO notifications (channel, enabled, config) VALUES (?, ?, ?)",
                    ('all', int(data.get('enabled', True)), config_json))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

@router.get("/config/export")
async def export_config(current_user: User = Depends(get_current_user)):
    config_path = os.getenv("CONFIG_PATH", "config.yml")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(config_path, 'r') as f:
        return {"content": f.read()}

@router.post("/config/import-prometheus")
async def import_prometheus_config(data: dict, current_user: User = Depends(get_current_user)):
    yaml_content = data.get("yaml_content")
    if not yaml_content:
        raise HTTPException(status_code=400, detail="No YAML content provided")
    
    import yaml
    from datetime import datetime, timezone
    from pymon.config import load_config
    
    try:
        prom_data = yaml.safe_load(yaml_content)
        scrape_configs = prom_data.get("scrape_configs", [])
        
        # Save to DB as servers or update config.yml? 
        # Better: Add to 'servers' table so they appear in UI
        conn = get_db()
        c = conn.cursor()
        count = 0
        for sc in scrape_configs:
            job_name = sc.get("job_name", "imported_job")
            static_configs = sc.get("static_configs", [])
            if not isinstance(static_configs, list): continue

            for static_cfg in static_configs:
                targets = static_cfg.get("targets", [])
                if not isinstance(targets, list): continue
                
                for target in targets:
                    try:
                        t_str = str(target).strip()
                        if not t_str: continue

                        # Check if it's a URL (for Services)
                        if t_str.startswith(('http://', 'https://')):
                            # This is a service
                            exists_srv = c.execute("SELECT 1 FROM services WHERE target_url = ?", (t_str,)).fetchone()
                            if not exists_srv:
                                svc_name = job_name if job_name != 'blackbox' else t_str
                                c.execute("INSERT INTO services (name, target_url, check_type, interval, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                         (svc_name, t_str, 'http', 60, 1, datetime.now(timezone.utc).isoformat()))
                                count += 1
                            continue
                        
                        # Handle Servers (host:port)
                        host = t_str
                        port = 9182 # Default
                        
                        if ':' in t_str:
                            parts = t_str.rsplit(':', 1)
                            # Only treat as port if the part after : is numeric
                            if parts[1].isdigit():
                                host = parts[0].strip('[] ')
                                port = int(parts[1])
                            else:
                                host = t_str.strip('[] ')
                        else:
                            host = t_str.strip('[] ')
                        
                        if not host: continue

                        # Auto-detect OS based on port
                        os_type = 'linux'
                        if port in [9182, 1030, 1035]:
                            os_type = 'windows'
                        elif port == 9100:
                            os_type = 'linux'

                        # Check if exists (Servers)
                        existing = c.execute("SELECT id FROM servers WHERE host = ? AND agent_port = ?", (host, port)).fetchone()
                        if not existing:
                            c.execute("INSERT INTO servers (name, host, agent_port, os_type, enabled, server_group, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                     (job_name, host, port, os_type, 1, "Imported", datetime.now(timezone.utc).isoformat()))
                            count += 1
                        else:
                            # Update existing server group and OS type
                            c.execute("UPDATE servers SET os_type = ?, server_group = ? WHERE id = ?", (os_type, job_name, existing['id']))
                    except Exception as e:
                        print(f"Import error for target {target}: {e}")
                        continue
        conn.commit()
        conn.close()
        return {"status": "ok", "imported": count}
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full error to server console
        raise HTTPException(status_code=500, detail=f"Помилка парсингу або імпорту: {str(e)}")
