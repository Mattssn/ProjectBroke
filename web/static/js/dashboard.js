// Dashboard State
let botState = { running: false, auto_trade: false };
let botConfig = {};
let tradingStats = {};
let portfolioData = null;
let positionsData = [];
let decisionsData = [];
let performanceChart = null;

// Available Sports
const SPORTS = [
    { key: 'americanfootball_nfl', name: 'NFL' },
    { key: 'basketball_nba', name: 'NBA' },
    { key: 'baseball_mlb', name: 'MLB' },
    { key: 'icehockey_nhl', name: 'NHL' },
    { key: 'americanfootball_ncaaf', name: 'NCAAF' },
    { key: 'basketball_ncaab', name: 'NCAAB' },
    { key: 'soccer_usa_mls', name: 'MLS' },
    { key: 'mma_mixed_martial_arts', name: 'UFC/MMA' }
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    initNavigation();
    initSportsCheckboxes();
    refreshData();
    fetchBotStatus();
    setInterval(refreshData, 30000);
    setInterval(fetchBotStatus, 5000);
});

// Navigation
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            showSection(section);
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function showSection(section) {
    document.getElementById('dashboard-section').style.display = section === 'dashboard' ? 'block' : 'none';
    document.getElementById('settings-section').style.display = section === 'settings' ? 'block' : 'none';
    document.getElementById('trade-section').style.display = section === 'trade' ? 'block' : 'none';
    
    if (section === 'settings') loadSettings();
    if (section === 'trade') loadOpenOrders();
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// Chart
function initChart() {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Portfolio', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.4, pointRadius: 0 }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(30,34,42,0.5)' }, ticks: { color: '#7a7d85', font: { size: 10 } } },
                y: { grid: { color: 'rgba(30,34,42,0.5)' }, ticks: { color: '#7a7d85', font: { size: 10 }, callback: v => '$' + v } }
            }
        }
    });
    updateChart();
}

function updateChart() {
    const now = new Date();
    const labels = [], data = [];
    let value = portfolioData?.portfolio_value_usd || 1000;
    for (let i = 23; i >= 0; i--) {
        const time = new Date(now - i * 3600000);
        labels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
        value += (Math.random() - 0.48) * 15;
        data.push(Math.max(0, value));
    }
    performanceChart.data.labels = labels;
    performanceChart.data.datasets[0].data = data;
    performanceChart.update();
}

// Bot Control
async function fetchBotStatus() {
    try {
        const res = await fetch('/api/bot/status');
        const result = await res.json();
        if (result.success) {
            botState = result.state;
            botConfig = result.config;
            tradingStats = result.stats;
            updateBotUI();
        }
    } catch (e) { console.error('Bot status error:', e); }
}

function updateBotUI() {
    const indicator = document.getElementById('bot-indicator');
    const statusText = document.getElementById('bot-status-text');
    const statusDetail = document.getElementById('bot-status-detail');
    const startBtn = document.getElementById('btn-start-bot');
    const stopBtn = document.getElementById('btn-stop-bot');
    const autoToggle = document.getElementById('auto-trade-toggle');
    const connStatus = document.getElementById('connection-status');
    const connText = document.getElementById('connection-text');

    if (botState.running) {
        indicator.className = 'bot-status-indicator running';
        statusText.textContent = 'Running';
        statusDetail.textContent = botState.current_sport ? `Scanning ${botState.current_sport}...` : 'Waiting for next scan...';
        startBtn.style.display = 'none';
        stopBtn.style.display = 'flex';
        connStatus.className = 'status-dot online';
        connText.textContent = 'Bot Active';
    } else {
        indicator.className = 'bot-status-indicator stopped';
        statusText.textContent = 'Stopped';
        statusDetail.textContent = 'Click Start to begin scanning';
        startBtn.style.display = 'flex';
        stopBtn.style.display = 'none';
        connStatus.className = 'status-dot offline';
        connText.textContent = 'Bot Inactive';
    }

    autoToggle.className = botState.auto_trade ? 'toggle active' : 'toggle';
    
    document.getElementById('events-analyzed').textContent = tradingStats.total_analyzed || 0;
    document.getElementById('recommendations-count').textContent = tradingStats.total_recommended || 0;
    document.getElementById('trades-today').textContent = tradingStats.trades_today || 0;
    const pnl = tradingStats.daily_pnl || 0;
    const pnlEl = document.getElementById('daily-pnl');
    pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
    pnlEl.className = 'control-value ' + (pnl >= 0 ? 'green' : 'red');
}

async function startBot() {
    try {
        const res = await fetch('/api/bot/start', { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            showToast('Bot started successfully', 'success');
            fetchBotStatus();
        } else {
            showToast(result.error || 'Failed to start bot', 'error');
        }
    } catch (e) { showToast('Error starting bot', 'error'); }
}

async function stopBot() {
    try {
        const res = await fetch('/api/bot/stop', { method: 'POST' });
        const result = await res.json();
        if (result.success) {
            showToast('Bot stopped', 'info');
            fetchBotStatus();
        }
    } catch (e) { showToast('Error stopping bot', 'error'); }
}

async function toggleAutoTrade() {
    const newState = !botState.auto_trade;
    try {
        const res = await fetch('/api/bot/auto-trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: newState })
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message, newState ? 'success' : 'info');
            fetchBotStatus();
        }
    } catch (e) { showToast('Error toggling auto-trade', 'error'); }
}

// Data Refresh
async function refreshData() {
    await Promise.all([fetchPortfolio(), fetchPositions(), fetchTrades(), fetchDecisions()]);
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

async function fetchPortfolio() {
    try {
        const res = await fetch('/api/portfolio');
        const result = await res.json();
        if (result.success && result.data) {
            portfolioData = result.data;
            document.getElementById('portfolio-value').textContent = '$' + (portfolioData.portfolio_value_usd || 0).toFixed(2);
            document.getElementById('available-balance').textContent = '$' + (portfolioData.balance_usd || 0).toFixed(2);
            updateChart();
        }
    } catch (e) { console.error('Portfolio error:', e); }
}

async function fetchPositions() {
    try {
        const res = await fetch('/api/positions');
        const result = await res.json();
        if (result.success) {
            positionsData = result.data || [];
            document.getElementById('active-positions').textContent = positionsData.length;
            updatePositionsTable();
        }
    } catch (e) { console.error('Positions error:', e); }
}

function updatePositionsTable() {
    const tbody = document.getElementById('positions-tbody');
    if (!positionsData.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary);padding:30px;">No open positions</td></tr>';
        return;
    }
    tbody.innerHTML = positionsData.slice(0, 10).map(p => {
        const pnl = (p.market_exposure || 0) / 100;
        return `<tr>
            <td><span class="position-ticker">${p.ticker || 'N/A'}</span></td>
            <td><span class="position-side ${p.position === 'yes' ? 'yes' : 'no'}">${(p.position || 'YES').toUpperCase()}</span></td>
            <td>${p.total_traded || 0}</td>
            <td class="${pnl >= 0 ? 'activity-amount positive' : 'activity-amount negative'}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
        </tr>`;
    }).join('');
}

async function fetchTrades() {
    try {
        const res = await fetch('/api/trades');
        const result = await res.json();
        if (result.success) {
            updateActivityFeed(result.data || []);
        }
    } catch (e) { console.error('Trades error:', e); }
}

function updateActivityFeed(trades) {
    const feed = document.getElementById('activity-feed');
    if (!trades.length) {
        feed.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px;">No recent activity</div>';
        return;
    }
    feed.innerHTML = trades.slice(0, 8).map(t => {
        const isBuy = t.action === 'buy';
        const amt = (t.count || 0) * ((t.price || 0) / 100);
        return `<div class="activity-item">
            <div class="activity-icon ${isBuy ? 'buy' : 'sell'}">${isBuy ? '↑' : '↓'}</div>
            <div class="activity-content">
                <div class="activity-title">${t.ticker || 'Unknown'}</div>
                <div class="activity-meta">${isBuy ? 'Bought' : 'Sold'} ${t.count || 0} @ ${t.price || 0}¢</div>
            </div>
            <div class="activity-amount ${isBuy ? 'negative' : 'positive'}">${isBuy ? '-' : '+'}$${amt.toFixed(2)}</div>
        </div>`;
    }).join('');
}

async function fetchDecisions() {
    try {
        const res = await fetch('/api/decisions');
        const result = await res.json();
        if (result.success) {
            decisionsData = result.decisions || [];
            document.getElementById('decisions-today').textContent = decisionsData.length;
            updateDecisions();
        }
    } catch (e) { console.error('Decisions error:', e); }
}

function updateDecisions() {
    const container = document.getElementById('decisions-container');
    if (!decisionsData.length) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px;">No AI decisions yet</div>';
        return;
    }
    container.innerHTML = decisionsData.slice(-5).reverse().map(item => {
        const d = item.decision || {};
        const isRec = d.decision === 'place_bet';
        return `<div class="decision-item">
            <div class="decision-header">
                <span class="decision-event">${d.event_name || 'Unknown'}</span>
                <span class="decision-badge ${isRec ? 'place-bet' : 'skip'}">${isRec ? '✓ Bet' : 'Skip'}</span>
            </div>
            <div class="decision-details">
                <div><div class="decision-detail-label">Confidence</div><div class="decision-detail-value">${((d.confidence || 0) * 100).toFixed(0)}%</div></div>
                <div><div class="decision-detail-label">Edge</div><div class="decision-detail-value">${((d.expected_value || 0) * 100).toFixed(1)}%</div></div>
                <div><div class="decision-detail-label">Type</div><div class="decision-detail-value">${d.bet_type || '--'}</div></div>
            </div>
        </div>`;
    }).join('');
}

// Settings
function initSportsCheckboxes() {
    const container = document.getElementById('sports-checkboxes');
    container.innerHTML = SPORTS.map(s => 
        `<div class="sport-checkbox" data-sport="${s.key}" onclick="toggleSport(this)">${s.name}</div>`
    ).join('');
}

function toggleSport(el) {
    el.classList.toggle('active');
}

async function loadSettings() {
    try {
        const res = await fetch('/api/bot/config');
        const result = await res.json();
        if (result.success) {
            const c = result.config;
            document.getElementById('setting-min-confidence').value = c.min_confidence || 0.6;
            document.getElementById('setting-min-edge').value = (c.min_edge || 0.03) * 100;
            document.getElementById('setting-max-bet-pct').value = (c.max_bet_pct || 0.02) * 100;
            document.getElementById('setting-max-position').value = c.max_position_size || 1000;
            document.getElementById('setting-max-daily-trades').value = c.max_daily_trades || 10;
            document.getElementById('setting-max-daily-loss').value = c.max_daily_loss || 100;
            document.getElementById('setting-scan-interval').value = botState.scan_interval || 300;
            document.getElementById('setting-model').value = c.preferred_model || 'anthropic/claude-3.5-sonnet';
            
            if (c.use_research) document.getElementById('setting-use-research').classList.add('active');
            else document.getElementById('setting-use-research').classList.remove('active');
            
            if (c.auto_execute) document.getElementById('setting-auto-execute').classList.add('active');
            else document.getElementById('setting-auto-execute').classList.remove('active');
            
            document.querySelectorAll('.sport-checkbox').forEach(el => {
                el.classList.toggle('active', (c.enabled_sports || []).includes(el.dataset.sport));
            });
        }
    } catch (e) { console.error('Load settings error:', e); }
}

async function saveSettings() {
    const enabledSports = Array.from(document.querySelectorAll('.sport-checkbox.active')).map(el => el.dataset.sport);
    
    const config = {
        min_confidence: parseFloat(document.getElementById('setting-min-confidence').value),
        min_edge: parseFloat(document.getElementById('setting-min-edge').value) / 100,
        max_bet_pct: parseFloat(document.getElementById('setting-max-bet-pct').value) / 100,
        max_position_size: parseInt(document.getElementById('setting-max-position').value),
        max_daily_trades: parseInt(document.getElementById('setting-max-daily-trades').value),
        max_daily_loss: parseFloat(document.getElementById('setting-max-daily-loss').value),
        scan_interval: parseInt(document.getElementById('setting-scan-interval').value),
        preferred_model: document.getElementById('setting-model').value,
        use_research: document.getElementById('setting-use-research').classList.contains('active'),
        auto_execute: document.getElementById('setting-auto-execute').classList.contains('active'),
        enabled_sports: enabledSports
    };

    try {
        const res = await fetch('/api/bot/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const result = await res.json();
        if (result.success) {
            showToast('Settings saved successfully', 'success');
            fetchBotStatus();
        } else {
            showToast('Failed to save settings', 'error');
        }
    } catch (e) { showToast('Error saving settings', 'error'); }
}

// Scan Modal
function openScanModal() {
    document.getElementById('scan-modal').classList.add('active');
}

function closeScanModal() {
    document.getElementById('scan-modal').classList.remove('active');
}

async function runScan() {
    const sport = document.getElementById('scan-sport').value;
    const maxEvents = parseInt(document.getElementById('scan-max-events').value);
    const includeResearch = document.getElementById('scan-research').classList.contains('active');

    closeScanModal();
    showToast(`Scanning ${sport}...`, 'info');

    try {
        const res = await fetch('/api/bot/scan-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sport, max_events: maxEvents, include_research: includeResearch })
        });
        const result = await res.json();
        if (result.success) {
            showToast(`Found ${result.recommendations} recommendations from ${result.total_analyzed} events`, 'success');
            fetchDecisions();
            fetchBotStatus();
        } else {
            showToast(result.error || 'Scan failed', 'error');
        }
    } catch (e) { showToast('Error running scan', 'error'); }
}

// Trading
async function placeTrade() {
    const ticker = document.getElementById('trade-ticker').value.trim();
    const side = document.getElementById('trade-side').value;
    const action = document.getElementById('trade-action').value;
    const count = parseInt(document.getElementById('trade-quantity').value);
    const price = parseInt(document.getElementById('trade-price').value);
    const type = document.getElementById('trade-type').value;

    if (!ticker) {
        showToast('Please enter a market ticker', 'error');
        return;
    }

    try {
        const res = await fetch('/api/trade/place', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker, side, action, count, type,
                [side === 'yes' ? 'yes_price' : 'no_price']: price
            })
        });
        const result = await res.json();
        if (result.success) {
            showToast('Order placed successfully!', 'success');
            loadOpenOrders();
            refreshData();
        } else {
            showToast(result.error || 'Order failed', 'error');
        }
    } catch (e) { showToast('Error placing order', 'error'); }
}

async function loadOpenOrders() {
    const container = document.getElementById('open-orders');
    try {
        const res = await fetch('/api/orders');
        const result = await res.json();
        if (result.success) {
            const orders = result.orders || [];
            if (!orders.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px;">No open orders</div>';
                return;
            }
            container.innerHTML = orders.map(o => `
                <div class="decision-item">
                    <div class="decision-header">
                        <span class="decision-event">${o.ticker || 'N/A'}</span>
                        <button class="btn btn-danger" style="padding:4px 10px;font-size:11px;" onclick="cancelOrder('${o.order_id}')">Cancel</button>
                    </div>
                    <div class="decision-details">
                        <div><div class="decision-detail-label">Side</div><div class="decision-detail-value">${o.side?.toUpperCase()}</div></div>
                        <div><div class="decision-detail-label">Action</div><div class="decision-detail-value">${o.action?.toUpperCase()}</div></div>
                        <div><div class="decision-detail-label">Qty</div><div class="decision-detail-value">${o.remaining_count || o.count}</div></div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) { container.innerHTML = '<div style="color:var(--accent-red);">Error loading orders</div>'; }
}

async function cancelOrder(orderId) {
    try {
        const res = await fetch(`/api/trade/cancel/${orderId}`, { method: 'DELETE' });
        const result = await res.json();
        if (result.success) {
            showToast('Order cancelled', 'success');
            loadOpenOrders();
        } else {
            showToast(result.error || 'Cancel failed', 'error');
        }
    } catch (e) { showToast('Error cancelling order', 'error'); }
}
