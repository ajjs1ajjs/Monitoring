"""Modern Enhanced Dashboard for PyMon"""

from fastapi import APIRouter

router = APIRouter()

# ============================================================================
# Login HTML (Modern & Clean)
# ============================================================================

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .glass { background: rgba(20, 22, 26, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .gradient-bg { background: radial-gradient(circle at top left, #1e293b, #0f172a); }
        .glow { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    </style>
</head>
<body class="gradient-bg min-h-screen flex items-center justify-center p-6 text-slate-200">
    <div class="glass w-full max-w-md p-10 rounded-3xl glow">
        <div class="text-center mb-10">
            <div class="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold mx-auto mb-4 shadow-lg shadow-blue-500/30">P</div>
            <h1 class="text-3xl font-bold tracking-tight text-white">PyMon</h1>
            <p class="text-slate-400 mt-2">Enterprise Server Monitoring</p>
        </div>

        <div id="errorBox" class="hidden mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm text-center">
            Invalid username or password
        </div>

        <form id="loginForm" class="space-y-6">
            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Username</label>
                <input type="text" id="username" required class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all" placeholder="admin">
            </div>
            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Password</label>
                <input type="password" id="password" required class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all" placeholder="••••••••">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-blue-600/20 active:scale-[0.98]">
                Sign In
            </button>
        </form>

        <p class="mt-8 text-center text-slate-500 text-xs">
            &copy; 2026 PyMon Monitoring System. All rights reserved.
        </p>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorBox = document.getElementById('errorBox');
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
                errorBox.textContent = 'Connection error. Please try again.';
                errorBox.classList.remove('hidden');
            }
        });
    </script>
</body>
</html>"""

# ============================================================================
# Main Enhanced Dashboard HTML
# ============================================================================

ENHANCED_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMon Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .glass { background: rgba(20, 22, 26, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); }
        .sidebar-item-active { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border-right: 2px solid #3b82f6; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        .chart-gradient-cpu { background: linear-gradient(180deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0) 100%); }
        .pulsing-dot { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    </style>
</head>
<body class="bg-[#0b0c0f] text-slate-300 min-h-screen flex overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 border-r border-slate-800/50 flex flex-col glass z-20">
        <div class="p-6 flex items-center gap-3">
            <div class="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/20">P</div>
            <span class="text-xl font-bold text-white tracking-tight">PyMon</span>
        </div>

        <nav class="flex-1 px-4 py-6 space-y-1">
            <button data-section="overview" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group active">
                <i data-lucide="layout-dashboard" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Overview</span>
            </button>
            <button data-section="servers" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group">
                <i data-lucide="server" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Servers</span>
            </button>
            <button data-section="alerts" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group">
                <i data-lucide="bell" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Alert Rules</span>
            </button>
            <button data-section="logs" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group">
                <i data-lucide="clipboard-list" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Audit Logs</span>
            </button>
            <button data-section="deploy" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group">
                <i data-lucide="rocket" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Deploy Agent</span>
            </button>
            <div class="pt-10 pb-4 text-[10px] font-bold text-slate-600 uppercase tracking-widest px-4">System</div>
            <button data-section="settings" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group">
                <i data-lucide="settings" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Settings</span>
            </button>
        </nav>

        <div class="p-4 border-t border-slate-800/50">
            <button id="logoutBtn" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-red-500/10 hover:text-red-400 group">
                <i data-lucide="log-out" class="w-5 h-5"></i>
                <span class="font-medium text-sm">Logout</span>
            </button>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <!-- Header -->
        <header class="h-20 border-bottom border-slate-800/30 flex items-center justify-between px-8 z-10">
            <div>
                <h2 id="pageTitle" class="text-2xl font-bold text-white tracking-tight">Overview</h2>
                <p class="text-xs text-slate-500 mt-0.5">Real-time infrastructure monitoring</p>
            </div>

            <div class="flex items-center gap-4">
                <div class="flex bg-slate-900/50 rounded-xl p-1 border border-slate-800">
                    <button data-range="1h" class="range-btn px-4 py-1.5 rounded-lg text-xs font-medium transition-all active bg-blue-600 text-white">1h</button>
                    <button data-range="6h" class="range-btn px-4 py-1.5 rounded-lg text-xs font-medium transition-all text-slate-400 hover:text-slate-200">6h</button>
                    <button data-range="24h" class="range-btn px-4 py-1.5 rounded-lg text-xs font-medium transition-all text-slate-400 hover:text-slate-200">24h</button>
                    <button data-range="7d" class="range-btn px-4 py-1.5 rounded-lg text-xs font-medium transition-all text-slate-400 hover:text-slate-200">7d</button>
                </div>

                <button id="refreshBtn" class="w-10 h-10 flex items-center justify-center rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-600 transition-all">
                    <i data-lucide="rotate-cw" class="w-4 h-4 text-slate-400"></i>
                </button>
            </div>
        </header>

        <!-- Content Area -->
        <div id="content" class="flex-1 overflow-y-auto p-8 custom-scrollbar space-y-8">
            <!-- Section: Overview -->
            <div id="section-overview" class="section active space-y-8">
                <!-- Summary Cards -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div class="glass p-6 rounded-3xl relative overflow-hidden group">
                        <div class="absolute -right-4 -top-4 w-24 h-24 bg-emerald-500/10 blur-3xl rounded-full transition-all group-hover:bg-emerald-500/20"></div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="p-3 bg-emerald-500/10 rounded-2xl text-emerald-500">
                                <i data-lucide="check-circle" class="w-6 h-6"></i>
                            </div>
                            <span class="text-emerald-500 text-xs font-bold tracking-wider uppercase">Online</span>
                        </div>
                        <div class="text-4xl font-bold text-white mb-1" id="stat-online">0</div>
                        <div class="text-slate-500 text-xs">Operational nodes</div>
                    </div>

                    <div class="glass p-6 rounded-3xl relative overflow-hidden group">
                        <div class="absolute -right-4 -top-4 w-24 h-24 bg-red-500/10 blur-3xl rounded-full transition-all group-hover:bg-red-500/20"></div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="p-3 bg-red-500/10 rounded-2xl text-red-500">
                                <i data-lucide="alert-triangle" class="w-6 h-6"></i>
                            </div>
                            <span class="text-red-500 text-xs font-bold tracking-wider uppercase">Offline</span>
                        </div>
                        <div class="text-4xl font-bold text-white mb-1" id="stat-offline">0</div>
                        <div class="text-slate-500 text-xs">Requires attention</div>
                    </div>

                    <div class="glass p-6 rounded-3xl relative overflow-hidden group">
                        <div class="absolute -right-4 -top-4 w-24 h-24 bg-blue-500/10 blur-3xl rounded-full transition-all group-hover:bg-blue-500/20"></div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="p-3 bg-blue-500/10 rounded-2xl text-blue-500">
                                <i data-lucide="cpu" class="w-6 h-6"></i>
                            </div>
                            <span class="text-blue-500 text-xs font-bold tracking-wider uppercase">Avg CPU</span>
                        </div>
                        <div class="text-4xl font-bold text-white mb-1" id="stat-cpu-avg">0%</div>
                        <div class="flex items-center gap-1 text-emerald-500 text-[10px] font-bold" id="cpu-trend">
                            <i data-lucide="trending-down" class="w-3 h-3"></i> -1.2%
                        </div>
                    </div>

                    <div class="glass p-6 rounded-3xl relative overflow-hidden group">
                        <div class="absolute -right-4 -top-4 w-24 h-24 bg-purple-500/10 blur-3xl rounded-full transition-all group-hover:bg-purple-500/20"></div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="p-3 bg-purple-500/10 rounded-2xl text-purple-500">
                                <i data-lucide="layers" class="w-6 h-6"></i>
                            </div>
                            <span class="text-purple-500 text-xs font-bold tracking-wider uppercase">Avg RAM</span>
                        </div>
                        <div class="text-4xl font-bold text-white mb-1" id="stat-mem-avg">0%</div>
                        <div class="flex items-center gap-1 text-red-500 text-[10px] font-bold" id="mem-trend">
                            <i data-lucide="trending-up" class="w-3 h-3"></i> +0.4%
                        </div>
                    </div>
                </div>

                <!-- Charts Row -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div class="glass p-8 rounded-[2rem] space-y-6">
                        <div class="flex items-center justify-between">
                            <h3 class="text-lg font-bold text-white">CPU Performance</h3>
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-emerald-500 pulsing-dot"></span>
                                <span class="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Real-time</span>
                            </div>
                        </div>
                        <div class="h-[280px] w-full">
                            <canvas id="cpuChart"></canvas>
                        </div>
                    </div>

                    <div class="glass p-8 rounded-[2rem] space-y-6">
                        <div class="flex items-center justify-between">
                            <h3 class="text-lg font-bold text-white">Memory Utilization</h3>
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-blue-500 pulsing-dot"></span>
                                <span class="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Real-time</span>
                            </div>
                        </div>
                        <div class="h-[280px] w-full">
                            <canvas id="memoryChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Server List Quick View -->
                <div class="glass rounded-[2rem] overflow-hidden">
                    <div class="p-8 border-b border-slate-800/30 flex items-center justify-between bg-slate-900/20">
                        <h3 class="text-lg font-bold text-white">Infrastructure Status</h3>
                        <button onclick="showSection('servers')" class="text-blue-500 text-xs font-bold hover:underline">View all nodes</button>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left">
                            <thead class="text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-900/10">
                                <tr>
                                    <th class="px-8 py-5">Node Name</th>
                                    <th class="px-8 py-5">Status</th>
                                    <th class="px-8 py-5">CPU</th>
                                    <th class="px-8 py-5">RAM</th>
                                    <th class="px-8 py-5 text-right">Last Check</th>
                                </tr>
                            </thead>
                            <tbody id="quickServerList" class="divide-y divide-slate-800/20">
                                <!-- Row template -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Section: Servers (Full List) -->
            <div id="section-servers" class="section hidden space-y-8">
                <div class="flex justify-between items-center">
                    <h3 class="text-xl font-bold text-white">Monitored Nodes</h3>
                    <button id="addServerBtn" class="bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20">
                        <i data-lucide="plus" class="w-4 h-4"></i> Add Server
                    </button>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6" id="serverCards">
                    <!-- Cards will be injected here -->
                </div>
            </div>

            <!-- Section: Deploy -->
            <div id="section-deploy" class="section hidden space-y-8">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div class="glass p-8 rounded-[2rem] space-y-6">
                        <div class="flex items-center gap-4 mb-2">
                            <div class="p-3 bg-blue-500/10 rounded-2xl text-blue-500"><i data-lucide="monitor" class="w-6 h-6"></i></div>
                            <h3 class="text-xl font-bold text-white">Windows Agent</h3>
                        </div>
                        <p class="text-sm text-slate-400">Install <strong>windows_exporter</strong> to monitor CPU, Memory, Disks, and Network on Windows Server.</p>
                        <div class="bg-slate-900 rounded-2xl p-6 font-mono text-xs text-blue-400 border border-slate-800 relative group">
                            <pre class="whitespace-pre-wrap break-all" id="winCmd">Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/install_exporter.ps1'))</pre>
                            <button onclick="copyCmd('winCmd')" class="absolute top-4 right-4 p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 opacity-0 group-hover:opacity-100 transition-all">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>

                    <div class="glass p-8 rounded-[2rem] space-y-6">
                        <div class="flex items-center gap-4 mb-2">
                            <div class="p-3 bg-orange-500/10 rounded-2xl text-orange-500"><i data-lucide="terminal" class="w-6 h-6"></i></div>
                            <h3 class="text-xl font-bold text-white">Linux Agent</h3>
                        </div>
                        <p class="text-sm text-slate-400">Install <strong>node_exporter</strong> via our automated script to monitor Linux infrastructure.</p>
                        <div class="bg-slate-900 rounded-2xl p-6 font-mono text-xs text-orange-400 border border-slate-800 relative group">
                            <pre class="whitespace-pre-wrap break-all" id="linuxCmd">curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/agent/install-linux.sh | sudo bash</pre>
                            <button onclick="copyCmd('linuxCmd')" class="absolute top-4 right-4 p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 opacity-0 group-hover:opacity-100 transition-all">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section: Logs -->
            <div id="section-logs" class="section hidden space-y-8">
                <div class="glass rounded-[2rem] overflow-hidden">
                    <div class="p-8 border-b border-slate-800/30 bg-slate-900/20">
                        <h3 class="text-lg font-bold text-white">Audit Logs</h3>
                    </div>
                    <div class="p-6">
                        <div id="auditLogs" class="space-y-4">
                            <!-- Logs will be injected here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Modals -->
    <div id="addServerModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden items-center justify-center p-6">
        <div class="glass w-full max-w-lg p-10 rounded-[2.5rem] glow relative">
            <button onclick="toggleModal('addServerModal', false)" class="absolute top-8 right-8 text-slate-500 hover:text-white">
                <i data-lucide="x" class="w-6 h-6"></i>
            </button>
            <h3 class="text-2xl font-bold text-white mb-2">Add New Node</h3>
            <p class="text-sm text-slate-500 mb-8">Connect a new server to the monitoring mesh</p>

            <form id="addServerForm" class="space-y-6">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Server Name</label>
                    <input type="text" id="nodeName" required class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all" placeholder="Web-Srv-01">
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Host / IP</label>
                    <input type="text" id="nodeHost" required class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all" placeholder="10.0.0.5">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">OS Type</label>
                        <select id="nodeOS" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all">
                            <option value="linux">Linux</option>
                            <option value="windows">Windows</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Agent Port</label>
                        <input type="number" id="nodePort" value="9100" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all">
                    </div>
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-4 rounded-2xl transition-all shadow-lg shadow-blue-600/20 active:scale-[0.98] mt-4">
                    Register Node
                </button>
            </form>
        </div>
    </div>

    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';

        let charts = {};
        let currentRange = '1h';
        let servers = [];

        // Initialize Lucide Icons
        lucide.createIcons();

        // Navigation
        document.querySelectorAll('nav button').forEach(btn => {
            btn.addEventListener('click', () => {
                const section = btn.dataset.section;
                document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
                document.getElementById('section-' + section).classList.remove('hidden');

                document.querySelectorAll('nav button').forEach(b => b.classList.remove('active', 'sidebar-item-active'));
                btn.classList.add('sidebar-item-active');

                document.getElementById('pageTitle').textContent = section.charAt(0).toUpperCase() + section.slice(1);
            });
        });

        // Range Buttons
        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active', 'bg-blue-600', 'text-white'));
                document.querySelectorAll('.range-btn').forEach(b => b.classList.add('text-slate-400'));
                btn.classList.remove('text-slate-400');
                btn.classList.add('active', 'bg-blue-600', 'text-white');
                currentRange = btn.dataset.range;
                loadData();
            });
        });

        // Logout
        document.getElementById('logoutBtn').addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/login';
        });

        // Refresh
        document.getElementById('refreshBtn').addEventListener('click', () => loadData());

        // Modals
        function toggleModal(id, show) {
            const modal = document.getElementById(id);
            modal.classList.toggle('hidden', !show);
            modal.classList.toggle('flex', show);
        }

        document.getElementById('addServerBtn').addEventListener('click', () => toggleModal('addServerModal', true));

        document.getElementById('addServerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            await fetch('/api/v1/servers', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({
                    name: document.getElementById('nodeName').value,
                    host: document.getElementById('nodeHost').value,
                    os_type: document.getElementById('nodeOS').value,
                    agent_port: parseInt(document.getElementById('nodePort').value)
                })
            });
            toggleModal('addServerModal', false);
            loadData();
        });

        // Chart Helper
        function createChart(canvasId, label, color) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, color + '33');
            gradient.addColorStop(1, color + '00');

            return new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        pointHoverBackgroundColor: color,
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
                    scales: {
                        y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b', font: { size: 10 }, callback: v => v + '%' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 }, maxRotation: 0 } }
                    }
                }
            });
        }

        charts.cpu = createChart('cpuChart', 'CPU Usage', '#10b981');
        charts.memory = createChart('memoryChart', 'Memory Usage', '#3b82f6');

        // Data Loading
        async function loadData() {
            try {
                // 1. Load Servers
                const sResp = await fetch('/api/v1/servers', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                if (sResp.status === 401) window.location.href = '/login';
                servers = await sResp.json();

                updateOverview();
                updateServerUI();

                // 2. Load History for Charts
                const hResp = await fetch(`/api/v1/servers/history?range=${currentRange}`, {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                const hData = await hResp.json();

                if (hData.servers && hData.servers.length > 0) {
                    // Just pick first server for global overview charts for now
                    const sData = hData.servers[0];
                    updateChart(charts.cpu, sData.labels, sData.cpu);
                    updateChart(charts.memory, sData.labels, sData.memory);
                }

                // 3. Load Trends
                loadTrends();

                // 4. Load Audit Logs
                if (!document.getElementById('section-logs').classList.contains('hidden')) {
                    loadAuditLogs();
                }

            } catch (e) {
                console.error('Failed to load data', e);
            }
        }

        function updateChart(chart, labels, data) {
            chart.data.labels = labels.map(l => l.split('T')[1].substring(0, 5));
            chart.data.datasets[0].data = data;
            chart.update();
        }

        function updateOverview() {
            const online = servers.filter(s => s.last_status === 'up').length;
            const offline = servers.length - online;

            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;

            if (servers.length > 0) {
                const cpu = servers.reduce((a, b) => a + (b.cpu_percent || 0), 0) / servers.length;
                const mem = servers.reduce((a, b) => a + (b.memory_percent || 0), 0) / servers.length;
                document.getElementById('stat-cpu-avg').textContent = cpu.toFixed(1) + '%';
                document.getElementById('stat-mem-avg').textContent = mem.toFixed(1) + '%';
            }
        }

        function updateServerUI() {
            // Quick List
            const quickList = document.getElementById('quickServerList');
            quickList.innerHTML = servers.slice(0, 5).map(s => `
                <tr class="hover:bg-slate-800/20 transition-all">
                    <td class="px-8 py-5 font-medium text-white text-sm">${s.name}</td>
                    <td class="px-8 py-5">
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider ${s.last_status === 'up' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}">
                            <span class="w-1.5 h-1.5 rounded-full ${s.last_status === 'up' ? 'bg-emerald-500' : 'bg-red-500'} pulsing-dot"></span>
                            ${s.last_status === 'up' ? 'Online' : 'Offline'}
                        </span>
                    </td>
                    <td class="px-8 py-5">
                        <div class="flex items-center gap-3">
                            <div class="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div class="h-full bg-emerald-500 rounded-full" style="width: ${s.cpu_percent || 0}%"></div>
                            </div>
                            <span class="text-xs font-bold text-slate-400">${(s.cpu_percent || 0).toFixed(0)}%</span>
                        </div>
                    </td>
                    <td class="px-8 py-5">
                        <div class="flex items-center gap-3">
                            <div class="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div class="h-full bg-blue-500 rounded-full" style="width: ${s.memory_percent || 0}%"></div>
                            </div>
                            <span class="text-xs font-bold text-slate-400">${(s.memory_percent || 0).toFixed(0)}%</span>
                        </div>
                    </td>
                    <td class="px-8 py-5 text-right text-xs text-slate-500">${s.last_check ? s.last_check.split('T')[1].substring(0, 5) : '-'}</td>
                </tr>
            `).join('');

            // Full Grid
            const grid = document.getElementById('serverCards');
            grid.innerHTML = servers.map(s => `
                <div class="glass p-6 rounded-[2rem] space-y-6 relative overflow-hidden group">
                    <div class="absolute right-6 top-6">
                        <span class="p-2 bg-slate-800/50 rounded-lg text-slate-500 hover:text-white cursor-pointer transition-all" onclick="deleteServer(${s.id})">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </span>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="p-4 ${s.os_type === 'windows' ? 'bg-blue-500/10 text-blue-500' : 'bg-orange-500/10 text-orange-500'} rounded-2xl">
                            <i data-lucide="${s.os_type === 'windows' ? 'monitor' : 'terminal'}" class="w-6 h-6"></i>
                        </div>
                        <div>
                            <h4 class="font-bold text-white text-lg">${s.name}</h4>
                            <p class="text-xs text-slate-500">${s.host}:${s.agent_port}</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-slate-900/40 p-4 rounded-2xl border border-slate-800/30">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">CPU</div>
                            <div class="text-2xl font-bold text-emerald-500">${(s.cpu_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div class="bg-slate-900/40 p-4 rounded-2xl border border-slate-800/30">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">Memory</div>
                            <div class="text-2xl font-bold text-blue-500">${(s.memory_percent || 0).toFixed(1)}%</div>
                        </div>
                    </div>

                    <div class="pt-2 flex items-center justify-between text-[10px] font-bold text-slate-600 uppercase">
                        <span>Status: <span class="${s.last_status === 'up' ? 'text-emerald-500' : 'text-red-500'}">${s.last_status}</span></span>
                        <span>Uptime: ${s.uptime || '-'}</span>
                    </div>
                </div>
            `).join('');

            lucide.createIcons();
        }

        async function loadTrends() {
            const cpuTrend = await (await fetch(`/api/v1/servers/compare?metric=cpu&range=${currentRange}`, {headers: {'Authorization': 'Bearer ' + token}})).json();
            const memTrend = await (await fetch(`/api/v1/servers/compare?metric=memory&range=${currentRange}`, {headers: {'Authorization': 'Bearer ' + token}})).json();

            updateTrendUI('cpu-trend', cpuTrend);
            updateTrendUI('mem-trend', memTrend);
        }

        function updateTrendUI(id, data) {
            const el = document.getElementById(id);
            const isDown = data.delta < 0;
            el.innerHTML = `<i data-lucide="trending-${isDown ? 'down' : 'up'}" class="w-3 h-3"></i> ${isDown ? '' : '+'}${data.delta_percent}%`;
            el.className = `flex items-center gap-1 ${isDown ? 'text-emerald-500' : 'text-red-500'} text-[10px] font-bold`;
            lucide.createIcons();
        }

        async function loadAuditLogs() {
            const resp = await fetch('/api/v1/audit-log?limit=20', {headers: {'Authorization': 'Bearer ' + token}});
            const data = await resp.json();
            const logs = document.getElementById('auditLogs');
            logs.innerHTML = data.logs.map(l => `
                <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-slate-800/30 transition-all border border-transparent hover:border-slate-800/50">
                    <div class="p-2 bg-blue-500/10 rounded-xl text-blue-500 mt-1"><i data-lucide="user" class="w-4 h-4"></i></div>
                    <div class="flex-1">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-sm font-bold text-white">${l.username} <span class="text-slate-500 font-normal">performed</span> ${l.action}</span>
                            <span class="text-[10px] font-bold text-slate-600 uppercase">${l.timestamp.split('T')[1].substring(0, 5)}</span>
                        </div>
                        <p class="text-xs text-slate-500">Target: ${l.target || 'System'}</p>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        async function deleteServer(id) {
            if (confirm('Decommission this node?')) {
                await fetch(`/api/v1/servers/${id}`, {method: 'DELETE', headers: {'Authorization': 'Bearer ' + token}});
                loadData();
            }
        }

        function copyCmd(id) {
            const text = document.getElementById(id).textContent;
            navigator.clipboard.writeText(text);
            alert('Command copied to clipboard!');
        }

        // Auto Refresh
        loadData();
        setInterval(loadData, 30000);
    </script>
</body>
</html>"""
