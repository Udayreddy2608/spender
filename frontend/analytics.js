/* ─────────────────────────────────────────────────────────────────────────
   Spender — Analytics Page JS
   ───────────────────────────────────────────────────────────────────────── */

const API = 'http://localhost:8000/api';

const CAT_CONFIG = {
    food: { emoji: '🍔', label: 'Food', color: '#f59e0b' },
    travel: { emoji: '✈️', label: 'Travel', color: '#6c63ff' },
    clothes: { emoji: '👗', label: 'Clothes', color: '#ec4899' },
    skincare: { emoji: '✨', label: 'Skincare', color: '#a78bfa' },
    studies: { emoji: '📚', label: 'Studies', color: '#14b8a6' },
    health: { emoji: '💊', label: 'Health', color: '#22d3a5' },
    subscriptions: { emoji: '📱', label: 'Subscriptions', color: '#3b82f6' },
    rent: { emoji: '🏠', label: 'Rent', color: '#f43f5e' },
    emi: { emoji: '💳', label: 'EMI', color: '#fb923c' },
    misc: { emoji: '📦', label: 'Misc', color: '#9ca3af' },
};

let charts = {};

// ─── Init ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadAnalytics();
});

async function loadAnalytics() {
    const main = document.getElementById('analytics-main');
    main.innerHTML = `<div class="analytics-loading" id="loading-state"><div class="spinner"></div><span>Loading analytics…</span></div>`;

    try {
        const [analytics, dashboard] = await Promise.all([
            apiFetch('/analytics'),
            apiFetch('/dashboard').catch(() => null),
        ]);
        renderAnalytics(analytics, dashboard);
    } catch (e) {
        main.innerHTML = `
            <div class="analytics-loading">
                <div class="chart-empty-icon">📊</div>
                <span>No data yet — log some expenses to see analytics!</span>
                <a href="/" class="btn btn-primary" style="margin-top:8px">Go to Dashboard</a>
            </div>`;
    }
}

async function apiFetch(path) {
    const res = await fetch(API + path, { headers: { 'Content-Type': 'application/json' } });
    if (!res.ok) throw new Error('API error');
    return res.json();
}

// ─── Main Render ──────────────────────────────────────────────────────────

function renderAnalytics(data, dashboard) {
    const main = document.getElementById('analytics-main');

    const goal = dashboard?.goal;
    const projection = dashboard?.projection;

    // Destroy old charts
    Object.values(charts).forEach(c => c.destroy());
    charts = {};

    main.innerHTML = buildHTML(data, goal, projection);

    // Render charts after DOM is ready
    requestAnimationFrame(() => {
        renderWeeklyChart(data.weekly_history);
        renderCategoryChart(data.category_breakdown);
        renderDailyChart(data.daily_spend_30d);
        if (goal && projection) {
            renderGoalProgressChart(goal, projection);
        }
    });
}

// ─── HTML Builder ─────────────────────────────────────────────────────────

function buildHTML(data, goal, projection) {
    const pct = goal && projection
        ? Math.min(100, Math.round((projection.total_saved / goal.target_amount) * 100))
        : null;

    const underspend = data.current_week_underspend;
    const underspendTile = underspend !== null && underspend !== undefined
        ? underspend > 0
            ? `<div class="a-tile green" style="--tile-accent:var(--green)">
                <div class="a-tile-icon">🎉</div>
                <div class="a-tile-label">This Week Saved</div>
                <div class="a-tile-value">₹${fmt(underspend)}</div>
                <div class="a-tile-sub">under your weekly limit</div>
               </div>`
            : underspend < 0
                ? `<div class="a-tile red" style="--tile-accent:var(--red)">
                    <div class="a-tile-icon">⚠️</div>
                    <div class="a-tile-label">This Week Over</div>
                    <div class="a-tile-value">₹${fmt(Math.abs(underspend))}</div>
                    <div class="a-tile-sub">over your weekly limit</div>
                   </div>`
                : ''
        : '';

    const goalProgressCard = goal && projection ? `
        <div class="chart-card">
            <div class="chart-header">
                <div class="chart-title"><span class="chart-title-icon">🎯</span> Goal Progress</div>
                <span class="chart-badge">${pct}% done</span>
            </div>
            <div class="chart-wrap">
                <canvas id="chart-goal"></canvas>
            </div>
            <div style="margin-top:14px;font-size:12px;color:var(--text-muted);display:flex;justify-content:space-between">
                <span>Saved: <strong style="color:var(--green)">₹${fmt(projection.total_saved)}</strong></span>
                <span>Target: <strong style="color:var(--accent2)">₹${fmt(goal.target_amount)}</strong></span>
                <span>Remaining: <strong style="color:var(--yellow)">₹${fmt(projection.remaining_target)}</strong></span>
            </div>
        </div>` : '';

    return `
    <!-- Hero -->
    <div class="analytics-hero">
        <div>
            <div class="analytics-hero-title">📊 Spending Analytics</div>
            <div class="analytics-hero-sub">Visual breakdown of your financial mission</div>
        </div>
        <a href="/" class="analytics-hero-back">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back to Dashboard
        </a>
    </div>

    <!-- Summary Tiles -->
    <div class="analytics-tiles">
        <div class="a-tile purple">
            <div class="a-tile-icon">💸</div>
            <div class="a-tile-label">Total Spent (All Time)</div>
            <div class="a-tile-value">₹${fmt(data.total_spent_all)}</div>
            <div class="a-tile-sub">${data.category_breakdown.length} categories</div>
        </div>
        <div class="a-tile yellow">
            <div class="a-tile-icon">📆</div>
            <div class="a-tile-label">Avg Weekly Spend</div>
            <div class="a-tile-value">₹${fmt(data.avg_weekly_spend)}</div>
            <div class="a-tile-sub">across ${data.weekly_history.filter(w => {
        const today = new Date();
        const ws = new Date(w.week_start_date);
        const currentWS = new Date(today);
        currentWS.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1));
        return ws < currentWS;
    }).length} completed weeks</div>
        </div>
        ${data.best_week_saved !== null
            ? `<div class="a-tile green">
                <div class="a-tile-icon">🏆</div>
                <div class="a-tile-label">Best Week Saved</div>
                <div class="a-tile-value">₹${fmt(data.best_week_saved)}</div>
                <div class="a-tile-sub">most under weekly cap</div>
               </div>`
            : `<div class="a-tile">
                <div class="a-tile-icon">🏆</div>
                <div class="a-tile-label">Best Week Saved</div>
                <div class="a-tile-value">—</div>
                <div class="a-tile-sub">no completed weeks yet</div>
               </div>`}
        ${data.worst_week_overspend !== null
            ? `<div class="a-tile red">
                <div class="a-tile-icon">🔥</div>
                <div class="a-tile-label">Worst Overspend</div>
                <div class="a-tile-value">₹${fmt(data.worst_week_overspend)}</div>
                <div class="a-tile-sub">over cap in a single week</div>
               </div>`
            : `<div class="a-tile">
                <div class="a-tile-icon">✅</div>
                <div class="a-tile-label">Worst Overspend</div>
                <div class="a-tile-value">None!</div>
                <div class="a-tile-sub">you've never gone over</div>
               </div>`}
        ${underspendTile}
    </div>

    <!-- Charts Row 1 -->
    <div class="chart-grid">
        <!-- Weekly Spend vs Cap -->
        <div class="chart-card full-width">
            <div class="chart-header">
                <div class="chart-title"><span class="chart-title-icon">📆</span> Weekly Spend vs Cap</div>
                <span class="chart-badge">All Weeks</span>
            </div>
            ${data.weekly_history.length === 0
            ? `<div class="chart-empty"><div class="chart-empty-icon">📆</div><span>No weekly data yet</span></div>`
            : `<div class="chart-wrap tall"><canvas id="chart-weekly"></canvas></div>
                   <div class="weekly-legend">
                       <div class="wl-item"><div class="wl-dot" style="background:#6c63ff"></div> Spent</div>
                       <div class="wl-item"><div class="wl-dot" style="background:rgba(108,99,255,0.2);border:1px dashed #6c63ff"></div> Cap</div>
                       <div class="wl-item"><div class="wl-dot" style="background:#22d3a5"></div> Saved (under cap)</div>
                       <div class="wl-item"><div class="wl-dot" style="background:#f43f5e"></div> Overspent</div>
                   </div>`}
        </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="chart-grid">
        <!-- Category Donut -->
        <div class="chart-card">
            <div class="chart-header">
                <div class="chart-title"><span class="chart-title-icon">🍩</span> Spending by Category</div>
                <span class="chart-badge">All Time</span>
            </div>
            ${data.category_breakdown.length === 0
            ? `<div class="chart-empty"><div class="chart-empty-icon">🍩</div><span>No expenses yet</span></div>`
            : `<div class="chart-wrap"><canvas id="chart-category"></canvas></div>
                   <div class="cat-legend" id="cat-legend"></div>`}
        </div>

        <!-- Goal Progress or Daily Spend -->
        ${goalProgressCard || `
        <div class="chart-card">
            <div class="chart-header">
                <div class="chart-title"><span class="chart-title-icon">📈</span> Daily Spend (30 Days)</div>
                <span class="chart-badge">Last 30d</span>
            </div>
            ${data.daily_spend_30d.length === 0
            ? `<div class="chart-empty"><div class="chart-empty-icon">📈</div><span>No data in last 30 days</span></div>`
            : `<div class="chart-wrap"><canvas id="chart-daily"></canvas></div>`}
        </div>`}
    </div>

    <!-- Charts Row 3 — Daily spend (if goal card shown above) -->
    ${goalProgressCard ? `
    <div class="chart-grid">
        <div class="chart-card full-width">
            <div class="chart-header">
                <div class="chart-title"><span class="chart-title-icon">📈</span> Daily Spend (Last 30 Days)</div>
                <span class="chart-badge">Last 30d</span>
            </div>
            ${data.daily_spend_30d.length === 0
                ? `<div class="chart-empty"><div class="chart-empty-icon">📈</div><span>No data in last 30 days</span></div>`
                : `<div class="chart-wrap"><canvas id="chart-daily"></canvas></div>`}
        </div>
    </div>` : ''}
    `;
}

// ─── Chart: Weekly Spend vs Cap ───────────────────────────────────────────

function renderWeeklyChart(history) {
    const canvas = document.getElementById('chart-weekly');
    if (!canvas || history.length === 0) return;

    const labels = history.map(w => {
        const d = new Date(w.week_start_date + 'T00:00:00');
        return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    });

    const spentData = history.map(w => w.spent);
    const capData = history.map(w => w.weekly_cap);
    const savedData = history.map(w => Math.max(0, w.saved));
    const overData = history.map(w => Math.max(0, -w.saved));

    charts.weekly = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Spent',
                    data: spentData,
                    backgroundColor: history.map(w =>
                        w.spent > w.weekly_cap ? 'rgba(244,63,94,0.7)' : 'rgba(108,99,255,0.7)'
                    ),
                    borderColor: history.map(w =>
                        w.spent > w.weekly_cap ? '#f43f5e' : '#6c63ff'
                    ),
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Cap',
                    data: capData,
                    type: 'line',
                    borderColor: 'rgba(108,99,255,0.5)',
                    borderDash: [6, 4],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d28',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#e8eaf0',
                    bodyColor: '#9ca3af',
                    padding: 12,
                    callbacks: {
                        label: ctx => {
                            const w = history[ctx.dataIndex];
                            if (ctx.datasetIndex === 0) {
                                const diff = w.weekly_cap - w.spent;
                                const sign = diff >= 0 ? '🟢 Saved ₹' + fmt(diff) : '🔴 Over ₹' + fmt(-diff);
                                return [`Spent: ₹${fmt(w.spent)}`, sign];
                            }
                            return `Cap: ₹${fmt(w.weekly_cap)}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#6b7280', font: { size: 11 } },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 },
                        callback: v => '₹' + fmt(v),
                    },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ─── Chart: Category Donut ────────────────────────────────────────────────

function renderCategoryChart(breakdown) {
    const canvas = document.getElementById('chart-category');
    if (!canvas || breakdown.length === 0) return;

    const colors = breakdown.map(b => (CAT_CONFIG[b.category]?.color || '#9ca3af'));
    const labels = breakdown.map(b => {
        const c = CAT_CONFIG[b.category];
        return (c ? c.emoji + ' ' + c.label : b.category);
    });

    charts.category = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: breakdown.map(b => b.total),
                backgroundColor: colors.map(c => c + 'cc'),
                borderColor: colors,
                borderWidth: 2,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d28',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#e8eaf0',
                    bodyColor: '#9ca3af',
                    padding: 12,
                    callbacks: {
                        label: ctx => {
                            const b = breakdown[ctx.dataIndex];
                            const total = breakdown.reduce((s, x) => s + x.total, 0);
                            const pct = Math.round(b.total / total * 100);
                            return [`₹${fmt(b.total)} (${pct}%)`, `${b.count} transactions`];
                        },
                    },
                },
            },
        },
    });

    // Build legend
    const legend = document.getElementById('cat-legend');
    if (legend) {
        const total = breakdown.reduce((s, b) => s + b.total, 0);
        legend.innerHTML = breakdown.map((b, i) => {
            const c = CAT_CONFIG[b.category];
            const pct = Math.round(b.total / total * 100);
            return `
            <div class="cat-legend-item">
                <div class="cat-legend-left">
                    <div class="cat-dot" style="background:${colors[i]}"></div>
                    <span class="cat-name">${c ? c.emoji + ' ' + c.label : b.category}</span>
                    <span class="cat-count">${b.count}×</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:10px;color:var(--text-muted)">${pct}%</span>
                    <span class="cat-amount">₹${fmt(b.total)}</span>
                </div>
            </div>`;
        }).join('');
    }
}

// ─── Chart: Daily Spend ───────────────────────────────────────────────────

function renderDailyChart(daily) {
    const canvas = document.getElementById('chart-daily');
    if (!canvas || daily.length === 0) return;

    // Fill in missing days with 0
    const allDays = [];
    if (daily.length > 0) {
        const start = new Date(daily[0].date + 'T00:00:00');
        const end = new Date(daily[daily.length - 1].date + 'T00:00:00');
        const dayMap = {};
        daily.forEach(d => { dayMap[d.date] = d.total; });

        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            const key = d.toISOString().split('T')[0];
            allDays.push({ date: key, total: dayMap[key] || 0 });
        }
    }

    const labels = allDays.map(d => {
        const dt = new Date(d.date + 'T00:00:00');
        return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    });

    charts.daily = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Daily Spend',
                data: allDays.map(d => d.total),
                borderColor: '#14b8a6',
                backgroundColor: 'rgba(20,184,166,0.08)',
                borderWidth: 2,
                pointRadius: allDays.map(d => d.total > 0 ? 4 : 0),
                pointBackgroundColor: '#14b8a6',
                pointBorderColor: '#0a0b0f',
                pointBorderWidth: 2,
                fill: true,
                tension: 0.4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d28',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#e8eaf0',
                    bodyColor: '#9ca3af',
                    padding: 12,
                    callbacks: {
                        label: ctx => `₹${fmt(ctx.raw)}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 10 },
                        maxTicksLimit: 10,
                    },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 11 },
                        callback: v => '₹' + fmt(v),
                    },
                    beginAtZero: true,
                },
            },
        },
    });
}

// ─── Chart: Goal Progress ─────────────────────────────────────────────────

function renderGoalProgressChart(goal, projection) {
    const canvas = document.getElementById('chart-goal');
    if (!canvas) return;

    const saved = projection.total_saved;
    const remaining = projection.remaining_target;

    charts.goal = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Saved', 'Remaining'],
            datasets: [{
                data: [saved, remaining],
                backgroundColor: ['rgba(34,211,165,0.8)', 'rgba(255,255,255,0.06)'],
                borderColor: ['#22d3a5', 'rgba(255,255,255,0.1)'],
                borderWidth: 2,
                hoverOffset: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d28',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#e8eaf0',
                    bodyColor: '#9ca3af',
                    padding: 12,
                    callbacks: {
                        label: ctx => {
                            const pct = Math.round(ctx.raw / goal.target_amount * 100);
                            return `₹${fmt(ctx.raw)} (${pct}%)`;
                        },
                    },
                },
            },
        },
        plugins: [{
            id: 'centerText',
            afterDraw(chart) {
                const { ctx, chartArea: { width, height, left, top } } = chart;
                const cx = left + width / 2;
                const cy = top + height / 2;
                const pct = Math.min(100, Math.round(saved / goal.target_amount * 100));
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#22d3a5';
                ctx.font = 'bold 28px JetBrains Mono, monospace';
                ctx.fillText(pct + '%', cx, cy - 10);
                ctx.fillStyle = '#6b7280';
                ctx.font = '11px Inter, sans-serif';
                ctx.fillText('of goal', cx, cy + 14);
                ctx.restore();
            },
        }],
    });
}

// ─── Formatter ────────────────────────────────────────────────────────────

function fmt(n) {
    if (n === null || n === undefined) return '—';
    return Math.round(n).toLocaleString('en-IN');
}
