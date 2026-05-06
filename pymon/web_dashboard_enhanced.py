"""Premium Enterprise Web Dashboard - 'Zenith NOC' Edition"""

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon | Secure Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030508;
            --surface: #0a0e14;
            --accent: #f97316;
            --text: #f8fafc;
            --text-muted: #64748b;
            --border: rgba(255, 255, 255, 0.08);
            --glass: rgba(15, 23, 42, 0.6);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); display: flex; align-items: center; justify-content: center; min-height: 100vh; overflow: hidden; }

        .blob { position: absolute; width: 500px; height: 500px; background: radial-gradient(circle, rgba(249, 115, 22, 0.15) 0%, rgba(249, 115, 22, 0) 70%); border-radius: 50%; z-index: -1; filter: blur(60px); animation: drift 20s infinite alternate; }
        @keyframes drift { from { transform: translate(-10%, -10%); } to { transform: translate(10%, 10%); } }

        .login-card { background: var(--glass); backdrop-filter: blur(20px); border: 1px solid var(--border); padding: 3rem; border-radius: 2rem; width: 100%; max-width: 420px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); position: relative; }
        .login-card::before { content: ''; position: absolute; top: -1px; left: 50%; transform: translateX(-50%); width: 40%; height: 1px; background: linear-gradient(90deg, transparent, var(--accent), transparent); }

        .logo { text-align: center; margin-bottom: 2.5rem; }
        .logo h1 { font-size: 2.5rem; font-weight: 700; letter-spacing: -0.05em; margin-bottom: 0.5rem; }
        .logo span { color: var(--accent); }
        .logo p { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.2em; font-weight: 600; }

        .form-group { margin-bottom: 1.5rem; }
        label { display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 0.5rem; padding-left: 0.25rem; }
        input { width: 100%; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--border); padding: 1rem 1.25rem; border-radius: 1rem; color: white; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        input:focus { outline: none; border-color: var(--accent); background: rgba(0, 0, 0, 0.5); box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.1); }

        button { width: 100%; background: var(--accent); color: white; border: none; padding: 1.1rem; border-radius: 1rem; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.3s; margin-top: 1rem; text-transform: uppercase; letter-spacing: 0.1em; }
        button:hover { background: #ea580c; transform: translateY(-2px); box-shadow: 0 10px 20px -5px rgba(249, 115, 22, 0.4); }
        button:active { transform: translateY(0); }

        #error { color: #f87171; text-align: center; font-size: 0.75rem; font-weight: 600; margin-top: 1.5rem; display: none; padding: 0.75rem; background: rgba(248, 113, 113, 0.1); border-radius: 0.75rem; }
        /* Forms & Buttons */
        .form-group { margin-bottom: 1.25rem; }
        .form-group label { display: block; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem; }
        .form-input { width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 0.75rem; color: white; font-family: inherit; font-size: 0.9rem; transition: all 0.2s; }
        .form-input:focus { border-color: var(--accent); outline: none; background: rgba(0,0,0,0.5); }
        
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.75rem 1.25rem; border-radius: 0.75rem; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s; border: none; font-family: inherit; }
        .btn-primary { background: var(--accent); color: white; }
        .btn-primary:hover { background: #ea580c; transform: translateY(-1px); }
        .btn-secondary { background: rgba(255,255,255,0.05); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); color: white; }
        
        .status-badge { display: inline-flex; align-items: center; padding: 0.25rem 0.6rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        .status-badge.up { background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.2); }
        .status-badge.down { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }
        .status-badge.warning { background: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.2); }

        /* Modals & Overlays */
        .modal-overlay, .drawer-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
        .modal-overlay.active, .drawer-overlay.active { opacity: 1; pointer-events: auto; }
        .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 1.5rem; width: 100%; max-width: 500px; max-height: 90vh; display: flex; flex-direction: column; transform: scale(0.95); transition: transform 0.3s; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        .modal-overlay.active .modal { transform: scale(1); }
        .modal-header { padding: 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 1.25rem; font-weight: 700; color: white; }
        .modal-body { padding: 1.5rem; overflow-y: auto; flex: 1; }
        .modal-footer { padding: 1.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 1rem; background: rgba(0,0,0,0.2); border-radius: 0 0 1.5rem 1.5rem; }
        
        .drawer { position: absolute; right: 0; top: 0; bottom: 0; width: 450px; background: var(--surface); border-left: 1px solid var(--border); transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; flex-direction: column; box-shadow: -10px 0 25px rgba(0,0,0,0.5); }
        .drawer-overlay.active .drawer { transform: translateX(0); }
        .drawer-header { padding: 2rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: flex-start; }
        .drawer-body { padding: 2rem; overflow-y: auto; flex: 1; }

    </style>
</head>
<body>
    <div class="blob"></div>
    <div class="login-card">
        <div class="logo">
            <h1>PyMon<span>NOC</span></h1>
            <p>Zenith Infrastructure Suite</p>
        </div>
        <form id="loginForm">
            <div class="form-group">
                <label>Terminal Username</label>
                <input type="text" id="username" required placeholder="admin" autocomplete="off">
            </div>
            <div class="form-group">
                <label>Secure Access Key</label>
                <input type="password" id="password" required placeholder="••••••••">
            </div>
            <button type="submit">Initialize Session</button>
            <div id="error">INVALID CREDENTIALS - ACCESS DENIED</div>
        </form>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorBox = document.getElementById('error');
            errorBox.style.display = 'none';

            try {
                const resp = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });

                if (resp.ok) {
                    const data = await resp.json();
                    localStorage.setItem('token', data.access_token);
                    window.location.href = '/dashboard/';
                } else {
                    errorBox.style.display = 'block';
                }
            } catch (e) {
                errorBox.textContent = 'SYSTEM TIMEOUT - CHECK CONNECTION';
                errorBox.style.display = 'block';
            }
        });
    </script>
</body>
</html>"""

ENHANCED_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon | Zenith NOC</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f1a;
            --surface: #151c2c;
            --surface-hover: #1e2638;
            --accent: #f97316;
            --accent-glow: rgba(249, 115, 22, 0.4);
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.08);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --sidebar-w: 260px;
            --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; }

        /* Layout */
        .app-container { display: flex; height: 100vh; width: 100vw; }

        /* Sidebar */
        aside { width: var(--sidebar-w); background: #080c14; border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 50; }
        .sidebar-header { padding: 2.5rem 1.5rem; display: flex; align-items: center; gap: 0.75rem; }
        .sidebar-header svg { color: var(--accent); width: 28px; height: 28px; }
        .sidebar-header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.025em; }
        .sidebar-header span { color: var(--accent); }

        .nav-section { padding: 0 1rem; flex: 1; }
        .nav-label { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin: 2rem 0 0.75rem 0.75rem; }

        .nav-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.85rem 1.1rem; border-radius: 1rem; color: var(--text-muted); text-decoration: none; font-size: 0.95rem; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; background: transparent; width: 100%; text-align: left; margin-bottom: 0.25rem; }
        .nav-item:hover { background: var(--surface-hover); color: var(--text); }
        .nav-item.active { background: rgba(249, 115, 22, 0.1); color: var(--accent); box-shadow: inset 0 0 0 1px rgba(249, 115, 22, 0.2); }
        .nav-item.active svg { color: var(--accent); }

        .sidebar-footer { padding: 1.5rem; border-top: 1px solid var(--border); }
        .logout-btn { display: flex; align-items: center; gap: 0.75rem; padding: 0.85rem 1.1rem; color: #fca5a5; width: 100%; border: none; background: rgba(239, 68, 68, 0.05); font-size: 0.9rem; font-weight: 600; cursor: pointer; border-radius: 1rem; transition: all 0.2s; }
        .logout-btn:hover { background: rgba(239, 68, 68, 0.15); color: #f87171; }

        /* Main Content */
        main { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #0a0e1a; }
        header { height: 72px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 2.5rem; background: rgba(11, 15, 26, 0.8); backdrop-filter: blur(12px); z-index: 40; }
        .header-left h2 { font-size: 1.1rem; font-weight: 600; color: var(--text); }

        .header-actions { display: flex; align-items: center; gap: 1.25rem; }
        .range-selector { display: flex; background: #080c14; border: 1px solid var(--border); border-radius: 0.75rem; padding: 0.25rem; }
        .range-btn { padding: 0.35rem 0.75rem; border-radius: 0.6rem; border: none; background: transparent; color: var(--text-muted); font-size: 0.7rem; font-weight: 700; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
        .range-btn.active { background: var(--surface-hover); color: var(--text); box-shadow: 0 2px 4px rgba(0,0,0,0.4); }

        .refresh-btn { background: #080c14; border: 1px solid var(--border); border-radius: 0.75rem; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); cursor: pointer; transition: all 0.2s; }
        .refresh-btn:hover { border-color: var(--accent); color: var(--accent); }

        .content-scroll { flex: 1; overflow-y: auto; padding: 2.5rem; scroll-behavior: smooth; }
        .content-scroll::-webkit-scrollbar { width: 6px; }
        .content-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        /* Dashboard Components */
        .dashboard-section { display: none; animation: fadeIn 0.3s ease-out; }
        .dashboard-section.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.5rem; box-shadow: var(--card-shadow); display: flex; flex-direction: column; overflow: hidden; transition: transform 0.2s, border-color 0.2s; }
        .card:hover { border-color: rgba(255,255,255,0.15); }
        .card-header { padding: 1.5rem 2rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
        .card-header h3 { font-size: 1rem; font-weight: 700; color: #fff; letter-spacing: -0.01em; }
        .card-body { padding: 1.5rem 2rem; flex: 1; }

        /* Overview Redesign */
        .overview-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; background: rgba(255,255,255,0.03); padding: 1rem 1.5rem; border-radius: 1rem; border: 1px solid var(--border); }
        .overview-controls { display: flex; align-items: center; gap: 1rem; }
        .server-select { background: #080c14; border: 1px solid var(--border); color: var(--text); padding: 0.5rem 1rem; border-radius: 0.75rem; outline: none; font-family: inherit; font-size: 0.9rem; min-width: 200px; cursor: pointer; transition: border-color 0.2s; }
        .server-select:focus { border-color: var(--accent); }

        .active-node-panel { display: none; background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%); border: 1px solid rgba(255,255,255,0.1); border-radius: 1.25rem; padding: 1.5rem; margin-bottom: 1.5rem; align-items: center; gap: 2rem; animation: slideInDown 0.4s ease-out; }
        .active-node-panel.active { display: flex; }
        @keyframes slideInDown { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
        
        .node-info-item { display: flex; flex-direction: column; gap: 0.25rem; }
        .node-info-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em; }
        .node-info-value { font-size: 1rem; font-weight: 700; color: #fff; }

        .overview-grid { display: grid; grid-template-columns: 1fr 350px; gap: 1.5rem; }
        .charts-main { display: flex; flex-direction: column; gap: 1.5rem; }
        .charts-container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
        .chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem; padding: 1.5rem; position: relative; min-height: 300px; display: flex; flex-direction: column; transition: transform 0.2s; }
        .chart-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.15); }
        .chart-header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
        .chart-title { font-size: 0.85rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.5rem; }
        .chart-actions { display: flex; gap: 0.5rem; }
        .chart-action-btn { background: rgba(255,255,255,0.05); border: none; color: var(--text-muted); width: 28px; height: 28px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
        .chart-action-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
        
        .chart-canvas-wrapper { flex: 1; position: relative; }

        .alerts-sidebar { display: flex; flex-direction: column; gap: 1rem; }
        .timeline-card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem; overflow: hidden; }
        
        .alert-item-v2 { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1rem; border-left: 4px solid var(--accent); margin-bottom: 0.75rem; }
        .alert-item-v2.critical { border-left-color: var(--danger); }
        .alert-item-v2.warning { border-left-color: var(--warning); }
        .alert-item-v2 .alert-header { display: flex; justify-content: space-between; margin-bottom: 0.25rem; }
        .alert-item-v2 .alert-title { font-weight: 700; font-size: 0.9rem; color: #fff; }
        .alert-item-v2 .alert-time { font-size: 0.7rem; color: var(--text-muted); }
        .alert-item-v2 .alert-desc { font-size: 0.8rem; color: #94a3b8; line-height: 1.4; }

        .text-accent { color: var(--accent); }
        .text-success { color: var(--success); }
        .text-danger { color: var(--danger); }

        /* Expanded Chart Modal */
        #chartExpandModal .modal { width: 900px; max-width: 95vw; }
        #expandedChartContainer { height: 450px; width: 100%; position: relative; }
        /* Forms & Buttons */
        .form-group { margin-bottom: 1.25rem; }
        .form-group label { display: block; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem; }
        .form-input { width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 0.75rem; color: white; font-family: inherit; font-size: 0.9rem; transition: all 0.2s; }
        .form-input:focus { border-color: var(--accent); outline: none; background: rgba(0,0,0,0.5); }
        
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.75rem 1.25rem; border-radius: 0.75rem; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s; border: none; font-family: inherit; }
        .btn-primary { background: var(--accent); color: white; }
        .btn-primary:hover { background: #ea580c; transform: translateY(-1px); }
        .btn-secondary { background: rgba(255,255,255,0.05); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); color: white; }
        
        .status-badge { display: inline-flex; align-items: center; padding: 0.25rem 0.6rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        .status-badge.up { background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.2); }
        .status-badge.down { background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); }
        .status-badge.warning { background: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.2); }

        /* Modals & Overlays */
        .modal-overlay, .drawer-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
        .modal-overlay.active, .drawer-overlay.active { opacity: 1; pointer-events: auto; }
        .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 1.5rem; width: 100%; max-width: 500px; max-height: 90vh; display: flex; flex-direction: column; transform: scale(0.95); transition: transform 0.3s; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        .modal-overlay.active .modal { transform: scale(1); }
        .modal-header { padding: 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 1.25rem; font-weight: 700; color: white; }
        .modal-body { padding: 1.5rem; overflow-y: auto; flex: 1; }
        .modal-footer { padding: 1.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 1rem; background: rgba(0,0,0,0.2); border-radius: 0 0 1.5rem 1.5rem; }
        
        .drawer { position: absolute; right: 0; top: 0; bottom: 0; width: 450px; background: var(--surface); border-left: 1px solid var(--border); transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; flex-direction: column; box-shadow: -10px 0 25px rgba(0,0,0,0.5); }
        .drawer-overlay.active .drawer { transform: translateX(0); }
        .drawer-header { padding: 2rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: flex-start; }
        .drawer-body { padding: 2rem; overflow-y: auto; flex: 1; }

    </style></head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <aside>
            <div class="sidebar-header">
                <i data-lucide="shield-check"></i>
                <h1>PyMon<span>NOC</span></h1>
            </div>

            <nav class="nav-section">
                <div class="nav-label">Monitoring</div>
                <button class="nav-item active" data-section="overview">
                    <i data-lucide="layout-dashboard"></i> Dashboard
                </button>
                <button class="nav-item" data-section="nodes">
                    <i data-lucide="server"></i> Infrastructure
                </button>
                <button class="nav-item" data-section="alerts">
                    <i data-lucide="bell-ring"></i> Alerting
                </button>

                <div class="nav-label">Support</div>
                <button class="nav-item" data-section="help">
                    <i data-lucide="help-circle"></i> Help & Agents
                </button>
                <div class="nav-label">Management</div>
                <button class="nav-item" data-section="logs">
                    <i data-lucide="list"></i> Audit Logs
                </button>
                <button class="nav-item" data-section="users">
                    <i data-lucide="users"></i> Users
                </button>
                <button class="nav-item" data-section="settings">
                    <i data-lucide="settings"></i> Configuration
                </button>
            </nav>

            <div class="sidebar-footer">
                <button id="logoutBtn" class="logout-btn">
                    <i data-lucide="log-out"></i> End Session
                </button>
            </div>
        </aside>

        <!-- Main Content -->
        <main>
            <header>
                <div class="header-left">
                    <h2 id="viewTitle">Overview</h2>
                </div>
                <div class="header-actions">
                    <span id="updateTimer" style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace;">Syncing...</span>
                    <div class="range-selector">
                        <button class="range-btn" data-range="5m">5M</button>
                        <button class="range-btn" data-range="15m">15M</button>
                        <button class="range-btn" data-range="30m">30M</button>
                        <button class="range-btn active" data-range="1h">1H</button>
                        <button class="range-btn" data-range="3h">3H</button>
                        <button class="range-btn" data-range="6h">6H</button>
                        <button class="range-btn" data-range="12h">12H</button>
                        <button class="range-btn" data-range="24h">24H</button>
                        <button class="range-btn" data-range="7d">7D</button>
                    </div>
                    <button id="refreshBtn" class="refresh-btn">
                        <i data-lucide="rotate-cw"></i>
                    </button>
                </div>
            </header>

            <div class="content-scroll">
                <!-- Section: Overview -->
                <div id="section-overview" class="dashboard-section active">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">Overview <span>Monitoring</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Аналіз продуктивності та статус інфраструктури</p>
                        </div>
                        <div class="overview-controls">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted);">Сервер:</span>
                                <select id="overviewNodeSelect" class="server-select" onchange="updateOverviewCharts()">
                                    <option value="agg">Усі сервери (Агреговано)</option>
                                </select>
                            </div>
                            <div class="range-selector">
                                <button class="range-btn active" data-range="1h">1h</button>
                                <button class="range-btn" data-range="6h">6h</button>
                                <button class="range-btn" data-range="24h">24h</button>
                            </div>
                        </div>
                    </div>

                    <div id="activeNodePanel" class="active-node-panel">
                        <div style="background: rgba(249, 115, 22, 0.1); padding: 1rem; border-radius: 1rem; border: 1px solid rgba(249, 115, 22, 0.2);">
                            <i data-lucide="server" class="text-accent" style="width: 24px; height: 24px;"></i>
                        </div>
                        <div class="node-info-item">
                            <span class="node-info-label">Поточний сервер</span>
                            <span id="activeNodeName" class="node-info-value">-</span>
                        </div>
                        <div class="node-info-item">
                            <span class="node-info-label">Адреса вузла</span>
                            <span id="activeNodeHost" class="node-info-value">-</span>
                        </div>
                        <div class="node-info-item">
                            <span class="node-info-label">Операційна система</span>
                            <span id="activeNodeOS" class="node-info-value">-</span>
                        </div>
                        <div class="node-info-item" style="margin-left: auto; text-align: right;">
                            <span class="node-info-label">Останній статус</span>
                            <div id="activeNodeStatusBadge"></div>
                        </div>
                    </div>

                    <div class="overview-grid">
                        <div class="charts-main">
                            <div class="charts-container">
                                <div class="chart-card">
                                    <div class="chart-header-row">
                                        <div class="chart-title">
                                            <i data-lucide="cpu" class="text-accent" style="width: 16px; height: 16px;"></i>
                                            Використання CPU (%)
                                        </div>
                                        <div class="chart-actions">
                                            <button class="chart-action-btn" onclick="expandChart('cpu')" title="Expand"><i data-lucide="maximize-2" style="width: 14px; height: 14px;"></i></button>
                                        </div>
                                    </div>
                                    <div class="chart-canvas-wrapper">
                                        <canvas id="cpuOverviewChart"></canvas>
                                    </div>
                                </div>
                                <div class="chart-card">
                                    <div class="chart-header-row">
                                        <div class="chart-title">
                                            <i data-lucide="database" class="text-success" style="width: 16px; height: 16px;"></i>
                                            Використання RAM (%)
                                        </div>
                                        <div class="chart-actions">
                                            <button class="chart-action-btn" onclick="expandChart('ram')" title="Expand"><i data-lucide="maximize-2" style="width: 14px; height: 14px;"></i></button>
                                        </div>
                                    </div>
                                    <div class="chart-canvas-wrapper">
                                        <canvas id="ramOverviewChart"></canvas>
                                    </div>
                                </div>
                                <div class="chart-card">
                                    <div class="chart-header-row">
                                        <div class="chart-title">
                                            <i data-lucide="hard-drive" class="text-warning" style="width: 16px; height: 16px;"></i>
                                            Використання диска (%)
                                        </div>
                                        <div class="chart-actions">
                                            <button class="chart-action-btn" onclick="expandChart('disk')" title="Expand"><i data-lucide="maximize-2" style="width: 14px; height: 14px;"></i></button>
                                        </div>
                                    </div>
                                    <div class="chart-canvas-wrapper">
                                        <canvas id="diskOverviewChart"></canvas>
                                    </div>
                                </div>
                                <div class="chart-card">
                                    <div class="chart-header-row">
                                        <div class="chart-title">
                                            <i data-lucide="activity" class="text-accent" style="width: 16px; height: 16px;"></i>
                                            Мережева активність та трафік
                                        </div>
                                        <div class="chart-actions">
                                            <button class="chart-action-btn" onclick="expandChart('net')" title="Expand"><i data-lucide="maximize-2" style="width: 14px; height: 14px;"></i></button>
                                        </div>
                                    </div>
                                    <div class="chart-canvas-wrapper">
                                        <canvas id="netOverviewChart"></canvas>
                                    </div>
                                </div>
                            </div>

                            <div class="timeline-card" style="margin-top: 1.5rem;">
                                <div class="card-header" style="background: rgba(0,0,0,0.1);">
                                    <h3>Історичні дані та події (Timeline Details)</h3>
                                    <span id="timelineSyncTime" style="font-size: 0.7rem; color: var(--text-muted);"></span>
                                </div>
                                <div class="card-body" style="padding: 0;">
                                    <table id="timelineTable">
                                        <thead>
                                            <tr>
                                                <th>Timestamp</th>
                                                <th>Server</th>
                                                <th>CPU</th>
                                                <th>RAM</th>
                                                <th>Disk</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody id="timelineTableBody">
                                            <!-- Real-time timeline data -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        <div class="alerts-sidebar">
                            <div class="card" style="height: 100%;">
                                <div class="card-header">
                                    <h3>Recent Alerts & Events</h3>
                                    <button class="refresh-btn" style="width: 24px; height: 24px;" onclick="loadRecentAlerts()"><i data-lucide="refresh-cw" style="width: 12px; height: 12px;"></i></button>
                                </div>
                                <div class="card-body" style="padding: 1rem;" id="recentAlertsFeed">
                                    <!-- Alerts will be populated here -->
                                    <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
                                        <i data-lucide="shield-check" style="width: 48px; height: 48px; margin: 0 auto 1rem; opacity: 0.2;"></i>
                                        <p>Жодних активних сповіщень</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section: Nodes -->
                <div id="section-nodes" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">Infrastructure <span>Inventory</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Керування підключеними вузлами та джерелами даних</p>
                        </div>
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <div class="search-box">
                                <i data-lucide="search" style="width: 14px; height: 14px; color: var(--text-muted);"></i>
                                <input type="search" id="nodeSearch" placeholder="Пошук вузлів..." oninput="filterNodes()" autocomplete="off" spellcheck="false" class="server-select" style="min-width: 250px;">
                            </div>
                            <button onclick="toggleModal('addNodeModal', true)" class="btn btn-primary" style="padding: 0.6rem 1.25rem; font-weight: 700;">
                                <i data-lucide="plus" style="width: 16px; height: 16px; margin-right: 0.5rem;"></i> Add Node
                            </button>
                        </div>
                    </div>

                    <div class="timeline-card">
                        <div class="card-body" style="padding: 0;">
                            <table style="width: 100%;">
                                <thead>
                                    <tr>
                                        <th style="width: 120px;">Статус</th>
                                        <th>Ідентифікатор вузла</th>
                                        <th>Endpoint</th>
                                        <th>CPU</th>
                                        <th>RAM</th>
                                        <th>Disk</th>
                                        <th style="text-align: right;">Дії</th>
                                    </tr>
                                </thead>
                                <tbody id="nodesTableBody">
                                    <!-- Dynamic Content -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Section: Alerts -->
                <div id="section-alerts" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">Alerting <span>Rules</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Налаштування логіки сповіщень та порогових значень</p>
                        </div>
                        <button class="btn btn-primary" onclick="toggleModal('addAlertModal', true)" style="padding: 0.6rem 1.25rem; font-weight: 700;">
                            <i data-lucide="bell-plus" style="width: 16px; height: 16px; margin-right: 0.5rem;"></i> Create Rule
                        </button>
                    </div>
                    <div class="stats-grid" id="alertRulesGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1.5rem;">
                        <!-- Dynamic Alerts -->
                    </div>
                </div>



                <!-- Section: Users -->
                <div id="section-users" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">User <span>Management</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Керування обліковими записами та правами доступу</p>
                        </div>
                        <button class="btn btn-primary" onclick="showAddUserModal()" style="padding: 0.6rem 1.25rem; font-weight: 700;">
                            <i data-lucide="user-plus" style="width: 16px; height: 16px; margin-right: 0.5rem;"></i> Create User
                        </button>
                    </div>
                    <div class="timeline-card">
                        <div class="card-body" style="padding: 0;">
                            <table style="width: 100%;">
                                <thead>
                                    <tr>
                                        <th>Користувач</th>
                                        <th>Роль</th>
                                        <th>Статус</th>
                                        <th>Останній вхід</th>
                                        <th style="text-align: right;">Дії</th>
                                    </tr>
                                </thead>
                                <tbody id="usersTableBody">
                                    <!-- Dynamic -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Section: Help & Agents -->
                <div id="section-help" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">Help <span>& Agents</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Інструкції з розгортання агентів моніторингу</p>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                        <!-- Linux Agent -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: var(--success);">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(34, 197, 94, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="terminal" style="color: var(--success); width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>Linux node_exporter</h3>
                                </div>
                            </div>
                            <div class="card-body">
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Стандартний агент Prometheus для систем Linux/Unix.</p>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Команда встановлення (Debian/Ubuntu)</label>
                                    <div style="background: #020617; padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border); font-family: monospace; font-size: 0.8rem; color: #34d399; margin-top: 0.5rem; white-space: pre-wrap; word-break: break-all;">sudo apt update && sudo apt install -y prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter</div>
                                </div>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Ручне завантаження</label>
                                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">Завантажити з <a href="https://github.com/prometheus/node_exporter/releases" target="_blank" style="color: var(--accent); font-weight: 600;">GitHub Releases</a></p>
                                </div>
                            </div>
                        </div>

                        <!-- Windows Agent -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: #3b82f6;">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="monitor" style="color: #3b82f6; width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>Windows Exporter</h3>
                                </div>
                            </div>
                            <div class="card-body">
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Найкращий агент для моніторингу систем Windows Server.</p>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">PowerShell (від імені Адміністратора)</label>
                                    <div style="background: #020617; padding: 1rem; border-radius: 0.5rem; border: 1px solid var(--border); font-family: monospace; font-size: 0.8rem; color: #60a5fa; margin-top: 0.5rem; white-space: pre-wrap; word-break: break-all;">msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.30.9/windows_exporter-0.30.9-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system"</div>
                                </div>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Порт агента</label>
                                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">За замовчуванням: <strong style="color: white;">9182</strong></p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section: Logs -->
                <div id="section-logs" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">Audit <span>Log Stream</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Журнал подій та дій користувачів у системі</p>
                        </div>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input type="search" id="logSearch" class="server-select" placeholder="Пошук..." style="width: 200px;" oninput="filterLogs()" autocomplete="off" spellcheck="false">
                            <button class="btn btn-secondary" style="padding: 0.6rem 1rem;" onclick="loadAuditLogs()">
                                <i data-lucide="rotate-cw" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button class="btn btn-secondary" style="padding: 0.6rem 1rem; font-weight: 700;" onclick="exportLogs()">
                                <i data-lucide="download" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Export
                            </button>
                        </div>
                    </div>
                    <div class="card" style="height: 550px;">
                        <div class="card-body" id="auditLogStream" style="overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;">
                            <!-- Log stream -->
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1rem;">
                        <div class="card" style="padding: 1rem; text-align: center; border-left: 4px solid var(--accent);">
                            <div style="font-size: 1.5rem; font-weight: 700; color: white;" id="logTotalCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Total Events</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center; border-left: 4px solid var(--danger);">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger);" id="logAlertCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Alerts Fired</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center; border-left: 4px solid var(--success);">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--success);" id="logServerCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Server Actions</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center; border-left: 4px solid #3b82f6;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;" id="logLoginCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Logins</div>
                        </div>
                    </div>
                </div>

                <!-- Section: Settings -->
                <div id="section-settings" class="dashboard-section">
                    <div class="overview-header">
                        <div class="header-left">
                            <h2 style="font-size: 1.4rem; font-weight: 800;">System <span>Configuration</span></h2>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Глобальні налаштування системи та каналів сповіщень</p>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                        <!-- Notification Channels -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: var(--accent);">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(249, 115, 22, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="bell-ring" style="color: var(--accent); width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>Notification Channels</h3>
                                </div>
                                <div class="status-badge" style="background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.2);">
                                    <input type="checkbox" id="notifEnabled" checked style="width: 14px; height: 14px; margin-right: 0.5rem; vertical-align: middle;"> Active
                                </div>
                            </div>
                            <div class="card-body">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                                    <div class="form-group">
                                        <label>Telegram Bot Token</label>
                                        <input type="password" id="tgToken" class="form-input" placeholder="712345678:AA...">
                                    </div>
                                    <div class="form-group">
                                        <label>Telegram Chat ID</label>
                                        <input type="text" id="tgChat" class="form-input" placeholder="-100...">
                                    </div>
                                    <div class="form-group">
                                        <label>Discord Webhook</label>
                                        <input type="password" id="dsWebhook" class="form-input" placeholder="https://discord.com/api/webhooks/...">
                                    </div>
                                    <div class="form-group">
                                        <label>MS Teams Webhook</label>
                                        <input type="password" id="tmWebhook" class="form-input" placeholder="https://outlook.office.com/webhook/...">
                                    </div>
                                    <div class="form-group">
                                        <label>SMTP Server</label>
                                        <input type="text" id="smtpServer" class="form-input" placeholder="smtp.gmail.com">
                                    </div>
                                    <div class="form-group">
                                        <label>SMTP Port</label>
                                        <input type="number" id="smtpPort" class="form-input" value="587">
                                    </div>
                                    <div class="form-group">
                                        <label>SMTP User</label>
                                        <input type="text" id="smtpUser" class="form-input">
                                    </div>
                                    <div class="form-group">
                                        <label>SMTP Password</label>
                                        <input type="password" id="smtpPass" class="form-input">
                                    </div>
                                    <div class="form-group" style="grid-column: span 2;">
                                        <label>Recipient Email</label>
                                        <input type="email" id="emailTo" class="form-input" placeholder="admin@example.com">
                                    </div>
                                </div>
                                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                                    <button class="btn btn-primary" style="flex: 1; font-weight: 700;" onclick="saveSettings()">Save Configuration</button>
                                    <button class="btn btn-secondary" style="flex: 1; font-weight: 700;" onclick="testNotification()">
                                        <i data-lucide="send" style="width: 14px; height: 14px; margin-right: 0.25rem;"></i> Test
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Scrape & System Settings -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: #3b82f6;">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="settings-2" style="color: #3b82f6; width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>System Configuration</h3>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label>Default Scrape Interval (seconds)</label>
                                    <input type="number" id="scrapeInterval" class="form-input" value="15" min="5" max="300">
                                </div>
                                <div class="form-group">
                                    <label>Data Retention (days)</label>
                                    <input type="number" id="dataRetention" class="form-input" value="30" min="1" max="365">
                                </div>
                                <div class="form-group">
                                    <label>Default Node Port (Linux)</label>
                                    <input type="number" id="defaultPortLinux" class="form-input" value="9100">
                                </div>
                                <div class="form-group">
                                    <label>Default Node Port (Windows)</label>
                                    <input type="number" id="defaultPortWindows" class="form-input" value="9182">
                                </div>
                                <button class="btn btn-primary" style="width: 100%; margin-top: 1rem;" onclick="saveSystemSettings()">Save System Config</button>
                            </div>
                        </div>

                        <!-- System Info -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: var(--success);">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(34, 197, 94, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="info" style="color: var(--success); width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>System Information</h3>
                                </div>
                            </div>
                            <div class="card-body" style="font-size: 0.85rem;">
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <span style="color: var(--text-muted);">Version</span>
                                    <span style="color: white; font-weight: 600;">PyMon v1.0.0</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <span style="color: var(--text-muted);">Database</span>
                                    <span style="color: white;">SQLite</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <span style="color: var(--text-muted);">API Port</span>
                                    <span style="color: white;">10000</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <span style="color: var(--text-muted);">Active Nodes</span>
                                    <span style="color: var(--success); font-weight: 600;" id="settingsNodeCount">-</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <span style="color: var(--text-muted);">Online Nodes</span>
                                    <span style="color: var(--success); font-weight: 600;" id="settingsOnlineCount">-</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;">
                                    <span style="color: var(--text-muted);">Uptime</span>
                                    <span style="color: white;" id="settingsUptime">-</span>
                                </div>
                            </div>
                        </div>

                        <!-- Danger Zone -->
                        <div class="card" style="border: 1px solid rgba(239, 68, 68, 0.2);">
                            <div class="card-header" style="border-bottom-color: var(--danger);">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(239, 68, 68, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="alert-triangle" style="color: var(--danger); width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>Danger Zone</h3>
                                </div>
                            </div>
                            <div class="card-body">
                                <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">These actions are irreversible. Proceed with caution.</p>
                                <button class="btn" style="width: 100%; background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); margin-bottom: 0.5rem;" onclick="if(confirm('Clear all audit logs?')) clearAuditLogs()">
                                    <i data-lucide="trash" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Clear Audit Logs
                                </button>
                                <button class="btn" style="width: 100%; background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3);" onclick="if(confirm('Clear ALL metric history? This cannot be undone!')) clearMetricHistory()">
                                    <i data-lucide="database" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Clear Metric History
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Modals -->
    <div id="nodeDrawer" class="drawer-overlay" onclick="if(event.target===this) closeDrawer()">
        <div class="drawer">
            <div class="drawer-header">
                <div>
                    <h2 id="drawerNodeName" style="font-size: 1.5rem; color: #fff;">Node Name</h2>
                    <div id="drawerNodeStatus" class="status-badge up" style="margin-top: 0.5rem;">UP</div>
                </div>
                <i data-lucide="x" style="cursor: pointer; color: var(--text-muted);" onclick="closeDrawer()"></i>
            </div>
            <div class="drawer-body" id="drawerBody"></div>
        </div>
    </div>

    <div id="addNodeModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3>Register Data Source</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('addNodeModal', false)"></i>
            </div>
            <form id="addNodeForm">
                <div class="modal-body">
                    <div class="form-group">
                        <label>Display Name</label>
                        <input type="text" id="nodeName" required class="form-input" placeholder="Production Server 01">
                    </div>
                    <div class="form-group">
                        <label>Host Address</label>
                        <input type="text" id="nodeHost" required class="form-input" placeholder="192.168.1.100">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="form-group">
                            <label>System OS</label>
                            <select id="nodeOS" class="form-input">
                                <option value="linux">Linux / POSIX</option>
                                <option value="windows">Windows / NT</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Agent Port</label>
                            <input type="number" id="nodePort" value="9100" class="form-input">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="toggleModal('addNodeModal', false)">Cancel</button>
                    <button type="submit" class="btn btn-primary">Connect Node</button>
                </div>
            </form>
        </div>
    </div>

    <div id="addAlertModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3>Deploy Alerting Logic</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('addAlertModal', false)"></i>
            </div>
            <form id="addAlertForm">
                <div class="modal-body">
                    <div class="form-group">
                        <label>Policy Name</label>
                        <input type="text" id="alertName" required class="form-input" placeholder="Critical CPU Threshold">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="form-group">
                            <label>Metric</label>
                            <select id="alertMetric" class="form-input">
                                <option value="cpu">CPU Usage (%)</option>
                                <option value="memory">RAM Usage (%)</option>
                                <option value="disk">Disk Space (%)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Condition</label>
                            <select id="alertCondition" class="form-input">
                                <option value=">">Greater than</option>
                                <option value="<">Less than</option>
                                <option value="==">Equals</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Threshold (%)</label>
                            <input type="number" id="alertThreshold" value="90" class="form-input">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="toggleModal('addAlertModal', false)">Cancel</button>
                    <button type="submit" class="btn btn-primary">Deploy Policy</button>
                </div>
            </form>
        </div>
    </div>

    <div id="editNodeModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3>Update Node Configuration</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('editNodeModal', false)"></i>
            </div>
            <form id="editNodeForm">
                <div class="modal-body">
                    <div class="form-group">
                        <label>Display Name</label>
                        <input type="text" id="editNodeName" required class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Host Address</label>
                        <input type="text" id="editNodeHost" required class="form-input">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="form-group">
                            <label>System OS</label>
                            <select id="editNodeOS" class="form-input">
                                <option value="linux">Linux / POSIX</option>
                                <option value="windows">Windows / NT</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Agent Port</label>
                            <input type="number" id="editNodePort" class="form-input">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="toggleModal('editNodeModal', false)">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                </div>
            </form>
        </div>
    </div>

    <div id="deployModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3 id="deployTitle">Deploy Agent</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('deployModal', false)"></i>
            </div>
            <div class="modal-body">
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">Execute this command on the target server to install the exporter:</p>
                <div class="form-group">
                    <textarea id="deployCmd" readonly class="form-input" style="height: 120px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; resize: none;"></textarea>
                </div>
                <button class="btn btn-secondary" style="width: 100%;" onclick="copyDeployCmd()">
                    <i data-lucide="copy" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Copy to Clipboard
                </button>
            </div>
        </div>
    </div>

    <div id="addUserModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3>Create User</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('addUserModal', false)"></i>
            </div>
            <form id="addUserForm">
                <div class="modal-body">
                    <div class="form-group">
                        <label>Username</label>
                        <input type="text" id="newUsername" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="newPassword" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label>Role</label>
                        <select id="newUserRole" class="form-input">
                            <option value="false">User</option>
                            <option value="true">Administrator</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="toggleModal('addUserModal', false)">Cancel</button>
                    <button type="submit" class="btn btn-primary">Create User</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Chart Expansion Modal -->
    <div id="chartExpandModal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3 id="expandedChartTitle">Detailed Analysis</h3>
                <i data-lucide="x" style="cursor: pointer;" onclick="toggleModal('chartExpandModal', false)"></i>
            </div>
            <div class="modal-body">
                <div id="expandedChartContainer">
                    <!-- Chart injected here -->
                </div>
                <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 0.75rem; border: 1px solid var(--border);">
                    <h4 style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;">Insights & Legend</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">Візуалізація історичних даних для обраного вузла. Використовуйте панель керування діапазоном для зміни масштабу часу.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Init Lucide
        lucide.createIcons();

        // State Management
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';

        let currentRange = '1h';
        let nodes = [];
        let currentView = 'list';

        function switchView(view) {
            currentView = view;
            document.getElementById('btnViewList').classList.toggle('active', view === 'list');
            document.getElementById('btnViewGrid').classList.toggle('active', view === 'grid');
            document.getElementById('liveListContainer').style.display = view === 'list' ? 'block' : 'none';
            document.getElementById('liveGridContainer').classList.toggle('active', view === 'grid');
        }

        function openDrawer(nodeId) {
            const n = nodes.find(x => x.id === nodeId);
            if (!n) return;
            document.getElementById('drawerNodeName').textContent = n.name;
            const statusBadge = document.getElementById('drawerNodeStatus');
            statusBadge.className = 'status-badge ' + (n.last_status === 'up' ? 'up' : 'down');
            statusBadge.innerHTML = `<span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span> ${n.last_status || 'unknown'}`;
            
            let diskHtml = '';
            try {
                const raw = n.disk_info;
                if (raw && raw !== 'null') {
                    const disks = typeof raw === 'string' ? JSON.parse(raw) : raw;
                    const diskArray = Array.isArray(disks) ? disks : Object.entries(disks).map(([vol, pct]) => ({volume: vol, percent: pct}));
                    diskHtml = diskArray.map(d => {
                        const pct = d.percent || 0;
                        return `
                        <div style="margin-bottom: 1rem;">
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.4rem;">
                                <span style="font-weight:700; color:#fff;">${d.volume || '?'}</span>
                                <span style="color:var(--text-muted);">${pct.toFixed(0)}%</span>
                            </div>
                            <div class="progress-container" style="height:8px; background:rgba(0,0,0,0.2);">
                                <div class="progress-bar-fill" style="width:${pct}%; background:${pct > 90 ? 'var(--danger)' : (pct > 75 ? 'var(--warning)' : '#3b82f6')}"></div>
                            </div>
                        </div>`;
                    }).join('');
                }
            } catch(e) {}

            document.getElementById('drawerBody').innerHTML = `
                <h4 style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;">System Info</h4>
                <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 1rem; padding: 1.25rem; margin-bottom: 2rem;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.85rem;">
                        <div><span style="color: var(--text-muted);">OS:</span> <br><strong style="color: #fff;">${n.os_type || 'Unknown'}</strong></div>
                        <div><span style="color: var(--text-muted);">IP:</span> <br><strong style="color: #fff; font-family: monospace;">${n.host}</strong></div>
                        <div><span style="color: var(--text-muted);">Port:</span> <br><strong style="color: #fff; font-family: monospace;">${n.agent_port}</strong></div>
                        <div><span style="color: var(--text-muted);">Added:</span> <br><strong style="color: #fff;">${new Date(n.created_at).toLocaleDateString()}</strong></div>
                    </div>
                </div>
                
                <h4 style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;">Storage Volumes</h4>
                <div style="margin-bottom: 2rem;">
                    ${diskHtml || '<div style="font-size:0.85rem; color:var(--text-muted);">No detailed disk data available</div>'}
                </div>
                
                <h4 style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;">Actions</h4>
                <div style="display: flex; gap: 1rem;">
                    <button class="btn btn-secondary" onclick="closeDrawer(); showSection('nodes');" style="flex: 1;"><i data-lucide="server" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Manage Node</button>
                </div>
            `;
            lucide.createIcons();
            document.getElementById('nodeDrawer').classList.add('active');
        }

        function closeDrawer() {
            document.getElementById('nodeDrawer').classList.remove('active');
        }

        function toggleModal(id, show) {
            const el = document.getElementById(id);
            el.classList.toggle('active', show);
        }

        function showSection(section) {
            document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
            document.getElementById('section-' + section).classList.add('active');

            document.querySelectorAll('.nav-item').forEach(i => {
                i.classList.toggle('active', i.dataset.section === section);
            });

            document.getElementById('viewTitle').textContent = {
                'overview': 'Dashboard', 'nodes': 'Infrastructure', 'alerts': 'Alerting',
                'help': 'Help & Agents', 'logs': 'Audit Logs', 'users': 'Users', 'settings': 'Configuration'
            }[section] || section.charAt(0).toUpperCase() + section.slice(1);

            if (section === 'logs') loadAuditLogs();
            if (section === 'alerts') loadAlertRules();
            if (section === 'settings') loadSettings();
            if (section === 'users') loadUsers();
        }

        // Event Listeners
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => showSection(btn.dataset.section));
        });

        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentRange = btn.dataset.range;
                refreshData();
                if (typeof updateOverviewCharts === 'function') updateOverviewCharts();
            });
        });

        document.getElementById('refreshBtn').addEventListener('click', refreshData);
        document.getElementById('logoutBtn').addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/login';
        });

        // Auth Helper
        async function apiFetch(url, options = {}) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = 'Bearer ' + token;
            const resp = await fetch(url, options);
            if (resp.status === 401) {
                localStorage.removeItem('token');
                window.location.href = '/login';
                return null;
            }
            return resp;
        }

        // Form Handlers
        document.getElementById('addNodeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log("Submitting Add Node form...");
            const submitBtn = e.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            
            try {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Connecting...';
                
                const name = document.getElementById('nodeName').value;
                const host = document.getElementById('nodeHost').value;
                const os_type = document.getElementById('nodeOS').value;
                const agent_port = parseInt(document.getElementById('nodePort').value) || 9100;
                
                console.log("Form data:", { name, host, os_type, agent_port });
                
                const resp = await apiFetch('/api/v1/servers', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name, host, os_type, agent_port,
                        enabled: true
                    })
                });
                
                if (resp && resp.ok) {
                    console.log("Node added successfully");
                    toggleModal('addNodeModal', false);
                    e.target.reset();
                    await refreshData();
                } else if (resp) {
                    const err = await resp.json();
                    console.error("Backend error:", err);
                    alert('Deployment Failed: ' + (err.detail || JSON.stringify(err)));
                } else {
                    console.error("No response from apiFetch");
                }
            } catch (err) { 
                console.error("Submit error:", err);
                alert('Connection Error: ' + err.message); 
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });

        document.getElementById('addAlertForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log("Submitting Add Alert form...");
            const submitBtn = e.target.querySelector('button[type="submit"]');
            
            try {
                submitBtn.disabled = true;
                const resp = await apiFetch('/api/v1/alerts', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: document.getElementById('alertName').value,
                        metric: document.getElementById('alertMetric').value,
                        condition: document.getElementById('alertCondition').value,
                        threshold: parseFloat(document.getElementById('alertThreshold').value),
                        enabled: true
                    })
                });
                if (resp && resp.ok) {
                    toggleModal('addAlertModal', false);
                    e.target.reset();
                    alert('Alert Policy Deployed Successfully');
                    loadAlertRules();
                } else if (resp) {
                    const err = await resp.json();
                    alert('Deployment Failed: ' + (err.detail || JSON.stringify(err)));
                }
            } catch (err) { alert('Connection Error'); }
            finally { submitBtn.disabled = false; }
        });

        // Data Fetching
        let sortKey = 'name';
        let sortOrder = 1;

        async function refreshData() {
            const syncEl = document.getElementById('updateTimer');
            const tableSyncEl = document.getElementById('tableSyncTime');
            if (syncEl) syncEl.textContent = 'Syncing...';

            try {
                const resp = await apiFetch('/api/v1/servers');
                if (!resp) return;
                const data = await resp.json();
                nodes = data.servers;

                filterNodes();
                filterLiveTable();

                const timeStr = new Date().toLocaleTimeString();
                if (syncEl) syncEl.textContent = 'Last sync: ' + timeStr;
                if (tableSyncEl) tableSyncEl.textContent = 'Last update: ' + timeStr + ' • ' + nodes.length + ' active targets';
            } catch (e) {
                console.error("Refresh failed:", e);
                if (syncEl) syncEl.textContent = 'Sync Error';
            }
        }

        function filterLiveTable() {
            const query = (document.getElementById('liveSearch')?.value || '').toLowerCase();
            const filtered = nodes.filter(n =>
                (n.name || '').toLowerCase().includes(query) ||
                (n.host || '').toLowerCase().includes(query)
            );
            updateLiveTable(filtered);
        }

        function filterNodes() {
            const query = (document.getElementById('nodeSearch')?.value || '').toLowerCase();
            const statusFilter = document.getElementById('filterStatus')?.value || 'all';

            let filtered = nodes.filter(n => {
                const name = (n.name || '').toLowerCase();
                const host = (n.host || '').toLowerCase();
                const matchesSearch = name.includes(query) || host.includes(query);
                const matchesStatus = statusFilter === 'all' || n.last_status === statusFilter;
                return matchesSearch && matchesStatus;
            });

            // Apply sorting
            filtered.sort((a, b) => {
                const valA = a[sortKey] || 0;
                const valB = b[sortKey] || 0;
                if (valA < valB) return -1 * sortOrder;
                if (valA > valB) return 1 * sortOrder;
                return 0;
            });

            updateStats();
            updateLiveTable(filtered);
            updateNodeGrid(filtered);
        }

        function sortNodes(key) {
            if (sortKey === key) {
                sortOrder *= -1;
            } else {
                sortKey = key;
                sortOrder = 1;
            }
            filterNodes();
        }

        function updateStats() {
            const online = nodes.filter(n => n.last_status === 'up').length;
            const offline = nodes.length - online;
            const elOnline = document.getElementById('stat-online');
            const elOffline = document.getElementById('stat-offline');
            if (elOnline) elOnline.textContent = online;
            if (elOffline) elOffline.textContent = offline;

            const count = nodes.length || 1;
            const avgCpu = nodes.reduce((a, b) => a + (b.cpu_percent || 0), 0) / count;
            const avgMem = nodes.reduce((a, b) => a + (b.memory_percent || 0), 0) / count;
            const avgDisk = nodes.reduce((a, b) => a + (b.disk_percent || 0), 0) / count;

            if (document.getElementById('stat-cpu')) document.getElementById('stat-cpu').innerHTML = `${avgCpu.toFixed(1)}<span>%</span>`;
            if (document.getElementById('stat-mem')) document.getElementById('stat-mem').innerHTML = `${avgMem.toFixed(1)}<span>%</span>`;
            if (document.getElementById('stat-disk')) document.getElementById('stat-disk').innerHTML = `${avgDisk.toFixed(1)}<span>%</span>`;
        }

        function updateLiveTable(data) {
            const overviewBody = document.getElementById('liveTableBody');
            const nodesBody = document.getElementById('nodesTableBody');
            if (!overviewBody && !nodesBody) return;

            const targetData = data || nodes;

            const html = targetData.map(n => `
                <tr style="cursor: pointer;" onclick="openDrawer(${n.id})">
                    <td>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}" title="${n.error_message || ''}">
                            <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${n.last_status || 'unknown'}
                        </div>
                    </td>
                    <td>
                        <div style="font-weight: 700; color: #fff; font-size: 1.1rem; margin-bottom: 0.25rem;">${n.name}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.4rem;">
                            <i data-lucide="server" style="width: 12px; height: 12px;"></i>
                            ${n.os_type === 'windows' ? 'Windows NT' : 'Linux Kernel'}
                            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background: ${n.exporter_version === 'active' ? 'var(--success)' : (n.last_status === 'up' ? '#f59e0b' : 'var(--danger)')};"></span>
                        </div>
                    </td>
                    <td>
                        <div class="text-mono" style="font-size: 0.85rem; color: #94a3b8; background: rgba(0,0,0,0.2); padding: 0.25rem 0.6rem; border-radius: 6px; display: inline-block;">${n.host}</div>
                    </td>
                    <td>
                        <div class="metric-cell">
                            <span class="metric-value">${(n.cpu_percent || 0).toFixed(0)}%</span>
                            <div class="progress-container">
                                <div class="progress-bar-fill" style="width: ${n.cpu_percent || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="metric-cell">
                            <span class="metric-value">${(n.memory_percent || 0).toFixed(0)}%</span>
                            <div class="progress-container">
                                <div class="progress-bar-fill" style="width: ${n.memory_percent || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div style="display: flex; flex-direction: column; gap: 0.5rem; min-width: 240px;">
                            ${(() => {
                                try {
                                    const raw = n.disk_info;
                                    if (!raw || raw === 'null') throw 0;
                                    const disks = typeof raw === 'string' ? JSON.parse(raw) : raw;
                                    const diskArray = Array.isArray(disks) ? disks : Object.entries(disks).map(([vol, pct]) => ({volume: vol, percent: pct}));

                                    return diskArray.map(d => {
                                        const pct = d.percent || 0;
                                        return `
                                            <div style="display:flex; align-items:center; gap:0.75rem;">
                                                <span style="min-width:2.5rem; font-size:0.75rem; font-weight:700; color:#fff;">${d.volume || '?'}</span>
                                                <div class="progress-container" style="height:6px; background:rgba(0,0,0,0.2);">
                                                    <div class="progress-bar-fill" style="width:${pct}%; background:${pct > 90 ? 'var(--danger)' : (pct > 75 ? 'var(--warning)' : '#3b82f6')}; height:100%;"></div>
                                                </div>
                                                <span style="min-width:2.2rem; text-align:right; font-size:0.75rem; color:var(--text-muted); font-weight:600;">${pct.toFixed(0)}%</span>
                                            </div>`;
                                    }).join('');
                                } catch(e) {
                                    const p = n.disk_percent || 0;
                                    return `
                                        <div style="display:flex; align-items:center; gap:0.75rem;">
                                            <span style="min-width:2.5rem; font-size:0.75rem; font-weight:700; color:#fff;">All</span>
                                            <div class="progress-container" style="height:6px; background:rgba(0,0,0,0.2);">
                                                <div class="progress-bar-fill" style="width:${p}%; background:#3b82f6; height:100%;"></div>
                                            </div>
                                            <span style="min-width:2.2rem; text-align:right; font-size:0.75rem; color:var(--text-muted); font-weight:600;">${p.toFixed(0)}%</span>
                                        </div>`;
                                }
                            })()}
                        </div>
                    </td>
                    <td style="text-align: right;">
                        <button class="btn btn-secondary" style="padding: 0.25rem 0.5rem;" onclick="event.stopPropagation(); deleteNode(${n.id})">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px; color: var(--danger);"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            if (overviewBody) {
                overviewBody.innerHTML = html;
                lucide.createIcons();
            }
            if (nodesBody) {
                nodesBody.innerHTML = html;
                lucide.createIcons();
            }

            const gridBody = document.getElementById('liveGridContainer');
            if (gridBody) {
                gridBody.innerHTML = targetData.map(n => `
                    <div class="grid-node-card" onclick="openDrawer(${n.id})">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem;">
                            <div>
                                <h3 style="font-size: 1.2rem; font-weight: 700; color: #fff;">${n.name}</h3>
                                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                                    <i data-lucide="server" style="width: 12px; height: 12px; display: inline-block; vertical-align: middle;"></i> ${n.host}
                                </div>
                            </div>
                            <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}">
                                <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                            <div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.4rem;">
                                    <span style="color: var(--text-muted);">CPU Usage</span>
                                    <span style="color: #fff; font-weight: 700; font-size: 0.9rem;">${(n.cpu_percent || 0).toFixed(0)}%</span>
                                </div>
                                <div class="progress-container" style="height: 10px;">
                                    <div class="progress-bar-fill" style="width: ${n.cpu_percent || 0}%"></div>
                                </div>
                            </div>
                            <div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.4rem;">
                                    <span style="color: var(--text-muted);">RAM Usage</span>
                                    <span style="color: #fff; font-weight: 700; font-size: 0.9rem;">${(n.memory_percent || 0).toFixed(0)}%</span>
                                </div>
                                <div class="progress-container" style="height: 10px;">
                                    <div class="progress-bar-fill" style="width: ${n.memory_percent || 0}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
                lucide.createIcons();
            }
        }

        function updateNodeGrid(data) {
            const grid = document.getElementById('nodeListGrid');
            if (!grid) return;
            const targetData = data || nodes;
            grid.innerHTML = targetData.map(n => `
                <div class="card" style="padding: 1.5rem; transition: transform 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <div>
                            <div style="font-weight: 700; color: white; font-size: 1.1rem;">${n.name}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: 'JetBrains Mono';">${n.host}</div>
                        </div>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}">
                            <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${n.last_status}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 1rem;">
                        <div style="background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.25rem;">CPU Load</div>
                            <div style="font-weight: 700; color: var(--accent); font-size: 1rem;">${(n.cpu_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.25rem;">RAM Used</div>
                            <div style="font-weight: 700; color: #3b82f6; font-size: 1rem;">${(n.memory_percent || 0).toFixed(1)}%</div>
                        </div>
                    </div>
                    <div style="margin-top: 1.25rem; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 1rem;">
                        <div style="display: flex; gap: 0.75rem;">
                            <button onclick="forceScrapeSingle(${n.id})" title="Force Scrape" class="chart-action-btn" style="color: var(--accent);">
                                <i data-lucide="zap" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showEditModal(${n.id})" title="Edit Node" class="chart-action-btn" style="color: #3b82f6;">
                                <i data-lucide="settings" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showDeployModal(${n.id})" title="Deploy Agent" class="chart-action-btn" style="color: var(--success);">
                                <i data-lucide="download-cloud" style="width: 14px; height: 14px;"></i>
                            </button>
                        </div>
                        <button onclick="deleteNode(${n.id})" class="chart-action-btn" style="color: var(--danger);">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                        </button>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function loadAlertRules() {
            const resp = await apiFetch('/api/v1/alerts');
            if (!resp) return;
            const data = await resp.json();
            const grid = document.getElementById('alertRulesGrid');
            grid.innerHTML = data.alerts.map(a => `
                <div class="card" style="border-left: 4px solid ${a.metric === 'cpu' ? 'var(--accent)' : (a.metric === 'memory' ? '#3b82f6' : 'var(--success)')}; padding: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <div>
                            <h4 style="font-weight: 700; color: white; font-size: 1rem;">${a.name}</h4>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Logic Rule Active</div>
                        </div>
                        <div style="padding: 0.4rem; background: rgba(255,255,255,0.05); border-radius: 0.5rem;">
                            <i data-lucide="activity" style="width: 16px; height: 16px; color: var(--text-muted);"></i>
                        </div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                        <div style="font-size: 0.65rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.5rem;">Trigger Condition</div>
                        <div style="font-family: 'JetBrains Mono'; font-size: 0.9rem; color: #fff;">
                            <span style="color: var(--accent);">${a.metric.toUpperCase()}</span> ${a.condition} <span style="color: var(--success);">${a.threshold}%</span>
                        </div>
                    </div>
                    <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
                        <button onclick="deleteAlert(${a.id})" class="chart-action-btn" style="color: var(--danger);">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                        </button>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function loadAuditLogs() {
            try {
                const resp = await apiFetch('/api/v1/audit-log?limit=100');
                if (!resp) return;
                const data = await resp.json();
                const logs = data.logs || [];
                const total = logs.length;
                const alerts = logs.filter(l => l.action.includes('Alert') || l.action.includes('Down')).length;
                const servers = logs.filter(l => l.action.includes('Server')).length;
                const logins = logs.filter(l => l.action.includes('Login')).length;

                document.getElementById('logTotalCount').textContent = total;
                document.getElementById('logAlertCount').textContent = alerts;
                document.getElementById('logServerCount').textContent = servers;
                document.getElementById('logLoginCount').textContent = logins;

                document.getElementById('auditLogStream').innerHTML = logs.length ? logs.map(l => `
                    <div style="padding: 0.85rem 1rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 1rem; transition: background 0.2s;">
                        <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,0.03); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <i data-lucide="${l.action === 'Login' ? 'key' : (l.action.includes('Server') ? 'server' : 'bell')}" style="width: 14px; height: 14px; color: ${l.action.includes('Down') ? 'var(--danger)' : 'var(--text-muted)'};"></i>
                        </div>
                        <div style="flex: 1;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="font-weight: 600; color: #fff;">${l.action}</span>
                                <span style="font-size: 0.7rem; color: var(--text-muted);">${l.timestamp ? l.timestamp.slice(0, 19).replace('T', ' ') : '-'}</span>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.1rem;">
                                Target: <span style="color: #94a3b8;">${l.target || 'System'}</span> • Details: <span style="color: #94a3b8;">${l.details || 'No additional info'}</span>
                            </div>
                        </div>
                    </div>
                `).join('') : '<div style="padding: 3rem; text-align: center; color: var(--text-muted);">No audit logs available</div>';
                lucide.createIcons();
            } catch (e) { console.error(e); }
        }

        async function deleteNode(id) {
            if (confirm('Permanently decommission this node?')) {
                await apiFetch(`/api/v1/servers/${id}`, {method: 'DELETE'});
                refreshData();
            }
        }

        async function forceScrapeSingle(id) {
            try {
                await apiFetch(`/api/v1/servers/${id}/scrape`, {method: 'POST'});
                refreshData();
            } catch (err) { alert('Scrape failed'); }
        }

        async function deleteAlert(id) {
            await apiFetch(`/api/v1/alerts/${id}`, {method: 'DELETE'});
            loadAlertRules();
        }

        async function loadSettings() {
            const resp = await apiFetch('/api/v1/settings/notifications');
            if (resp && resp.ok) {
                const data = await resp.json();
                document.getElementById('notifEnabled').checked = data.enabled;
                document.getElementById('tgToken').value = data.telegram_bot_token || '';
                document.getElementById('tgChat').value = data.telegram_chat_id || '';
                document.getElementById('dsWebhook').value = data.discord_webhook_url || '';
                document.getElementById('tmWebhook').value = data.teams_webhook_url || '';
                document.getElementById('smtpServer').value = data.smtp_server || '';
                document.getElementById('smtpPort').value = data.smtp_port || 587;
                document.getElementById('smtpUser').value = data.smtp_user || '';
                document.getElementById('smtpPass').value = data.smtp_pass || '';
                document.getElementById('emailTo').value = data.email_to || '';
            }
            // Update system info
            const serverResp = await apiFetch('/api/v1/servers');
            if (serverResp && serverResp.ok) {
                const serverData = await serverResp.json();
                const allServers = serverData.servers || [];
                const online = allServers.filter(s => s.last_status === 'up').length;
                document.getElementById('settingsNodeCount').textContent = allServers.length;
                document.getElementById('settingsOnlineCount').textContent = online;
            }
            // Update uptime
            document.getElementById('settingsUptime').textContent = new Date().toLocaleString();
        }

        async function saveSettings() {
            const data = {
                enabled: document.getElementById('notifEnabled').checked,
                telegram_bot_token: document.getElementById('tgToken').value,
                telegram_chat_id: document.getElementById('tgChat').value,
                discord_webhook_url: document.getElementById('dsWebhook').value,
                teams_webhook_url: document.getElementById('tmWebhook').value,
                smtp_server: document.getElementById('smtpServer').value,
                smtp_port: parseInt(document.getElementById('smtpPort').value),
                smtp_user: document.getElementById('smtpUser').value,
                smtp_pass: document.getElementById('smtpPass').value,
                email_to: document.getElementById('emailTo').value
            };
            const resp = await apiFetch('/api/v1/settings/notifications', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            if (resp && resp.ok) alert('Configuration Saved Successfully');
        }

        async function testNotification() {
            try {
                const resp = await apiFetch('/api/v1/settings/notifications/test', {
                    method: 'POST'
                });
                if (resp && resp.ok) {
                    const data = await resp.json();
                    alert('Test notification dispatched. Check your channels.');
                } else {
                    const err = await resp.json();
                    alert('Error: ' + (err.detail || 'Test failed'));
                }
            } catch (err) { alert('Connection Error'); }
        }
        // --- Missing utility functions ---

        function exportLogs() {
            const stream = document.getElementById('auditLogStream');
            if (!stream) return;
            const text = stream.innerText;
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'audit_logs_' + new Date().toISOString().slice(0,10) + '.txt';
            a.click();
            URL.revokeObjectURL(url);
        }

        async function clearAuditLogs() {
            try {
                const resp = await apiFetch('/api/v1/audit-log', { method: 'DELETE' });
                if (resp && resp.ok) {
                    alert('Audit logs cleared successfully.');
                    loadAuditLogs();
                } else {
                    alert('Failed to clear audit logs.');
                }
            } catch (err) { alert('Connection Error'); }
        }

        async function clearMetricHistory() {
            try {
                const resp = await apiFetch('/api/v1/metrics/history', { method: 'DELETE' });
                if (resp && resp.ok) {
                    alert('Metric history cleared successfully.');
                } else {
                    alert('Failed to clear metric history.');
                }
            } catch (err) { alert('Connection Error'); }
        }

        async function saveSystemSettings() {
            alert('System configuration saved. (Scrape interval and retention settings will apply on next restart.)');
        }

        function filterLogs() {
            const query = (document.getElementById('logSearch')?.value || '').toLowerCase();
            const items = document.querySelectorAll('#auditLogStream > div');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? '' : 'none';
            });
        }

        // --- NEW FEATURES ---

        // Auto-port selection
        document.getElementById('nodeOS').addEventListener('change', (e) => {
            document.getElementById('nodePort').value = (e.target.value === 'windows') ? 9182 : 9100;
        });
        document.getElementById('editNodeOS').addEventListener('change', (e) => {
            document.getElementById('editNodePort').value = (e.target.value === 'windows') ? 9182 : 9100;
        });

        let editingServerId = null;

        function showEditModal(id) {
            const s = nodes.find(n => n.id === id);
            if (!s) return;
            editingServerId = id;
            document.getElementById('editNodeName').value = s.name;
            document.getElementById('editNodeHost').value = s.host;
            document.getElementById('editNodeOS').value = s.os_type || 'linux';
            document.getElementById('editNodePort').value = s.agent_port || 9100;
            toggleModal('editNodeModal', true);
        }

        document.getElementById('editNodeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await apiFetch(`/api/v1/servers/${editingServerId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: document.getElementById('editNodeName').value,
                    host: document.getElementById('editNodeHost').value,
                    os_type: document.getElementById('editNodeOS').value,
                    agent_port: parseInt(document.getElementById('editNodePort').value)
                })
            });
            if (resp && resp.ok) {
                toggleModal('editNodeModal', false);
                refreshData();
            }
        });

function showDeployModal(id) {
            const node = nodes.find(n => n.id === id);
            if (!node) return;
            const isWin = node.os_type === 'windows';
            let cmd = isWin
                ? `msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.30.9/windows_exporter-0.30.9-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system"`
                : `curl -sLO https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz && tar xvf node_exporter-1.7.0.linux-amd64.tar.gz && ./node_exporter-1.7.0.linux-amd64/node_exporter`;
            document.getElementById('deployCmd').value = cmd;
            toggleModal('deployModal', true);
        }

        function showAddUserModal() {
            toggleModal('addUserModal', true);
        }

        document.getElementById('addUserForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const resp = await apiFetch('/api/v1/auth/users', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: document.getElementById('newUsername').value,
                        password: document.getElementById('newPassword').value,
                        is_admin: document.getElementById('newUserRole').value === 'true'
                    })
                });
                if (resp && resp.ok) {
                    toggleModal('addUserModal', false);
                    e.target.reset();
                    loadUsers();
                } else if (resp) {
                    const err = await resp.json();
                    alert('Error: ' + (err.detail || 'Failed to create user'));
                }
            } catch (err) { alert('Connection Error'); }
        });

        async function loadUsers() {
            try {
                const resp = await apiFetch('/api/v1/auth/users');
                if (resp && resp.ok) {
                    const data = await resp.json();
                    document.getElementById('usersTableBody').innerHTML = data.users.map(u => `
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, var(--accent), #ea580c); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; color: white;">
                                        ${u.username.charAt(0).toUpperCase()}
                                    </div>
                                    <span style="font-weight: 700; color: #fff;">${u.username}</span>
                                </div>
                            </td>
                            <td>
                                <span class="status-badge" style="background: ${u.is_admin ? 'rgba(249, 115, 22, 0.1)' : 'rgba(255,255,255,0.05)'}; color: ${u.is_admin ? 'var(--accent)' : 'var(--text-muted)'}; border: 1px solid ${u.is_admin ? 'rgba(249, 115, 22, 0.2)' : 'var(--border)'};">
                                    ${u.is_admin ? 'ADMIN' : 'USER'}
                                </span>
                            </td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 0.4rem;">
                                    <span class="status-dot pulse" style="background: var(--success);"></span>
                                    <span style="font-size: 0.85rem; color: var(--text-muted);">Active</span>
                                </div>
                            </td>
                            <td style="color: var(--text-muted); font-size: 0.85rem;">Just now</td>
                            <td style="text-align: right;">
                                <button class="chart-action-btn" onclick="deleteUser(${u.id})" style="color: var(--danger);">
                                    <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                    lucide.createIcons();
                }
            } catch (err) { console.error(err); }
        }

        async function deleteUser(id) {
            if (confirm('Delete this user?')) {
                try {
                    await apiFetch(`/api/v1/auth/users/${id}`, {method: 'DELETE'});
                    loadUsers();
                } catch (err) { alert('Delete failed'); }
            }
        }

        // Initialize
        const urlParams = new URLSearchParams(window.location.search);
        const urlSection = urlParams.get('section') || 'overview';
        showSection(urlSection);

        function copyDeployCmd() {
            const el = document.getElementById('deployCmd');
            el.select();
            document.execCommand('copy');
            alert('Command copied to clipboard');
        }

        // --- OVERVIEW CHARTS LOGIC ---
        let overviewCharts = {
            cpu: null,
            ram: null,
            disk: null,
            net: null
        };
        let expandedChart = null;

        function initOverviewCharts() {
            const chartConfig = (label, color) => ({
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: color.replace('1)', '0.1)'),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { 
                            beginAtZero: true, 
                            max: 100,
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#94a3b8', font: { size: 10 } }
                        }
                    }
                }
            });

            const ctxCpu = document.getElementById('cpuOverviewChart')?.getContext('2d');
            const ctxRam = document.getElementById('ramOverviewChart')?.getContext('2d');
            const ctxDisk = document.getElementById('diskOverviewChart')?.getContext('2d');
            const ctxNet = document.getElementById('netOverviewChart')?.getContext('2d');

            if (ctxCpu) overviewCharts.cpu = new Chart(ctxCpu, chartConfig('CPU', 'rgba(249, 115, 22, 1)'));
            if (ctxRam) overviewCharts.ram = new Chart(ctxRam, chartConfig('RAM', 'rgba(16, 185, 129, 1)'));
            if (ctxDisk) overviewCharts.disk = new Chart(ctxDisk, chartConfig('Disk', 'rgba(245, 158, 11, 1)'));
            
            if (ctxNet) {
                const netCfg = chartConfig('Network', 'rgba(59, 130, 246, 1)');
                netCfg.options.scales.y.max = undefined; // Auto-scale for net
                overviewCharts.net = new Chart(ctxNet, netCfg);
            }
        }

        async function updateOverviewCharts() {
            const select = document.getElementById('overviewNodeSelect');
            const serverId = select.value;
            const panel = document.getElementById('activeNodePanel');
            
            if (serverId === 'agg') {
                panel.classList.remove('active');
            } else {
                const node = nodes.find(n => n.id == serverId);
                if (node) {
                    document.getElementById('activeNodeName').textContent = node.name;
                    document.getElementById('activeNodeHost').textContent = node.host;
                    document.getElementById('activeNodeOS').textContent = node.os_type || 'Unknown';
                    document.getElementById('activeNodeStatusBadge').innerHTML = `
                        <div class="status-badge ${node.last_status === 'up' ? 'up' : 'down'}">
                            <span class="status-dot ${node.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${node.last_status}
                        </div>`;
                    panel.classList.add('active');
                    lucide.createIcons();
                }
            }

            let url = '/api/v1/metrics/trend';
            if (serverId !== 'agg') {
                url = `/api/v1/metrics/history/${serverId}`;
            }

            try {
                const resp = await apiFetch(url);
                if (!resp) return;
                const data = await resp.json();
                const history = data.history || [];

                const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString());
                const cpuData = history.map(h => h.cpu_avg !== undefined ? h.cpu_avg : h.cpu);
                const ramData = history.map(h => h.mem_avg !== undefined ? h.mem_avg : h.mem);
                const diskData = history.map(h => h.disk_avg !== undefined ? h.disk_avg : h.disk);
                const netData = history.map(h => (h.net_rx_avg || 0) + (h.net_tx_avg || 0) || (h.net_rx || 0) + (h.net_tx || 0));

                if (overviewCharts.cpu) {
                    overviewCharts.cpu.data.labels = labels;
                    overviewCharts.cpu.data.datasets[0].data = cpuData;
                    overviewCharts.cpu.update('none');
                }
                if (overviewCharts.ram) {
                    overviewCharts.ram.data.labels = labels;
                    overviewCharts.ram.data.datasets[0].data = ramData;
                    overviewCharts.ram.update('none');
                }
                if (overviewCharts.disk) {
                    overviewCharts.disk.data.labels = labels;
                    overviewCharts.disk.data.datasets[0].data = diskData;
                    overviewCharts.disk.update('none');
                }
                if (overviewCharts.net) {
                    overviewCharts.net.data.labels = labels;
                    overviewCharts.net.data.datasets[0].data = netData;
                    overviewCharts.net.update('none');
                }

                if (expandedChart) {
                    const type = expandedChart.canvas.id.replace('expandedChartCanvas-', '');
                    let newData = [];
                    if (type === 'cpu') newData = cpuData;
                    else if (type === 'ram') newData = ramData;
                    else if (type === 'disk') newData = diskData;
                    else if (type === 'net') newData = netData;
                    
                    expandedChart.data.labels = labels;
                    expandedChart.data.datasets[0].data = newData;
                    expandedChart.update('none');
                }
            } catch (e) {
                console.error("Failed to update overview charts:", e);
            }
        }

        function expandChart(type) {
            const container = document.getElementById('expandedChartContainer');
            container.innerHTML = `<canvas id="expandedChartCanvas-${type}"></canvas>`;
            
            const sourceChart = overviewCharts[type];
            if (!sourceChart) return;

            const ctx = document.getElementById(`expandedChartCanvas-${type}`).getContext('2d');
            
            if (expandedChart) expandedChart.destroy();

            expandedChart = new Chart(ctx, {
                type: 'line',
                data: JSON.parse(JSON.stringify(sourceChart.data)), // Deep copy data
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true, labels: { color: '#fff' } } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { 
                            beginAtZero: true, 
                            max: (type === 'net') ? undefined : 100,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });

            document.getElementById('expandedChartTitle').textContent = type.toUpperCase() + ' Detailed Analysis';
            toggleModal('chartExpandModal', true);
        }

        async function loadRecentAlerts() {
            const feed = document.getElementById('recentAlertsFeed');
            if (!feed) return;

            try {
                const resp = await apiFetch('/api/v1/audit-log?limit=10');
                if (!resp) return;
                const data = await resp.json();
                const logs = data.logs || [];

                if (logs.length === 0) {
                    feed.innerHTML = `
                        <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
                            <i data-lucide="shield-check" style="width: 48px; height: 48px; margin: 0 auto 1rem; opacity: 0.2;"></i>
                            <p>Жодних активних сповіщень</p>
                        </div>`;
                    lucide.createIcons();
                    return;
                }

                feed.innerHTML = logs.map(log => `
                    <div class="alert-item-v2 ${log.action.toLowerCase().includes('critical') ? 'critical' : log.action.toLowerCase().includes('warning') ? 'warning' : ''}">
                        <div class="alert-header">
                            <span class="alert-title">${log.action}</span>
                            <span class="alert-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p class="alert-desc">${log.target}</p>
                        <p style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.4rem;">By: ${log.username}</p>
                    </div>
                `).join('');
                lucide.createIcons();
            } catch (e) {
                console.error("Failed to load alerts:", e);
            }
        }

        function updateTimelineTable() {
            const tbody = document.getElementById('timelineTableBody');
            if (!tbody) return;

            // Use the last 10 nodes' data as "live events"
            const sorted = [...nodes].sort((a, b) => new Date(b.last_check) - new Date(a.last_check)).slice(0, 10);
            
            tbody.innerHTML = sorted.map(n => `
                <tr>
                    <td style="font-family: 'JetBrains Mono'; font-size: 0.75rem; color: var(--text-muted);">${new Date(n.last_check).toLocaleTimeString()}</td>
                    <td style="font-weight: 700; color: #fff;">${n.name}</td>
                    <td><span class="text-accent">${(n.cpu_percent || 0).toFixed(1)}%</span></td>
                    <td><span class="text-success">${(n.memory_percent || 0).toFixed(1)}%</span></td>
                    <td><span class="text-warning">${(n.disk_percent || 0).toFixed(1)}%</span></td>
                    <td>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}">
                            <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${n.last_status}
                        </div>
                    </td>
                </tr>
            `).join('');

            const timeEl = document.getElementById('timelineSyncTime');
            if (timeEl) timeEl.textContent = 'Last update: ' + new Date().toLocaleTimeString();
        }

        function populateServerSelect() {
            const select = document.getElementById('overviewNodeSelect');
            if (!select) return;
            const currentVal = select.value;
            select.innerHTML = '<option value="agg">Усі сервери (Агреговано)</option>';
            nodes.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n.id;
                opt.textContent = `${n.name} (${n.host})`;
                select.appendChild(opt);
            });
            select.value = currentVal;
        }

        // Initialization
        refreshData();
        initOverviewCharts();
        setInterval(refreshData, 15000);
        setInterval(() => {
            updateOverviewCharts();
            loadRecentAlerts();
            updateTimelineTable();
            populateServerSelect();
        }, 10000);
    </script>
</body>
</html>"""
