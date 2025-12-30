// Dashboard State
let botState = { running: false, auto_trade: false };
let botConfig = {};
let tradingStats = {};
let portfolioData = null;
let positionsData = [];
let decisionsData = [];
let performanceChart = null;
let scanInProgress = false;

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
    setInterval(refreshData, 10000);
    setInterval(fetchBotStatus, 3000);
    setInterval(fetchDecisions, 5000);
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
    document.getElementById('ai-analysis-section').style.display = section === 'ai-analysis' ? 'block' : 'none';
    
    if (section === 'settings') loadSettings();
    if (section === 'trade') loadOpenOrders();
    if (section === 'ai-analysis') renderAIAnalyses();
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
    if (!positionsData || positionsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary);padding:30px;">No open positions</td></tr>';
        return;
    }
    tbody.innerHTML = positionsData.slice(0, 10).map(p => {
        const ticker = p.ticker || p.market_ticker || 'N/A';
        const positionNum = p.position || 0;
        const side = positionNum >= 0 ? 'YES' : 'NO';
        const quantity = Math.abs(positionNum);
        const realizedPnl = (p.realized_pnl || 0) / 100;
        const sideClass = positionNum >= 0 ? 'yes' : 'no';
        const pnlClass = realizedPnl >= 0 ? 'positive' : 'negative';
        const pnlSign = realizedPnl >= 0 ? '+' : '';
        return `<tr>
            <td><span class="position-ticker">${ticker}</span></td>
            <td><span class="position-side ${sideClass}">${side}</span></td>
            <td>${quantity}</td>
            <td class="activity-amount ${pnlClass}">${pnlSign}$${realizedPnl.toFixed(2)}</td>
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
    if (!trades || trades.length === 0) {
        feed.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:30px;">No recent activity</div>';
        return;
    }
    feed.innerHTML = trades.slice(0, 8).map(t => {
        const action = t.action || 'buy';
        const isBuy = action.toLowerCase() === 'buy';
        const ticker = t.ticker || t.market_ticker || 'Unknown';
        const count = t.count || 0;
        const side = t.side || 'yes';
        const price = side === 'yes' ? (t.yes_price || 0) : (t.no_price || 0);
        const amt = count * (price / 100);
        return `<div class="activity-item">
            <div class="activity-icon ${isBuy ? 'buy' : 'sell'}">${isBuy ? '↑' : '↓'}</div>
            <div class="activity-content">
                <div class="activity-title">${ticker}</div>
                <div class="activity-meta">${isBuy ? 'Bought' : 'Sold'} ${count} ${side.toUpperCase()} @ ${price}¢</div>
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
            const oldCount = decisionsData.length;
            decisionsData = result.decisions || [];
            document.getElementById('decisions-today').textContent = decisionsData.length;
            updateDecisions();
            if (decisionsData.length > oldCount && document.getElementById('ai-analysis-section').style.display !== 'none') {
                renderAIAnalyses();
            }
        }
    } catch (e) { console.error('Decisions error:', e); }
}

function updateDecisions() {
    const container = document.getElementById('decisions-container');
    if (!decisionsData || decisionsData.length === 0) {
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
            
            // Budget mode
            if (c.budget_mode) document.getElementById('setting-budget-mode').classList.add('active');
            else document.getElementById('setting-budget-mode').classList.remove('active');
            
            document.querySelectorAll('.sport-checkbox').forEach(el => {
                el.classList.toggle('active', (c.enabled_sports || []).includes(el.dataset.sport));
            });
        }
    } catch (e) { console.error('Load settings error:', e); }
    
    // Also load debug settings
    await loadDebugSettings();
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
        budget_mode: document.getElementById('setting-budget-mode').classList.contains('active'),
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
    scanInProgress = true;
    
    // Switch to AI Analysis tab to show progress
    showSection('ai-analysis');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-section="ai-analysis"]').classList.add('active');
    
    showScanProgress(sport, maxEvents);
    showToast(`Starting scan of ${sport}...`, 'info');

    try {
        const res = await fetch('/api/bot/scan-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sport, max_events: maxEvents, include_research: includeResearch })
        });
        const result = await res.json();
        
        if (result.success) {
            // Scan started successfully - it runs in background
            // Don't set scanInProgress = false yet - let the polling detect completion
            showToast(`Scan started! Analyzing ${maxEvents} events. Decisions will appear as they complete.`, 'success');
            
            // Start polling more frequently while scan is running
            startScanPolling(maxEvents);
        } else {
            scanInProgress = false;
            showToast(result.error || 'Scan failed to start', 'error');
            renderAIAnalyses();
        }
    } catch (e) { 
        scanInProgress = false;
        showToast('Error starting scan', 'error'); 
        renderAIAnalyses();
    }
}

// Track decisions during active scan
let scanStartDecisionCount = 0;
let expectedEvents = 0;
let scanPollInterval = null;

function startScanPolling(maxEvents) {
    expectedEvents = maxEvents;
    scanStartDecisionCount = decisionsData.length;
    
    // Clear any existing polling
    if (scanPollInterval) clearInterval(scanPollInterval);
    
    // Poll every 3 seconds for new decisions
    scanPollInterval = setInterval(async () => {
        await fetchDecisions();
        
        const newDecisions = decisionsData.length - scanStartDecisionCount;
        
        // Update progress display
        updateScanProgressCount(newDecisions, expectedEvents);
        
        // Check if scan is complete (got all expected decisions or bot is no longer scanning)
        if (newDecisions >= expectedEvents || (!botState.current_sport && newDecisions > 0)) {
            clearInterval(scanPollInterval);
            scanPollInterval = null;
            scanInProgress = false;
            
            const recommendations = decisionsData.slice(-newDecisions).filter(d => 
                d.decision && d.decision.decision === 'place_bet'
            ).length;
            
            showToast(`✓ Scan complete! ${recommendations} recommendations from ${newDecisions} events`, 'success');
            renderAIAnalyses();
        }
    }, 3000);
    
    // Safety timeout - stop polling after 10 minutes
    setTimeout(() => {
        if (scanPollInterval) {
            clearInterval(scanPollInterval);
            scanPollInterval = null;
            scanInProgress = false;
            renderAIAnalyses();
        }
    }, 600000);
}

function updateScanProgressCount(completed, total) {
    const countEl = document.getElementById('scan-progress-count');
    if (countEl) {
        countEl.textContent = `${completed} of ${total} events analyzed`;
    }
    
    const fillEl = document.getElementById('scan-progress-fill');
    if (fillEl && total > 0) {
        const pct = Math.min(95, (completed / total) * 100);
        fillEl.style.width = pct + '%';
    }
    
    // Update step indicators based on progress
    if (completed > 0) {
        const steps = ['step-odds', 'step-research', 'step-ai', 'step-complete'];
        steps.forEach(s => {
            const el = document.getElementById(s);
            if (el) el.style.opacity = '1';
        });
    }
}

function showScanProgress(sport, maxEvents) {
    const container = document.getElementById('ai-analyses-container');
    const sportName = SPORTS.find(s => s.key === sport)?.name || sport;
    container.innerHTML = `
        <div class="card" style="max-width:500px;margin:40px auto;">
            <div class="card-body" style="text-align:center;">
                <div class="spinner" style="width:40px;height:40px;margin:0 auto 20px;"></div>
                <h3 style="margin-bottom:8px;">Scanning ${sportName}...</h3>
                <p id="scan-progress-count" style="color:var(--accent-blue);font-weight:600;margin-bottom:16px;">0 of ${maxEvents} events analyzed</p>
                <p style="color:var(--text-secondary);margin-bottom:20px;">Decisions appear in real-time as each analysis completes</p>
                <div style="text-align:left;max-width:300px;margin:0 auto;">
                    <div class="scan-step" id="step-odds" style="padding:8px 0;opacity:0.4;">📊 Fetching odds from bookmakers</div>
                    <div class="scan-step" id="step-research" style="padding:8px 0;opacity:0.4;">🔬 Researching teams & matchups</div>
                    <div class="scan-step" id="step-ai" style="padding:8px 0;opacity:0.4;">🤖 AI analyzing opportunities</div>
                    <div class="scan-step" id="step-complete" style="padding:8px 0;opacity:0.4;">✓ Generating recommendations</div>
                </div>
                <div style="margin-top:20px;height:6px;background:var(--bg-tertiary);border-radius:3px;overflow:hidden;">
                    <div id="scan-progress-fill" style="height:100%;width:5%;background:linear-gradient(90deg,var(--accent-blue),var(--accent-green));transition:width 0.5s;"></div>
                </div>
                <p style="font-size:11px;color:var(--text-muted);margin-top:12px;">Each analysis takes ~60-90 seconds with research enabled</p>
            </div>
        </div>
    `;
    
    // Start initial animation
    setTimeout(() => {
        const el = document.getElementById('step-odds');
        if (el) el.style.opacity = '1';
    }, 500);
}

// Animation is now handled by real-time polling in startScanPolling()

// Trading
async function placeTrade() {
    const ticker = document.getElementById('trade-ticker').value.trim();
    const side = document.getElementById('trade-side').value;
    const action = document.getElementById('trade-action').value;
    const count = parseInt(document.getElementById('trade-quantity').value);
    const price = parseInt(document.getElementById('trade-price').value);
    const type = document.getElementById('trade-type').value;
    if (!ticker) { showToast('Please enter a market ticker', 'error'); return; }
    try {
        const res = await fetch('/api/trade/place', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, side, action, count, type, [side === 'yes' ? 'yes_price' : 'no_price']: price })
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

// ==================== AI Analysis Section ====================

let currentFilter = 'all';

function filterAnalyses(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderAIAnalyses();
}

function renderAIAnalyses() {
    const container = document.getElementById('ai-analyses-container');
    if (scanInProgress) return;
    
    if (!decisionsData || decisionsData.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:60px 20px;color:var(--text-secondary);">
                <div style="font-size:48px;margin-bottom:16px;">🔍</div>
                <div>No AI analyses yet</div>
                <div style="font-size:13px;margin-top:8px;">Run a scan to see detailed AI breakdowns</div>
            </div>
        `;
        return;
    }
    
    let filtered = decisionsData;
    if (currentFilter !== 'all') {
        filtered = decisionsData.filter(item => (item.decision || {}).decision === currentFilter);
    }
    
    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:60px 20px;color:var(--text-secondary);">
                <div style="font-size:48px;margin-bottom:16px;">📋</div>
                <div>No ${currentFilter === 'place_bet' ? 'recommended' : 'skipped'} analyses</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = filtered.slice().reverse().map((item, index) => {
        const d = item.decision || {};
        const timestamp = item.timestamp || d.created_at || '';
        const isRec = d.decision === 'place_bet';
        const conf = ((d.confidence || 0) * 100).toFixed(0);
        const ev = ((d.expected_value || 0) * 100).toFixed(1);
        
        return `
            <div class="card" style="margin-bottom:16px;">
                <div class="card-header" style="cursor:pointer;" onclick="toggleAnalysis(${index})">
                    <div>
                        <span class="card-title">${d.event_name || 'Unknown Event'}</span>
                        <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${formatTimestamp(timestamp)} • ${d.sport || ''}</div>
                    </div>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span class="decision-badge ${isRec ? 'place-bet' : 'skip'}">${isRec ? '✓ Recommended' : 'Skip'}</span>
                        <span style="font-family:'JetBrains Mono';font-size:13px;">${conf}%</span>
                        <span id="expand-${index}" style="color:var(--text-secondary);transition:transform 0.2s;">▼</span>
                    </div>
                </div>
                <div class="card-body" id="analysis-body-${index}" style="display:none;background:var(--bg-secondary);">
                    ${renderAnalysisDetails(d)}
                </div>
            </div>
        `;
    }).join('');
}

function renderAnalysisDetails(d) {
    const conf = ((d.confidence || 0) * 100).toFixed(0);
    const ev = ((d.expected_value || 0) * 100).toFixed(1);
    const winProb = ((d.win_probability || 0) * 100).toFixed(0);
    const research = d.research_summary || {};
    
    return `
        <div class="control-grid" style="margin-bottom:16px;">
            <div class="control-item">
                <div class="control-label">Confidence</div>
                <div class="control-value ${conf >= 60 ? 'green' : ''}">${conf}%</div>
            </div>
            <div class="control-item">
                <div class="control-label">Expected Value</div>
                <div class="control-value ${ev > 0 ? 'green' : 'red'}">${ev > 0 ? '+' : ''}${ev}%</div>
            </div>
            <div class="control-item">
                <div class="control-label">Win Probability</div>
                <div class="control-value">${winProb}%</div>
            </div>
            <div class="control-item">
                <div class="control-label">Bet Type</div>
                <div class="control-value" style="font-size:14px;">${d.bet_type || '--'}</div>
            </div>
        </div>
        
        ${d.decision === 'place_bet' ? `
        <div style="background:var(--accent-green-dim);border-left:3px solid var(--accent-green);padding:12px;border-radius:8px;margin-bottom:16px;">
            <strong>${d.bet_side?.toUpperCase() || 'N/A'}</strong> on ${d.bet_type || 'moneyline'}
            ${d.bet_amount_usd ? ` • Suggested: $${d.bet_amount_usd.toFixed(2)}` : ''}
        </div>
        ` : ''}
        
        <div style="margin-bottom:16px;">
            <div style="font-size:12px;color:var(--accent-blue);text-transform:uppercase;margin-bottom:8px;font-weight:600;">🧠 AI Reasoning</div>
            <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px;border-left:3px solid var(--accent-blue);max-height:200px;overflow-y:auto;">
                ${d.reasoning || 'No reasoning provided'}
            </div>
        </div>
        
        ${d.key_insights && d.key_insights.length > 0 ? `
        <div style="margin-bottom:16px;">
            <div style="font-size:12px;color:var(--accent-blue);text-transform:uppercase;margin-bottom:8px;font-weight:600;">💡 Key Insights</div>
            <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px;">
                ${d.key_insights.map(i => `<div style="padding:4px 0;border-bottom:1px solid var(--border);">→ ${i}</div>`).join('')}
            </div>
        </div>
        ` : ''}
        
        ${d.risk_factors && d.risk_factors.length > 0 ? `
        <div style="margin-bottom:16px;">
            <div style="font-size:12px;color:var(--accent-yellow);text-transform:uppercase;margin-bottom:8px;font-weight:600;">⚠️ Risk Factors</div>
            <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px;">
                ${d.risk_factors.map(r => `<div style="padding:4px 0;border-bottom:1px solid var(--border);">⚠ ${r}</div>`).join('')}
            </div>
        </div>
        ` : ''}
        
        ${renderResearchSummary(research)}
        
        <div style="font-size:11px;color:var(--text-muted);margin-top:16px;">
            Model: ${d.model_used || 'Unknown'} • Event: ${d.event_id || 'N/A'}
        </div>
    `;
}

function renderResearchSummary(research) {
    if (!research || Object.keys(research).length === 0) return '';
    const hasContent = research.home_team?.analysis || research.away_team?.analysis || research.matchup?.analysis || research.betting_trends;
    if (!hasContent) return '';
    
    return `
        <div style="margin-bottom:16px;">
            <div style="font-size:12px;color:var(--accent-green);text-transform:uppercase;margin-bottom:8px;font-weight:600;">📚 Research Summary</div>
            ${research.matchup?.analysis ? `
            <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px;margin-bottom:8px;border-left:3px solid var(--accent-green);max-height:150px;overflow-y:auto;">
                <strong>Matchup:</strong> ${truncateText(research.matchup.analysis, 400)}
            </div>
            ` : ''}
            ${research.betting_trends ? `
            <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px;border-left:3px solid var(--accent-yellow);max-height:150px;overflow-y:auto;">
                <strong>Betting Trends:</strong> ${truncateText(research.betting_trends, 300)}
            </div>
            ` : ''}
        </div>
    `;
}

function toggleAnalysis(index) {
    const body = document.getElementById(`analysis-body-${index}`);
    const icon = document.getElementById(`expand-${index}`);
    if (body.style.display === 'none') {
        body.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    } else {
        body.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }
}

function formatTimestamp(ts) {
    if (!ts) return 'Unknown time';
    try {
        const date = new Date(ts);
        return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return ts; }
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// ==================== Debug Panel Functions ====================

let debugLogs = [];

async function applyDebugSettings() {
    const settings = {
        log_level: document.getElementById('debug-log-level').value,
        component: document.getElementById('debug-component').value,
        log_api_requests: document.getElementById('debug-log-api').classList.contains('active'),
        log_api_responses: document.getElementById('debug-log-responses').classList.contains('active'),
        log_decisions: document.getElementById('debug-log-decisions').classList.contains('active'),
        log_research: document.getElementById('debug-log-research').classList.contains('active')
    };
    
    try {
        const res = await fetch('/api/debug/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        const result = await res.json();
        if (result.success) {
            showToast('Debug settings applied', 'success');
        } else {
            showToast(result.error || 'Failed to apply settings', 'error');
        }
    } catch (e) {
        showToast('Error applying debug settings', 'error');
    }
}

async function fetchDebugLogs() {
    const output = document.getElementById('debug-log-output');
    output.innerHTML = '<div style="color:var(--text-muted);">Loading logs...</div>';
    
    try {
        const res = await fetch('/api/debug/logs?limit=100');
        const result = await res.json();
        
        if (result.success && result.logs) {
            debugLogs = result.logs;
            renderDebugLogs();
        } else {
            output.innerHTML = '<div style="color:var(--accent-red);">Failed to load logs</div>';
        }
    } catch (e) {
        output.innerHTML = '<div style="color:var(--accent-red);">Error fetching logs</div>';
    }
}

function renderDebugLogs() {
    const output = document.getElementById('debug-log-output');
    
    if (!debugLogs || debugLogs.length === 0) {
        output.innerHTML = '<div style="color:var(--text-muted);">No logs available</div>';
        return;
    }
    
    output.innerHTML = debugLogs.map(log => {
        let color = 'var(--text-secondary)';
        if (log.level === 'ERROR') color = 'var(--accent-red)';
        else if (log.level === 'WARNING') color = 'var(--accent-yellow)';
        else if (log.level === 'INFO') color = 'var(--accent-blue)';
        else if (log.level === 'DEBUG') color = 'var(--text-muted)';
        
        const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '';
        const component = log.component ? `[${log.component}]` : '';
        
        return `<div style="color:${color};padding:2px 0;border-bottom:1px solid var(--border);">
            <span style="color:var(--text-muted)">${time}</span> 
            <span style="color:var(--accent-blue)">${component}</span> 
            ${log.message || log}
        </div>`;
    }).join('');
    
    // Scroll to bottom
    output.scrollTop = output.scrollHeight;
}

function clearDebugLogs() {
    debugLogs = [];
    const output = document.getElementById('debug-log-output');
    output.innerHTML = '<div style="color:var(--text-muted);">Logs cleared</div>';
    
    // Also clear on server
    fetch('/api/debug/logs/clear', { method: 'POST' }).catch(() => {});
}

async function loadDebugSettings() {
    try {
        const res = await fetch('/api/debug/settings');
        const result = await res.json();
        
        if (result.success && result.settings) {
            const s = result.settings;
            document.getElementById('debug-log-level').value = s.log_level || 'INFO';
            document.getElementById('debug-component').value = s.component || 'all';
            
            if (s.log_api_requests) document.getElementById('debug-log-api').classList.add('active');
            else document.getElementById('debug-log-api').classList.remove('active');
            
            if (s.log_api_responses) document.getElementById('debug-log-responses').classList.add('active');
            else document.getElementById('debug-log-responses').classList.remove('active');
            
            if (s.log_decisions) document.getElementById('debug-log-decisions').classList.add('active');
            else document.getElementById('debug-log-decisions').classList.remove('active');
            
            if (s.log_research) document.getElementById('debug-log-research').classList.add('active');
            else document.getElementById('debug-log-research').classList.remove('active');
        }
    } catch (e) {
        console.error('Failed to load debug settings:', e);
    }
}
