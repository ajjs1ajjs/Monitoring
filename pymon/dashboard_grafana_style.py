"""Grafana-style Enterprise Dashboard"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon - Enterprise Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { 
            --bg: #0b0c0f; --card: #14161a; --card-hover: #1a1d22; --border: #262a30; --border-light: #363b42;
            --text: #e0e0e0; --muted: #8b8d98; --muted-light: #a0a2ab; --blue: #5794f2; --blue-glow: rgba(87,148,242,0.15);
            --green: #73bf69; --green-glow: rgba(115,191,105,0.15); --red: #f2495c; --red-glow: rgba(242,73,92,0.15);
            --yellow: #f2cc0c; --yellow-glow: rgba(242,204,12,0.15); --purple: #b877d9; --purple-glow: rgba(184,119,217,0.15);
            --orange: #ff780a; --cyan: #00d8d8;
        }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; font-size: 13px; }
        
        /* Top Navigation */
        .top-nav { background: linear-gradient(180deg, #1a1d22 0%, #14161a 100%); border-bottom: 1px solid var(--border); padding: 0 20px; height: 56px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        .nav-left { display: flex; align-items: center; gap: 24px; }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--blue), #2c7bd9); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white; font-weight: bold; box-shadow: 0 2px 8px rgba(87,148,242,0.3); }
        .logo h1 { color: var(--blue); font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item { display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 8px; cursor: pointer; color: var(--muted); font-weight: 500; font-size: 13px; border: none; background: transparent; transition: all 0.2s; }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active { background: var(--blue-glow); color: var(--blue); box-shadow: inset 0 0 0 1px rgba(87,148,242,0.3); }
        .nav-right { display: flex; align-items: center; gap: 16px; }
        
        /* Time Range Selector */
        .time-range { display: flex; gap: 2px; background: var(--card); border-radius: 8px; padding: 3px; border: 1px solid var(--border); }
        .time-btn { padding: 6px 14px; background: transparent; border: none; border-radius: 5px; color: var(--muted); font-size: 12px; cursor: pointer; transition: all 0.2s; }
        .time-btn:hover { color: var(--text); }
        .time-btn.active { background: var(--blue); color: white; }
        
        /* Main Content */
        .main { padding: 20px; max-width: 1920px; margin: 0 auto; }
        
        /* Stats Overview */
        .stats-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; transition: all 0.3s; cursor: pointer; }
        .stat-card:hover { transform: translateY(-2px); border-color: var(--border-light); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
        .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .stat-content { flex: 1; }
        .stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
        .stat-label { color: var(--muted); font-size: 12px; margin-top: 4px; }
        .stat-trend { display: flex; align-items: center; gap: 4px; font-size: 12px; margin-top: 8px; }
        .stat-trend.up { color: var(--green); }
        .stat-trend.down { color: var(--red); }
        
        /* Grid Layout */
        .dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .grid-item { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .grid-item.col-4 { grid-column: span 4; }
        .grid-item.col-6 { grid-column: span 6; }
        .grid-item.col-8 { grid-column: span 8; }
        .grid-item.col-12 { grid-column: span 12; }
        .grid-item.row-2 { grid-row: span 2; }
        
        /* Panel */
        .panel { height: 100%; display: flex; flex-direction: column; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); }
        .panel-title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .panel-actions { display: flex; gap: 8px; }
        .panel-body { flex: 1; padding: 16px; min-height: 200px; position: relative; }
        
        /* Chart Container */
        .chart-container { width: 100%; height: 250px; position: relative; }
        .chart-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
        .legend-item { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: background 0.2s; }
        .legend-item:hover { background: rgba(255,255,255,0.05); }
        .legend-color { width: 12px; height: 12px; border-radius: 3px; }
        .legend-name { font-size: 12px; color: var(--text); }
        .legend-value { font-size: 12px; color: var(--muted); font-weight: 600; }
        
        /* Server Cards */
        .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; max-height: 600px; overflow-y: auto; padding-right: 8px; }
        .server-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; transition: all 0.2s; cursor: pointer; }
        .server-card:hover { border-color: var(--border-light); transform: translateY(-1px); }
        .server-card.online { border-left: 3px solid var(--green); }
        .server-card.offline { border-left: 3px solid var(--red); }
        .server-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .server-name { font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .server-status { width: 8px; height: 8px; border-radius: 50%; }
        .server-os { font-size: 11px; padding: 2px 8px; background: rgba(255,255,255,0.05); border-radius: 4px; color: var(--muted); }
        .server-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .metric-box { background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center; }
        .metric-label { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-bottom: 4px; }
        .metric-value { font-size: 18px; font-weight: 600; }
        .metric-progress { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; margin-top: 6px; overflow: hidden; }
        .metric-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
        
        /* Alert List */
        .alert-list { max-height: 500px; overflow-y: auto; }
        .alert-item { padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; transition: background 0.2s; }
        .alert-item:hover { background: rgba(255,255,255,0.02); }
        .alert-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .alert-content { flex: 1; }
        .alert-title { font-weight: 500; font-size: 13px; }
        .alert-desc { color: var(--muted); font-size: 11px; margin-top: 2px; }
        .alert-time { color: var(--muted-light); font-size: 11px; }
        
        /* Gauge */
        .gauge-container { display: flex; justify-content: space-around; padding: 20px 0; }
        .gauge-item { text-align: center; }
        .gauge-value { font-size: 32px; font-weight: 700; color: var(--text); }
        .gauge-label { color: var(--muted); font-size: 12px; margin-top: 8px; }
        .gauge-bar { width: 120px; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; margin: 12px auto; overflow: hidden; }
        .gauge-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
        
        /* Search and Filters */
        .toolbar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-box { flex: 1; min-width: 200px; position: relative; }
        .search-box input { width: 100%; padding: 10px 16px 10px 40px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 13px; }
        .search-box input:focus { outline: none; border-color: var(--blue); }
        .search-box i { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--muted); }
        .filter-btn { padding: 10px 16px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 13px; cursor: pointer; transition: all 0.2s; }
        .filter-btn:hover { border-color: var(--border-light); }
        .filter-btn.active { background: var(--blue); border-color: var(--blue); }
        
        /* Buttons */
        .btn { padding: 10px 18px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
        .btn-primary { background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(44,123,217,0.4); }
        .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--card-hover); }
        .btn-danger { background: linear-gradient(135deg, rgba(242,73,92,0.3), rgba(242,73,92,0.15)); color: var(--red); }
        .btn-danger:hover { background: linear-gradient(135deg, rgba(242,73,92,0.5), rgba(242,73,92,0.3)); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        
        /* Table */
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        tr:hover td { background: rgba(255,255,255,0.02); }
        
        /* Status Badges */
        .badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
        .badge-success { background: var(--green-glow); color: var(--green); }
        .badge-danger { background: var(--red-glow); color: var(--red); }
        .badge-warning { background: var(--yellow-glow); color: var(--yellow); }
        .badge-info { background: var(--blue-glow); color: var(--blue); }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--border-light); }
        
        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-title { font-size: 18px; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 24px; cursor: pointer; }
        
        /* Form */
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 600; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 13px; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: var(--blue); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        
        /* Tabs */
        .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
        .tab { padding: 12px 20px; color: var(--muted); cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab:hover { color: var(--text); }
        .tab.active { color: var(--blue); border-bottom-color: var(--blue); }
        
        /* Animations */
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-pulse { animation: pulse 2s infinite; }
        .animate-spin { animation: spin 1s linear infinite; }
        
        /* Responsive */
        @media (max-width: 1200px) { .grid-item.col-4, .grid-item.col-6, .grid-item.col-8 { grid-column: span 12; } }
        @media (max-width: 768px) { .nav-menu { display: none; } .stats-overview { grid-template-columns: 1fr; } .main { padding: 12px; } }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="nav-left">
            <div class="logo"><div class="logo-icon">P</div><h1>PyMon</h1></div>
            <div class="nav-menu">
                <button class="nav-item active" data-section="dashboard"><i class="fas fa-chart-line"></i> Dashboard</button>
                <button class="nav-item" data-section="servers"><i class="fas fa-server"></i> Servers</button>
                <button class="nav-item" data-section="alerts"><i class="fas fa-bell"></i> Alerts</button>
                <button class="nav-item" data-section="reports"><i class="fas fa-file-alt"></i> Reports</button>
                <button class="nav-item" data-section="settings"><i class="fas fa-cog"></i> Settings</button>
            </div>
        </div>
        <div class="nav-right">
            <div class="time-range">
                <button class="time-btn" data-range="5m">5m</button>
                <button class="time-btn" data-range="15m">15m</button>
                <button class="time-btn active" data-range="1h">1h</button>
                <button class="time-btn" data-range="6h">6h</button>
                <button class="time-btn" data-range="24h">24h</button>
            </div>
            <button class="btn btn-secondary btn-sm" id="refreshBtn"><i class="fas fa-sync"></i></button>
            <button class="btn btn-secondary btn-sm" id="logoutBtn"><i class="fas fa-sign-out-alt"></i></button>
        </div>
    </nav>
    
    <main class="main">
        <!-- Dashboard Section -->
        <div id="section-dashboard" class="section-content active">
            <!-- Stats Overview -->
            <div class="stats-overview">
                <div class="stat-card" onclick="filterBy('online')" style="cursor:pointer;">
                    <div class="stat-icon" style="background: var(--green-glow); color: var(--green);"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-online">0</div>
                        <div class="stat-label">Online Servers</div>
                        <div class="stat-trend up" id="trend-online"><i class="fas fa-arrow-up"></i> All systems operational</div>
                    </div>
                </div>
                <div class="stat-card" onclick="filterBy('offline')" style="cursor:pointer;">
                    <div class="stat-icon" style="background: var(--red-glow); color: var(--red);"><i class="fas fa-times-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-offline">0</div>
                        <div class="stat-label">Offline Servers</div>
                        <div class="stat-trend down" id="trend-offline"></div>
                    </div>
                </div>
                <div class="stat-card" style="cursor:pointer;">
                    <div class="stat-icon" style="background: var(--blue-glow); color: var(--blue);"><i class="fas fa-microchip"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-cpu-avg">0%</div>
                        <div class="stat-label">Avg CPU Usage</div>
                    </div>
                </div>
                <div class="stat-card" style="cursor:pointer;">
                    <div class="stat-icon" style="background: var(--yellow-glow); color: var(--yellow);"><i class="fas fa-memory"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-mem-avg">0%</div>
                        <div class="stat-label">Avg Memory Usage</div>
                    </div>
                </div>
            </div>
            
            <!-- Toolbar -->
            <div class="toolbar">
                <div class="search-box"><i class="fas fa-search"></i><input type="text" id="serverSearch" placeholder="Search servers..."></div>
                <select id="filterStatus" class="filter-btn"><option value="">All Status</option><option value="up">Online</option><option value="down">Offline</option></select>
                <select id="filterOS" class="filter-btn"><option value="">All OS</option><option value="linux">Linux</option><option value="windows">Windows</option></select>
                <button class="btn btn-primary btn-sm" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button>
            </div>
            
            <!-- Dashboard Grid -->
            <div class="dashboard-grid">
                <!-- CPU Usage Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-microchip" style="color: var(--blue);"></i> CPU Usage</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="expandPanel('cpu')"><i class="fas fa-expand"></i></button></div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="cpuChart"></canvas></div>
                            <div class="chart-legend" id="cpuLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Memory Usage Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-memory" style="color: var(--yellow);"></i> Memory Usage</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="expandPanel('memory')"><i class="fas fa-expand"></i></button></div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="memoryChart"></canvas></div>
                            <div class="chart-legend" id="memoryLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Disk Usage Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-hdd" style="color: var(--green);"></i> Disk Usage</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="expandPanel('disk')"><i class="fas fa-expand"></i></button></div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="diskChart"></canvas></div>
                            <div class="chart-legend" id="diskLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Network Traffic Chart -->
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-network-wired" style="color: var(--purple);"></i> Network Traffic</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="expandPanel('network')"><i class="fas fa-expand"></i></button></div>
                        </div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="networkChart"></canvas></div>
                            <div class="chart-legend" id="networkLegend"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Server Map -->
                <div class="grid-item col-8">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-server" style="color: var(--cyan);"></i> Server Map</div>
                            <div class="panel-actions">
                                <select id="serverSortSelect" class="filter-btn btn-sm"><option value="name">Sort by Name</option><option value="status">Sort by Status</option><option value="cpu">Sort by CPU</option><option value="memory">Sort by Memory</option></select>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="server-grid" id="serverGrid"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Alerts -->
                <div class="grid-item col-4 row-2">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-bell" style="color: var(--orange);"></i> Recent Alerts</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="showSection('alerts')">View All</button></div>
                        </div>
                        <div class="panel-body" style="padding: 0;">
                            <div class="alert-list" id="alertList"></div>
                        </div>
                    </div>
                </div>
                
                <!-- RAID Status -->
                <div class="grid-item col-12">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-hdd" style="color: var(--green);"></i> RAID Arrays Status</div>
                            <div class="panel-actions"><button class="btn btn-secondary btn-sm" onclick="refreshRAID()"><i class="fas fa-sync"></i></button></div>
                        </div>
                        <div class="panel-body">
                            <div id="raidStatus"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Servers Section -->
        <div id="section-servers" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title"><i class="fas fa-server"></i> Monitored Servers</div>
                        <div class="panel-actions"><button class="btn btn-primary btn-sm" id="addServerBtn2"><i class="fas fa-plus"></i> Add Server</button></div>
                    </div>
                    <div class="panel-body" style="padding:0;">
                        <div class="table-container">
                            <table>
                                <thead><tr><th>Status</th><th>Name</th><th>Host:Port</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last Check</th><th>Actions</th></tr></thead>
                                <tbody id="serversTable"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Alerts Section -->
        <div id="section-alerts" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title"><i class="fas fa-bell"></i> Alert Rules</div>
                        <div class="panel-actions"><button class="btn btn-primary btn-sm" id="addAlertBtn"><i class="fas fa-plus"></i> New Alert</button></div>
                    </div>
                    <div class="panel-body" style="padding:0;">
                        <div class="alert-list" id="alertsList"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Reports Section -->
        <div id="section-reports" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><i class="fas fa-file-alt"></i> Reports</div></div>
                    <div class="panel-body"><p style="color: var(--muted); text-align: center; padding: 40px;">Reports functionality coming soon...</p></div>
                </div>
            </div>
        </div>
        
        <!-- Settings Section -->
        <div id="section-settings" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><i class="fas fa-cog"></i> Settings</div></div>
                    <div class="panel-body"><p style="color: var(--muted); text-align: center; padding: 40px;">Settings functionality coming soon...</p></div>
                </div>
            </div>
        </div>
    </main>
    
    <!-- Add Server Modal -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title">Add Server</div><button class="modal-close" id="closeServerModal">&times;</button></div>
            <form id="addServerForm">
                <div class="form-group"><label>Server Name</label><input type="text" id="server-name" required placeholder="Production Server"></div>
                <div class="form-group"><label>Host / IP Address</label><input type="text" id="server-host" required placeholder="192.168.1.100"></div>
                <div class="form-row">
                    <div class="form-group"><label>Operating System</label><select id="server-os"><option value="linux">Linux</option><option value="windows">Windows</option></select></div>
                    <div class="form-group"><label>Agent Port</label><input type="number" id="server-port" value="9100"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%">Add Server</button>
            </form>
        </div>
    </div>
    
    <!-- Alert Modal -->
    <div class="modal" id="alertModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title" id="alertModalTitle">Add Alert Rule</div><button class="modal-close" id="closeAlertModal">&times;</button></div>
            <form id="alertForm">
                <input type="hidden" id="alert-id">
                <div class="form-group"><label>Alert Name</label><input type="text" id="alert-name" required placeholder="High CPU"></div>
                <div class="form-row">
                    <div class="form-group"><label>Metric</label><select id="alert-metric"><option value="cpu">CPU Usage</option><option value="memory">Memory</option><option value="disk">Disk</option></select></div>
                    <div class="form-group"><label>Threshold (%)</label><input type="number" id="alert-threshold" value="80"></div>
                </div>
                <div class="form-group"><label>Severity</label><select id="alert-severity"><option value="warning">Warning</option><option value="critical">Critical</option></select></div>
                <button type="submit" class="btn btn-primary" style="width:100%">Save Alert</button>
            </form>
        </div>
    </div>

<script>
const token = localStorage.getItem('token');
if (!token) window.location.href = '/login';

let servers = [];
let charts = {};
let currentRange = '1h';
let currentFilter = '';
const colors = ['#73bf69', '#f2cc0c', '#5794f2', '#ff780a', '#b877d9', '#00d8d8', '#f2495c', '#9673b9'];

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', function() {
        const section = this.dataset.section;
        if (section) showSection(section);
    });
});

document.querySelectorAll('.time-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentRange = this.dataset.range;
        loadData();
    });
});

document.getElementById('logoutBtn').addEventListener('click', () => { localStorage.removeItem('token'); window.location.href = '/login'; });
document.getElementById('refreshBtn').addEventListener('click', () => { loadData(); });
document.getElementById('addServerBtn').addEventListener('click', () => { document.getElementById('addServerModal').classList.add('active'); });
document.getElementById('closeServerModal').addEventListener('click', () => { document.getElementById('addServerModal').classList.remove('active'); });
document.getElementById('addServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await fetch('/api/servers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({
            name: document.getElementById('server-name').value,
            host: document.getElementById('server-host').value,
            os_type: document.getElementById('server-os').value,
            agent_port: parseInt(document.getElementById('server-port').value) || 9100
        })
    });
    document.getElementById('addServerModal').classList.remove('active');
    loadData();
});

['serverSearch', 'filterStatus', 'filterOS'].forEach(id => {
    document.getElementById(id).addEventListener('input', loadData);
    document.getElementById(id).addEventListener('change', loadData);
});

function showSection(section) {
    document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById('section-' + section).classList.add('active');
    document.querySelector(`.nav-item[data-section="${section}"]`)?.classList.add('active');
}

async function loadData() {
    try {
        const resp = await fetch('/api/servers', {headers: {'Authorization': 'Bearer ' + token}});
        const data = await resp.json();
        servers = data.servers || [];
        updateStats();
        updateCharts();
        updateServerGrid();
        updateServerTable();
    } catch(e) { console.error(e); }
}

function updateStats() {
    const online = servers.filter(s => s.last_status === 'up').length;
    const offline = servers.length - online;
    const cpuAvg = servers.length ? (servers.reduce((a, s) => a + (s.cpu_percent || 0), 0) / servers.length).toFixed(1) : 0;
    const memAvg = servers.length ? (servers.reduce((a, s) => a + (s.memory_percent || 0), 0) / servers.length).toFixed(1) : 0;
    
    document.getElementById('stat-online').textContent = online;
    document.getElementById('stat-offline').textContent = offline;
    document.getElementById('stat-cpu-avg').textContent = cpuAvg + '%';
    document.getElementById('stat-mem-avg').textContent = memAvg + '%';
}

function updateCharts() {
    const labels = generateLabels();
    const filtered = getFilteredServers();
    
    if (!charts.cpu) {
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.memory = new Chart(document.getElementById('memoryChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.disk = new Chart(document.getElementById('diskChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.network = new Chart(document.getElementById('networkChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts(' MB/s', 0, null)});
    }
    
    const getDatasets = (key, unit) => {
        if (!filtered.length) return [{label: 'No Data', data: rand(12, 0, 10), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true, tension: 0.3}];
        return filtered.map((s, i) => ({
            label: s.name,
            data: rand(12, s[key + '_percent'] || Math.random() * 50, 20),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20',
            fill: true,
            tension: 0.3
        }));
    };
    
    charts.cpu.data.labels = labels;
    charts.cpu.data.datasets = getDatasets('cpu', '%');
    charts.cpu.update();
    updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
    
    charts.memory.data.labels = labels;
    charts.memory.data.datasets = getDatasets('memory', '%');
    charts.memory.update();
    updateLegend('memoryLegend', charts.memory.data.datasets, '%');
    
    charts.disk.data.labels = labels;
    charts.disk.data.datasets = getDatasets('disk', '%');
    charts.disk.update();
    updateLegend('diskLegend', charts.disk.data.datasets, '%');
    
    charts.network.data.labels = labels;
    charts.network.data.datasets = getDatasets('network', ' MB/s');
    charts.network.update();
    updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
}

function updateLegend(id, datasets, unit) {
    const el = document.getElementById(id);
    el.innerHTML = datasets.map((ds, i) => `
        <div class="legend-item">
            <div class="legend-color" style="background: ${ds.borderColor}"></div>
            <div class="legend-name">${ds.label}</div>
            <div class="legend-value">${ds.data[ds.data.length-1].toFixed(1)}${unit}</div>
        </div>
    `).join('');
}

function updateServerGrid() {
    const el = document.getElementById('serverGrid');
    el.innerHTML = servers.map(s => {
        const status = s.last_status === 'up' ? 'online' : 'offline';
        const statusColor = s.last_status === 'up' ? 'var(--green)' : 'var(--red)';
        const cpuColor = (s.cpu_percent || 0) > 80 ? 'var(--red)' : (s.cpu_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        const memColor = (s.memory_percent || 0) > 80 ? 'var(--red)' : (s.memory_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        return `
        <div class="server-card ${status}" onclick="window.location.href='/server/${s.id}'">
            <div class="server-header">
                <div class="server-name">
                    <div class="server-status" style="background: ${statusColor}"></div>
                    ${s.name}
                </div>
                <div class="server-os">${s.os_type}</div>
            </div>
            <div class="server-metrics">
                <div class="metric-box">
                    <div class="metric-label">CPU</div>
                    <div class="metric-value" style="color: ${cpuColor}">${(s.cpu_percent || 0).toFixed(1)}%</div>
                    <div class="metric-progress"><div class="metric-fill" style="width: ${s.cpu_percent || 0}%; background: ${cpuColor}"></div></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Memory</div>
                    <div class="metric-value" style="color: ${memColor}">${(s.memory_percent || 0).toFixed(1)}%</div>
                    <div class="metric-progress"><div class="metric-fill" style="width: ${s.memory_percent || 0}%; background: ${memColor}"></div></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Disk</div>
                    <div class="metric-value" style="color: var(--blue)">${(s.disk_percent || 0).toFixed(1)}%</div>
                </div>
            </div>
        </div>`;
    }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No servers configured</p>';
}

function updateServerTable() {
    const el = document.getElementById('serversTable');
    el.innerHTML = servers.map(s => {
        const statusBadge = s.last_status === 'up' ? '<span class="badge badge-success"><i class="fas fa-circle"></i> Online</span>' : '<span class="badge badge-danger"><i class="fas fa-circle"></i> Offline</span>';
        return `<tr>
            <td>${statusBadge}</td>
            <td><strong>${s.name}</strong></td>
            <td style="color: var(--muted)">${s.host}:${s.agent_port || 9100}</td>
            <td>${s.os_type}</td>
            <td>${(s.cpu_percent || 0).toFixed(1)}%</td>
            <td>${(s.memory_percent || 0).toFixed(1)}%</td>
            <td>${(s.disk_percent || 0).toFixed(1)}%</td>
            <td style="color: var(--muted)">${s.last_check ? s.last_check.substring(11, 19) : '-'}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="scrapeServer(${s.id})"><i class="fas fa-sync"></i></button>
                <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id})"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" style="text-align: center; padding: 40px; color: var(--muted);">No servers</td></tr>';
}

function getFilteredServers() {
    const search = document.getElementById('serverSearch').value.toLowerCase();
    const status = document.getElementById('filterStatus').value;
    const os = document.getElementById('filterOS').value;
    return servers.filter(s => {
        if (search && !s.name.toLowerCase().includes(search) && !s.host.toLowerCase().includes(search)) return false;
        if (status && s.last_status !== status) return false;
        if (os && s.os_type !== os) return false;
        return true;
    });
}

function generateLabels() {
    const labels = [];
    const now = new Date();
    const pts = 12;
    for (let i = pts-1; i >= 0; i--) {
        const t = new Date(now.getTime() - i * 5 * 60000);
        labels.push(t.getHours().toString().padStart(2,'0') + ':' + t.getMinutes().toString().padStart(2,'0'));
    }
    return labels;
}

function rand(n, base, variance) {
    const arr = [];
    let val = base;
    for (let i = 0; i < n; i++) {
        val = Math.max(0, Math.min(100, val + (Math.random() - 0.5) * variance));
        arr.push(val);
    }
    return arr;
}

function chartOpts(suffix, min, max) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        scales: {
            y: { min, max, grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#666', font: { size: 10 }, callback: v => v + suffix } },
            x: { grid: { display: false }, ticks: { color: '#666', font: { size: 10 } } }
        },
        plugins: { legend: { display: false } }
    };
}

function filterBy(type) {
    document.getElementById('filterStatus').value = type === 'online' ? 'up' : type === 'offline' ? 'down' : '';
    loadData();
}

async function scrapeServer(id) {
    const btn = event.target.closest('button');
    const icon = btn.querySelector('i');
    icon.classList.add('animate-spin');
    try {
        await fetch(`/api/servers/${id}/scrape`, { method: 'POST', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
    } catch(e) { alert('Error: ' + e.message); }
    setTimeout(() => icon.classList.remove('animate-spin'), 500);
}

async function deleteServer(id) {
    if (confirm('Delete this server?')) {
        await fetch(`/api/servers/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
    }
}

// Auto-refresh
let refreshInterval = setInterval(loadData, 30000);

// Initial load
loadData();
</script>
</body>
</html>"""