"""Quick API test: login, then hit all section-relevant endpoints."""
import json, sys
try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError
except ImportError:
    print("FAIL: urllib not available"); sys.exit(1)

BASE = "http://localhost:10000"

def api(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urlopen(req)
        return resp.status, json.loads(resp.read().decode())
    except Exception as e:
        return getattr(e, 'code', 0), str(e)

# 1. Login
print("=== 1. LOGIN ===")
status, data = api("/api/v1/auth/login", "POST", {"username": "admin", "password": "changeme"})
if status == 200 and "access_token" in data:
    token = data["access_token"]
    print(f"  PASS: Login successful, token received")
else:
    print(f"  FAIL: Login returned {status}: {data}")
    sys.exit(1)

# 2. Dashboard HTML
print("\n=== 2. DASHBOARD HTML ===")
req = Request(f"{BASE}/dashboard/")
resp = urlopen(req)
html = resp.read().decode()
checks = {
    "section-overview": 'id="section-overview"' in html,
    "section-nodes": 'id="section-nodes"' in html,
    "section-alerts": 'id="section-alerts"' in html,
    "section-help": 'id="section-help"' in html,
    "section-logs": 'id="section-logs"' in html,
    "section-users": 'id="section-users"' in html,
    "section-settings": 'id="section-settings"' in html,
}
for name, ok in checks.items():
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")

# 3. Functions defined
print("\n=== 3. JS FUNCTIONS ===")
funcs = [
    "expandChart", "exportLogs", "clearAuditLogs", "clearMetricHistory",
    "saveSystemSettings", "saveSettings", "testNotification", "loadAuditLogs",
    "loadAlertRules", "loadSettings", "loadUsers", "showAddUserModal",
    "showEditModal", "showDeployModal", "deleteNode", "deleteAlert",
    "deleteUser", "toggleModal", "showSection", "openDrawer", "closeDrawer",
    "filterLogs", "filterNodes", "copyDeployCmd"
]
for f in funcs:
    defined = f"function {f}(" in html
    print(f"  {f}: {'PASS' if defined else 'FAIL'}")

# 4. API Endpoints
print("\n=== 4. API ENDPOINTS ===")
endpoints = [
    ("GET", "/api/v1/servers"),
    ("GET", "/api/v1/alerts"),
    ("GET", "/api/v1/audit-log?limit=10"),
    ("GET", "/api/v1/settings/notifications"),
    ("GET", "/api/v1/auth/users"),
]
for method, path in endpoints:
    status, data = api(path, method, token=token)
    print(f"  {method} {path}: {'PASS' if status == 200 else 'FAIL'} (status={status})")

# 5. Modal HTML elements
print("\n=== 5. MODAL ELEMENTS ===")
modals = ["addNodeModal", "addAlertModal", "editNodeModal", "deployModal", "addUserModal", "chartExpandModal"]
for m in modals:
    exists = f'id="{m}"' in html
    print(f"  {m}: {'PASS' if exists else 'FAIL'}")

print("\n=== SUMMARY ===")
all_sections = all(checks.values())
all_funcs = all(f"function {f}(" in html for f in funcs)
all_modals = all(f'id="{m}"' in html for m in modals)
print(f"  Sections: {'ALL PASS' if all_sections else 'SOME FAIL'}")
print(f"  Functions: {'ALL PASS' if all_funcs else 'SOME FAIL'}")
print(f"  Modals: {'ALL PASS' if all_modals else 'SOME FAIL'}")
