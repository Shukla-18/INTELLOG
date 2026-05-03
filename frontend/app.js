/**
 * Intellog Dashboard - Frontend Application
 * Handles auth, data fetching, charts, auto-refresh
 */

const API_BASE = `${window.location.origin}/api`;
let authToken = localStorage.getItem('intellog_token') || '';
let refreshInterval = null;
let charts = {};

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showDashboard();
        initDashboard();
    } else {
        showLogin();
    }

    // Login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);

    // Nav
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => switchSection(btn.dataset.section));
    });

    // VM selector
    document.getElementById('vm-select').addEventListener('change', () => fetchDashboardData());

    // Scan button
    document.getElementById('scan-btn').addEventListener('click', handleScan);

    // Report button
    document.getElementById('report-btn').addEventListener('click', handleReport);

    // Logout
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
});

// ==================== AUTH ====================

let authMode = 'login'; // 'login' or 'register'

function switchAuthTab(mode) {
    authMode = mode;
    const loginTab = document.getElementById('tab-login');
    const registerTab = document.getElementById('tab-register');
    const confirmGroup = document.getElementById('confirm-pass-group');
    const btnText = document.getElementById('auth-btn-text');
    const errEl = document.getElementById('login-error');

    errEl.textContent = '';

    if (mode === 'register') {
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
        confirmGroup.style.display = 'flex';
        document.getElementById('confirm-pass').required = true;
        btnText.textContent = 'Create Account';
    } else {
        registerTab.classList.remove('active');
        loginTab.classList.add('active');
        confirmGroup.style.display = 'none';
        document.getElementById('confirm-pass').required = false;
        btnText.textContent = 'Sign In';
    }
}

function togglePassword() {
    const input = document.getElementById('login-pass');
    const eyeOpen = document.getElementById('eye-open');
    const eyeClosed = document.getElementById('eye-closed');

    if (input.type === 'password') {
        input.type = 'text';
        eyeOpen.style.display = 'none';
        eyeClosed.style.display = 'block';
    } else {
        input.type = 'password';
        eyeOpen.style.display = 'block';
        eyeClosed.style.display = 'none';
    }
}

function toggleConfirmPassword() {
    const input = document.getElementById('confirm-pass');
    const eyeOpen = document.querySelector('.eye-open-confirm');
    const eyeClosed = document.querySelector('.eye-closed-confirm');

    if (input.type === 'password') {
        input.type = 'text';
        eyeOpen.style.display = 'none';
        eyeClosed.style.display = 'block';
    } else {
        input.type = 'password';
        eyeOpen.style.display = 'block';
        eyeClosed.style.display = 'none';
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const user = document.getElementById('login-user').value.trim();
    const pass = document.getElementById('login-pass').value;
    const errEl = document.getElementById('login-error');

    if (!user || !pass) {
        errEl.textContent = 'Please fill in all fields';
        return;
    }

    if (authMode === 'register') {
        const confirmPass = document.getElementById('confirm-pass').value;
        if (pass !== confirmPass) {
            errEl.textContent = 'Passwords do not match';
            return;
        }
        if (pass.length < 6) {
            errEl.textContent = 'Password must be at least 6 characters';
            return;
        }
    }

    const endpoint = authMode === 'register' ? '/auth/register' : '/auth/login';

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass }),
        });

        if (!res.ok) {
            const data = await res.json();
            errEl.textContent = data.detail || 'Authentication failed';
            return;
        }

        const data = await res.json();
        authToken = data.access_token;
        localStorage.setItem('intellog_token', authToken);
        errEl.textContent = '';
        showDashboard();
        initDashboard();
        toast(authMode === 'register' ? 'Account created successfully' : 'Authenticated successfully', 'success');
    } catch (err) {
        errEl.textContent = 'Cannot connect to server. Is backend running?';
    }
}

function handleLogout() {
    authToken = '';
    localStorage.removeItem('intellog_token');
    if (refreshInterval) clearInterval(refreshInterval);
    showLogin();
    toast('Logged out', 'info');
}

function showLogin() {
    document.getElementById('login-overlay').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('login-overlay').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
}

// ==================== DASHBOARD ====================

function initDashboard() {
    initCharts();
    fetchDashboardData();

    // Auto-refresh every 8 seconds
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(fetchDashboardData, 8000);
}

async function fetchDashboardData() {
    const vmSelect = document.getElementById('vm-select');
    const vmName = vmSelect.value;
    const params = new URLSearchParams();
    if (vmName) params.set('vm_name', vmName);
    params.set('limit', '50');

    try {
        const res = await fetch(`${API_BASE}/dashboard-data?${params}`);
        if (!res.ok) return;

        const data = await res.json();
        updateStats(data);
        updateVMSelector(data.vm_list);
        updateCharts(data);
        updateMetricsTable(data.recent_metrics);
        updateNetworkTable(data.recent_network);
        updateLogsTable(data.recent_logs);
        updateAlerts(data.recent_alerts);
        updateLastRefresh();
    } catch (err) {
        console.error('Fetch error:', err);
    }
}

// ==================== UPDATE UI ====================

function updateStats(data) {
    animateValue('total-vms', data.total_vms);
    animateValue('total-logs', data.total_logs);
    animateValue('total-alerts', data.total_alerts);
    animateValue('active-alerts', data.active_alerts);

    // Alert badge
    const badge = document.getElementById('alert-badge');
    if (data.active_alerts > 0) {
        badge.classList.remove('hidden');
        badge.textContent = data.active_alerts;
    } else {
        badge.classList.add('hidden');
    }
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    const current = parseInt(el.textContent) || 0;
    if (current === target) return;

    const diff = target - current;
    const steps = 20;
    const inc = diff / steps;
    let step = 0;

    const timer = setInterval(() => {
        step++;
        el.textContent = Math.round(current + inc * step);
        if (step >= steps) {
            el.textContent = target;
            clearInterval(timer);
        }
    }, 30);
}

function updateVMSelector(vms) {
    const select = document.getElementById('vm-select');
    const currentVal = select.value;
    const existingOpts = new Set([...select.options].map(o => o.value));

    vms.forEach(vm => {
        if (!existingOpts.has(vm)) {
            const opt = document.createElement('option');
            opt.value = vm;
            opt.textContent = vm;
            select.appendChild(opt);
        }
    });

    if (currentVal) select.value = currentVal;
}

function updateLastRefresh() {
    const now = new Date().toLocaleTimeString();
    document.getElementById('last-update').textContent = `Last update: ${now}`;
}

// ==================== CHARTS ====================

const chartColors = {
    cyan: 'rgba(0, 245, 212, 1)',
    cyanBg: 'rgba(0, 245, 212, 0.1)',
    blue: 'rgba(0, 187, 249, 1)',
    blueBg: 'rgba(0, 187, 249, 0.1)',
    purple: 'rgba(155, 93, 229, 1)',
    purpleBg: 'rgba(155, 93, 229, 0.1)',
    pink: 'rgba(241, 91, 181, 1)',
    pinkBg: 'rgba(241, 91, 181, 0.1)',
    high: 'rgba(255, 71, 87, 0.8)',
    medium: 'rgba(255, 165, 2, 0.8)',
    low: 'rgba(46, 213, 115, 0.8)',
};

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { labels: { color: '#8892b0', font: { family: 'Inter', size: 11 } } },
    },
    scales: {
        x: {
            ticks: { color: '#4a5568', font: { size: 10 }, maxTicksLimit: 10 },
            grid: { color: 'rgba(30, 58, 95, 0.3)' },
        },
        y: {
            ticks: { color: '#4a5568', font: { size: 10 } },
            grid: { color: 'rgba(30, 58, 95, 0.3)' },
        },
    },
};

function initCharts() {
    // CPU chart
    charts.cpu = new Chart(document.getElementById('cpu-chart'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'CPU %', data: [], borderColor: chartColors.cyan, backgroundColor: chartColors.cyanBg, fill: true, tension: 0.4, pointRadius: 2 }] },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, min: 0, max: 100 } } },
    });

    // Memory chart
    charts.memory = new Chart(document.getElementById('memory-chart'), {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Memory %', data: [], borderColor: chartColors.purple, backgroundColor: chartColors.purpleBg, fill: true, tension: 0.4, pointRadius: 2 }] },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, min: 0, max: 100 } } },
    });

    // Network chart
    charts.network = new Chart(document.getElementById('network-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { label: 'Sent (B/s)', data: [], borderColor: chartColors.cyan, backgroundColor: 'transparent', tension: 0.4, pointRadius: 1 },
                { label: 'Recv (B/s)', data: [], borderColor: chartColors.pink, backgroundColor: 'transparent', tension: 0.4, pointRadius: 1 },
            ],
        },
        options: chartDefaults,
    });

    // Severity distribution chart
    charts.severity = new Chart(document.getElementById('severity-chart'), {
        type: 'doughnut',
        data: {
            labels: ['High', 'Medium', 'Low'],
            datasets: [{ data: [0, 0, 0], backgroundColor: [chartColors.high, chartColors.medium, chartColors.low], borderWidth: 0 }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#8892b0', padding: 16, font: { family: 'Inter', size: 12 } } } },
            cutout: '65%',
        },
    });

    // Metrics detail chart
    charts.metricsDetail = new Chart(document.getElementById('metrics-detail-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { label: 'CPU %', data: [], borderColor: chartColors.cyan, backgroundColor: 'transparent', tension: 0.4, pointRadius: 2 },
                { label: 'Memory %', data: [], borderColor: chartColors.purple, backgroundColor: 'transparent', tension: 0.4, pointRadius: 2 },
            ],
        },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, min: 0, max: 100 } } },
    });

    // Network detail chart
    charts.networkDetail = new Chart(document.getElementById('network-detail-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { label: 'Sent Rate', data: [], borderColor: chartColors.cyan, backgroundColor: chartColors.cyanBg, fill: true, tension: 0.4, pointRadius: 1 },
                { label: 'Recv Rate', data: [], borderColor: chartColors.pink, backgroundColor: chartColors.pinkBg, fill: true, tension: 0.4, pointRadius: 1 },
            ],
        },
        options: chartDefaults,
    });
}

function updateCharts(data) {
    const metrics = [...data.recent_metrics].reverse();
    const network = [...data.recent_network].reverse();
    const alerts = data.recent_alerts;

    // Time labels
    const metricLabels = metrics.map(m => formatTime(m.timestamp));
    const netLabels = network.map(n => formatTime(n.timestamp));

    // CPU
    charts.cpu.data.labels = metricLabels;
    charts.cpu.data.datasets[0].data = metrics.map(m => m.cpu_percent);
    charts.cpu.update('none');

    // Memory
    charts.memory.data.labels = metricLabels;
    charts.memory.data.datasets[0].data = metrics.map(m => m.memory_percent);
    charts.memory.update('none');

    // Network
    charts.network.data.labels = netLabels;
    charts.network.data.datasets[0].data = network.map(n => n.bytes_sent_rate);
    charts.network.data.datasets[1].data = network.map(n => n.bytes_recv_rate);
    charts.network.update('none');

    // Severity doughnut
    let h = 0, m2 = 0, l = 0;
    alerts.forEach(a => {
        if (a.severity === 'HIGH') h++;
        else if (a.severity === 'MEDIUM') m2++;
        else l++;
    });
    charts.severity.data.datasets[0].data = [h, m2, l];
    charts.severity.update('none');

    // Detail charts
    charts.metricsDetail.data.labels = metricLabels;
    charts.metricsDetail.data.datasets[0].data = metrics.map(m => m.cpu_percent);
    charts.metricsDetail.data.datasets[1].data = metrics.map(m => m.memory_percent);
    charts.metricsDetail.update('none');

    charts.networkDetail.data.labels = netLabels;
    charts.networkDetail.data.datasets[0].data = network.map(n => n.bytes_sent_rate);
    charts.networkDetail.data.datasets[1].data = network.map(n => n.bytes_recv_rate);
    charts.networkDetail.update('none');
}

// ==================== TABLES ====================

function updateMetricsTable(metrics) {
    const tbody = document.querySelector('#metrics-table tbody');
    tbody.innerHTML = metrics.map(m => `
        <tr>
            <td>${m.vm_name}</td>
            <td>${m.cpu_percent.toFixed(1)}</td>
            <td>${m.memory_percent.toFixed(1)}</td>
            <td>${m.disk_percent ? m.disk_percent.toFixed(1) : '-'}</td>
            <td><span class="sev-badge ${m.severity.toLowerCase()}">${m.severity}</span></td>
            <td>${formatTime(m.timestamp)}</td>
        </tr>
    `).join('');
}

function updateNetworkTable(network) {
    const tbody = document.querySelector('#network-table tbody');
    tbody.innerHTML = network.map(n => `
        <tr>
            <td>${n.vm_name}</td>
            <td>${formatBytes(n.bytes_sent_rate)}/s</td>
            <td>${formatBytes(n.bytes_recv_rate)}/s</td>
            <td>${n.packets_sent || 0}</td>
            <td>${n.packets_recv || 0}</td>
            <td><span class="sev-badge ${n.severity.toLowerCase()}">${n.severity}</span></td>
            <td>${formatTime(n.timestamp)}</td>
        </tr>
    `).join('');
}

function updateLogsTable(logs) {
    const tbody = document.querySelector('#logs-table tbody');
    tbody.innerHTML = logs.map(l => `
        <tr>
            <td>${l.vm_name}</td>
            <td>${l.source || '-'}</td>
            <td title="${escapeHtml(l.content)}">${escapeHtml(l.content.substring(0, 80))}${l.content.length > 80 ? '...' : ''}</td>
            <td>${l.tags || '-'}</td>
            <td><span class="sev-badge ${l.severity.toLowerCase()}">${l.severity}</span></td>
            <td>${formatTime(l.timestamp)}</td>
        </tr>
    `).join('');
}

function updateAlerts(alerts) {
    const overviewList = document.getElementById('overview-alerts');
    const fullList = document.getElementById('alerts-full-list');

    const renderAlert = (a, showResolve = false) => `
        <div class="alert-item ${a.severity.toLowerCase()}">
            <div class="alert-header">
                <div class="alert-meta">
                    <span class="sev-badge ${a.severity.toLowerCase()}">${a.severity}</span>
                    <span class="alert-vm">${a.vm_name}</span>
                    <span class="alert-type">${a.alert_type}</span>
                </div>
                <span class="alert-time">${formatTime(a.timestamp)}</span>
            </div>
            <div class="alert-message">${escapeHtml(a.message)}</div>
            ${a.explanation ? `<div class="alert-explanation">${escapeHtml(a.explanation)}</div>` : ''}
            ${showResolve && !a.resolved ? `<div class="alert-actions"><button class="btn-resolve" onclick="resolveAlert(${a.id})">Resolve</button></div>` : ''}
        </div>
    `;

    if (alerts.length === 0) {
        const empty = '<div class="empty-state"><p>No alerts detected. Systems nominal.</p></div>';
        overviewList.innerHTML = empty;
        fullList.innerHTML = empty;
    } else {
        overviewList.innerHTML = alerts.slice(0, 5).map(a => renderAlert(a)).join('');
        fullList.innerHTML = alerts.map(a => renderAlert(a, true)).join('');
    }
}

// ==================== ACTIONS ====================

async function resolveAlert(id) {
    try {
        await fetch(`${API_BASE}/alerts/${id}/resolve`, { method: 'PATCH' });
        toast('Alert resolved', 'success');
        fetchDashboardData();
    } catch (err) {
        toast('Failed to resolve alert', 'error');
    }
}

async function handleScan() {
    const btn = document.getElementById('scan-btn');
    btn.classList.add('scanning');
    btn.querySelector('span').textContent = 'Scanning...';
    toast('Cloud scan initiated — monitoring for active VMs...', 'info');

    await fetchDashboardData();

    setTimeout(() => {
        btn.classList.remove('scanning');
        btn.querySelector('span').textContent = 'Scan Cloud';
        toast('Scan complete', 'success');
    }, 3000);
}

async function handleReport() {
    toast('Generating security report...', 'info');
    try {
        const res = await fetch(`${API_BASE}/report/generate`);
        const data = await res.json();
        toast(`Report generated: ${data.file}`, 'success');
    } catch (err) {
        toast('Report generation failed', 'error');
    }
}

function switchSection(section) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.getElementById(`section-${section}`).classList.add('active');

    const titles = { overview: 'System Overview', metrics: 'System Metrics', network: 'Network Traffic', logs: 'System Logs', alerts: 'Security Alerts' };
    document.getElementById('section-title').textContent = titles[section] || 'Dashboard';
}

// ==================== UTILS ====================

function formatTime(ts) {
    if (!ts) return '-';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${message}</span>`;
    container.appendChild(el);
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(100px)';
        el.style.transition = 'all 0.3s ease';
        setTimeout(() => el.remove(), 300);
    }, 4000);
}
