"""Enhanced Web Dashboard Template - 'Grafana Edition'"""

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Space Grotesk', sans-serif; background: #05070d; color: white; }
        .glass { background: rgba(13, 18, 30, 0.8); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen">
    <div class="glass p-10 rounded-[2.5rem] w-full max-w-md shadow-2xl border border-orange-500/20">
        <h1 class="text-3xl font-bold mb-2 text-center text-white">PyMon <span class="text-orange-500">NOC</span></h1>
        <p class="text-slate-500 text-center mb-8 text-sm uppercase tracking-widest font-bold">Secure Access Gateway</p>
        
        <form id="loginForm" class="space-y-6">
            <div>
                <label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Operator ID</label>
                <input type="text" id="username" required class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-orange-500 transition-all font-mono">
            </div>
            <div>
                <label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Access Key</label>
                <input type="password" id="password" required class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-orange-500 transition-all font-mono">
            </div>
            <button type="submit" class="w-full bg-orange-600 hover:bg-orange-500 text-white font-black py-5 rounded-xl shadow-2xl shadow-orange-600/40 transition-all uppercase tracking-widest text-sm">
                Authenticate
            </button>
            <div id="error" class="text-red-500 text-center text-xs hidden font-bold">ACCESS DENIED</div>
        </form>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorBox = document.getElementById('error');
            errorBox.classList.add('hidden');
            
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
                    errorBox.classList.remove('hidden');
                }
            } catch (e) {
                errorBox.textContent = 'NETWORK TIMEOUT';
                errorBox.classList.remove('hidden');
            }
        });
    </script>
</body>
</html>"""

ENHANCED_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon | NOC Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Space Grotesk', sans-serif; background: #0b0e14; color: #d8d9da; }
        code, pre, .mono { font-family: 'JetBrains Mono', monospace; }
        .glass { background: #161b22; border: 1px solid #30363d; }
        .glass:hover { border-color: #8b949e; }
        .sidebar-item-active { background: #1f242c; color: #f0883e; border-left: 4px solid #f0883e; border-right: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #0b0e14; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }
        .pulsing-dot { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: .4; transform: scale(1.5); } 100% { opacity: 1; transform: scale(1); } }
        .stat-card { border-left: 4px solid transparent; }
        .stat-card.online { border-left-color: #3fb950; }
        .stat-card.offline { border-left-color: #f85149; }
        .stat-card.warning { border-left-color: #d29922; }
    </style>
</head>
<body class="overflow-hidden">
    <div class="flex h-screen relative">
        <!-- Sidebar -->
        <aside class="w-64 bg-[#0d1117] border-r border-[#30363d] flex flex-col z-20">
            <div class="p-6">
                <div class="flex items-center gap-3 mb-8">
                    <img src="https://grafana.com/static/img/menu/grafana_icon.svg" class="w-8 h-8 opacity-80" alt="PyMon">
                    <h1 class="text-xl font-bold text-white tracking-tight">PyMon <span class="text-xs font-normal text-slate-500">v0.1</span></h1>
                </div>

                <nav class="space-y-1">
                    <button data-section="overview" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm sidebar-item-active">
                        <i data-lucide="layout-grid" class="w-4 h-4"></i> Overview
                    </button>
                    <button data-section="servers" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm">
                        <i data-lucide="server" class="w-4 h-4"></i> Nodes
                    </button>
                    <button data-section="alerts" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm">
                        <i data-lucide="bell" class="w-4 h-4"></i> Alerting
                    </button>
                    <button data-section="logs" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm">
                        <i data-lucide="list" class="w-4 h-4"></i> Explorer
                    </button>
                    <div class="pt-6 pb-2 text-[10px] font-bold text-slate-600 uppercase tracking-widest px-3">Administration</div>
                    <button data-section="deploy" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm text-slate-400">
                        <i data-lucide="plus-circle" class="w-4 h-4"></i> Add Data Source
                    </button>
                    <button data-section="settings" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-[#1f242c] text-sm text-slate-400">
                        <i data-lucide="settings" class="w-4 h-4"></i> Configuration
                    </button>
                </nav>
            </div>

            <div class="mt-auto p-4 border-t border-[#30363d]">
                <button id="logoutBtn" class="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all hover:bg-red-500/10 text-sm text-slate-400 hover:text-red-400">
                    <i data-lucide="log-out" class="w-4 h-4"></i> Sign Out
                </button>
            </div>
        </aside>

        <!-- Main -->
        <main class="flex-1 flex flex-col min-w-0 bg-[#0b0e14]">
            <!-- Header -->
            <header class="h-12 border-b border-[#30363d] flex items-center justify-between px-6 bg-[#0d1117] shrink-0">
                <div class="flex items-center gap-4">
                    <h2 id="pageTitle" class="text-sm font-bold text-white">General / Overview</h2>
                    <div class="h-4 w-px bg-[#30363d]"></div>
                    <span class="text-[10px] text-slate-500 font-mono" id="lastUpdated">Last updated: 13:28:44</span>
                </div>

                <div class="flex items-center gap-2">
                    <div class="flex bg-[#161b22] border border-[#30363d] rounded p-0.5">
                        <button data-range="1h" class="range-btn px-3 py-0.5 rounded text-[10px] font-bold transition-all active bg-[#f0883e] text-black">1h</button>
                        <button data-range="6h" class="range-btn px-3 py-0.5 rounded text-[10px] font-bold text-slate-400 hover:text-white">6h</button>
                        <button data-range="24h" class="range-btn px-3 py-0.5 rounded text-[10px] font-bold text-slate-400 hover:text-white">24h</button>
                    </div>
                    <button id="refreshBtn" class="p-1.5 bg-[#161b22] border border-[#30363d] rounded hover:border-[#8b949e]">
                        <i data-lucide="rotate-cw" class="w-3.5 h-3.5 text-slate-400"></i>
                    </button>
                </div>
            </header>

            <!-- Scrollable Content -->
            <div id="content" class="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-4">
                <!-- Section: Overview -->
                <div id="section-overview" class="section space-y-4">
                    <!-- Stat Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div class="glass p-4 rounded stat-card online">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-1">Nodes Online</div>
                            <div class="text-3xl font-bold text-[#3fb950]" id="stat-online">0</div>
                        </div>
                        <div class="glass p-4 rounded stat-card offline">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-1">Nodes Offline</div>
                            <div class="text-3xl font-bold text-[#f85149]" id="stat-offline">0</div>
                        </div>
                        <div class="glass p-4 rounded stat-card warning">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-1">Avg CPU Load</div>
                            <div class="text-3xl font-bold text-[#f0883e]" id="stat-cpu-avg">0%</div>
                        </div>
                        <div class="glass p-4 rounded stat-card warning">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-1">Avg Memory</div>
                            <div class="text-3xl font-bold text-[#388bfd]" id="stat-mem-avg">0%</div>
                        </div>
                    </div>

                    <!-- Main Charts -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div class="glass p-4 rounded h-[300px] flex flex-col">
                            <div class="flex items-center justify-between mb-2">
                                <h3 class="text-xs font-bold text-white uppercase tracking-wider">CPU Usage History</h3>
                            </div>
                            <div class="flex-1 min-h-0">
                                <canvas id="cpuChart"></canvas>
                            </div>
                        </div>
                        <div class="glass p-4 rounded h-[300px] flex flex-col">
                            <div class="flex items-center justify-between mb-2">
                                <h3 class="text-xs font-bold text-white uppercase tracking-wider">Memory Usage History</h3>
                            </div>
                            <div class="flex-1 min-h-0">
                                <canvas id="memoryChart"></canvas>
                            </div>
                        </div>
                    </div>

                    <!-- Node Status Table -->
                    <div class="glass rounded overflow-hidden">
                        <div class="p-4 border-b border-[#30363d] bg-[#161b22]/50 flex items-center justify-between">
                            <h3 class="text-xs font-bold text-white uppercase tracking-wider">Infrastructure Status</h3>
                            <button onclick="showSection('servers')" class="text-[10px] text-blue-400 font-bold hover:underline">Manage Nodes</button>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-xs">
                                <thead class="bg-[#0d1117] text-slate-500 border-b border-[#30363d]">
                                    <tr>
                                        <th class="px-4 py-3 font-bold">Node</th>
                                        <th class="px-4 py-3 font-bold">Status</th>
                                        <th class="px-4 py-3 font-bold">CPU</th>
                                        <th class="px-4 py-3 font-bold">Memory</th>
                                        <th class="px-4 py-3 font-bold">Disk</th>
                                        <th class="px-4 py-3 font-bold">Net RX/TX</th>
                                        <th class="px-4 py-3 font-bold text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="quickServerList" class="divide-y divide-[#30363d]">
                                    <!-- Dynamic -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Section: Nodes -->
                <div id="section-servers" class="section hidden space-y-4">
                    <div class="flex justify-between items-center bg-[#161b22] p-4 rounded border border-[#30363d]">
                        <h3 class="text-sm font-bold text-white uppercase">Monitored Inventory</h3>
                        <button id="addServerBtn" class="bg-[#f0883e] hover:bg-[#ff9b5e] text-black text-[10px] font-bold px-4 py-1.5 rounded transition-all flex items-center gap-2">
                            <i data-lucide="plus" class="w-3 h-3"></i> Add Node
                        </button>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4" id="serverCards">
                        <!-- Cards -->
                    </div>
                </div>

                <!-- Section: Alerts -->
                <div id="section-alerts" class="section hidden space-y-4">
                    <div class="glass p-6 rounded">
                         <div class="flex justify-between items-center mb-6 pb-4 border-b border-[#30363d]">
                            <h3 class="text-sm font-bold text-white uppercase">Alerting Rules</h3>
                            <button id="addAlertBtn" class="bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold px-4 py-1.5 rounded transition-all">Create Rule</button>
                        </div>
                        <div id="alertsList" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
                    </div>
                </div>
                
                <!-- Section: Explorer (Logs) -->
                <div id="section-logs" class="section hidden space-y-4">
                    <div class="glass p-4 rounded flex flex-col h-[700px]">
                        <div class="flex items-center gap-4 mb-4 pb-4 border-b border-[#30363d]">
                            <h3 class="text-xs font-bold text-white uppercase">Audit Explorer</h3>
                        </div>
                        <div id="auditLogs" class="flex-1 overflow-y-auto font-mono text-[11px] space-y-1 custom-scrollbar"></div>
                    </div>
                </div>

                <!-- Section: Settings -->
                <div id="section-settings" class="section hidden space-y-4">
                    <div class="glass p-8 rounded max-w-2xl mx-auto">
                        <h3 class="text-xl font-bold text-white mb-6">System Preferences</h3>
                        <div class="space-y-6">
                            <div class="p-4 bg-[#0d1117] rounded border border-[#30363d]">
                                <h4 class="text-xs font-bold text-slate-400 uppercase mb-4">Security</h4>
                                <button onclick="changePassword()" class="w-full py-2 bg-[#1f242c] text-white text-xs font-bold rounded hover:bg-[#30363d] transition-all">Update Admin Password</button>
                            </div>
                            <div class="p-4 bg-[#0d1117] rounded border border-[#30363d]">
                                <h4 class="text-xs font-bold text-slate-400 uppercase mb-4">Integrations</h4>
                                <div class="grid grid-cols-2 gap-4">
                                    <button class="py-4 bg-[#1f242c] rounded border border-[#30363d] text-center hover:bg-[#30363d]">
                                        <div class="text-xs font-bold text-white">Telegram Bot</div>
                                        <div class="text-[9px] text-slate-500">Configure notifications</div>
                                    </button>
                                    <button class="py-4 bg-[#1f242c] rounded border border-[#30363d] text-center hover:bg-[#30363d]">
                                        <div class="text-xs font-bold text-white">Discord Webhook</div>
                                        <div class="text-[9px] text-slate-500">Configure notifications</div>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Modals -->
    <div id="addServerModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden items-center justify-center p-4">
        <div class="glass w-full max-w-md p-6 rounded relative border-[#f0883e]/30">
            <button onclick="toggleModal('addServerModal', false)" class="absolute top-4 right-4 text-slate-500 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            <h3 class="text-lg font-bold text-white mb-6 uppercase tracking-wider">Register New Data Source</h3>
            <form id="addServerForm" class="space-y-4">
                <div>
                    <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Display Name</label>
                    <input type="text" id="nodeName" required class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#f0883e]">
                </div>
                <div>
                    <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Host / Endpoint</label>
                    <input type="text" id="nodeHost" required class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#f0883e]">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Architecture</label>
                        <select id="nodeOS" class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white">
                            <option value="linux">Linux / x64</option>
                            <option value="windows">Windows / x64</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Scrape Port</label>
                        <input type="number" id="nodePort" value="9100" class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white">
                    </div>
                </div>
                <button type="submit" class="w-full bg-[#f0883e] text-black font-bold py-3 rounded text-sm uppercase tracking-widest mt-4">Connect</button>
            </form>
        </div>
    </div>

    <div id="addAlertModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden items-center justify-center p-4">
        <div class="glass w-full max-w-md p-6 rounded relative border-blue-500/30">
            <button onclick="toggleModal('addAlertModal', false)" class="absolute top-4 right-4 text-slate-500 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            <h3 class="text-lg font-bold text-white mb-6 uppercase tracking-wider">Configure Alert Rule</h3>
            <form id="addAlertForm" class="space-y-4">
                <div>
                    <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Rule Name</label>
                    <input type="text" id="alertName" required class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Metric</label>
                        <select id="alertMetric" class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white">
                            <option value="cpu">CPU Usage</option>
                            <option value="memory">RAM Usage</option>
                            <option value="disk">Disk Space</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[10px] font-bold text-slate-500 uppercase mb-1">Threshold (%)</label>
                        <input type="number" id="alertThreshold" value="80" class="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-white">
                    </div>
                </div>
                <button type="submit" class="w-full bg-blue-600 text-white font-bold py-3 rounded text-sm uppercase tracking-widest mt-4">Deploy Rule</button>
            </form>
        </div>
    </div>

    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';

        function toggleModal(id, show) {
            const el = document.getElementById(id);
            if (!el) return;
            el.classList.toggle('hidden', !show);
            el.classList.toggle('flex', show);
        }

        let charts = {};
        let currentRange = '1h';
        let servers = [];

        lucide.createIcons();

        function showSection(section) {
            document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
            const target = document.getElementById('section-' + section);
            if (target) {
                target.classList.remove('hidden');
                document.querySelectorAll('nav button').forEach(b => {
                    b.classList.toggle('sidebar-item-active', b.dataset.section === section);
                });
                document.getElementById('pageTitle').textContent = `General / ${section.charAt(0).toUpperCase() + section.slice(1)}`;
                if (section === 'logs') loadAuditLogs();
                if (section === 'alerts') loadAlerts();
            }
        }

        document.querySelectorAll('nav button').forEach(btn => {
            btn.addEventListener('click', () => showSection(btn.dataset.section));
        });

        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('bg-[#f0883e]', 'text-black'));
                document.querySelectorAll('.range-btn').forEach(b => b.classList.add('text-slate-400'));
                btn.classList.remove('text-slate-400');
                btn.classList.add('bg-[#f0883e]', 'text-black');
                currentRange = btn.dataset.range;
                loadData();
            });
        });

        document.getElementById('logoutBtn').addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/login';
        });

        document.getElementById('refreshBtn').addEventListener('click', () => loadData());
        document.getElementById('addServerBtn').addEventListener('click', () => toggleModal('addServerModal', true));
        document.getElementById('addAlertBtn').addEventListener('click', () => toggleModal('addAlertModal', true));

        // Forms
        document.getElementById('addServerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await fetch('/api/v1/servers', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({
                    name: document.getElementById('nodeName').value,
                    host: document.getElementById('nodeHost').value,
                    os_type: document.getElementById('nodeOS').value,
                    agent_port: parseInt(document.getElementById('nodePort').value)
                })
            });
            if (resp.status === 401) { window.location.href = '/login'; return; }
            if (resp.ok) { toggleModal('addServerModal', false); e.target.reset(); loadData(); }
            else { alert('Deployment failed'); }
        });

        document.getElementById('addAlertForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await fetch('/api/v1/alerts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({
                    name: document.getElementById('alertName').value,
                    metric: document.getElementById('alertMetric').value,
                    condition: '>',
                    threshold: parseInt(document.getElementById('alertThreshold').value),
                    duration: 60,
                    severity: 'warning'
                })
            });
            if (resp.ok) { toggleModal('addAlertModal', false); e.target.reset(); loadAlerts(); }
        });

        // Charts
        function createChart(canvasId, label, color) {
            const el = document.getElementById(canvasId);
            if (!el) return null;
            const ctx = el.getContext('2d');
            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        borderWidth: 1.5,
                        pointRadius: 0,
                        backgroundColor: color + '11',
                        fill: true,
                        tension: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: true, ticks: { color: '#444', font: { size: 9 } }, grid: { display: false } },
                        y: { beginAtZero: true, grid: { color: '#222' }, ticks: { color: '#444', font: { size: 9 } } }
                    }
                }
            });
        }

        async function loadData() {
            try {
                const resp = await fetch('/api/v1/servers', {headers: {'Authorization': 'Bearer ' + token}});
                if (resp.status === 401) { window.location.href = '/login'; return; }
                const data = await resp.json();
                servers = data.servers;
                document.getElementById('lastUpdated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
                updateUI();
                loadTrends();
            } catch (e) {}
        }

        function updateUI() {
            const online = servers.filter(s => s.last_status === 'up').length;
            const offline = servers.length - online;
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            
            const cpu = servers.length ? servers.reduce((a, b) => a + (b.cpu_percent || 0), 0) / servers.length : 0;
            const mem = servers.length ? servers.reduce((a, b) => a + (b.memory_percent || 0), 0) / servers.length : 0;
            document.getElementById('stat-cpu-avg').textContent = cpu.toFixed(1) + '%';
            document.getElementById('stat-mem-avg').textContent = mem.toFixed(1) + '%';

            const formatBytes = (b) => {
                if (!b) return '0 B';
                const i = Math.floor(Math.log(b) / Math.log(1024));
                return (b / Math.pow(1024, i)).toFixed(1) + ' ' + ['B', 'KB', 'MB', 'GB', 'TB'][i];
            };

            const list = document.getElementById('quickServerList');
            list.innerHTML = servers.map(s => `
                <tr class="hover:bg-[#161b22] transition-all group">
                    <td class="px-4 py-3 font-bold text-white">${s.name}</td>
                    <td class="px-4 py-3">
                        <span class="flex items-center gap-1.5 ${s.last_status === 'up' ? 'text-[#3fb950]' : 'text-[#f85149]'}">
                            <span class="w-1.5 h-1.5 rounded-full bg-current pulsing-dot"></span>
                            ${s.last_status.toUpperCase()}
                        </span>
                    </td>
                    <td class="px-4 py-3">
                        <div class="flex items-center gap-2">
                            <span class="w-8">${(s.cpu_percent || 0).toFixed(0)}%</span>
                            <div class="w-16 bg-[#30363d] h-1.5 rounded-full overflow-hidden"><div class="bg-[#f0883e] h-full" style="width: ${s.cpu_percent || 0}%"></div></div>
                        </div>
                    </td>
                    <td class="px-4 py-3">
                        <div class="flex items-center gap-2">
                            <span class="w-8">${(s.memory_percent || 0).toFixed(0)}%</span>
                            <div class="w-16 bg-[#30363d] h-1.5 rounded-full overflow-hidden"><div class="bg-[#388bfd] h-full" style="width: ${s.memory_percent || 0}%"></div></div>
                        </div>
                    </td>
                    <td class="px-4 py-3">${(s.disk_percent || 0).toFixed(0)}%</td>
                    <td class="px-4 py-3 font-mono text-[10px] text-slate-500">${formatBytes(s.network_rx)} / ${formatBytes(s.network_tx)}</td>
                    <td class="px-4 py-3 text-right">
                        <button onclick="deleteServer(${s.id})" class="text-slate-600 hover:text-red-400"><i data-lucide="trash-2" class="w-3.5 h-3.5"></i></button>
                    </td>
                </tr>
            `).join('');

            const grid = document.getElementById('serverCards');
            grid.innerHTML = servers.map(s => `
                <div class="glass p-4 rounded flex flex-col gap-3 group relative">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <i data-lucide="${s.os_type === 'windows' ? 'monitor' : 'terminal'}" class="w-4 h-4 ${s.last_status === 'up' ? 'text-blue-400' : 'text-slate-600'}"></i>
                            <span class="font-bold text-white text-xs">${s.name}</span>
                        </div>
                        <div class="w-2 h-2 rounded-full ${s.last_status === 'up' ? 'bg-[#3fb950]' : 'bg-[#f85149]'} pulsing-dot"></div>
                    </div>
                    <div class="space-y-1">
                        <div class="flex justify-between text-[10px] font-bold text-slate-500"><span>CPU</span><span>${(s.cpu_percent || 0).toFixed(1)}%</span></div>
                        <div class="bg-[#30363d] h-1 rounded-full overflow-hidden"><div class="bg-[#f0883e] h-full" style="width: ${s.cpu_percent || 0}%"></div></div>
                    </div>
                    <div class="space-y-1">
                        <div class="flex justify-between text-[10px] font-bold text-slate-500"><span>RAM</span><span>${(s.memory_percent || 0).toFixed(1)}%</span></div>
                        <div class="bg-[#30363d] h-1 rounded-full overflow-hidden"><div class="bg-[#388bfd] h-full" style="width: ${s.memory_percent || 0}%"></div></div>
                    </div>
                    <div class="pt-2 flex items-center justify-between text-[9px] text-slate-600 font-bold uppercase">
                        <span>${s.host}</span>
                        <button onclick="deleteServer(${s.id})" class="opacity-0 group-hover:opacity-100 transition-all text-red-500 hover:scale-110"><i data-lucide="trash-2" class="w-3 h-3"></i></button>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function loadTrends() {
            try {
                const resp = await fetch('/api/v1/metrics/trend', {headers: {'Authorization': 'Bearer ' + token}});
                if (!resp.ok) return;
                const data = await resp.json();
                if (!charts.cpu) charts.cpu = createChart('cpuChart', 'CPU', '#f0883e');
                if (!charts.mem) charts.mem = createChart('memoryChart', 'Memory', '#388bfd');
                
                const labels = data.history.map(h => new Date(h.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
                charts.cpu.data.labels = labels;
                charts.cpu.data.datasets[0].data = data.history.map(h => h.cpu_avg);
                charts.cpu.update('none');

                charts.mem.data.labels = labels;
                charts.mem.data.datasets[0].data = data.history.map(h => h.mem_avg);
                charts.mem.update('none');
            } catch(e){}
        }

        async function loadAlerts() {
            const resp = await fetch('/api/v1/alerts', {headers: {'Authorization': 'Bearer ' + token}});
            if (!resp.ok) return;
            const data = await resp.json();
            document.getElementById('alertsList').innerHTML = data.alerts.map(a => `
                <div class="p-4 bg-[#0d1117] rounded border border-[#30363d] flex items-center justify-between">
                    <div><div class="text-xs font-bold text-white">${a.name}</div><div class="text-[10px] text-slate-500">${a.metric} > ${a.threshold}%</div></div>
                    <button onclick="deleteAlert(${a.id})" class="text-red-500/50 hover:text-red-500"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function loadAuditLogs() {
            const resp = await fetch('/api/v1/audit-log?limit=50', {headers: {'Authorization': 'Bearer ' + token}});
            if (!resp.ok) return;
            const data = await resp.json();
            document.getElementById('auditLogs').innerHTML = data.logs.map(l => `
                <div class="flex gap-4">
                    <span class="text-slate-600">[${l.timestamp.split('T')[1].substring(0, 8)}]</span>
                    <span class="text-blue-400 font-bold">${l.username}</span>
                    <span class="text-white">${l.action}</span>
                    <span class="text-slate-500">${l.target || '-'}</span>
                </div>
            `).join('');
        }

        async function deleteServer(id) {
            if (confirm('REMOVE NODE?')) {
                await fetch(`/api/v1/servers/${id}`, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
                loadData();
            }
        }

        async function deleteAlert(id) {
            await fetch(`/api/v1/alerts/${id}`, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
            loadAlerts();
        }

        async function changePassword() {
            const p = prompt('NEW PASSWORD:');
            if (p) await fetch('/api/v1/auth/reset-password', {method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}, body: JSON.stringify({new_password: p})});
        }

        loadData();
        setInterval(loadData, 10000);
    </script>
</body>
</html>"""
