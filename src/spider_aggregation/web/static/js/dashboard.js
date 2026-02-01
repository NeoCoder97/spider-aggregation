// Spider Aggregation - Dashboard JavaScript

// Chart instance
let languageChart = null;

// ============================================================================
// Initialize Dashboard
// ============================================================================

async function initDashboard() {
    await Promise.all([
        loadStats(),
        loadLanguageChart(),
        loadRecentActivity(),
        loadFeedHealth(),
        loadSchedulerStatus(),
    ]);
}

// ============================================================================
// Load Statistics
// ============================================================================

async function loadStats() {
    try {
        const response = await App.api.get('/api/stats');

        document.getElementById('total-entries').textContent = response.total_entries || 0;
        document.getElementById('total-feeds').textContent = response.total_feeds || 0;
        document.getElementById('total-rules').textContent = response.total_rules || 0;

        if (response.most_recent) {
            const date = new Date(response.most_recent);
            document.getElementById('last-updated').textContent = App.formatRelativeTime(response.most_recent);
        } else {
            document.getElementById('last-updated').textContent = '从未';
        }

        return response;
    } catch (error) {
        console.error('加载统计失败:', error);
        document.getElementById('total-entries').textContent = '错误';
        document.getElementById('total-feeds').textContent = '错误';
        document.getElementById('total-rules').textContent = '错误';
    }
}

// ============================================================================
// Load Language Chart
// ============================================================================

async function loadLanguageChart() {
    try {
        const response = await App.api.get('/api/stats');
        const languageData = response.language_counts || {};

        const ctx = document.getElementById('language-chart');
        if (!ctx) return;

        // Destroy existing chart if any
        if (languageChart) {
            languageChart.destroy();
        }

        const labels = Object.keys(languageData);
        const data = Object.values(languageData);

        // Language display names
        const languageNames = {
            'en': 'English',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
        };

        const displayLabels = labels.map(l => languageNames[l] || l.toUpperCase());

        // Chart colors
        const colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
            '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
        ];

        languageChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: displayLabels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#ffffff',
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            },
                        },
                    },
                },
            },
        });

    } catch (error) {
        console.error('Failed to load language chart:', error);
    }
}

// ============================================================================
// Load Recent Activity
// ============================================================================

async function loadRecentActivity() {
    try {
        const response = await App.api.get('/api/dashboard/activity', { limit: 10 });
        const container = document.getElementById('recent-activity');

        if (!response.data || response.data.length === 0) {
            container.innerHTML = '<p class="empty-state">暂无最近活动</p>';
            return;
        }

        let html = '<div class="entries-list">';
        for (const entry of response.data) {
            const dateStr = entry.fetched_at || entry.published_at;
            const relativeTime = dateStr ? App.formatRelativeTime(dateStr) : '未知';

            html += `
                <div class="entry-card" style="padding: 1rem;">
                    <div class="entry-title" style="font-size: 1rem;">
                        <a href="/entry/${entry.id}">${App.escapeHtml(entry.title)}</a>
                    </div>
                    <div class="entry-meta">
                        <span>${relativeTime}</span>
                        ${entry.language ? `<span class="badge badge-secondary">${entry.language.toUpperCase()}</span>` : ''}
                    </div>
                </div>
            `;
        }
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('加载最近活动失败:', error);
        document.getElementById('recent-activity').innerHTML = '<p class="empty-state">加载活动失败</p>';
    }
}

// ============================================================================
// Load Feed Health
// ============================================================================

async function loadFeedHealth() {
    try {
        const response = await App.api.get('/api/dashboard/feed-health');
        const tbody = document.querySelector('#feed-health-table tbody');

        if (!response.data || response.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">暂无订阅源</td></tr>';
            return;
        }

        let html = '';
        for (const feed of response.data) {
            const statusClass = feed.enabled ? 'enabled' : 'disabled';
            const statusText = feed.enabled ? '已启用' : '已禁用';

            const healthClass = feed.error_count > 5 ? 'error' : feed.error_count > 0 ? 'warning' : 'healthy';

            const lastFetched = feed.last_fetched ? App.formatRelativeTime(feed.last_fetched) : '从未';

            html += `
                <tr>
                    <td>
                        <a href="/feeds" style="font-weight: 500;">${App.escapeHtml(feed.name)}</a>
                    </td>
                    <td>
                        <span class="feed-status ${statusClass}">${statusText}</span>
                    </td>
                    <td>${lastFetched}</td>
                    <td>
                        <div class="health-indicator">
                            <span class="health-dot ${healthClass}"></span>
                            <span>${feed.error_count} 个错误</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        tbody.innerHTML = html;

    } catch (error) {
        console.error('加载订阅源健康状态失败:', error);
        document.querySelector('#feed-health-table tbody').innerHTML =
            '<tr><td colspan="4" class="empty-state">加载健康状态失败</td></tr>';
    }
}

// ============================================================================
// Refresh All Data
// ============================================================================

function refreshDashboard() {
    App.showToast('正在刷新仪表盘...', 'info');
    initDashboard().then(() => {
        App.showToast('仪表盘刷新完成', 'success');
    });
}

// ============================================================================
// Scheduler Control
// ============================================================================

async function loadSchedulerStatus() {
    try {
        const response = await App.api.get('/api/scheduler/status');
        const status = response.data;

        const indicator = document.getElementById('scheduler-indicator');
        const statusText = document.getElementById('scheduler-status-text');
        const btnStart = document.getElementById('btn-start-scheduler');
        const btnStop = document.getElementById('btn-stop-scheduler');

        if (status.is_running) {
            indicator.className = 'status-indicator status-running';
            statusText.textContent = `Running (${status.enabled_feeds_count} feeds scheduled)`;
            btnStart.style.display = 'none';
            btnStop.style.display = 'inline-block';
        } else {
            indicator.className = 'status-indicator status-stopped';
            statusText.textContent = `Stopped (${status.enabled_feeds_count} feeds enabled)`;
            btnStart.style.display = 'inline-block';
            btnStop.style.display = 'none';
        }

        return status;
    } catch (error) {
        console.error('Failed to load scheduler status:', error);
        document.getElementById('scheduler-status-text').textContent = 'Error loading status';
    }
}

async function startScheduler() {
    const btnStart = document.getElementById('btn-start-scheduler');
    const btnStop = document.getElementById('btn-stop-scheduler');
    const indicator = document.getElementById('scheduler-indicator');
    const statusText = document.getElementById('scheduler-status-text');

    // 立即更新 UI 状态
    btnStart.disabled = true;
    btnStart.textContent = '启动中...';
    indicator.className = 'status-indicator status-pending';
    statusText.textContent = 'Starting...';

    App.showToast('正在启动调度器...', 'info');

    try {
        const response = await App.api.post('/api/scheduler/start');

        if (response.success) {
            App.showToast('调度器启动成功', 'success');
            await loadSchedulerStatus();
        } else {
            // 启动失败，恢复状态
            btnStart.disabled = false;
            btnStart.textContent = '启动调度器';
            indicator.className = 'status-indicator status-stopped';
            statusText.textContent = 'Start failed';
            App.showToast(response.error || '启动调度器失败', 'error');
        }
    } catch (error) {
        console.error('启动调度器错误:', error);
        // 恢复状态
        btnStart.disabled = false;
        btnStart.textContent = '启动调度器';
        indicator.className = 'status-indicator status-stopped';
        statusText.textContent = 'Error';
        App.showToast('启动调度器失败', 'error');
    }
}

async function stopScheduler() {
    App.modal.confirm(
        '确定要停止调度器吗？订阅源将不再自动抓取。',
        async () => {
            const btnStart = document.getElementById('btn-start-scheduler');
            const btnStop = document.getElementById('btn-stop-scheduler');
            const indicator = document.getElementById('scheduler-indicator');
            const statusText = document.getElementById('scheduler-status-text');

            // 立即更新 UI 状态
            btnStop.disabled = true;
            btnStop.textContent = '停止中...';
            indicator.className = 'status-indicator status-pending';
            statusText.textContent = 'Stopping...';

            App.showToast('正在停止调度器...', 'info');

            try {
                const response = await App.api.post('/api/scheduler/stop');

                if (response.success) {
                    App.showToast('调度器已停止', 'success');
                    await loadSchedulerStatus();
                } else {
                    // 停止失败，恢复状态
                    btnStop.disabled = false;
                    btnStop.textContent = '停止调度器';
                    indicator.className = 'status-indicator status-running';
                    statusText.textContent = 'Stop failed';
                    App.showToast(response.error || '停止调度器失败', 'error');
                }
            } catch (error) {
                console.error('停止调度器错误:', error);
                // 恢复状态
                btnStop.disabled = false;
                btnStop.textContent = '停止调度器';
                indicator.className = 'status-indicator status-running';
                statusText.textContent = 'Error';
                App.showToast('停止调度器失败', 'error');
            }
        },
        { title: '停止调度器' }
    );
}

async function fetchAllFeeds() {
    App.modal.confirm(
        '立即抓取所有已启用的订阅源？这可能需要一些时间。',
        async () => {
            App.showToast('正在抓取订阅源...', 'info');

            try {
                const response = await App.api.post('/api/scheduler/fetch-all');

                if (response.success) {
                    const data = response.data;
                    const message = `抓取完成：${data.results.length} 个订阅源，${data.total_created} 篇新文章，${data.total_skipped} 篇已存在`;
                    App.showToast(message, 'success');

                    // Refresh dashboard after a delay
                    setTimeout(() => {
                        refreshDashboard();
                    }, 1000);
                } else {
                    App.showToast(response.error || '抓取订阅源失败', 'error');
                }
            } catch (error) {
                console.error('抓取订阅源错误:', error);
                App.showToast('抓取订阅源失败', 'error');
            }
        },
        { title: '立即抓取全部' }
    );
}

// ============================================================================
// Initialize on Load
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initDashboard();

    // Auto-refresh every 5 minutes
    setInterval(refreshDashboard, 5 * 60 * 1000);

    // Auto-refresh scheduler status every 30 seconds
    setInterval(loadSchedulerStatus, 30 * 1000);
});
