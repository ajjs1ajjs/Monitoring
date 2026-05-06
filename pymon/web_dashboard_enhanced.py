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

        /* Performance Overview Grid */
        .performance-grid { display: grid; grid-template-columns: 1fr 400px; gap: 1.5rem; margin-top: 1.5rem; }

        /* Infrastructure Table */
        .table-card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.5rem; box-shadow: var(--card-shadow); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { padding: 1.25rem 2rem; background: rgba(0,0,0,0.15); color: var(--text-muted); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }
        td { padding: 1.5rem 2rem; border-top: 1px solid var(--border); font-size: 0.95rem; vertical-align: middle; transition: background 0.2s; }
        tr:hover td { background: rgba(255,255,255,0.02); }

        /* Metric Display */
        .metric-cell { display: flex; align-items: center; gap: 1rem; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: #fff; min-width: 3.5rem; }
        .metric-icon { color: var(--text-muted); width: 18px; height: 18px; opacity: 0.6; }

        /* Thick Progress Bars */
        .progress-container { flex: 1; height: 12px; background: rgba(0,0,0,0.3); border-radius: 6px; overflow: hidden; position: relative; }
        .progress-bar-fill { height: 100%; border-radius: 6px; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); background: linear-gradient(90deg, #10b981 0%, #f59e0b 60%, #ef4444 100%); background-size: 200% 100%; }

        .status-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.85rem; border-radius: 12px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.02em; }
        .status-badge.up { background: rgba(16, 185, 129, 0.1); color: var(--success); box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.2); }
        .status-badge.down { background: rgba(239, 68, 68, 0.1); color: var(--danger); box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.2); }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
        .status-dot.pulse { animation: statusPulse 2s infinite; box-shadow: 0 0 8px currentColor; }

        /* Event List */
        .event-item { padding: 0.85rem 0; border-bottom: 1px solid rgba(255,255,255,0.03); display: grid; grid-template-columns: 80px 1fr 100px; align-items: center; gap: 1rem; }
        .event-item:last-child { border-bottom: none; }
        .event-status { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; padding: 0.2rem 0.5rem; border-radius: 6px; text-align: center; }
        .event-status.critical { background: rgba(239, 68, 68, 0.15); color: #fca5a5; }
        .event-status.success { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; }
        .event-text { font-size: 0.85rem; color: #cbd5e1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .event-time { font-size: 0.75rem; color: var(--text-muted); text-align: right; }

        /* Utilities */
        .btn-primary { background: var(--accent); color: #000; box-shadow: 0 4px 14px 0 rgba(249, 115, 22, 0.3); }
        .btn-secondary { background: var(--surface-hover); color: var(--text); border: 1px solid var(--border); }
        .search-box { display: flex; align-items: center; gap: 0.75rem; background: #080c14; border: 1px solid var(--border); padding: 0.6rem 1rem; border-radius: 0.85rem; }
        .search-box input { background: transparent; border: none; color: white; font-size: 0.9rem; width: 100%; outline: none; }

        /* View Toggle */
        .view-toggle { display: flex; background: rgba(0,0,0,0.3); border-radius: 0.85rem; padding: 0.25rem; border: 1px solid var(--border); }
        .view-btn { background: transparent; border: none; color: var(--text-muted); padding: 0.4rem 0.75rem; border-radius: 0.6rem; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
        .view-btn.active { background: var(--surface-hover); color: var(--text); box-shadow: 0 2px 4px rgba(0,0,0,0.4); }

        /* Grid View */
        .nodes-grid { display: none; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; padding: 1.5rem 2.5rem 2.5rem 2.5rem; }
        .nodes-grid.active { display: grid; }
        .grid-node-card { background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 1.5rem; padding: 1.5rem; cursor: pointer; transition: transform 0.2s, border-color 0.2s; }
        .grid-node-card:hover { transform: translateY(-4px); border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.02); }

        /* Drawer */
        .drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
        .drawer-overlay.active { opacity: 1; pointer-events: auto; }
        .drawer { position: absolute; right: 0; top: 0; bottom: 0; width: 450px; background: #0a0e14; border-left: 1px solid var(--border); transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; flex-direction: column; box-shadow: -10px 0 30px rgba(0,0,0,0.5); }
        .drawer-overlay.active .drawer { transform: translateX(0); }
        .drawer-header { padding: 1.5rem 2rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: flex-start; }
        .drawer-body { padding: 2rem; flex: 1; overflow-y: auto; }
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
                    <div class="table-card">
                        <div class="card-header" style="padding: 2rem 2.5rem; background: rgba(0,0,0,0.1);">
                            <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                                <h3 style="font-size: 1.5rem; color: #fff; text-transform: none; letter-spacing: -0.01em;">Live Infrastructure Status</h3>
                                <span id="tableSyncTime" style="font-size: 0.85rem; color: var(--text-muted);">Syncing live data from nodes...</span>
                            </div>
                            <div style="display: flex; gap: 1.25rem; align-items: center;">
                                <div class="view-toggle">
                                    <button class="view-btn active" onclick="switchView('list')" id="btnViewList" title="List View"><i data-lucide="list" style="width: 16px; height: 16px;"></i></button>
                                    <button class="view-btn" onclick="switchView('grid')" id="btnViewGrid" title="Grid View"><i data-lucide="layout-grid" style="width: 16px; height: 16px;"></i></button>
                                </div>
                                <div class="search-box" style="min-width: 300px; background: rgba(0,0,0,0.3);">
                                    <i data-lucide="search" style="width: 16px; height: 16px; color: var(--text-muted);"></i>
                                    <input type="search" id="liveSearch" placeholder="Search infrastructure..." oninput="filterLiveTable()" autocomplete="off" spellcheck="false">
                                </div>
                                <button class="btn btn-secondary" style="padding: 0.65rem 1.25rem; font-weight: 700; font-size: 0.8rem;" onclick="showSection('nodes')">
                                    <i data-lucide="layout-grid" style="width: 14px; height: 14px; margin-right: 0.65rem; display: inline-block; vertical-align: middle;"></i>
                                    Full Inventory
                                </button>
                            </div>
                        </div>
                        <div id="liveListContainer" style="overflow-x: auto;">
                            <table style="min-width: 1200px;">
                                <thead>
                                    <tr>
                                        <th style="width: 140px;">Status</th>
                                        <th style="width: 300px;">Node Identity</th>
                                        <th style="width: 200px;">Endpoint</th>
                                        <th style="width: 280px;">
                                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                                CPU Usage <i data-lucide="cpu" style="width: 12px; height: 12px; opacity: 0.5;"></i>
                                            </div>
                                        </th>
                                        <th style="width: 280px;">
                                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                                RAM Usage <i data-lucide="memory-stick" style="width: 12px; height: 12px; opacity: 0.5;"></i>
                                            </div>
                                        </th>
                                        <th>Disk Distribution</th>
                                    </tr>
                                </thead>
                                <tbody id="liveTableBody">
                                    <!-- Dynamic -->
                                </tbody>
                            </table>
                        </div>
                        <div id="liveGridContainer" class="nodes-grid"></div>
                    </div>

                    <div class="performance-grid">
                        <!-- Left: Trends -->
                        <div class="card">
                            <div class="card-header">
                                <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                                    <h3>Infrastructure Performance Overview</h3>
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">Aggregated metrics across all clusters</span>
                                </div>
                                <div class="range-selector" style="transform: scale(0.9);">
                                    <button class="range-btn active">1 Hour</button>
                                    <button class="range-btn">3 Hours</button>
                                </div>
                            </div>
                            <div class="card-body" style="padding: 2rem;">
                                <div style="margin-bottom: 2.5rem;">
                                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; justify-content: space-between;">
                                        <span>Average CPU of all hosts</span>
                                        <span style="font-weight: 700; color: var(--accent);">Live Trend</span>
                                    </div>
                                    <div style="height: 120px; background: rgba(0,0,0,0.1); border-radius: 12px; position: relative; overflow: hidden;">
                                        <canvas id="cpuTrendChart"></canvas>
                                    </div>
                                </div>
                                <div>
                                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem; display: flex; justify-content: space-between;">
                                        <span>RAM usage average for all hosts</span>
                                        <span style="font-weight: 700; color: #3b82f6;">Live Trend</span>
                                    </div>
                                    <div style="height: 120px; background: rgba(0,0,0,0.1); border-radius: 12px; position: relative; overflow: hidden;">
                                        <canvas id="memTrendChart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Right: Events -->
                        <div class="card">
                            <div class="card-header">
                                <h3>Recent Alerts & Events</h3>
                                <i data-lucide="bell" style="width: 16px; height: 16px; color: var(--text-muted);"></i>
                            </div>
                            <div class="card-body" id="recentEventsList" style="padding: 1.5rem 2rem;">
                                <!-- Dynamic Events -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section: Nodes -->
                <div id="section-nodes" class="dashboard-section">
                    <div class="card-header" style="border-bottom: none; padding-bottom: 0;">
                        <h2 id="viewTitle">Infrastructure Inventory</h2>
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <div class="search-box">
                                <i data-lucide="search" style="width: 14px; height: 14px;"></i>
                                <input type="search" id="nodeSearch" placeholder="Search nodes..." oninput="filterNodes()" autocomplete="off" spellcheck="false">
                            </div>
                            <select id="filterStatus" class="form-input" style="width: 120px; padding: 0.4rem;" onchange="filterNodes()">
                                <option value="all">All Status</option>
                                <option value="up">Online</option>
                                <option value="down">Offline</option>
                            </select>
                            <button onclick="toggleModal('addNodeModal', true)" class="btn btn-primary" style="padding: 0.4rem 1rem;">
                                <i data-lucide="plus" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Add Node
                            </button>
                        </div>
                    </div>

                    <div class="table-card" style="margin-top: 1rem;">
                        <table>
                            <thead>
                                <tr>
                                    <th style="cursor: pointer;" onclick="sortNodes('last_status')">Status <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th style="cursor: pointer;" onclick="sortNodes('name')">Node Identity <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th>Endpoint</th>
                                    <th style="cursor: pointer;" onclick="sortNodes('cpu_percent')">CPU <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th style="cursor: pointer;" onclick="sortNodes('memory_percent')">RAM <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th style="cursor: pointer;" onclick="sortNodes('disk_percent')">Disk <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th style="text-align: right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="nodesTableBody">
                                <!-- Dynamic Content -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Section: Alerts -->
                <div id="section-alerts" class="dashboard-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                        <h2 style="font-size: 1.5rem; font-weight: 700;">Active Alert Rules</h2>
                        <button class="btn btn-primary" onclick="toggleModal('addAlertModal', true)">Create Logic Rule</button>
                    </div>
                    <div class="stats-grid" id="alertRulesGrid">
                        <!-- Dynamic Alerts -->
                    </div>
                </div>

                <!-- Section: Help & Agents -->
                <div id="section-help" class="dashboard-section">
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
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Standard Prometheus agent for Linux/Unix systems.</p>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Install Command (Debian/Ubuntu)</label>
                                    <textarea readonly class="form-input" style="height: 80px; font-family: monospace; font-size: 0.75rem; background: #020617;">sudo apt update && sudo apt install -y prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter</textarea>
                                </div>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Manual Download</label>
                                    <p style="font-size: 0.75rem;">Download from <a href="https://github.com/prometheus/node_exporter/releases" target="_blank" style="color: var(--accent);">Official Releases</a></p>
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
                                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Best-in-class agent for Windows Server monitoring.</p>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">PowerShell Install</label>
                                    <textarea readonly class="form-input" style="height: 80px; font-family: monospace; font-size: 0.75rem; background: #020617;">msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.30.9/windows_exporter-0.30.9-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system"</textarea>
                                </div>
                                <div class="form-group">
                                    <label style="font-size: 0.7rem; text-transform: uppercase;">Agent Port</label>
                                    <p style="font-size: 0.75rem;">Default Port: <strong style="color: white;">9182</strong></p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card" style="margin-top: 2rem;">
                        <div class="card-header">
                            <h3>Quick Setup Guide</h3>
                        </div>
                        <div class="card-body" style="font-size: 0.9rem; line-height: 1.6;">
                            <ol style="padding-left: 1.5rem;">
                                <li>Install the appropriate agent on your target server.</li>
                                <li>Ensure the firewall allows traffic on port <strong style="color: var(--accent);">9100</strong> (Linux) or <strong style="color: var(--accent);">9182</strong> (Windows).</li>
                                <li>Go to <strong>Infrastructure</strong> tab and click <strong>+ Add Node</strong>.</li>
                                <li>Enter the IP address and the correct port.</li>
                                <li>Wait 30-60 seconds for the first metrics to appear.</li>
                            </ol>
                        </div>
                    </div>
                </div>

                <!-- Section: Users -->
                <div id="section-users" class="dashboard-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                        <h2 style="font-size: 1.5rem; font-weight: 700;">User Management</h2>
                        <button class="btn btn-primary" onclick="showAddUserModal()">Create User</button>
                    </div>
                    <div class="card">
                        <table class="inventory-table">
                            <thead>
                                <tr>
                                    <th>Username</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th>Last Login</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="font-bold text-white">admin</td>
                                    <td><span class="status-badge up">Administrator</span></td>
                                    <td>Active</td>
                                    <td class="text-slate-500">Just now</td>
                                    <td>
                                        <button class="action-btn" style="color: #3b82f6;"><i data-lucide="edit-2" style="width: 14px; height: 14px;"></i></button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>



                <!-- Section: Logs -->
                <div id="section-logs" class="dashboard-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h2 style="font-size: 1.5rem; font-weight: 700;">Audit Log Stream</h2>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input type="search" id="logSearch" class="form-input" placeholder="Search logs..." style="width: 200px; padding: 0.3rem 0.75rem; font-size: 0.75rem;" oninput="filterLogs()" autocomplete="off" spellcheck="false">
                            <select id="logFilter" class="form-input" style="width: 140px; padding: 0.3rem 0.5rem; font-size: 0.75rem;" onchange="filterLogs()">
                                <option value="">All Actions</option>
                                <option value="Add Server">Add Server</option>
                                <option value="Delete Server">Delete Server</option>
                                <option value="Alert Triggered">Alert Triggered</option>
                                <option value="Exporter Down">Exporter Down</option>
                                <option value="Login">Login</option>
                            </select>
                            <button class="btn btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.7rem;" onclick="loadAuditLogs()">
                                <i data-lucide="rotate-cw" style="width: 12px; height: 12px;"></i>
                            </button>
                            <button class="btn btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.7rem;" onclick="exportLogs()">
                                <i data-lucide="download" style="width: 12px; height: 12px;"></i> Export
                            </button>
                        </div>
                    </div>
                    <div class="card" style="height: 550px;">
                        <div class="card-body" id="auditLogStream" style="overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">
                            <!-- Log stream -->
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1rem;">
                        <div class="card" style="padding: 1rem; text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: white;" id="logTotalCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Total Events</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--danger);" id="logAlertCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Alerts Fired</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--success);" id="logServerCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Server Actions</div>
                        </div>
                        <div class="card" style="padding: 1rem; text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;" id="logLoginCount">0</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">Logins</div>
                        </div>
                    </div>
                </div>

                <!-- Section: Settings -->
                <div id="section-settings" class="dashboard-section">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                        <!-- Notification Settings -->
                        <div class="card">
                            <div class="card-header" style="border-bottom-color: var(--accent);">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div style="padding: 0.5rem; background: rgba(249, 115, 22, 0.1); border-radius: 0.5rem;">
                                        <i data-lucide="bell" style="color: var(--accent); width: 20px; height: 20px;"></i>
                                    </div>
                                    <h3>Notification Channels</h3>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                                        <input type="checkbox" id="notifEnabled" style="width: 16px; height: 16px;">
                                        Broadcast Notifications Enabled
                                    </label>
                                </div>
                                <div class="form-group">
                                    <label>Telegram Bot Token</label>
                                    <input type="password" id="tgToken" class="form-input" placeholder="000000:ABC...">
                                </div>
                                <div class="form-group">
                                    <label>Telegram Chat ID</label>
                                    <input type="text" id="tgChat" class="form-input" placeholder="-100...">
                                </div>
                                <div class="form-group">
                                    <label>Discord Webhook URL</label>
                                    <input type="text" id="dsWebhook" class="form-input" placeholder="https://discord.com/api/webhooks/...">
                                </div>
                                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                                    <button class="btn btn-primary" style="flex: 1;" onclick="saveSettings()">Save</button>
                                    <button class="btn btn-secondary" style="flex: 1;" onclick="testNotification()">
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
                                <option value="cpu">CPU Load</option>
                                <option value="memory">Memory Usage</option>
                                <option value="disk">Disk Usage</option>
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

            document.getElementById('viewTitle').textContent = section.charAt(0).toUpperCase() + section.slice(1);

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
            const resp = await apiFetch('/api/v1/alerts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: document.getElementById('alertName').value,
                    metric: document.getElementById('alertMetric').value,
                    condition: '>',
                    threshold: parseInt(document.getElementById('alertThreshold').value),
                    duration: 60,
                    severity: 'warning'
                })
            });
            if (resp && resp.ok) {
                toggleModal('addAlertModal', false);
                e.target.reset();
                loadAlertRules();
            }
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
                <div class="node-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <div>
                            <div style="font-weight: 700; color: white;">${n.name}</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted);">${n.host}</div>
                        </div>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}">${n.last_status}</div>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">System Load</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                        <div style="background: rgba(255,255,255,0.03); padding: 0.5rem; border-radius: 0.5rem;">
                            <div style="font-size: 0.6rem; text-transform: uppercase;">CPU</div>
                            <div style="font-weight: 700; color: var(--accent);">${(n.cpu_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 0.5rem; border-radius: 0.5rem;">
                            <div style="font-size: 0.6rem; text-transform: uppercase;">RAM</div>
                            <div style="font-weight: 700; color: #3b82f6;">${(n.memory_percent || 0).toFixed(1)}%</div>
                        </div>
                    </div>
                    ${n.error_message ? `
                    <div style="margin-top: 0.75rem; padding: 0.5rem; background: rgba(239, 68, 68, 0.1); border-radius: 0.5rem; border-left: 2px solid var(--danger); font-size: 0.65rem; color: #fca5a5;">
                        <i data-lucide="alert-circle" style="width: 10px; height: 10px; display: inline; margin-right: 0.25rem;"></i>
                        ${n.error_message}
                    </div>` : ''}
                    <div style="margin-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap: 0.5rem;">
                            <button onclick="forceScrapeSingle(${n.id})" title="Force Scrape" style="background: transparent; border: none; color: var(--accent); cursor: pointer; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
                                <i data-lucide="zap" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showEditModal(${n.id})" title="Edit Node" style="background: transparent; border: none; color: #3b82f6; cursor: pointer; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
                                <i data-lucide="settings" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showDeployModal(${n.id})" title="Deploy Agent" style="background: transparent; border: none; color: var(--success); cursor: pointer; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
                                <i data-lucide="download-cloud" style="width: 14px; height: 14px;"></i>
                            </button>
                        </div>
                        <button onclick="deleteNode(${n.id})" style="background: transparent; border: none; color: #f87171; cursor: pointer; opacity: 0.5;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5">
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
                <div class="node-card" style="border-left: 4px solid ${a.severity === 'critical' ? 'var(--danger)' : 'var(--warning)'};">
                    <div style="font-weight: 700; color: white; margin-bottom: 0.25rem;">${a.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        Trigger: <span style="color: white; font-family: monospace;">${a.metric} > ${a.threshold}%</span>
                    </div>
                    <div style="margin-top: 1rem; display: flex; justify-content: flex-end;">
                        <button onclick="deleteAlert(${a.id})" style="background: transparent; border: none; color: #f87171; cursor: pointer; opacity: 0.5;">
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
                document.getElementById('auditLogStream').innerHTML = logs.length ? logs.slice(0, 50).map(l => `
                    <div style="padding: 0.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; font-size: 0.7rem;">
                        <span style="color: var(--text-muted);">${l.timestamp ? l.timestamp.slice(0, 19).replace('T', ' ') : '-'}</span>
                        <span style="color: ${l.action === 'Exporter Down' ? 'var(--danger)' : 'white'};">${l.action}</span>
                        <span style="color: var(--text-muted);">${l.target || '-'}</span>
                    </div>
                `).join('') : '<div style="padding: 1rem; text-align: center; color: var(--text-muted);">No audit logs</div>';
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
                discord_webhook_url: document.getElementById('dsWebhook').value
            };
            const resp = await apiFetch('/api/v1/settings/notifications', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            if (resp && resp.ok) alert('Configuration Saved Successfully');
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
                    const tbody = document.querySelector('#section-users tbody');
                    tbody.innerHTML = data.users.map(u => `
                        <tr>
                            <td class="font-bold text-white">${u.username}</td>
                            <td><span class="status-badge ${u.is_admin ? 'up' : ''}">${u.is_admin ? 'Administrator' : 'User'}</span></td>
                            <td>${u.must_change_password ? 'Password Change Required' : 'Active'}</td>
                            <td class="text-slate-500">${u.last_login ? u.last_login.slice(0, 19).replace('T', ' ') : 'Never'}</td>
                            <td>
                                <button class="action-btn" style="color: #ef4444;" onclick="deleteUser(${u.id})"><i data-lucide="trash-2" style="width: 14px; height: 14px;"></i></button>
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

        // Initialization
        refreshData();
        setInterval(refreshData, 15000);
    </script>
</body>
</html>"""
