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
            --bg: #020617;
            --surface: #0f172a;
            --surface-hover: #1e293b;
            --accent: #f97316;
            --accent-glow: rgba(249, 115, 22, 0.4);
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.06);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --sidebar-w: 260px;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; }

        /* Layout */
        .app-container { display: flex; height: 100vh; width: 100vw; }
        
        /* Sidebar */
        aside { width: var(--sidebar-w); background: #020617; border-right: 1px solid var(--border); display: flex; flex-direction: column; z-index: 50; }
        .sidebar-header { padding: 2rem 1.5rem; display: flex; align-items: center; gap: 0.75rem; }
        .sidebar-header svg { color: var(--accent); width: 28px; height: 28px; }
        .sidebar-header h1 { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.025em; }
        .sidebar-header span { color: var(--accent); }
        
        .nav-section { padding: 0 1rem; flex: 1; }
        .nav-label { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin: 1.5rem 0 0.75rem 0.75rem; }
        
        .nav-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; border-radius: 0.75rem; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; background: transparent; width: 100%; text-align: left; margin-bottom: 0.25rem; }
        .nav-item:hover { background: var(--surface-hover); color: var(--text); }
        .nav-item.active { background: rgba(249, 115, 22, 0.1); color: var(--accent); }
        .nav-item.active svg { color: var(--accent); }
        
        .sidebar-footer { padding: 1rem; border-top: 1px solid var(--border); }
        .logout-btn { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; color: #f87171; width: 100%; border: none; background: transparent; font-size: 0.9rem; cursor: pointer; border-radius: 0.75rem; transition: all 0.2s; }
        .logout-btn:hover { background: rgba(239, 68, 68, 0.1); }

        /* Main Content */
        main { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #030712; }
        header { height: 64px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; background: rgba(2, 6, 23, 0.5); backdrop-filter: blur(10px); z-index: 40; }
        .header-left h2 { font-size: 1rem; font-weight: 600; color: var(--text); }
        
        .header-actions { display: flex; align-items: center; gap: 1rem; }
        .range-selector { display: flex; background: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; padding: 0.25rem; overflow-x: auto; max-width: 400px; }
        .range-btn { padding: 0.25rem 0.6rem; border-radius: 0.375rem; border: none; background: transparent; color: var(--text-muted); font-size: 0.65rem; font-weight: 700; cursor: pointer; white-space: nowrap; }
        .range-btn.active { background: var(--surface-hover); color: var(--text); box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
        
        .refresh-btn { background: var(--surface); border: 1px solid var(--border); border-radius: 0.5rem; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); cursor: pointer; transition: all 0.2s; }
        .refresh-btn:hover { border-color: var(--text-muted); color: var(--text); }

        .content-scroll { flex: 1; overflow-y: auto; padding: 2rem; scroll-behavior: smooth; }
        .content-scroll::-webkit-scrollbar { width: 6px; }
        .content-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        /* Dashboard Grid */
        .dashboard-section { display: none; animation: fadeIn 0.2s ease-out; }
        .dashboard-section.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: var(--surface); border: 1px solid var(--border); padding: 1.5rem; border-radius: 1.25rem; position: relative; overflow: hidden; transition: transform 0.3s; }
        .stat-card:hover { transform: translateY(-4px); }
        .stat-card::after { content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 2px; background: transparent; }
        .stat-card.up::after { background: var(--success); }
        .stat-card.down::after { background: var(--danger); }
        .stat-card.alert::after { background: var(--warning); }
        
        .stat-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 0.5rem; }
        .stat-value { font-size: 2rem; font-weight: 700; color: var(--text); display: flex; align-items: baseline; gap: 0.25rem; }
        .stat-value span { font-size: 0.875rem; color: var(--text-muted); }

        .chart-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 2rem; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem; display: flex; flex-direction: column; }
        .card-header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
        .card-header h3 { font-size: 0.875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
        .card-body { padding: 1.5rem; flex: 1; position: relative; min-height: 250px; }

        /* Infrastructure Table */
        .table-card { background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { padding: 1rem 1.5rem; background: rgba(0,0,0,0.2); color: var(--text-muted); font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
        td { padding: 1rem 1.5rem; border-top: 1px solid var(--border); font-size: 0.875rem; vertical-align: middle; }
        tr:hover td { background: rgba(255,255,255,0.02); }

        .status-badge { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.25rem 0.625rem; border-radius: 9999px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
        .status-badge.up { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .status-badge.down { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
        .status-dot.pulse { animation: statusPulse 2s infinite; }
        @keyframes statusPulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

        .progress-bar { width: 100px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }

        /* Modals */
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 1rem; }
        .modal-overlay.active { display: flex; }
        .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 1.5rem; width: 100%; max-width: 480px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        .modal-header { padding: 1.5rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
        .modal-body { padding: 1.5rem; }
        .modal-footer { padding: 1rem 1.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 0.75rem; }
        
        .form-group { margin-bottom: 1.25rem; }
        .form-group label { display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.5rem; }
        .form-input { width: 100%; background: #020617; border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 0.75rem; color: white; font-size: 0.9rem; }
        .form-input:focus { outline: none; border-color: var(--accent); }

        .btn { padding: 0.625rem 1.25rem; border-radius: 0.75rem; font-weight: 600; cursor: pointer; transition: all 0.2s; border: 1px solid transparent; font-size: 0.875rem; }
        .btn-primary { background: var(--accent); color: #000; }
        .btn-primary:hover { background: #ea580c; transform: translateY(-1px); }
        .btn-secondary { background: var(--surface-hover); color: var(--text); border-color: var(--border); }
        .btn-secondary:hover { background: #334155; }
        
        .node-card { background: var(--surface); border: 1px solid var(--border); border-radius: 1rem; padding: 1.25rem; transition: border-color 0.2s; position: relative; }
        .node-card:hover { border-color: var(--text-muted); }

        /* Explorer Tools */
        .explorer-toolbar { display: flex; gap: 1rem; background: var(--surface); border: 1px solid var(--border); padding: 1rem; border-radius: 1rem; margin-bottom: 1.5rem; align-items: flex-end; }
        .explorer-field { flex: 1; }
        .explorer-field label { display: block; font-size: 0.65rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; }

        /* Utility */
        .hidden { display: none; }
        .text-mono { font-family: 'JetBrains Mono', monospace; }
        .font-bold { font-weight: 700; }
        .text-slate-500 { color: #64748b; }
        .text-white { color: #ffffff; }
        .text-xs { font-size: 0.75rem; }
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
</head>
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
                
                <div class="nav-label">Tools</div>
                <button class="nav-item" data-section="explorer">
                    <i data-lucide="activity"></i> Metrics Explorer
                </button>
                <button class="nav-item" data-section="manual">
                    <i data-lucide="wrench"></i> Manual Control
                </button>
                <button class="nav-item" data-section="logs">
                    <i data-lucide="list"></i> Audit Logs
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
                    <div class="stats-grid">
                        <div class="stat-card up">
                            <div class="stat-label">Active Nodes</div>
                            <div class="stat-value" id="stat-online">0</div>
                        </div>
                        <div class="stat-card down">
                            <div class="stat-label">Offline Nodes</div>
                            <div class="stat-value" id="stat-offline">0</div>
                        </div>
                        <div class="stat-card alert">
                            <div class="stat-label">Avg CPU Load</div>
                            <div class="stat-value" id="stat-cpu">0<span>%</span></div>
                        </div>
                        <div class="stat-card up">
                            <div class="stat-label">Avg Memory</div>
                            <div class="stat-value" id="stat-mem">0<span>%</span></div>
                        </div>
                    </div>

                    <div class="chart-grid">
                        <div class="card">
                            <div class="card-header">
                                <h3>CPU Usage Trends</h3>
                                <i data-lucide="cpu" style="width: 14px; height: 14px; color: var(--text-muted);"></i>
                            </div>
                            <div class="card-body">
                                <canvas id="cpuChart"></canvas>
                            </div>
                        </div>
                        <div class="card">
                            <div class="card-header">
                                <h3>Memory Utilization</h3>
                                <i data-lucide="database" style="width: 14px; height: 14px; color: var(--text-muted);"></i>
                            </div>
                            <div class="card-body">
                                <canvas id="memChart"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="table-card">
                        <div class="card-header">
                            <h3>Live Infrastructure Status</h3>
                            <button class="btn btn-secondary" style="padding: 0.25rem 0.75rem; font-size: 0.7rem;" onclick="showSection('nodes')">Detailed Inventory</button>
                        </div>
                        <div style="overflow-x: auto;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Status</th>
                                        <th>Node Identity</th>
                                        <th>Endpoint</th>
                                        <th>CPU</th>
                                        <th>RAM</th>
                                        <th>Storage</th>
                                        <th>Traffic (RX/TX)</th>
                                    </tr>
                                </thead>
                                <tbody id="liveTableBody">
                                    <!-- Dynamic -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Section: Nodes -->
                <div id="section-nodes" class="dashboard-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                        <h2 style="font-size: 1.5rem; font-weight: 700;">Managed Inventory</h2>
                        <button class="btn btn-primary" onclick="toggleModal('addNodeModal', true)">
                            <i data-lucide="plus" style="width: 16px; height: 16px; display: inline-block; vertical-align: middle; margin-right: 0.5rem;"></i> Register Node
                        </button>
                    </div>
                    <div class="stats-grid" id="nodeListGrid">
                        <!-- Dynamic Nodes -->
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

                <!-- Section: Explorer -->
                <div id="section-explorer" class="dashboard-section">
                    <div class="explorer-toolbar">
                        <div class="explorer-field">
                            <label>Target Series</label>
                            <select id="explorerSeries" class="form-input">
                                <option value="">Select Metric...</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" id="runQueryBtn">
                            <i data-lucide="play" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Execute Query
                        </button>
                    </div>
                    <div class="card" style="height: 500px;">
                        <div class="card-header">
                            <h3 id="explorerTitle">Query Results</h3>
                        </div>
                        <div class="card-body">
                            <canvas id="explorerChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Section: Manual Control -->
                <div id="section-manual" class="dashboard-section">
                    <div class="card" style="max-width: 800px; margin: 0 auto;">
                        <div class="card-header">
                            <h3>Manual Metric Injection</h3>
                        </div>
                        <div class="card-body">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                <div class="form-group">
                                    <label>Metric Name</label>
                                    <input type="text" id="manualMetricName" class="form-input" placeholder="custom_app_orders">
                                </div>
                                <div class="form-group">
                                    <label>Metric Value</label>
                                    <input type="number" id="manualMetricValue" class="form-input" placeholder="42.5">
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Metric Type</label>
                                <select id="manualMetricType" class="form-input">
                                    <option value="gauge">Gauge</option>
                                    <option value="counter">Counter</option>
                                </select>
                            </div>
                            <button class="btn btn-primary" style="width: 100%;" onclick="injectManualMetric()">Submit Metric</button>
                        </div>
                    </div>
                    
                    <div class="card" style="max-width: 800px; margin: 2rem auto;">
                        <div class="card-header">
                            <h3>Force Scrape Node</h3>
                        </div>
                        <div class="card-body">
                            <div class="form-group">
                                <label>Select Target</label>
                                <select id="forceScrapeTarget" class="form-input">
                                    <!-- Dynamic -->
                                </select>
                            </div>
                            <button class="btn btn-secondary" style="width: 100%; border-color: var(--accent); color: var(--accent);" onclick="forceScrape()">
                                <i data-lucide="zap" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Immediate Scrape
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Section: Logs -->
                <div id="section-logs" class="dashboard-section">
                    <div class="card" style="height: 600px;">
                        <div class="card-header">
                            <h3>Audit Log Stream</h3>
                            <button class="btn btn-secondary" style="padding: 0.25rem 0.75rem; font-size: 0.7rem;" onclick="loadAuditLogs()">
                                <i data-lucide="rotate-cw" style="width: 12px; height: 12px;"></i>
                            </button>
                        </div>
                        <div class="card-body" id="auditLogStream" style="overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">
                            <!-- Log stream -->
                        </div>
                    </div>
                </div>

                <!-- Section: Settings -->
                <div id="section-settings" class="dashboard-section">
                    <div class="card" style="max-width: 600px; margin: 0 auto;">
                        <div class="card-header">
                            <h3>Global Configuration</h3>
                        </div>
                        <div class="card-body">
                            <div class="form-group">
                                <label style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                                    <input type="checkbox" id="notifEnabled" style="width: 16px; height: 16px;">
                                    Broadcast Notifications Enabled
                                </label>
                            </div>
                            <div class="form-group">
                                <label>Telegram Bot Secret</label>
                                <input type="password" id="tgToken" class="form-input" placeholder="000000:ABC...">
                            </div>
                            <div class="form-group">
                                <label>Telegram Destination ID</label>
                                <input type="text" id="tgChat" class="form-input" placeholder="-100...">
                            </div>
                            <div class="form-group">
                                <label>Discord Webhook URL</label>
                                <input type="text" id="dsWebhook" class="form-input" placeholder="https://discord.com/api/webhooks/...">
                            </div>
                            <button class="btn btn-primary" style="width: 100%; margin-top: 1rem;" onclick="saveSettings()">Apply Configuration</button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Modals -->
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
                                <option value="disk">Storage Level</option>
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

    <script>
        // Init Lucide
        lucide.createIcons();

        // State Management
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';

        let charts = {};
        let currentRange = '1h';
        let nodes = [];

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
            
            if (section === 'explorer') loadExplorerMetadata();
            if (section === 'logs') loadAuditLogs();
            if (section === 'alerts') loadAlertRules();
            if (section === 'settings') loadSettings();
            if (section === 'manual') updateManualTargets();
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
            try {
                const resp = await apiFetch('/api/v1/servers', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: document.getElementById('nodeName').value,
                        host: document.getElementById('nodeHost').value,
                        os_type: document.getElementById('nodeOS').value,
                        agent_port: parseInt(document.getElementById('nodePort').value),
                        enabled: true
                    })
                });
                if (resp && resp.ok) {
                    toggleModal('addNodeModal', false);
                    e.target.reset();
                    refreshData();
                } else if (resp) {
                    const err = await resp.json();
                    alert('Deployment Failed: ' + (err.detail || 'Internal Error'));
                }
            } catch (err) { alert('Connection Error'); }
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

        // Charts
        function createLineChart(id, label, color) {
            const ctx = document.getElementById(id).getContext('2d');
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: color + '22',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: true, grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 } } },
                        y: { display: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b', font: { size: 10 } } }
                    }
                }
            });
        }

        function initCharts() {
            charts.cpu = createLineChart('cpuChart', 'CPU', '#f97316');
            charts.mem = createLineChart('memChart', 'RAM', '#3b82f6');
            charts.explorer = createLineChart('explorerChart', 'Metric Value', '#10b981');
        }

        // Data Fetching
        async function refreshData() {
            document.getElementById('updateTimer').textContent = 'Syncing...';
            try {
                const resp = await apiFetch('/api/v1/servers');
                if (!resp) return;
                const data = await resp.json();
                nodes = data.servers;
                
                updateStats();
                updateLiveTable();
                updateNodeGrid();
                updateTrends();
                
                document.getElementById('updateTimer').textContent = 'Last sync: ' + new Date().toLocaleTimeString();
            } catch (e) {
                document.getElementById('updateTimer').textContent = 'Sync Error';
            }
        }

        function updateStats() {
            const online = nodes.filter(n => n.last_status === 'up').length;
            const offline = nodes.length - online;
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            
            const avgCpu = nodes.length ? nodes.reduce((a, b) => a + (b.cpu_percent || 0), 0) / nodes.length : 0;
            const avgMem = nodes.length ? nodes.reduce((a, b) => a + (b.memory_percent || 0), 0) / nodes.length : 0;
            
            document.getElementById('stat-cpu').innerHTML = `${avgCpu.toFixed(1)}<span>%</span>`;
            document.getElementById('stat-mem').innerHTML = `${avgMem.toFixed(1)}<span>%</span>`;
        }

        function updateLiveTable() {
            const body = document.getElementById('liveTableBody');
            const formatBytes = (b) => {
                if (!b) return '0 B';
                const i = Math.floor(Math.log(b) / Math.log(1024));
                return (b / Math.pow(1024, i)).toFixed(1) + ' ' + ['B', 'KB', 'MB', 'GB', 'TB'][i];
            };

            body.innerHTML = nodes.map(n => `
                <tr>
                    <td>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}">
                            <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${n.last_status || 'unknown'}
                        </div>
                    </td>
                    <td class="font-bold text-white">${n.name}</td>
                    <td class="text-mono text-xs text-slate-500">${n.host}</td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="width: 2.5rem;">${(n.cpu_percent || 0).toFixed(0)}%</span>
                            <div class="progress-bar"><div class="progress-fill" style="width: ${n.cpu_percent || 0}%; background: var(--accent);"></div></div>
                        </div>
                    </td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="width: 2.5rem;">${(n.memory_percent || 0).toFixed(0)}%</span>
                            <div class="progress-bar"><div class="progress-fill" style="width: ${n.memory_percent || 0}%; background: #3b82f6;"></div></div>
                        </div>
                    </td>
                    <td>${(n.disk_percent || 0).toFixed(0)}%</td>
                    <td class="text-mono text-[10px] text-slate-500">${formatBytes(n.network_rx)} / ${formatBytes(n.network_tx)}</td>
                </tr>
            `).join('');
        }

        function updateNodeGrid() {
            const grid = document.getElementById('nodeListGrid');
            grid.innerHTML = nodes.map(n => `
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
                    <div style="margin-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                        <button onclick="forceScrapeSingle(${n.id})" title="Force Scrape" style="background: transparent; border: none; color: var(--accent); cursor: pointer; opacity: 0.6;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6">
                            <i data-lucide="zap" style="width: 14px; height: 14px;"></i>
                        </button>
                        <button onclick="deleteNode(${n.id})" style="background: transparent; border: none; color: #f87171; cursor: pointer; opacity: 0.5;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5">
                            <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                        </button>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function updateTrends() {
            try {
                const resp = await apiFetch(`/api/v1/metrics/trend?range=${currentRange}`);
                if (!resp) return;
                const data = await resp.json();
                const labels = data.history.map(h => h.timestamp.split('T')[1].substring(0, 5));

                charts.cpu.data.labels = labels;
                charts.cpu.data.datasets[0].data = data.history.map(h => h.cpu_avg);
                charts.cpu.update('none');

                charts.mem.data.labels = labels;
                charts.mem.data.datasets[0].data = data.history.map(h => h.mem_avg);
                charts.mem.update('none');
            } catch (e) {}
        }

        async function loadExplorerMetadata() {
            const resp = await apiFetch('/api/v1/series');
            if (!resp) return;
            const data = await resp.json();
            const select = document.getElementById('explorerSeries');
            select.innerHTML = '<option value="">Select Metric...</option>' + 
                data.series.sort().map(s => `<option value="${s}">${s}</option>`).join('');
        }

        document.getElementById('runQueryBtn').addEventListener('click', async () => {
            const series = document.getElementById('explorerSeries').value;
            if (!series) return;
            
            const btn = document.getElementById('runQueryBtn');
            btn.disabled = true;
            btn.innerHTML = '<i data-lucide="loader" class="animate-spin" style="width: 14px; height: 14px;"></i> Executing...';
            lucide.createIcons();

            try {
                const resp = await apiFetch(`/api/v1/query?query=${series}`);
                if (!resp) return;
                const data = await resp.json();
                
                const labels = data.result.map(r => r.timestamp.split('T')[1].substring(0, 8));
                charts.explorer.data.labels = labels;
                charts.explorer.data.datasets[0].data = data.result.map(r => r.value);
                charts.explorer.data.datasets[0].label = series;
                charts.explorer.update();
                
                document.getElementById('explorerTitle').textContent = 'Results for: ' + series;
            } catch (e) {
                alert('Query failed');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i data-lucide="play" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Execute Query';
                lucide.createIcons();
            }
        });

        async function injectManualMetric() {
            const name = document.getElementById('manualMetricName').value;
            const value = parseFloat(document.getElementById('manualMetricValue').value);
            const type = document.getElementById('manualMetricType').value;
            
            if (!name || isNaN(value)) return;
            
            const resp = await apiFetch('/api/v1/metrics', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, value, type})
            });
            
            if (resp && resp.ok) alert('Metric Injected');
        }

        function updateManualTargets() {
            const select = document.getElementById('forceScrapeTarget');
            select.innerHTML = nodes.map(n => `<option value="${n.id}">${n.name} (${n.host})</option>`).join('');
        }

        async function forceScrape() {
            const id = document.getElementById('forceScrapeTarget').value;
            forceScrapeSingle(id);
        }

        async function forceScrapeSingle(id) {
            const resp = await apiFetch(`/api/v1/servers/${id}/scrape`, {method: 'POST'});
            if (resp && resp.ok) {
                alert('Scrape Triggered');
                refreshData();
            } else {
                alert('Scrape command failed (Endpoint not yet implemented in backend)');
            }
        }

        async function loadAuditLogs() {
            const resp = await apiFetch('/api/v1/audit-log?limit=100');
            if (!resp) return;
            const data = await resp.json();
            const stream = document.getElementById('auditLogStream');
            stream.innerHTML = data.logs.map(l => `
                <div style="display: flex; gap: 1rem; margin-bottom: 0.25rem;">
                    <span style="color: #64748b;">[${l.timestamp ? l.timestamp.split('T')[1].substring(0, 8) : 'N/A'}]</span>
                    <span style="color: #3b82f6; width: 100px;">${l.username}</span>
                    <span style="color: #f8fafc;">${l.action}</span>
                    <span style="color: #64748b;">${l.target || ''}</span>
                </div>
            `).join('');
            stream.scrollTop = stream.scrollHeight;
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

        async function deleteNode(id) {
            if (confirm('Permanently decommission this node?')) {
                await apiFetch(`/api/v1/servers/${id}`, {method: 'DELETE'});
                refreshData();
            }
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

        // Initialization
        initCharts();
        refreshData();
        setInterval(refreshData, 15000);
    </script>
</body>
</html>"""
