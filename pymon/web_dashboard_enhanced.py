"""Enhanced Web Dashboard Template with Dark Mode NOC Aesthetics"""

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
    <div class="glass p-10 rounded-[2.5rem] w-full max-w-md shadow-2xl">
        <h1 class="text-3xl font-bold mb-2 text-center">PyMon</h1>
        <p class="text-slate-500 text-center mb-8 text-sm">Enter your credentials to access the NOC</p>
        
        <form id="loginForm" class="space-y-6">
            <div>
                <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Username</label>
                <input type="text" id="username" required class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500 transition-all">
            </div>
            <div>
                <label class="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Password</label>
                <input type="password" id="password" required class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-orange-500 transition-all">
            </div>
            <button type="submit" class="w-full bg-orange-600 hover:bg-orange-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-orange-600/20 transition-all">
                Authorize Access
            </button>
            <div id="error" class="text-red-500 text-center text-xs hidden">Invalid credentials</div>
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
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Space Grotesk', sans-serif; background: #05070d; }
        code, pre, .mono { font-family: 'JetBrains Mono', monospace; }
        .noc-bg {
            position: fixed; inset: 0; pointer-events: none; z-index: 0;
            background:
                radial-gradient(circle at 15% 15%, rgba(255, 122, 0, .22), transparent 32%),
                radial-gradient(circle at 86% 12%, rgba(0, 224, 255, .18), transparent 30%),
                radial-gradient(circle at 55% 90%, rgba(34, 197, 94, .12), transparent 26%),
                linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
            background-size: auto, auto, auto, 44px 44px, 44px 44px;
            mask-image: linear-gradient(to bottom, black, rgba(0,0,0,.55));
        }
        .glass {
            background: linear-gradient(180deg, rgba(13, 18, 30, .88), rgba(8, 11, 20, .76));
            backdrop-filter: blur(18px);
            border: 1px solid rgba(148, 163, 184, .14);
            box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 24px 80px rgba(0,0,0,.34);
        }
        .sidebar-item-active { background: rgba(255, 122, 0, 0.13); color: #ffb86b; border-right: 2px solid #ff7a00; }
        .critical-glow { box-shadow: 0 0 38px rgba(255, 122, 0, .18); }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        .pulsing-dot { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: .4; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }
    </style>
</head>
<body class="text-slate-300 selection:bg-orange-500/30 overflow-hidden">
    <div class="noc-bg"></div>

    <div class="flex h-screen relative z-10">
        <!-- Sidebar -->
        <aside class="w-72 glass border-r border-slate-800/50 flex flex-col">
            <div class="p-8">
                <div class="flex items-center gap-3 mb-10">
                    <div class="w-10 h-10 bg-orange-500 rounded-2xl flex items-center justify-center shadow-lg shadow-orange-500/20">
                        <i data-lucide="activity" class="text-black w-6 h-6"></i>
                    </div>
                    <div>
                        <h1 class="text-xl font-black text-white tracking-tighter">PYMON</h1>
                        <p class="text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">Control Node</p>
                    </div>
                </div>

                <nav class="space-y-2">
                    <button data-section="overview" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-slate-800/50 group sidebar-item-active">
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
            </div>

            <div class="mt-auto p-4 border-t border-slate-800/50">
                <button id="logoutBtn" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all hover:bg-red-500/10 hover:text-red-400 group">
                    <i data-lucide="log-out" class="w-5 h-5"></i>
                    <span class="font-medium text-sm">Logout</span>
                </button>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
            <!-- Header -->
            <header class="h-20 border-b border-slate-800/30 flex items-center justify-between px-8 z-10">
                <div>
                    <h2 id="pageTitle" class="text-3xl font-black text-white tracking-tight">Command Center</h2>
                    <p class="text-xs text-slate-500 mt-1 mono">live telemetry / exporters / incident surface</p>
                </div>

                    <!-- Summary Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <div class="glass p-6 rounded-3xl relative overflow-hidden group critical-glow">
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
                        </div>
                    </div>

                    <!-- Charts Row -->
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div class="glass p-8 rounded-[2rem] space-y-6">
                            <div class="flex items-center justify-between">
                                <h3 class="text-lg font-bold text-white">CPU Performance</h3>
                                <div class="flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 pulsing-dot"></span>
                                    <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Live</span>
                                </div>
                            </div>
                            <div class="h-[200px] w-full">
                                <canvas id="cpuChart"></canvas>
                            </div>
                        </div>

                        <div class="glass p-8 rounded-[2rem] space-y-6">
                            <div class="flex items-center justify-between">
                                <h3 class="text-lg font-bold text-white">Memory Load</h3>
                                <div class="flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-blue-500 pulsing-dot"></span>
                                    <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Live</span>
                                </div>
                            </div>
                            <div class="h-[200px] w-full">
                                <canvas id="memoryChart"></canvas>
                            </div>
                        </div>

                        <div class="glass p-8 rounded-[2rem] space-y-6">
                            <div class="flex items-center justify-between">
                                <h3 class="text-lg font-bold text-white">Network (MB)</h3>
                                <div class="flex items-center gap-2">
                                    <span class="w-2 h-2 rounded-full bg-orange-500 pulsing-dot"></span>
                                    <span class="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Live</span>
                                </div>
                            </div>
                            <div class="h-[200px] w-full">
                                <canvas id="networkChart"></canvas>
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
                                        <th class="px-8 py-5">Host</th>
                                        <th class="px-8 py-5">OS</th>
                                        <th class="px-8 py-5">CPU</th>
                                        <th class="px-8 py-5">RAM</th>
                                        <th class="px-8 py-5">Disk</th>
                                        <th class="px-8 py-5">Network (RX/TX)</th>
                                        <th class="px-8 py-5 text-right">Actions</th>
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

                <!-- Section: Alerts -->
                <div id="section-alerts" class="section hidden space-y-8">
                    <div class="glass rounded-[2rem] overflow-hidden">
                        <div class="p-8 border-b border-slate-800/30 bg-slate-900/20 flex items-center justify-between">
                            <h3 class="text-lg font-bold text-white">Alert Rules</h3>
                            <button id="addAlertBtn" class="px-6 py-2 rounded-xl bg-orange-500 text-black text-xs font-bold shadow-lg shadow-orange-500/20 hover:scale-105 transition-all">Create Rule</button>
                        </div>
                        <div class="p-8">
                            <div id="alertsList" class="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <!-- Alerts will be injected here -->
                            </div>
                        </div>
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

                <!-- Section: Settings -->
                <div id="section-settings" class="section hidden space-y-8">
                    <div class="glass rounded-[2rem] overflow-hidden">
                        <div class="p-8 border-b border-slate-800/30 bg-slate-900/20">
                            <h3 class="text-lg font-bold text-white">System Settings</h3>
                        </div>
                        <div class="p-8 space-y-8 max-w-2xl">
                            <div class="space-y-4">
                                <h4 class="text-xs font-bold text-slate-500 uppercase tracking-widest">General Configuration</h4>
                                <div class="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 flex items-center justify-between">
                                    <div>
                                        <div class="text-white font-medium">Metrics Retention</div>
                                        <div class="text-xs text-slate-500">How long to keep historical telemetry data</div>
                                    </div>
                                    <select class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none">
                                        <option>7 days</option>
                                        <option>30 days</option>
                                        <option>90 days</option>
                                    </select>
                                </div>
                            </div>
                            <div class="space-y-4">
                                <label class="block text-sm font-semibold text-slate-400">Admin Password</label>
                                <button onclick="changePassword()" class="px-6 py-3 rounded-xl bg-slate-800 text-white font-semibold hover:bg-slate-700 transition-all">Change Password</button>
                            </div>

                            <!-- Notification Channels -->
                            <div class="pt-8 border-t border-slate-800/30">
                                <h4 class="text-white font-bold mb-6 flex items-center gap-2"><i data-lucide="bell" class="w-5 h-5 text-orange-500"></i> Notification Channels</h4>
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div class="flex items-center justify-between p-4 bg-slate-900/50 rounded-2xl border border-slate-800">
                                        <div class="flex items-center gap-4">
                                            <div class="p-2 bg-[#229ED9]/10 text-[#229ED9] rounded-xl"><i data-lucide="send" class="w-4 h-4"></i></div>
                                            <div class="text-white font-bold text-sm">Telegram</div>
                                        </div>
                                        <button class="px-4 py-2 rounded-lg bg-slate-800 text-[10px] font-bold text-slate-400 hover:text-white transition-all">Setup</button>
                                    </div>
                                    <div class="flex items-center justify-between p-4 bg-slate-900/50 rounded-2xl border border-slate-800">
                                        <div class="flex items-center gap-4">
                                            <div class="p-2 bg-[#5865F2]/10 text-[#5865F2] rounded-xl"><i data-lucide="message-square" class="w-4 h-4"></i></div>
                                            <div class="text-white font-bold text-sm">Discord</div>
                                        </div>
                                        <button class="px-4 py-2 rounded-lg bg-slate-800 text-[10px] font-bold text-slate-400 hover:text-white transition-all">Setup</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

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

    <div id="addAlertModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden items-center justify-center p-6">
        <div class="glass w-full max-w-lg p-10 rounded-[2.5rem] glow relative">
            <button onclick="toggleModal('addAlertModal', false)" class="absolute top-8 right-8 text-slate-500 hover:text-white">
                <i data-lucide="x" class="w-6 h-6"></i>
            </button>
            <h3 class="text-2xl font-bold text-white mb-2">Create Alert Rule</h3>
            <p class="text-sm text-slate-500 mb-8">Define thresholds for automated notifications</p>

            <form id="addAlertForm" class="space-y-6">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Rule Name</label>
                    <input type="text" id="alertName" required class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all" placeholder="High CPU Usage">
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Metric</label>
                        <select id="alertMetric" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                            <option value="cpu">CPU Usage (%)</option>
                            <option value="memory">Memory Usage (%)</option>
                            <option value="disk">Disk Usage (%)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Threshold (%)</label>
                        <input type="number" id="alertThreshold" value="80" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Condition</label>
                        <select id="alertCondition" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                            <option value=">">Greater than</option>
                            <option value="<">Less than</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Duration (s)</label>
                        <input type="number" id="alertDuration" value="60" class="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white">
                    </div>
                </div>
                <button type="submit" class="w-full bg-orange-600 hover:bg-orange-500 text-white font-semibold py-4 rounded-2xl transition-all shadow-lg shadow-orange-600/20 active:scale-[0.98] mt-4">
                    Enable Alert Rule
                </button>
            </form>
        </div>
    </div>

    <script>
        const token = localStorage.getItem('token');
        if (!token) window.location.href = '/login';

        function toggleModal(id, show) {
            const el = document.getElementById(id);
            if (!el) return;
            if (show) {
                el.classList.remove('hidden');
                el.classList.add('flex');
            } else {
                el.classList.add('hidden');
                el.classList.remove('flex');
            }
        }

        let charts = {};
        let currentRange = '1h';
        let servers = [];

        // Initialize Lucide Icons
        lucide.createIcons();

        function showSection(section) {
            const sections = document.querySelectorAll('.section');
            const targetSection = document.getElementById('section-' + section);

            if (targetSection) {
                sections.forEach(s => s.classList.add('hidden'));
                targetSection.classList.remove('hidden');

                document.querySelectorAll('nav button').forEach(b => b.classList.remove('sidebar-item-active'));
                const btn = document.querySelector(`nav button[data-section="${section}"]`);
                if (btn) btn.classList.add('sidebar-item-active');

                const pageTitle = document.getElementById('pageTitle');
                if (pageTitle) {
                    pageTitle.textContent = section === 'overview' ? 'Command Center' : section.charAt(0).toUpperCase() + section.slice(1);
                }

                if (section === 'logs') loadAuditLogs();
                if (section === 'alerts') loadAlerts();
                if (section === 'overview') loadTrends();
            }
        }

        // Navigation
        document.querySelectorAll('nav button').forEach(btn => {
            btn.addEventListener('click', () => {
                showSection(btn.dataset.section);
            });
        });

        // Range Buttons
        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active', 'bg-orange-500', 'text-black'));
                document.querySelectorAll('.range-btn').forEach(b => b.classList.add('text-slate-400'));
                btn.classList.remove('text-slate-400');
                btn.classList.add('active', 'bg-orange-500', 'text-black');
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

        // Modals triggers
        const addSrvBtn = document.getElementById('addServerBtn');
        if (addSrvBtn) addSrvBtn.addEventListener('click', () => toggleModal('addServerModal', true));
        
        const addAltBtn = document.getElementById('addAlertBtn');
        if (addAltBtn) addAltBtn.addEventListener('click', () => toggleModal('addAlertModal', true));

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
            if (resp.ok) {
                toggleModal('addServerModal', false);
                e.target.reset();
                loadData();
            } else {
                const err = await resp.json();
                alert('Failed to add server: ' + (err.detail || 'Unknown error'));
            }
        });

        document.getElementById('addAlertForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await fetch('/api/v1/alerts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({
                    name: document.getElementById('alertName').value,
                    metric: document.getElementById('alertMetric').value,
                    condition: document.getElementById('alertCondition').value,
                    threshold: parseInt(document.getElementById('alertThreshold').value),
                    duration: parseInt(document.getElementById('alertDuration').value),
                    severity: 'warning'
                })
            });
            if (resp.status === 401) { window.location.href = '/login'; return; }
            if (resp.ok) {
                toggleModal('addAlertModal', false);
                e.target.reset();
                loadAlerts();
            } else {
                const err = await resp.json();
                alert('Failed to add alert rule: ' + (err.detail || 'Unknown error'));
            }
        });

        // Data Loading
        async function loadData() {
            try {
                const resp = await fetch('/api/v1/servers', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                if (resp.status === 401) { window.location.href = '/login'; return; }
                if (!resp.ok) return;
                const data = await resp.json();
                servers = data.servers;
                updateOverview();
                updateServerUI();
                loadTrends();
            } catch (e) { console.error('Failed to load data', e); }
        }

        function updateOverview() {
            const online = servers.filter(s => s.last_status === 'up').length;
            const offline = servers.length - online;
            document.getElementById('stat-online').textContent = online;
            document.getElementById('stat-offline').textContent = offline;
            const cpu = servers.length ? servers.reduce((a, b) => a + (b.cpu_percent || 0), 0) / servers.length : 0;
            const mem = servers.length ? servers.reduce((a, b) => a + (b.memory_percent || 0), 0) / servers.length : 0;
            document.getElementById('stat-cpu-avg').textContent = cpu.toFixed(1) + '%';
            document.getElementById('stat-mem-avg').textContent = mem.toFixed(1) + '%';
        }

        function updateServerUI() {
            const formatBytes = (b) => {
                if (!b) return '0 B';
                const i = Math.floor(Math.log(b) / Math.log(1024));
                return (b / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'KB', 'MB', 'GB', 'TB'][i];
            };

            const quickList = document.getElementById('quickServerList');
            quickList.innerHTML = servers.slice(0, 5).map(s => `
                <tr class="border-b border-slate-800/30 hover:bg-slate-800/20 transition-all group">
                    <td class="py-4 pl-8">
                        <div class="flex items-center gap-3">
                            <span class="w-2 h-2 rounded-full ${s.last_status === 'up' ? 'bg-emerald-500 pulsing-dot' : 'bg-red-500 pulsing-dot'}"></span>
                            <span class="font-semibold text-slate-200">${s.name}</span>
                        </div>
                    </td>
                    <td class="py-4 text-slate-400 text-sm font-mono">${s.host}</td>
                    <td class="py-4"><span class="px-2 py-1 rounded-lg bg-slate-800 text-[10px] font-bold text-slate-400 uppercase">${s.os_type}</span></td>
                    <td class="py-4">
                        <div class="flex flex-col gap-1">
                            <div class="text-[10px] font-bold text-slate-600">${(s.cpu_percent || 0).toFixed(1)}%</div>
                            <div class="w-20 bg-slate-800 h-1 rounded-full overflow-hidden">
                                <div class="bg-blue-500 h-full" style="width: ${s.cpu_percent || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td class="py-4">
                        <div class="flex flex-col gap-1">
                            <div class="text-[10px] font-bold text-slate-600">${(s.memory_percent || 0).toFixed(1)}%</div>
                            <div class="w-20 bg-slate-800 h-1 rounded-full overflow-hidden">
                                <div class="bg-emerald-500 h-full" style="width: ${s.memory_percent || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td class="py-4">
                        <div class="flex flex-col gap-1">
                            <div class="text-[10px] font-bold text-slate-600">${(s.disk_percent || 0).toFixed(1)}%</div>
                            <div class="w-20 bg-slate-800 h-1 rounded-full overflow-hidden">
                                <div class="bg-purple-500 h-full" style="width: ${s.disk_percent || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td class="py-4 text-xs font-mono text-slate-500">
                        ${formatBytes(s.network_rx)} / ${formatBytes(s.network_tx)}
                    </td>
                    <td class="py-4 text-right pr-8">
                        <button onclick="deleteServer(${s.id})" class="p-2 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-all opacity-0 group-hover:opacity-100">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

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
                            <div class="text-xl font-bold text-emerald-500">${(s.cpu_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div class="bg-slate-900/40 p-4 rounded-2xl border border-slate-800/30">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">RAM</div>
                            <div class="text-xl font-bold text-blue-500">${(s.memory_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div class="bg-slate-900/40 p-4 rounded-2xl border border-slate-800/30">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">Disk</div>
                            <div class="text-xl font-bold text-purple-500">${(s.disk_percent || 0).toFixed(1)}%</div>
                        </div>
                        <div class="bg-slate-900/40 p-4 rounded-2xl border border-slate-800/30">
                            <div class="text-[10px] font-bold text-slate-500 uppercase mb-2">Net Total</div>
                            <div class="text-[10px] font-bold text-orange-400">${formatBytes(s.network_rx + s.network_tx)}</div>
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


        async function loadAlerts() {
            try {
                const resp = await fetch('/api/v1/alerts', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                if (resp.status === 401) { window.location.href = '/login'; return; }
                if (!resp.ok) return;
                const data = await resp.json();
                const list = document.getElementById('alertsList');
                list.innerHTML = data.alerts.map(a => `
                    <div class="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 flex items-center justify-between">
                        <div>
                            <h4 class="font-bold text-white">${a.name}</h4>
                            <p class="text-xs text-slate-500">${a.metric} ${a.condition} ${a.threshold}% for ${a.duration}s</p>
                        </div>
                        <button onclick="deleteAlert(${a.id})" class="p-2 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-all">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                `).join('');
                lucide.createIcons();
            } catch (e) { console.error(e); }
        }

        async function deleteServer(id) {
            if (!confirm('Remove this node?')) return;
            const resp = await fetch(`/api/v1/servers/${id}`, {
                method: 'DELETE',
                headers: {'Authorization': 'Bearer ' + token}
            });
            if (resp.ok) loadData();
        }

        async function deleteAlert(id) {
            if (!confirm('Delete alert rule?')) return;
            const resp = await fetch(`/api/v1/alerts/${id}`, {
                method: 'DELETE',
                headers: {'Authorization': 'Bearer ' + token}
            });
            if (resp.ok) loadAlerts();
        }

        // Chart Helper
        function createChart(canvasId, label, color) {
            const el = document.getElementById(canvasId);
            if (!el) return null;
            const ctx = el.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, 200);
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
                        borderWidth: 2,
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
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } }
                        }
                    }
                }
            });
        }

        async function loadTrends() {
            try {
                const resp = await fetch('/api/v1/metrics/trend', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                if (!resp.ok) return;
                const data = await resp.json();
                
                if (!charts.cpu) charts.cpu = createChart('cpuChart', 'CPU', '#10b981');
                if (!charts.mem) charts.mem = createChart('memoryChart', 'Memory', '#3b82f6');
                if (!charts.net) charts.net = createChart('networkChart', 'Network', '#f59e0b');

                const labels = data.history.map(h => new Date(h.timestamp).toLocaleTimeString());
                const cpuData = data.history.map(h => h.cpu_avg);
                const memData = data.history.map(h => h.mem_avg);
                const netData = data.history.map(h => (h.net_rx_avg + h.net_tx_avg) / (1024 * 1024)); // MB

                if (charts.cpu) {
                    charts.cpu.data.labels = labels;
                    charts.cpu.data.datasets[0].data = cpuData;
                    charts.cpu.update('none');
                }
                if (charts.mem) {
                    charts.mem.data.labels = labels;
                    charts.mem.data.datasets[0].data = memData;
                    charts.mem.update('none');
                }
                if (charts.net) {
                    charts.net.data.labels = labels;
                    charts.net.data.datasets[0].data = netData;
                    charts.net.update('none');
                }
            } catch (e) { console.error(e); }
        }

        async function loadAuditLogs() {
            const resp = await fetch('/api/v1/audit-log?limit=20', {headers: {'Authorization': 'Bearer ' + token}});
            if (resp.status === 401) { window.location.href = '/login'; return; }
            if (!resp.ok) return;
            const data = await resp.json();
            const logs = document.getElementById('auditLogs');
            logs.innerHTML = data.logs.map(l => `
                <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-slate-800/30 transition-all">
                    <div class="p-2 bg-blue-500/10 rounded-xl text-blue-500 mt-1"><i data-lucide="user" class="w-4 h-4"></i></div>
                    <div class="flex-1">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-bold text-white">${l.username} ${l.action}</span>
                            <span class="text-[10px] text-slate-600 uppercase font-bold">${l.timestamp.split('T')[1].substring(0, 5)}</span>
                        </div>
                        <p class="text-xs text-slate-500">Target: ${l.target || 'System'}</p>
                    </div>
                </div>
            `).join('');
            lucide.createIcons();
        }

        function copyCmd(id) {
            const text = document.getElementById(id).textContent;
            navigator.clipboard.writeText(text);
            alert('Copied!');
        }

        async function changePassword() {
            const p = prompt('New password:');
            if (!p) return;
            const resp = await fetch('/api/v1/auth/reset-password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({new_password: p})
            });
            if (resp.ok) alert('Updated');
        }

        loadData();
        setInterval(loadData, 15000);
    </script>
</body>
</html>"""
