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

        .action-btn { background: transparent; border: none; cursor: pointer; opacity: 0.6; transition: all 0.2s; padding: 4px; display: flex; align-items: center; justify-content: center; }
        .action-btn:hover { opacity: 1; transform: scale(1.1); }
        .action-btn:active { transform: scale(0.9); }

        .search-box { display: flex; align-items: center; gap: 0.5rem; background: #020617; border: 1px solid var(--border); padding: 0.4rem 0.75rem; border-radius: 0.75rem; flex: 1; max-width: 300px; }
        .search-box input { background: transparent; border: none; color: white; font-size: 0.85rem; width: 100%; outline: none; }
        .search-box i { color: var(--text-muted); }
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
                            <div class="stat-label">Avg CPU</div>
                            <div class="stat-value" id="stat-cpu">0<span>%</span></div>
                        </div>
                        <div class="stat-card up">
                            <div class="stat-label">Avg RAM</div>
                            <div class="stat-value" id="stat-mem">0<span>%</span></div>
                        </div>
                        <div class="stat-card alert">
                            <div class="stat-label">Avg Disk</div>
                            <div class="stat-value" id="stat-disk">0<span>%</span></div>
                        </div>
                        <div class="stat-card up">
                            <div class="stat-label">Net Throughput</div>
                            <div class="stat-value" id="stat-net">0<span>MB/s</span></div>
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
                        <div class="card">
                            <div class="card-header">
                                <h3>Network Throughput</h3>
                                <i data-lucide="activity" style="width: 14px; height: 14px; color: var(--text-muted);"></i>
                            </div>
                            <div class="card-body">
                                <canvas id="netChart"></canvas>
                            </div>
                        </div>
                        <div class="card">
                            <div class="card-header">
                                <h3>Storage Distribution</h3>
                                <i data-lucide="hard-drive" style="width: 14px; height: 14px; color: var(--text-muted);"></i>
                            </div>
                            <div class="card-body">
                                <canvas id="diskChart"></canvas>
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
                    <div class="card-header" style="border-bottom: none; padding-bottom: 0;">
                        <h2 id="viewTitle">Infrastructure Inventory</h2>
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <div class="search-box">
                                <i data-lucide="search" style="width: 14px; height: 14px;"></i>
                                <input type="text" id="nodeSearch" placeholder="Search nodes..." oninput="filterNodes()">
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
                                    <th style="cursor: pointer;" onclick="sortNodes('disk_percent')">Storage <i data-lucide="chevrons-up-down" style="width: 10px;"></i></th>
                                    <th>Traffic (RX/TX)</th>
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
                            <input type="text" id="logSearch" class="form-input" placeholder="Search logs..." style="width: 200px; padding: 0.3rem 0.75rem; font-size: 0.75rem;" oninput="filterLogs()">
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
                                    <span style="color: white;">8090</span>
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
            charts.net = createLineChart('netChart', 'Net MB/s', '#10b981');
            charts.disk = createLineChart('diskChart', 'Disk %', '#f59e0b');
        }

        // Data Fetching
        let sortKey = 'name';
        let sortOrder = 1;

        async function refreshData() {
            document.getElementById('updateTimer').textContent = 'Syncing...';
            try {
                const resp = await apiFetch('/api/v1/servers');
                if (!resp) return;
                const data = await resp.json();
                nodes = data.servers;
                
                filterNodes(); // This will also call update displays
                
                document.getElementById('updateTimer').textContent = 'Last sync: ' + new Date().toLocaleTimeString();
            } catch (e) {
                document.getElementById('updateTimer').textContent = 'Sync Error';
            }
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
            updateTrends();
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
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            
            const count = nodes.length || 1;
            const avgCpu = nodes.reduce((a, b) => a + (b.cpu_percent || 0), 0) / count;
            const avgMem = nodes.reduce((a, b) => a + (b.memory_percent || 0), 0) / count;
            const avgDisk = nodes.reduce((a, b) => a + (b.disk_percent || 0), 0) / count;
            const totalNet = nodes.reduce((a, b) => a + (b.network_rx || 0) + (b.network_tx || 0), 0) / (1024 * 1024);
            
            if (document.getElementById('stat-cpu')) document.getElementById('stat-cpu').innerHTML = `${avgCpu.toFixed(1)}<span>%</span>`;
            if (document.getElementById('stat-mem')) document.getElementById('stat-mem').innerHTML = `${avgMem.toFixed(1)}<span>%</span>`;
            if (document.getElementById('stat-disk')) document.getElementById('stat-disk').innerHTML = `${avgDisk.toFixed(1)}<span>%</span>`;
            if (document.getElementById('stat-net')) document.getElementById('stat-net').innerHTML = `${totalNet.toFixed(2)}<span>MB/s</span>`;
        }

        function updateLiveTable(data) {
            const overviewBody = document.getElementById('liveTableBody');
            const nodesBody = document.getElementById('nodesTableBody');
            if (!overviewBody && !nodesBody) return;
            
            const targetData = data || nodes;
            const formatBytes = (b) => {
                if (!b) return '0 B';
                const i = Math.floor(Math.log(b) / Math.log(1024));
                return (b / Math.pow(1024, i)).toFixed(1) + ' ' + ['B', 'KB', 'MB', 'GB', 'TB'][i];
            };

            const html = targetData.map(n => `
                <tr>
                    <td>
                        <div class="status-badge ${n.last_status === 'up' ? 'up' : 'down'}" title="${n.error_message || ''}">
                            <span class="status-dot ${n.last_status === 'up' ? 'pulse' : ''}"></span>
                            ${n.last_status || 'unknown'}
                        </div>
                    </td>
                    <td>
                        <div class="font-bold text-white">${n.name}</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.25rem;">
                            <i data-lucide="package" style="width: 10px; height: 10px;"></i>
                            ${n.os_type === 'windows' ? 'windows_exporter' : 'node_exporter'}
                            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background: ${n.exporter_version === 'active' ? 'var(--success)' : (n.last_status === 'up' ? '#f59e0b' : 'var(--danger)')}; margin-left: 0.25rem;"></span>
                        </div>
                    </td>
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
                    <td>
                        <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                            ${(() => {
                                try {
                                    const raw = n.disk_info;
                                    if (!raw || raw === 'null') throw 0;
                                    const disks = typeof raw === 'string' ? JSON.parse(raw) : raw;
                                    if (Array.isArray(disks)) {
                                        return disks.map(d => {
                                            const pct = d.percent || 0;
                                            return '<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.65rem;">' +
                                                '<span style="min-width:1.8rem;color:white;font-weight:600;">' + (d.volume || '?') + '</span>' +
                                                '<div class="progress-bar" style="height:4px;flex-grow:1;"><div class="progress-fill" style="width:' + pct + '%;background:' + (pct > 90 ? 'var(--danger)' : '#f59e0b') + ';"></div></div>' +
                                                '<span style="min-width:2rem;text-align:right;opacity:0.7;">' + pct.toFixed(0) + '%</span></div>';
                                        }).join('');
                                    }
                                    return Object.entries(disks).map(([vol, pct]) =>
                                        '<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.65rem;">' +
                                        '<span style="min-width:1.8rem;color:white;font-weight:600;">' + vol + '</span>' +
                                        '<div class="progress-bar" style="height:4px;flex-grow:1;"><div class="progress-fill" style="width:' + pct + '%;background:' + (pct > 90 ? 'var(--danger)' : '#f59e0b') + ';"></div></div>' +
                                        '<span style="min-width:2rem;text-align:right;opacity:0.7;">' + Math.round(pct) + '%</span></div>'
                                    ).join('');
                                } catch(e) {
                                    const p = n.disk_percent || 0;
                                    return '<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.65rem;">' +
                                        '<span style="min-width:1.8rem;color:white;font-weight:600;">All</span>' +
                                        '<div class="progress-bar" style="height:4px;flex-grow:1;"><div class="progress-fill" style="width:' + p + '%;background:' + (p > 90 ? 'var(--danger)' : '#f59e0b') + ';"></div></div>' +
                                        '<span style="min-width:2rem;text-align:right;opacity:0.7;">' + Math.round(p) + '%</span></div>';
                                }
                            })()}
                        </div>
                    </td>
                    <td class="text-mono text-[10px] text-slate-500">${formatBytes(n.network_rx)} / ${formatBytes(n.network_tx)}</td>
                    <td style="text-align: right;">
                        <div style="display: flex; gap: 0.25rem; justify-content: flex-end;">
                            <button onclick="forceScrapeSingle(${n.id})" title="Force Scrape" class="action-btn" style="color: var(--accent);">
                                <i data-lucide="zap" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showEditModal(${n.id})" title="Edit Node" class="action-btn" style="color: #3b82f6;">
                                <i data-lucide="settings" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="showDeployModal(${n.id})" title="Deploy Agent" class="action-btn" style="color: var(--success);">
                                <i data-lucide="download-cloud" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button onclick="deleteNode(${n.id})" title="Delete Node" class="action-btn" style="color: #f87171;">
                                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                            </button>
                        </div>
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

                charts.net.data.labels = labels;
                charts.net.data.datasets[0].data = data.history.map(h => (h.net_rx_avg + h.net_tx_avg) / (1024 * 1024));
                charts.net.update('none');

                charts.disk.data.labels = labels;
                charts.disk.data.datasets[0].data = data.history.map(h => nodes.reduce((a, b) => a + (b.disk_percent || 0), 0) / (nodes.length || 1));
                charts.disk.update('none');
            } catch (e) {}
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
        initCharts();
        refreshData();
        setInterval(refreshData, 15000);
    </script>
</body>
</html>"""

