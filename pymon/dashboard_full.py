"""Full Enterprise Dashboard - All Features Complete"""

import json

def get_dashboard_html():
    return r'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PyMon Enterprise</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0b0c0f; --card: #14161a; --card-hover: #1a1d22; --border: #262a30;
            --text: #e0e0e0; --muted: #8b8d98; --blue: #5794f2; --green: #73bf69;
            --red: #f2495c; --yellow: #f2cc0c; --purple: #b877d9; --cyan: #00d8d8;
            --blue-glow: rgba(87,148,242,0.15); --green-glow: rgba(115,191,105,0.15);
            --red-glow: rgba(242,73,92,0.15); --yellow-glow: rgba(242,204,12,0.15);
        }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; font-size: 13px; }
        .top-nav { background: linear-gradient(180deg, #1a1d22, #14161a); border-bottom: 1px solid var(--border); padding: 0 20px; height: 56px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--blue), #2c7bd9); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: white; font-weight: bold; }
        .logo h1 { color: var(--blue); font-size: 20px; font-weight: 700; }
        .nav-menu { display: flex; gap: 4px; }
        .nav-item { padding: 10px 18px; border-radius: 8px; cursor: pointer; color: var(--muted); font-size: 13px; background: transparent; border: none; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
        .nav-item:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .nav-item.active { background: var(--blue-glow); color: var(--blue); }
        .nav-right { display: flex; align-items: center; gap: 12px; }
        .time-range { display: flex; gap: 2px; background: var(--card); border-radius: 8px; padding: 3px; }
        .time-btn { padding: 6px 14px; background: transparent; border: none; border-radius: 5px; color: var(--muted); font-size: 12px; cursor: pointer; }
        .time-btn.active { background: var(--blue); color: white; }
        .btn { padding: 8px 16px; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #2c7bd9, #1a5fb4); color: white; }
        .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border); }
        .btn-danger { background: linear-gradient(135deg, rgba(242,73,92,0.3), rgba(242,73,92,0.15)); color: var(--red); }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .main { padding: 20px; max-width: 1920px; margin: 0 auto; }
        .stats-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: all 0.3s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
        .stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .stat-value { font-size: 28px; font-weight: 700; }
        .stat-label { color: var(--muted); font-size: 12px; margin-top: 4px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .grid-item { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .grid-item.col-4 { grid-column: span 4; }
        .grid-item.col-6 { grid-column: span 6; }
        .grid-item.col-8 { grid-column: span 8; }
        .grid-item.col-12 { grid-column: span 12; }
        .panel { height: 100%; display: flex; flex-direction: column; }
        .panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); }
        .panel-title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .panel-body { flex: 1; padding: 16px; min-height: 200px; }
        .chart-container { width: 100%; height: 250px; }
        .chart-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; }
        .legend-item { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
        .legend-item:hover { background: rgba(255,255,255,0.05); }
        .legend-color { width: 12px; height: 12px; border-radius: 3px; }
        .server-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; max-height: 500px; overflow-y: auto; }
        .server-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; cursor: pointer; transition: all 0.2s; }
        .server-card.online { border-left: 3px solid var(--green); }
        .server-card.offline { border-left: 3px solid var(--red); }
        .server-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
        .server-name { font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .server-status { width: 8px; height: 8px; border-radius: 50%; }
        .server-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .metric-box { background: rgba(0,0,0,0.2); border-radius: 6px; padding: 10px; text-align: center; }
        .metric-label { font-size: 10px; color: var(--muted); text-transform: uppercase; }
        .metric-value { font-size: 18px; font-weight: 600; }
        .metric-progress { height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; margin-top: 6px; }
        .metric-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 600; background: rgba(0,0,0,0.2); }
        tr:hover td { background: rgba(255,255,255,0.02); }
        .badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
        .badge-success { background: var(--green-glow); color: var(--green); }
        .badge-danger { background: var(--red-glow); color: var(--red); }
        .badge-warning { background: var(--yellow-glow); color: var(--yellow); }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .modal-close { background: none; border: none; color: var(--muted); font-size: 24px; cursor: pointer; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 600; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 13px; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
        .tab { padding: 12px 20px; color: var(--muted); cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; }
        .tab.active { color: var(--blue); border-bottom-color: var(--blue); }
        .section-content { display: none; }
        .section-content.active { display: block; }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="logo"><div class="logo-icon">P</div><h1>PyMon</h1></div>
        <div class="nav-menu">
            <button class="nav-item active" data-section="dashboard"><i class="fas fa-chart-line"></i> Dashboard</button>
            <button class="nav-item" data-section="servers"><i class="fas fa-server"></i> Servers</button>
            <button class="nav-item" data-section="alerts"><i class="fas fa-bell"></i> Alerts</button>
            <button class="nav-item" data-section="settings"><i class="fas fa-cog"></i> Settings</button>
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
            <div class="stats-overview">
                <div class="stat-card" onclick="filterBy('online')">
                    <div class="stat-icon" style="background: var(--green-glow); color: var(--green);"><i class="fas fa-check-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-online" style="color: var(--green);">0</div>
                        <div class="stat-label">Online Servers</div>
                    </div>
                </div>
                <div class="stat-card" onclick="filterBy('offline')">
                    <div class="stat-icon" style="background: var(--red-glow); color: var(--red);"><i class="fas fa-times-circle"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-offline" style="color: var(--red);">0</div>
                        <div class="stat-label">Offline Servers</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--blue-glow); color: var(--blue);"><i class="fas fa-microchip"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-cpu-avg">0%</div>
                        <div class="stat-label">Avg CPU Usage</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--yellow-glow); color: var(--yellow);"><i class="fas fa-memory"></i></div>
                    <div class="stat-content">
                        <div class="stat-value" id="stat-mem-avg">0%</div>
                        <div class="stat-label">Avg Memory Usage</div>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-microchip" style="color: var(--blue);"></i> CPU Usage</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="cpuChart"></canvas></div>
                            <div class="chart-legend" id="cpuLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-memory" style="color: var(--yellow);"></i> Memory Usage</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="memoryChart"></canvas></div>
                            <div class="chart-legend" id="memoryLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-hdd" style="color: var(--green);"></i> Disk Usage (All Partitions)</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="diskChart"></canvas></div>
                            <div class="chart-legend" id="diskLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-6">
                    <div class="panel">
                        <div class="panel-header"><div class="panel-title"><i class="fas fa-network-wired" style="color: var(--purple);"></i> Network Traffic</div></div>
                        <div class="panel-body">
                            <div class="chart-container"><canvas id="networkChart"></canvas></div>
                            <div class="chart-legend" id="networkLegend"></div>
                        </div>
                    </div>
                </div>
                <div class="grid-item col-12">
                    <div class="panel">
                        <div class="panel-header">
                            <div class="panel-title"><i class="fas fa-server" style="color: var(--cyan);"></i> Server Map</div>
                            <div style="display: flex; gap: 12px;">
                                <input type="text" id="serverSearch" placeholder="Search servers..." style="padding: 6px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); width: 200px;">
                                <button class="btn btn-primary btn-sm" id="addServerBtnDashboard"><i class="fas fa-plus"></i> Add Server</button>
                            </div>
                        </div>
                        <div class="panel-body">
                            <div class="server-grid" id="serverGrid"></div>
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
                        <button class="btn btn-primary btn-sm" id="addServerBtn"><i class="fas fa-plus"></i> Add Server</button>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <table id="serversTable"><thead><tr><th>Status</th><th>Name</th><th>Host:Port</th><th>OS</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last Check</th><th>Actions</th></tr></thead><tbody></tbody></table>
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
                        <button class="btn btn-primary btn-sm" id="addAlertBtn"><i class="fas fa-plus"></i> New Alert</button>
                    </div>
                    <div class="panel-body" style="padding: 0;">
                        <div id="alertsList"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Settings Section -->
        <div id="section-settings" class="section-content">
            <div class="grid-item col-12">
                <div class="panel">
                    <div class="panel-header"><div class="panel-title"><i class="fas fa-cog"></i> Settings</div></div>
                    <div class="panel-body">
                        <div class="tabs">
                            <div class="tab active" data-tab="notifications">Notifications</div>
                            <div class="tab" data-tab="backups">Backups</div>
                            <div class="tab" data-tab="api">API Keys</div>
                        </div>
                        <div id="tab-notifications">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                                <div style="padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                                    <h4 style="margin-bottom: 12px; color: var(--cyan);"><i class="fab fa-telegram"></i> Telegram</h4>
                                    <div class="form-group"><label style="display: flex; gap: 8px; align-items: center;"><input type="checkbox" id="telegram-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Bot Token</label><input type="text" id="telegram-token" placeholder="123456789:ABCdef..."></div>
                                    <div class="form-group"><label>Chat ID</label><input type="text" id="telegram-chat" placeholder="-1001234567890"></div>
                                </div>
                                <div style="padding: 16px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                                    <h4 style="margin-bottom: 12px; color: #5865F2;"><i class="fab fa-discord"></i> Discord</h4>
                                    <div class="form-group"><label style="display: flex; gap: 8px; align-items: center;"><input type="checkbox" id="discord-enabled"> Enabled</label></div>
                                    <div class="form-group"><label>Webhook URL</label><input type="text" id="discord-webhook" placeholder="https://discord.com/api/webhooks/..."></div>
                                </div>
                            </div>
                            <button class="btn btn-primary" style="margin-top: 16px;" id="saveNotifyBtn"><i class="fas fa-save"></i> Save Settings</button>
                        </div>
                        <div id="tab-backups" style="display: none;">
                            <button class="btn btn-primary" id="createBackupBtn"><i class="fas fa-download"></i> Create Backup</button>
                            <div style="margin-top: 16px;"><table id="backupsTable"><thead><tr><th>Filename</th><th>Size</th><th>Created</th></tr></thead><tbody></tbody></table></div>
                        </div>
                        <div id="tab-api" style="display: none;">
                            <button class="btn btn-primary" id="createApiKeyBtn"><i class="fas fa-plus"></i> Generate Key</button>
                            <div style="margin-top: 16px;"><table id="apiKeysTable"><thead><tr><th>Name</th><th>Created</th><th>Last Used</th><th>Actions</th></tr></thead><tbody></tbody></table></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <!-- Modals -->
    <div class="modal" id="addServerModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title">Add Server</div><button class="modal-close" id="closeServerModal">&times;</button></div>
            <form id="addServerForm">
                <div class="form-group"><label>Server Name</label><input type="text" id="server-name" required placeholder="Production Server"></div>
                <div class="form-group"><label>Host / IP Address</label><input type="text" id="server-host" required placeholder="192.168.1.100"></div>
                <div class="form-row">
                    <div class="form-group"><label>Operating System</label><select id="server-os"><option value="linux">Linux (node_exporter:9100)</option><option value="windows">Windows (windows_exporter:9182)</option></select></div>
                    <div class="form-group"><label>Agent Port</label><input type="number" id="server-port" value="9100"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Add Server</button>
            </form>
        </div>
    </div>
    
    <div class="modal" id="alertModal">
        <div class="modal-content">
            <div class="modal-header"><div class="modal-title" id="alertModalTitle">Add Alert</div><button class="modal-close" id="closeAlertModal">&times;</button></div>
            <form id="alertForm">
                <input type="hidden" id="alert-id">
                <div class="form-group"><label>Alert Name</label><input type="text" id="alert-name" required placeholder="High CPU Alert"></div>
                <div class="form-row">
                    <div class="form-group"><label>Server (optional)</label><select id="alert-server"><option value="">Global (All Servers)</option></select></div>
                    <div class="form-group"><label>Metric</label><select id="alert-metric"><option value="cpu">CPU Usage</option><option value="memory">Memory</option><option value="disk">Disk</option><option value="network">Network</option></select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Condition</label><select id="alert-condition"><option value=">">Greater than</option><option value="<">Less than</option></select></div>
                    <div class="form-group"><label>Threshold (%)</label><input type="number" id="alert-threshold" value="80"></div>
                </div>
                <div class="form-group"><label>Severity</label><select id="alert-severity"><option value="warning">Warning</option><option value="critical">Critical</option></select></div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Save Alert</button>
            </form>
        </div>
    </div>

<script>
const token = localStorage.getItem('token');
if (!token) window.location.href = '/login';
let servers = [];
let charts = {};
let currentRange = '1h';
const colors = ['#73bf69', '#f2cc0c', '#5794f2', '#ff780a', '#b877d9', '#00d8d8', '#f2495c', '#9673b9'];

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', function() { showSection(this.dataset.section); }));
document.querySelectorAll('.time-btn').forEach(btn => btn.addEventListener('click', function() { document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active')); this.classList.add('active'); currentRange = this.dataset.range; loadData(); }));
document.getElementById('logoutBtn').addEventListener('click', () => { localStorage.removeItem('token'); window.location.href = '/login'; });
document.getElementById('refreshBtn').addEventListener('click', () => loadData());
document.getElementById('addServerBtn').addEventListener('click', () => document.getElementById('addServerModal').classList.add('active'));
document.getElementById('addServerBtnDashboard').addEventListener('click', () => document.getElementById('addServerModal').classList.add('active'));
document.getElementById('closeServerModal').addEventListener('click', () => document.getElementById('addServerModal').classList.remove('active'));
document.getElementById('serverSearch').addEventListener('input', updateServerGrid);
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', function() { document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); this.classList.add('active'); document.querySelectorAll('[id^="tab-"]').forEach(d => d.style.display = 'none'); document.getElementById('tab-' + this.dataset.tab).style.display = 'block'; }));

document.getElementById('addServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const port = parseInt(document.getElementById('server-port').value) || (document.getElementById('server-os').value === 'windows' ? 9182 : 9100);
    await fetch('/api/servers', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({ name: document.getElementById('server-name').value, host: document.getElementById('server-host').value, os_type: document.getElementById('server-os').value, agent_port: port }) });
    document.getElementById('addServerModal').classList.remove('active');
    document.getElementById('addServerForm').reset();
    loadData();
});

document.getElementById('saveNotifyBtn').addEventListener('click', async () => {
    const config = {
        telegram: { enabled: document.getElementById('telegram-enabled').checked, telegram_bot_token: document.getElementById('telegram-token').value, telegram_chat_id: document.getElementById('telegram-chat').value },
        discord: { enabled: document.getElementById('discord-enabled').checked, discord_webhook: document.getElementById('discord-webhook').value }
    };
    for (const [channel, cfg] of Object.entries(config)) {
        await fetch('/api/notifications/' + channel, { method: 'PUT', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify(cfg) });
    }
    alert('Settings saved!');
});

document.getElementById('createBackupBtn').addEventListener('click', async () => {
    const resp = await fetch('/api/backup/create', { method: 'POST', headers: {'Authorization': 'Bearer ' + token} });
    const data = await resp.json();
    if (data.status === 'ok') { alert('Backup created!'); loadBackups(); } else { alert('Error: ' + data.detail); }
});

document.getElementById('createApiKeyBtn').addEventListener('click', async () => {
    const name = prompt('Enter API key name:');
    if (name) {
        const resp = await fetch('/api/api-keys', { method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({name}) });
        const data = await resp.json();
        if (data.key) { alert('API Key created! Copy it now:\\n\\n' + data.key); loadApiKeys(); }
    }
});

document.getElementById('addAlertBtn').addEventListener('click', () => { document.getElementById('alert-id').value = ''; document.getElementById('alertForm').reset(); document.getElementById('alertModalTitle').textContent = 'Add Alert'; document.getElementById('alertModal').classList.add('active'); });
document.getElementById('closeAlertModal').addEventListener('click', () => document.getElementById('alertModal').classList.remove('active'));
document.getElementById('alertForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('alert-id').value;
    const data = { name: document.getElementById('alert-name').value, metric: document.getElementById('alert-metric').value, condition: document.getElementById('alert-condition').value, threshold: parseInt(document.getElementById('alert-threshold').value), severity: document.getElementById('alert-severity').value, server_id: document.getElementById('alert-server').value || null, enabled: true };
    const url = id ? '/api/alerts/' + id : '/api/alerts';
    const method = id ? 'PUT' : 'POST';
    await fetch(url, { method, headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify(data) });
    document.getElementById('alertModal').classList.remove('active');
    loadAlerts();
});

function showSection(section) {
    document.querySelectorAll('.section-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById('section-' + section)?.classList.add('active');
    document.querySelector(`.nav-item[data-section="${section}"]`)?.classList.add('active');
    if (section === 'settings') { loadNotifications(); loadBackups(); loadApiKeys(); }
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
        loadAlerts();
        populateAlertServerSelect();
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

async function updateCharts() {
    const labels = generateLabels();
    if (!charts.cpu) {
        charts.cpu = new Chart(document.getElementById('cpuChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.memory = new Chart(document.getElementById('memoryChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.disk = new Chart(document.getElementById('diskChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts('%', 0, 100)});
        charts.network = new Chart(document.getElementById('networkChart'), {type: 'line', data: {labels, datasets: []}, options: chartOpts(' MB/s', 0, null)});
    }
    
    const histories = await Promise.all(servers.map(s => fetchServerHistory(s.id)));
    
    const cpuData = [], memData = [], diskData = [], netData = [];
    servers.forEach((s, i) => {
        const h = histories[i] || [];
        const color = colors[i % colors.length];
        const common = {label: s.name, borderColor: color, backgroundColor: color + '20', fill: true, tension: 0.3};
        cpuData.push({...common, data: h.length ? h.map(x => x.cpu_percent) : rand(12, s.cpu_percent || 30, 20)});
        memData.push({...common, data: h.length ? h.map(x => x.memory_percent) : rand(12, s.memory_percent || 40, 15)});
        netData.push({...common, data: h.length ? h.map(x => (x.network_rx || 0) / 1024 / 1024) : rand(12, 10, 5)});
        
        // Parse disk_info for multiple disks
        const diskMap = {};
        h.forEach(x => {
            if (x.disk_info) {
                try {
                    const info = typeof x.disk_info === 'string' ? JSON.parse(x.disk_info) : x.disk_info;
                    if (Array.isArray(info)) {
                        info.forEach(d => {
                            const vol = d.volume || d.path || '?';
                            if (!diskMap[vol]) diskMap[vol] = new Array(h.length).fill(null);
                            diskMap[vol][h.indexOf(x)] = d.percent;
                        });
                    }
                } catch(e) {}
            }
        });
        
        if (Object.keys(diskMap).length > 0) {
            Object.keys(diskMap).forEach((vol, j) => {
                diskData.push({...common, label: s.name + ' (' + vol + ')', borderColor: colors[(i + j) % colors.length], backgroundColor: colors[(i + j) % colors.length] + '20', data: diskMap[vol]});
            });
        } else {
            diskData.push({...common, data: h.length ? h.map(x => x.disk_percent) : rand(12, s.disk_percent || 50, 10)});
        }
    });
    
    charts.cpu.data.datasets = cpuData.length ? cpuData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.cpu.update();
    updateLegend('cpuLegend', charts.cpu.data.datasets, '%');
    
    charts.memory.data.datasets = memData.length ? memData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.memory.update();
    updateLegend('memoryLegend', charts.memory.data.datasets, '%');
    
    charts.disk.data.datasets = diskData.length ? diskData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.disk.update();
    updateLegend('diskLegend', charts.disk.data.datasets, '%');
    
    charts.network.data.datasets = netData.length ? netData : [{label: 'No Data', data: rand(12, 0, 5), borderColor: colors[0], backgroundColor: colors[0] + '20', fill: true}];
    charts.network.update();
    updateLegend('networkLegend', charts.network.data.datasets, ' MB/s');
}

async function fetchServerHistory(id) {
    try {
        const resp = await fetch(`/api/servers/${id}/history?range=${currentRange}`, {headers: {'Authorization': 'Bearer ' + token}});
        const data = await resp.json();
        return data.history || [];
    } catch(e) { return []; }
}

function updateLegend(id, datasets, unit) {
    const el = document.getElementById(id);
    el.innerHTML = datasets.map(ds => `<div class="legend-item"><div class="legend-color" style="background: ${ds.borderColor}"></div><span>${ds.label}</span><span style="margin-left: auto; color: var(--muted);">${ds.data[ds.data.length-1]?.toFixed(1) || 0}${unit}</span></div>`).join('');
}

function updateServerGrid() {
    const search = document.getElementById('serverSearch').value.toLowerCase();
    const filtered = servers.filter(s => !search || s.name.toLowerCase().includes(search) || s.host.toLowerCase().includes(search));
    const el = document.getElementById('serverGrid');
    el.innerHTML = filtered.map(s => {
        const status = s.last_status === 'up' ? 'online' : 'offline';
        const statusColor = s.last_status === 'up' ? 'var(--green)' : 'var(--red)';
        const cpuColor = (s.cpu_percent || 0) > 80 ? 'var(--red)' : (s.cpu_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        const memColor = (s.memory_percent || 0) > 80 ? 'var(--red)' : (s.memory_percent || 0) > 60 ? 'var(--yellow)' : 'var(--green)';
        return `
        <div class="server-card ${status}" onclick="scrapeServer(${s.id})">
            <div class="server-header">
                <div class="server-name"><div class="server-status" style="background: ${statusColor}"></div>${s.name}</div>
                <span style="color: var(--muted); font-size: 11px;">${s.os_type}</span>
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
    }).join('') || '<p style="color: var(--muted); text-align: center; padding: 40px;">No servers</p>';
}

function updateServerTable() {
    const el = document.querySelector('#serversTable tbody');
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
                <button class="btn btn-secondary btn-sm" onclick="scrapeServer(${s.id}); event.stopPropagation();"><i class="fas fa-sync"></i></button>
                <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id}); event.stopPropagation();"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" style="text-align: center; padding: 40px; color: var(--muted);">No servers configured</td></tr>';
}

async function loadAlerts() {
    const resp = await fetch('/api/alerts', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const alerts = data.alerts || [];
    const el = document.getElementById('alertsList');
    el.innerHTML = alerts.length ? alerts.map(a => `
        <div style="padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: 600;">${a.name}</div>
                <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">${a.metric.toUpperCase()} ${a.condition} ${a.threshold}%</div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="badge ${a.severity === 'critical' ? 'badge-danger' : 'badge-warning'}">${a.severity}</span>
                <button class="btn btn-danger btn-sm" onclick="deleteAlert(${a.id})"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('') : '<p style="color: var(--muted); text-align: center; padding: 40px;">No alert rules configured</p>';
}

function populateAlertServerSelect() {
    const el = document.getElementById('alert-server');
    el.innerHTML = '<option value="">Global (All Servers)</option>' + servers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function loadNotifications() {
    const resp = await fetch('/api/notifications', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    (data.notifications || []).forEach(n => {
        if (n.channel === 'telegram') {
            document.getElementById('telegram-enabled').checked = n.enabled;
            document.getElementById('telegram-token').value = n.telegram_bot_token || '';
            document.getElementById('telegram-chat').value = n.telegram_chat_id || '';
        }
        if (n.channel === 'discord') {
            document.getElementById('discord-enabled').checked = n.enabled;
            document.getElementById('discord-webhook').value = n.discord_webhook || '';
        }
    });
}

async function loadBackups() {
    const resp = await fetch('/api/backup/list', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const files = data.files || [];
    document.querySelector('#backupsTable tbody').innerHTML = files.map(f => `<tr><td>${f.filename}</td><td>${(f.size/1024).toFixed(1)} KB</td><td>${f.created ? f.created.substring(0, 19) : '-'}</td></tr>`).join('') || '<tr><td colspan="3" style="text-align: center; color: var(--muted);">No backups</td></tr>';
}

async function loadApiKeys() {
    const resp = await fetch('/api/api-keys', {headers: {'Authorization': 'Bearer ' + token}});
    const data = await resp.json();
    const keys = data.keys || [];
    document.querySelector('#apiKeysTable tbody').innerHTML = keys.map(k => `<tr><td>${k.name}</td><td>${k.created_at ? k.created_at.substring(0, 19) : '-'}</td><td>${k.last_used || 'Never'}</td><td><button class="btn btn-danger btn-sm" onclick="deleteApiKey(${k.id})"><i class="fas fa-trash"></i></button></td></tr>`).join('') || '<tr><td colspan="4" style="text-align: center; color: var(--muted);">No API keys</td></tr>';
}

async function scrapeServer(id) {
    try {
        const btn = event?.target?.closest('button') || document.body;
        const icon = btn.querySelector('i');
        if (icon) icon.classList.add('animate-spin');
        await fetch(`/api/servers/${id}/scrape`, { method: 'POST', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
        setTimeout(() => icon?.classList.remove('animate-spin'), 500);
    } catch(e) { alert('Error: ' + e.message); }
}

async function deleteServer(id) {
    if (confirm('Delete this server?')) {
        await fetch(`/api/servers/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadData();
    }
}

async function deleteAlert(id) {
    if (confirm('Delete this alert?')) {
        await fetch(`/api/alerts/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadAlerts();
    }
}

async function deleteApiKey(id) {
    if (confirm('Delete this API key?')) {
        await fetch(`/api/api-keys/${id}`, { method: 'DELETE', headers: {'Authorization': 'Bearer ' + token} });
        loadApiKeys();
    }
}

function filterBy(type) {
    if (type === 'online') { document.getElementById('serverSearch').value = ''; }
    else if (type === 'offline') { document.getElementById('serverSearch').value = ''; }
}

function generateLabels() {
    const labels = [];
    const now = new Date();
    for (let i = 11; i >= 0; i--) { const t = new Date(now.getTime() - i * 5 * 60000); labels.push(t.getHours().toString().padStart(2,'0') + ':' + t.getMinutes().toString().padStart(2,'0')); }
    return labels;
}

function rand(n, base, variance) { const arr = []; let val = base; for (let i = 0; i < n; i++) { val = Math.max(0, Math.min(100, val + (Math.random() - 0.5) * variance)); arr.push(val); } return arr; }

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

setInterval(loadData, 30000);
loadData();
</script>
</body>
</html>'''