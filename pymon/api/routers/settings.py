import json
import os

from fastapi import APIRouter, Depends, HTTPException

from pymon.api.deps import get_db
from pymon.auth import User, get_admin_user
from pymon.notifications import build_channels, dispatcher

router = APIRouter(prefix="/settings", tags=["settings"])

# Key-name hints whose values are credential-bearing and must be redacted before
# the config is ever serialized into an API response.
_SECRET_KEY_HINTS = ("password", "pass", "token", "secret", "api_key", "webhook_url")
_REDACTED = "***REDACTED***"


def _redact_config(obj):
    """Recursively mask secret values in a parsed config structure (in place)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl == "headers":
                # Auth headers (e.g. Authorization: Bearer ...) are entirely secret.
                obj[k] = _REDACTED
            elif any(h in kl for h in _SECRET_KEY_HINTS) and isinstance(v, str) and v:
                obj[k] = _REDACTED
            else:
                _redact_config(v)
    elif isinstance(obj, list):
        for item in obj:
            _redact_config(item)
    return obj

@router.get("/notifications")
def get_notification_settings(current_user: User = Depends(get_admin_user)):
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
def save_notification_settings(data: dict, current_user: User = Depends(get_admin_user)):
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

@router.post("/notifications/test")
def test_notification_settings(current_user: User = Depends(get_admin_user)):
    conn = get_db()
    try:
        row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No notification config found")
        data = json.loads(row[0])

        channels = build_channels(data)

        if not channels:
            raise HTTPException(status_code=400, detail="No valid channels configured")

        results = dispatcher.dispatch("Test Alert", "This is a test notification from PyMon.", channels)
        successes = [k for k, v in results.items() if v]
        failures = [k for k, v in results.items() if not v]

        if not successes:
            raise HTTPException(status_code=400, detail=f"All channels failed: {failures}")

        return {"status": "ok", "success": successes, "failed": failures}
    finally:
        conn.close()

@router.get("/config/export")
def export_config(current_user: User = Depends(get_admin_user)):
    config_path = os.getenv("CONFIG_PATH", "config.yml")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=404, detail="Config file not found")
    import yaml

    # Never echo raw credentials (admin_password, smtp_pass, bot_token, webhook
    # URLs, auth headers) into an API response — redact before returning.
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Could not parse config: {e}")
    return {"content": yaml.safe_dump(_redact_config(data), sort_keys=False, allow_unicode=True)}

@router.post("/config/import-prometheus")
def import_prometheus_config(data: dict, current_user: User = Depends(get_admin_user)):
    yaml_content = data.get("yaml_content")
    if not yaml_content:
        raise HTTPException(status_code=400, detail="No YAML content provided")

    from datetime import datetime, timezone

    import yaml


    try:
        prom_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    # safe_load returns None for empty input and a scalar/list for non-mapping
    # YAML; guard before calling .get() so it's a clean 400, not a 500.
    if not isinstance(prom_data, dict):
        raise HTTPException(status_code=400, detail="Invalid Prometheus config: expected a YAML mapping")
    scrape_configs = prom_data.get("scrape_configs", [])

    # Save to DB as servers or update config.yml?
    # Better: Add to 'servers' table so they appear in UI
    conn = get_db()
    try:
        c = conn.cursor()
        count = 0
        for sc in scrape_configs:
            job_name = sc.get("job_name", "imported_job")
            static_configs = sc.get("static_configs", [])
            if not isinstance(static_configs, list):
                continue

            for static_cfg in static_configs:
                targets = static_cfg.get("targets", [])
                if not isinstance(targets, list):
                    continue

                for target in targets:
                    try:
                        t_str = str(target).strip()
                        if not t_str:
                            continue

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

                        if not host:
                            continue

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
        return {"status": "ok", "imported": count}
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()  # Print full error to server console
        raise HTTPException(status_code=500, detail=f"Помилка парсингу або імпорту: {str(e)}")
    finally:
        conn.close()
