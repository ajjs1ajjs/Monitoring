import os
path = 'd:/CODE/Monitoring/pymon/api/endpoints.py'
with open(path, 'r') as f:
    content = f.read()

target = 'conn.commit()\n\n        server_id = c.lastrowid'
replacement = '''conn.commit()

        # Log action
        c.execute("INSERT INTO audit_logs (username, action, target, timestamp) VALUES (?, ?, ?, ?)", 
                  (current_user.username, "Add Server", f"{data.name} ({data.host})", datetime.now(timezone.utc).isoformat()))
        conn.commit()

        server_id = c.lastrowid'''

if target in content:
    with open(path, 'w') as f:
        f.write(content.replace(target, replacement))
    print("Success")
else:
    print("Target not found")
