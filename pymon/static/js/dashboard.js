// Init Lucide
if (window.lucide) lucide.createIcons();

// State Management
const token = localStorage.getItem('token');
if (!token) window.location.href = '/login';

let currentRange = '1h';
let nodes = [];
let currentView = 'list';
let lastFetchedHistory = []; // Store history for detailed expansion

function switchView(view) {
    currentView = view;
    document.getElementById('btnViewList').classList.toggle('active', view === 'list');
    document.getElementById('btnViewGrid').classList.toggle('active', view === 'grid');
    document.getElementById('liveListContainer').style.display = view === 'list' ? 'block' : 'none';
    document.getElementById('liveGridContainer').classList.toggle('active', view === 'grid');
}

function isUsefulVolume(vol) {
    if (!vol) return false;
    const v = vol.toLowerCase();
    if (v.includes('harddiskvolume')) return false;
    if (v.includes('/snap/') || v.includes('docker') || v.includes('kubelet') || v.includes('tmpfs') || v.includes('overlay') || v === 'shm' || v.includes('/run/user/')) return false;
    return true;
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
        if (n.volumes) {
            const raw = n.volumes;
            const disks = typeof raw === 'string' ? JSON.parse(raw) : raw;
            const diskArray = Array.isArray(disks) ? disks : [];
            diskHtml = diskArray.filter(d => isUsefulVolume(d.volume)).map(d => {
                const pct = (d.used_percent || d.percent || 0);
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
                <div><span style="color: var(--text-muted);">Version:</span> <br><strong style="color: #fff;">${n.exporter_version || 'N/A'}</strong></div>
                <div><span style="color: var(--text-muted);">Maintenance:</span> <br><strong style="color: ${n.is_maintenance ? 'var(--warning)' : 'var(--success)'};">${n.is_maintenance ? 'ON' : 'OFF'}</strong></div>
                <div><span style="color: var(--text-muted);">Added:</span> <br><strong style="color: #fff;">${new Date(n.created_at).toLocaleDateString()}</strong></div>
            </div>
        </div>

        <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
            <button onclick="toggleMaintenance(${n.id}, ${!n.is_maintenance})" class="btn" style="flex: 1; background: ${n.is_maintenance ? 'var(--success)' : 'var(--warning)'}; color: #000; font-weight: 600;">
                ${n.is_maintenance ? 'Exit Maintenance' : 'Set Maintenance'}
            </button>
            <button onclick="generateReport(${n.id})" class="btn" style="flex: 1; border: 1px solid var(--border);">
                Generate Report
            </button>
        </div>
        
        <h4 style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;">Storage Volumes</h4>
        <div style="margin-bottom: 2rem;">
            ${diskHtml || '<div style="font-size:0.85rem; color:var(--text-muted);">No detailed disk data available</div>'}
        </div>
        
        <h4 style="color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;">Actions</h4>
        <div style="display: flex; gap: 1rem;">
            <button class="btn btn-secondary" onclick="closeDrawer(); showEditModal(${n.id});" style="flex: 1;"><i data-lucide="settings" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Manage Node</button>
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
    if (!el) return;
    el.classList.toggle('active', show);
}

function showSection(section) {
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
    const target = document.getElementById('section-' + section);
    if (target) target.classList.add('active');

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

function promptCustomRange(btn) {
    const range = prompt("Введіть власний період (наприклад: 2h, 45m, 10d):", "2h");
    if (range) {
        document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
        
        // Update all custom buttons to match
        document.querySelectorAll('.custom-btn').forEach(b => {
            b.dataset.realRange = range;
            b.textContent = range;
            b.classList.add('active');
        });
        
        currentRange = range;
        refreshData();
        if (typeof updateOverviewCharts === 'function') updateOverviewCharts();
    }
}

// Event Listeners
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => showSection(btn.dataset.section));
});

document.querySelectorAll('.range-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (btn.dataset.range === 'custom') {
            if (!btn.dataset.realRange) return; // Wait for prompt if first time
            currentRange = btn.dataset.realRange;
        } else {
            currentRange = btn.dataset.range;
        }
        
        document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
        
        // Synchronize active state across ALL buttons with same range
        document.querySelectorAll(`.range-btn[data-range="${btn.dataset.range}"]`).forEach(b => b.classList.add('active'));
        if (btn.dataset.range === 'custom') {
            document.querySelectorAll('.custom-btn').forEach(b => b.classList.add('active'));
        }
        
        refreshData();
        if (typeof updateOverviewCharts === 'function') updateOverviewCharts();
    });
});

const refreshBtn = document.getElementById('refreshBtn');
if (refreshBtn) refreshBtn.addEventListener('click', refreshData);

const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
});

// Auth Helper
async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = 'Bearer ' + token;
    try {
        const resp = await fetch(url, options);
        if (resp.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
            return null;
        }
        if (!resp.ok) {
            console.error(`API Error ${resp.status} on ${url}`);
            return null;
        }
        return resp;
    } catch (e) {
        console.error(`Fetch error on ${url}:`, e);
        return null;
    }
}

// Form Handlers
const addNodeForm = document.getElementById('addNodeForm');
if (addNodeForm) addNodeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Connecting...';
        
        const name = document.getElementById('nodeName').value;
        const host = document.getElementById('nodeHost').value;
        const os_type = document.getElementById('nodeOS').value;
        const agent_port = parseInt(document.getElementById('nodePort').value) || 9100;
        
        const resp = await apiFetch('/api/v1/servers', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name, host, os_type, agent_port,
                enabled: true
            })
        });
        
        if (resp && resp.ok) {
            toggleModal('addNodeModal', false);
            e.target.reset();
            await refreshData();
        } else if (resp) {
            const err = await resp.json();
            alert('Deployment Failed: ' + (err.detail || JSON.stringify(err)));
        }
    } catch (err) { 
        alert('Connection Error: ' + err.message); 
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});

const addAlertForm = document.getElementById('addAlertForm');
if (addAlertForm) addAlertForm.addEventListener('submit', async (e) => {
    e.preventDefault();
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
let services = [];

async function refreshData() {
    const syncEl = document.getElementById('updateTimer');
    const tableSyncEl = document.getElementById('tableSyncTime');
    if (syncEl) syncEl.textContent = 'Syncing...';

    try {
        const [servResp, servicesResp] = await Promise.all([
            apiFetch('/api/v1/servers'),
            apiFetch('/api/v1/services')
        ]);

        if (servResp && servResp.ok) {
            const data = await servResp.json();
            nodes = data.servers;
            filterNodes();
            const liveSearch = document.getElementById('liveSearch');
            if (liveSearch) filterLiveTable();
        }

        if (servicesResp && servicesResp.ok) {
            services = await servicesResp.json();
            updateServicesTable(services);
        }

        const timeStr = new Date().toLocaleTimeString();
        if (syncEl) syncEl.textContent = 'Last sync: ' + timeStr;
        if (tableSyncEl) tableSyncEl.textContent = 'Last update: ' + timeStr + ' • ' + nodes.length + ' active targets';
    } catch (e) {
        console.error("Refresh failed:", e);
        if (syncEl) syncEl.textContent = 'Sync Error';
    }
}

function filterLiveTable() {
    const liveSearch = document.getElementById('liveSearch');
    const query = (liveSearch?.value || '').toLowerCase();
    const filtered = nodes.filter(n =>
        (n.name || '').toLowerCase().includes(query) ||
        (n.host || '').toLowerCase().includes(query)
    );
    updateLiveTable(filtered);
}

function filterNodes() {
    const nodeSearch = document.getElementById('nodeSearch');
    const filterStatus = document.getElementById('filterStatus');
    
    const query = (nodeSearch?.value || '').toLowerCase();
    const statusFilter = filterStatus?.value || 'all';

    let filtered = nodes.filter(n => {
        const name = (n.name || '').toLowerCase();
        const host = (n.host || '').toLowerCase();
        const matchesSearch = name.includes(query) || host.includes(query);
        const matchesStatus = statusFilter === 'all' || n.last_status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Apply sorting
    filtered.sort((a, b) => {
        const valA = a[sortKey] || '';
        const valB = b[sortKey] || '';
        if (typeof valA === 'string') {
            return valA.localeCompare(valB) * sortOrder;
        }
        return (valA - valB) * sortOrder;
    });

    updateStats();
    updateLiveTable(filtered);
    updateNodeGrid(filtered);
    if (window.lucide) lucide.createIcons();
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
                    <span style="display:flex; align-items:center; gap:0.25rem; background: rgba(255,255,255,0.05); padding: 1px 4px; border-radius: 4px; border: 1px solid var(--border);">
                        <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background: ${n.exporter_version && n.exporter_version !== 'unknown' ? 'var(--success)' : 'var(--text-muted)'};"></span>
                        <span style="font-size: 0.65rem; color: ${n.exporter_version && n.exporter_version !== 'unknown' ? '#fff' : 'var(--text-muted)'}; font-family: 'JetBrains Mono';">${n.exporter_version || 'v?'}</span>
                    </span>
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
                            const raw = n.volumes;
                            if (!raw || raw === 'null') throw 0;
                            const disks = typeof raw === 'string' ? JSON.parse(raw) : raw;
                            const diskArray = Array.isArray(disks) ? disks : [];

                            return diskArray.filter(d => isUsefulVolume(d.volume)).map(d => {
                                const pct = (d.used_percent || d.percent || 0);
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
    if (!grid) return;
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
                    <span style="color: var(--accent);">${a.metric.toUpperCase()}</span> ${a.condition} <span style="color: var(--success);">${a.threshold}${a.metric.includes('latency') ? 'ms' : (a.metric.includes('status') ? '' : '%')}</span>
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

        const logTotalCount = document.getElementById('logTotalCount');
        if (logTotalCount) logTotalCount.textContent = total;
        if (document.getElementById('logAlertCount')) document.getElementById('logAlertCount').textContent = alerts;
        if (document.getElementById('logServerCount')) document.getElementById('logServerCount').textContent = servers;
        if (document.getElementById('logLoginCount')) document.getElementById('logLoginCount').textContent = logins;

        const auditLogStream = document.getElementById('auditLogStream');
        if (auditLogStream) {
            auditLogStream.innerHTML = logs.length ? logs.map(l => `
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
        }
    } catch (e) { console.error(e); }
}

async function deleteNode(id) {
    if (confirm('Permanently decommission this node?')) {
        try {
            const resp = await apiFetch(`/api/v1/servers/${id}`, {method: 'DELETE'});
            if (resp && resp.ok) {
                refreshData();
            } else {
                const err = await resp.json();
                alert('Error: ' + (err.detail || 'Could not delete server'));
            }
        } catch (err) {
            alert('Network error: ' + err);
        }
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
        const notifEnabled = document.getElementById('notifEnabled');
        if (notifEnabled) notifEnabled.checked = data.enabled;
        if (document.getElementById('tgToken')) document.getElementById('tgToken').value = data.telegram_bot_token || '';
        if (document.getElementById('tgChat')) document.getElementById('tgChat').value = data.telegram_chat_id || '';
        if (document.getElementById('dsWebhook')) document.getElementById('dsWebhook').value = data.discord_webhook_url || '';
        if (document.getElementById('tmWebhook')) document.getElementById('tmWebhook').value = data.teams_webhook_url || '';
        if (document.getElementById('smtpServer')) document.getElementById('smtpServer').value = data.smtp_server || '';
        if (document.getElementById('smtpPort')) document.getElementById('smtpPort').value = data.smtp_port || 587;
        if (document.getElementById('smtpUser')) document.getElementById('smtpUser').value = data.smtp_user || '';
        if (document.getElementById('smtpPass')) document.getElementById('smtpPass').value = data.smtp_pass || '';
        if (document.getElementById('emailTo')) document.getElementById('emailTo').value = data.email_to || '';
    }
    // Update system info
    const serverResp = await apiFetch('/api/v1/servers');
    if (serverResp && serverResp.ok) {
        const serverData = await serverResp.json();
        const allServers = serverData.servers || [];
        const online = allServers.filter(s => s.last_status === 'up').length;
        const settingsNodeCount = document.getElementById('settingsNodeCount');
        if (settingsNodeCount) settingsNodeCount.textContent = allServers.length;
        if (document.getElementById('settingsOnlineCount')) document.getElementById('settingsOnlineCount').textContent = online;
    }
    // Update uptime
    const settingsUptime = document.getElementById('settingsUptime');
    if (settingsUptime) settingsUptime.textContent = new Date().toLocaleString();
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
            alert('Test notification dispatched. Check your channels.');
        } else {
            const err = await resp.json();
            alert('Error: ' + (err.detail || 'Test failed'));
        }
    } catch (err) { alert('Connection Error'); }
}

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

// Auto-port selection
const nodeOS = document.getElementById('nodeOS');
if (nodeOS) nodeOS.addEventListener('change', (e) => {
    document.getElementById('nodePort').value = (e.target.value === 'windows') ? 9182 : 9100;
});
const editNodeOS = document.getElementById('editNodeOS');
if (editNodeOS) editNodeOS.addEventListener('change', (e) => {
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

const editNodeForm = document.getElementById('editNodeForm');
if (editNodeForm) editNodeForm.addEventListener('submit', async (e) => {
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
    
    // Updated to latest versions (April 2026)
    let cmd = isWin
        ? `msiexec /i https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.6/windows_exporter-0.31.6-amd64.msi ENABLED_COLLECTORS="cpu,cs,logical_disk,net,os,system" /qn`
        : `curl -sLO https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz && tar xvf node_exporter-1.11.1.linux-amd64.tar.gz && cd node_exporter-1.11.1.linux-amd64 && ./node_exporter &`;
    
    document.getElementById('deployCmd').value = cmd;
    toggleModal('deployModal', true);
}

function showAddUserModal() {
    toggleModal('addUserModal', true);
}

const addUserForm = document.getElementById('addUserForm');
if (addUserForm) addUserForm.addEventListener('submit', async (e) => {
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
            const usersTableBody = document.getElementById('usersTableBody');
            if (usersTableBody) {
                usersTableBody.innerHTML = data.users.map(u => `
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
                        <td style="text-align: right; display: flex; gap: 0.4rem; justify-content: flex-end;">
                            <button class="chart-action-btn" onclick="showChangePasswordModal(${u.id}, '${u.username}')" style="color: var(--accent);" title="Change password">
                                <i data-lucide="key" style="width: 14px; height: 14px;"></i>
                            </button>
                            <button class="chart-action-btn" onclick="deleteUser(${u.id})" style="color: var(--danger);" title="Delete user">
                                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
                lucide.createIcons();
            }
        }
    } catch (err) { console.error(err); }
}

async function deleteUser(id) {
    if (!confirm('Видалити цього користувача?')) return;
    try {
        await apiFetch(`/api/v1/auth/users/${id}`, {method: 'DELETE'});
        loadUsers();
    } catch (err) { alert('Помилка видалення'); }
}

function showChangePasswordModal(userId, username) {
    document.getElementById('changePwdUserId').value = userId;
    document.getElementById('changePwdUsername').textContent = username;
    document.getElementById('changePwdNewPassword').value = '';
    document.getElementById('changePwdConfirmPassword').value = '';
    toggleModal('changePasswordModal', true);
}

async function changeUserPassword() {
    const userId = document.getElementById('changePwdUserId').value;
    const newPassword = document.getElementById('changePwdNewPassword').value;
    const confirmPassword = document.getElementById('changePwdConfirmPassword').value;

    if (!newPassword || newPassword.length < 12) {
        return alert('Пароль має бути мінімум 12 символів');
    }
    if (newPassword !== confirmPassword) {
        return alert('Паролі не співпадають');
    }
    if (!/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
        return alert('Пароль має містити велику літеру, малу літеру та цифру');
    }

    try {
        const resp = await apiFetch(`/api/v1/auth/users/${userId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: newPassword})
        });
        if (resp && resp.ok) {
            alert('✅ Пароль змінено');
            toggleModal('changePasswordModal', false);
        } else {
            const err = resp ? await resp.json() : {};
            alert('Помилка: ' + (err.detail || 'Failed to change password'));
        }
    } catch (err) { alert('Connection Error'); }
}

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
    net: null,
    service: null
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
                backgroundColor: function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) return color.replace('1)', '0.1)');
                    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    gradient.addColorStop(0, color.replace('1)', '0.6)'));
                    gradient.addColorStop(0.5, color.replace('1)', '0.2)'));
                    gradient.addColorStop(1, color.replace('1)', '0.0)'));
                    return gradient;
                },
                borderWidth: 4,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: color,
                pointBorderColor: '#fff',
                pointBorderWidth: 2
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
    const ctxService = document.getElementById('serviceOverviewChart')?.getContext('2d');

    if (ctxCpu) overviewCharts.cpu = new Chart(ctxCpu, chartConfig('CPU', 'rgba(249, 115, 22, 1)'));
    if (ctxRam) overviewCharts.ram = new Chart(ctxRam, chartConfig('RAM', 'rgba(16, 185, 129, 1)'));
    if (ctxDisk) overviewCharts.disk = new Chart(ctxDisk, chartConfig('Disk', 'rgba(245, 158, 11, 1)'));
    if (ctxService) overviewCharts.service = new Chart(ctxService, chartConfig('Latency', 'rgba(16, 185, 129, 1)'));
    
    if (ctxNet) {
        const netCfg = chartConfig('Network', 'rgba(59, 130, 246, 1)');
        netCfg.options.scales.y.max = undefined; // Auto-scale for net
        overviewCharts.net = new Chart(ctxNet, netCfg);
    }
}

async function updateOverviewCharts() {
    const select = document.getElementById('overviewNodeSelect');
    if (!select) return;
    const serverId = select.value;
    const panel = document.getElementById('activeNodePanel');
    
    if (serverId === 'agg') {
        if (panel) panel.classList.remove('active');
    } else {
        const node = nodes.find(n => n.id == serverId);
        if (node && panel) {
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

    let url = `/api/v1/metrics/trend?range=${currentRange}`;
    if (serverId !== 'agg') {
        url = `/api/v1/metrics/history/${serverId}?range=${currentRange}`;
    }

    try {
        const resp = await apiFetch(url);
        if (!resp) return;
        const data = await resp.json();
        const history = data.history || [];
        lastFetchedHistory = history; // Save for expandChart

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

    // Update Service Latency Chart
    try {
        const sResp = await apiFetch(`/api/v1/services/history?range=${currentRange}`);
        if (sResp && sResp.ok) {
            const sData = await sResp.json();
            if (!Array.isArray(sData)) return;
            const sLabels = sData.map(h => new Date(h.timestamp).toLocaleTimeString());
            const sLatency = sData.map(h => h.response_time);
            
            if (overviewCharts.service) {
                overviewCharts.service.data.labels = sLabels;
                overviewCharts.service.data.datasets[0].data = sLatency;
                overviewCharts.service.update('none');
            }
        }
    } catch(e) { console.error("Service chart update failed:", e); }
}

function expandChart(type) {
    const container = document.getElementById('expandedChartContainer');
    container.innerHTML = `<canvas id="expandedChartCanvas-${type}"></canvas>`;
    
    const sourceChart = overviewCharts[type];
    if (!sourceChart) return;

    const ctx = document.getElementById(`expandedChartCanvas-${type}`).getContext('2d');
    
    if (expandedChart) expandedChart.destroy();

    let datasets = [];
    
    if (type === 'disk' && lastFetchedHistory.length > 0 && lastFetchedHistory[0].disk_info) {
        // Multi-line disk chart
        const volumes = new Set();
        lastFetchedHistory.forEach(h => {
            if (h.disk_info) {
                Object.keys(h.disk_info).forEach(v => {
                    const vLower = v.toLowerCase();
                    if (vLower.includes('harddiskvolume') || 
                        vLower.includes('/snap/') || 
                        vLower.includes('docker') || 
                        vLower.includes('kubelet') || 
                        vLower.includes('tmpfs') || 
                        vLower.includes('overlay') || 
                        vLower.includes('shm') || 
                        vLower.includes('/run/user/')) {
                        return;
                    }
                    volumes.add(v);
                });
            }
        });

        const colors = ['#f97316', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
        let colorIdx = 0;

        Array.from(volumes).sort().forEach(vol => {
            const data = lastFetchedHistory.map(h => (h.disk_info && h.disk_info[vol] !== undefined) ? h.disk_info[vol] : null);
            datasets.push({
                label: vol,
                data: data,
                borderColor: colors[colorIdx % colors.length],
                borderWidth: 3,
                tension: 0.4,
                pointRadius: 0,
                fill: false
            });
            colorIdx++;
        });
    } else {
        datasets = JSON.parse(JSON.stringify(sourceChart.data.datasets));
        if (datasets.length > 0) datasets[0].label = type.toUpperCase();
    }

    expandedChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: JSON.parse(JSON.stringify(sourceChart.data.labels)),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { 
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: { color: '#fff', usePointStyle: true, padding: 20 } 
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#94a3b8',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', maxRotation: 0 } },
                y: { 
                    beginAtZero: true, 
                    max: (type === 'net') ? undefined : 100,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) { return value + (type === 'net' ? ' MB' : '%'); }
                    }
                }
            }
        }
    });

    document.getElementById('expandedChartTitle').textContent = type.toUpperCase() + ' Detailed Analysis';
    toggleModal('chartExpandModal', true);
}

let seenAlertIds = new Set();

async function loadRecentAlerts() {
    const feed = document.getElementById('recentAlertsFeed');
    if (!feed) return;

    try {
        const resp = await apiFetch('/api/v1/audit-log?limit=10');
        if (!resp) return;
        const data = await resp.json();
        const logs = data.logs || [];

        let hasNewCritical = false;
        logs.forEach(log => {
            if (!seenAlertIds.has(log.id)) {
                seenAlertIds.add(log.id);
                const actionLower = log.action.toLowerCase();
                if (actionLower.includes('critical') || actionLower.includes('warning') || actionLower.includes('alert')) {
                    hasNewCritical = true;
                }
            }
        });

        if (hasNewCritical && seenAlertIds.size > logs.length) {
            const audio = document.getElementById('alertSound');
            if (audio) {
                audio.play().catch(err => console.log('Sound play blocked by browser policy:', err));
            }
        }

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
                <p class="alert-desc" style="font-weight: 700; color: #fff; margin-bottom: 2px;">${log.target}</p>
                <p class="alert-desc" style="font-size: 0.75rem; opacity: 0.8;">${log.details || ''}</p>
                <p style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.5rem;">By: ${log.username}</p>
            </div>
        `).join('');
        lucide.createIcons();
    } catch (e) {
        console.error("Failed to load alerts:", e);
    }
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

// WebSocket Connection
let ws = null;
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/metrics`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        const timerEl = document.getElementById('updateTimer');
        if (timerEl) timerEl.textContent = 'Live';
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('WS Message received:', data);
            if (data.type === 'metrics_updated') {
                const select = document.getElementById('overviewNodeSelect');
                if (select && (select.value === 'agg' || select.value == data.server_id)) {
                    refreshData();
                    updateOverviewCharts();
                } else if (!select) {
                    refreshData();
                }
            }
        } catch (e) {
            console.error('WS parse error:', e);
        }
    };
    
    ws.onerror = (err) => {
        console.error('WS Error:', err);
    };
    
    ws.onclose = () => {
        console.log('WebSocket connection closed. Reconnecting in 5s...');
        const timerEl = document.getElementById('updateTimer');
        if (timerEl) timerEl.textContent = 'Offline (Reconnecting...)';
        setTimeout(connectWebSocket, 5000);
    };
}

// Theme Toggle
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    const body = document.body;
    const icon = document.getElementById('themeIcon');
    const toggleBtn = document.getElementById('themeToggleBtn');
    
    if (savedTheme === 'light') {
        body.classList.add('light-theme');
        if (icon) icon.setAttribute('data-lucide', 'moon');
    } else {
        body.classList.remove('light-theme');
        if (icon) icon.setAttribute('data-lucide', 'sun');
    }
    if (window.lucide) lucide.createIcons();
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const isLight = body.classList.toggle('light-theme');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            if (icon) {
                icon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
                if (window.lucide) lucide.createIcons();
            }
        });
    }
}

// Initialization
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js').catch(err => console.log('SW registration failed:', err));
    });
}

const urlParams = new URLSearchParams(window.location.search);
const urlSection = urlParams.get('section') || 'overview';
showSection(urlSection);

refreshData();
initOverviewCharts();
connectWebSocket();
initTheme();

setInterval(refreshData, 60000);
setInterval(() => {
    updateOverviewCharts();
    loadRecentAlerts();
    populateServerSelect();
}, 60000);

// --- NEW FEATURES ---

const addServiceForm = document.getElementById('addServiceForm');
if (addServiceForm) addServiceForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const resp = await apiFetch('/api/v1/services', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: document.getElementById('serviceName').value,
            target_url: document.getElementById('serviceUrl').value,
            check_type: document.getElementById('serviceType').value,
            interval: parseInt(document.getElementById('serviceInterval').value)
        })
    });
    if (resp && resp.ok) {
        toggleModal('addServiceModal', false);
        e.target.reset();
        refreshData();
    }
});

async function toggleMaintenance(serverId, status) {
    try {
        const resp = await apiFetch(`/api/v1/servers/${serverId}/maintenance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_maintenance: status })
        });
        if (resp && resp.ok) {
            refreshData();
            closeDrawer();
        }
    } catch (err) { console.error('Error toggling maintenance', err); }
}

function updateServicesTable(services) {
    const tbody = document.getElementById('servicesTableBody');
    if (!tbody) return;
    tbody.innerHTML = services.map(s => `
        <tr>
            <td>
                <div style="font-weight: 600;">${s.name}</div>
                <div style="font-size: 0.7rem; color: var(--text-muted);">${s.target_url}</div>
            </td>
            <td><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-muted);">${s.check_type.toUpperCase()}</span></td>
            <td>
                <span class="status-badge status-${(s.status || s.last_status || 'unknown')}">
                    <span class="status-dot status-${(s.status || s.last_status || 'unknown')}"></span>
                    ${(s.status || s.last_status || 'unknown').toUpperCase()}
                </span>
            </td>
            <td>${(s.response_time_ms || s.last_response_time) ? (s.response_time_ms || s.last_response_time).toFixed(1) + 'ms' : '-'}</td>
            <td>${s.last_check ? new Date(s.last_check).toLocaleTimeString() : 'Never'}</td>
            <td style="text-align: right;">
                <button onclick="deleteService(${s.id})" class="chart-action-btn" style="color: var(--danger);"><i data-lucide="trash-2" style="width: 14px; height: 14px;"></i></button>
            </td>
        </tr>
    `).join('');
    lucide.createIcons();
}

async function deleteService(id) {
    if (confirm('Delete this service?')) {
        await apiFetch(`/api/v1/services/${id}`, { method: 'DELETE' });
        refreshData();
    }
}

async function importPromConfig() {
    const yaml = document.getElementById('promYamlInput').value;
    if (!yaml) return alert('Please paste Prometheus YAML first');
    
    try {
        const resp = await apiFetch('/api/v1/settings/config/import-prometheus', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ yaml_content: yaml })
        });
        if (resp && resp.ok) {
            const data = await resp.json();
            alert(`Успішно! Імпортовано ${data.imported} нових об'єктів.`);
            document.getElementById('promYamlInput').value = '';
            refreshData();
        } else {
            const errData = await resp.json();
            alert('Помилка імпорту: ' + (errData.detail || 'Невідома помилка'));
        }
    } catch (e) { alert('Помилка під час імпорту: ' + e); }
}

async function exportPyMonConfig() {
    try {
        const resp = await apiFetch('/api/v1/settings/config/export');
        if (resp && resp.ok) {
            const data = await resp.json();
            const blob = new Blob([data.content], { type: 'text/yaml' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pymon_config_backup.yml';
            a.click();
        }
    } catch (e) { alert('Export failed'); }
}

async function generateReport(serverId) {
    const btn = document.querySelector(`button[onclick="generateReport(${serverId})"]`);
    const originalText = btn ? btn.innerHTML : null;
    if (btn) btn.innerHTML = '<i class="animate-spin" data-lucide="refresh-cw" style="width: 14px; height: 14px; margin-right: 0.5rem;"></i> Generating...';
    if (window.lucide) lucide.createIcons();

    try {
        const resp = await apiFetch(`/api/v1/reports/server/${serverId}`);
        if (resp && resp.ok) {
            const html = await resp.text();
            const w = window.open('', '_blank');
            if (w) {
                w.document.write(html);
                w.document.close();
            }
        } else if (resp) {
            const err = await resp.json();
            alert('Report generation failed: ' + (err.detail || 'Internal error'));
        }
    } catch (e) {
        alert('Could not connect to reporting engine');
    } finally {
        if (btn) btn.innerHTML = originalText;
        if (window.lucide) lucide.createIcons();
    }
}

// Final boot sequence handled by existing lifecycle intervals and initial calls above.

