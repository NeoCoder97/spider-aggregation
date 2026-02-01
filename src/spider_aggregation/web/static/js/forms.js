// MindWeaver - Form Handling JavaScript

// ============================================================================
// Feed Form Handling
// ============================================================================

function showAddFeedModal() {
    const content = `
        <form id="feed-form" onsubmit="handleFeedSubmit(event)">
            <div class="form-group">
                <label for="feed-url">订阅源链接 *</label>
                <input type="url" id="feed-url" name="url" class="form-control" required placeholder="https://example.com/feed">
                <div class="form-help">输入 RSS/Atom 订阅源链接</div>
            </div>

            <div class="form-group">
                <label for="feed-name">名称</label>
                <input type="text" id="feed-name" name="name" class="form-control" placeholder="我的博客订阅">
                <div class="form-help">可选的自定义名称（留空则自动从订阅源获取）</div>
            </div>

            <div class="form-group">
                <label for="feed-description">描述</label>
                <textarea id="feed-description" name="description" class="form-control" rows="2"></textarea>
            </div>

            <div class="form-group">
                <label for="feed-interval">抓取间隔（分钟）</label>
                <input type="number" id="feed-interval" name="fetch_interval_minutes" class="form-control" value="60" min="10" max="10080">
                <div class="form-help">抓取订阅源的频率（10-10080 分钟）</div>
            </div>

            <div class="form-group">
                <label for="max-entries">每次抓取最大文章数</label>
                <input type="number" id="max-entries" name="max_entries_per_fetch" class="form-control" value="100" min="0" max="1000">
                <div class="form-help">每次更新最多抓取的文章数量（0-1000，0表示不限制）</div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="fetch_only_recent">
                    仅抓取最近 30 天的文章
                </label>
                <div class="form-help">启用后只保存最近 30 天内发布的文章</div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="enabled" checked>
                    启用此订阅源
                </label>
            </div>

            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.modal.hide()">取消</button>
                <button type="submit" class="btn btn-primary">创建订阅源</button>
            </div>
        </form>
    `;

    App.modal.show('添加订阅源', content);
}

function showEditFeedModal(feedId) {
    const feedData = window.feedData.find(f => f.id === feedId);
    if (!feedData) {
        App.showToast('未找到订阅源', 'error');
        return;
    }

    const content = `
        <form id="feed-form" onsubmit="handleFeedUpdate(event, ${feedId})">
            <div class="form-group">
                <label for="feed-url">订阅源链接 *</label>
                <input type="url" id="feed-url" name="url" class="form-control" required value="${App.escapeHtml(feedData.url)}" readonly>
                <div class="form-help">订阅源链接不可更改</div>
            </div>

            <div class="form-group">
                <label for="feed-name">名称</label>
                <input type="text" id="feed-name" name="name" class="form-control" value="${App.escapeHtml(feedData.name || '')}">
            </div>

            <div class="form-group">
                <label for="feed-description">描述</label>
                <textarea id="feed-description" name="description" class="form-control" rows="2">${App.escapeHtml(feedData.description || '')}</textarea>
            </div>

            <div class="form-group">
                <label for="feed-interval">抓取间隔（分钟）</label>
                <input type="number" id="feed-interval" name="fetch_interval_minutes" class="form-control" value="${feedData.fetch_interval_minutes}" min="10" max="10080">
            </div>

            <div class="form-group">
                <label for="max-entries">每次抓取最大文章数</label>
                <input type="number" id="max-entries" name="max_entries_per_fetch" class="form-control"
                       value="${feedData.max_entries_per_fetch || 100}" min="0" max="1000">
                <div class="form-help">每次更新最多抓取的文章数量（0-1000，0表示不限制）</div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="fetch_only_recent" ${feedData.fetch_only_recent ? 'checked' : ''}>
                    仅抓取最近 30 天的文章
                </label>
                <div class="form-help">启用后只保存最近 30 天内发布的文章</div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="enabled" ${feedData.enabled ? 'checked' : ''}>
                    启用此订阅源
                </label>
            </div>

            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.modal.hide()">取消</button>
                <button type="submit" class="btn btn-primary">更新订阅源</button>
            </div>
        </form>
    `;

    App.modal.show('编辑订阅源', content);
}

async function handleFeedSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const validation = App.form.validate(form);

    if (!validation.valid) {
        App.showToast('请修正表单中的错误', 'error');
        return;
    }

    const data = App.form.serialize(form);

    try {
        const response = await App.api.post('/api/feeds', data);

        if (response.success) {
            App.showToast('订阅源创建成功', 'success');
            App.modal.hide();
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '创建订阅源失败', 'error');
        }
    } catch (error) {
        console.error('创建订阅源错误:', error);
        App.showToast('创建订阅源失败', 'error');
    }
}

async function handleFeedUpdate(event, feedId) {
    event.preventDefault();
    const form = event.target;
    const validation = App.form.validate(form);

    if (!validation.valid) {
        App.showToast('请修正表单中的错误', 'error');
        return;
    }

    const data = App.form.serialize(form);

    try {
        const response = await App.api.put(`/api/feeds/${feedId}`, data);

        if (response.success) {
            App.showToast('订阅源更新成功', 'success');
            App.modal.hide();
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '更新订阅源失败', 'error');
        }
    } catch (error) {
        console.error('更新订阅源错误:', error);
        App.showToast('更新订阅源失败', 'error');
    }
}

async function toggleFeed(feedId) {
    try {
        const response = await App.api.post(`/api/feeds/${feedId}/toggle`);

        if (response.success) {
            App.showToast(response.message, 'success');
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '切换状态失败', 'error');
        }
    } catch (error) {
        console.error('切换状态错误:', error);
        App.showToast('切换状态失败', 'error');
    }
}

async function deleteFeed(feedId) {
    const feedData = window.feedData.find(f => f.id === feedId);
    const feedName = feedData ? (feedData.name || feedData.url) : '未知';

    App.modal.confirm(
        `确定要删除订阅源 "${App.escapeHtml(feedName)}" 吗？`,
        async () => {
            try {
                const response = await App.api.delete(`/api/feeds/${feedId}`);

                if (response.success) {
                    App.showToast('订阅源删除成功', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    App.showToast(response.error || '删除订阅源失败', 'error');
                }
            } catch (error) {
                console.error('删除订阅源错误:', error);
                App.showToast('删除订阅源失败', 'error');
            }
        },
        { title: '删除订阅源', danger: true }
    );
}

async function fetchFeed(feedId) {
    try {
        const response = await App.api.post(`/api/feeds/${feedId}/fetch`);

        if (response.success) {
            App.showToast(response.message, 'success');
        } else {
            App.showToast(response.error || '抓取失败', 'error');
        }
    } catch (error) {
        console.error('抓取错误:', error);
        App.showToast('抓取失败', 'error');
    }
}

// ============================================================================
// Filter Rule Form Handling
// ============================================================================

function showAddFilterRuleModal() {
    const content = `
        <form id="filter-rule-form" onsubmit="handleFilterRuleSubmit(event)">
            <div class="form-group">
                <label for="rule-name">规则名称 *</label>
                <input type="text" id="rule-name" name="name" class="form-control" required placeholder="我的过滤规则">
            </div>

            <div class="form-group">
                <label for="rule-type">规则类型 *</label>
                <select id="rule-type" name="rule_type" class="form-control" required>
                    <option value="keyword">关键词</option>
                    <option value="regex">正则表达式</option>
                    <option value="tag">标签</option>
                    <option value="language">语言</option>
                </select>
            </div>

            <div class="form-group">
                <label for="match-type">匹配方式 *</label>
                <select id="match-type" name="match_type" class="form-control" required>
                    <option value="include">通过（匹配的文章会通过）</option>
                    <option value="exclude">过滤（匹配的文章会被过滤）</option>
                </select>
            </div>

            <div class="form-group">
                <label for="rule-pattern">模式 *</label>
                <input type="text" id="rule-pattern" name="pattern" class="form-control" required placeholder="关键词或正则表达式">
                <div class="form-help">关键词：精确匹配；正则：有效的正则表达式</div>
            </div>

            <div class="form-group">
                <label for="rule-priority">优先级</label>
                <input type="number" id="rule-priority" name="priority" class="form-control" value="0" min="0" max="100">
                <div class="form-help">优先级高的规则会先执行（0-100）</div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="enabled" checked>
                    启用此规则
                </label>
            </div>

            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.modal.hide()">取消</button>
                <button type="submit" class="btn btn-primary">创建规则</button>
            </div>
        </form>
    `;

    App.modal.show('添加过滤规则', content);
}

function showEditFilterRuleModal(ruleId) {
    const ruleData = window.ruleData.find(r => r.id === ruleId);
    if (!ruleData) {
        App.showToast('未找到过滤规则', 'error');
        return;
    }

    const content = `
        <form id="filter-rule-form" onsubmit="handleFilterRuleUpdate(event, ${ruleId})">
            <div class="form-group">
                <label for="rule-name">规则名称 *</label>
                <input type="text" id="rule-name" name="name" class="form-control" required value="${App.escapeHtml(ruleData.name)}">
            </div>

            <div class="form-group">
                <label for="rule-type">规则类型 *</label>
                <select id="rule-type" name="rule_type" class="form-control" required>
                    <option value="keyword" ${ruleData.rule_type === 'keyword' ? 'selected' : ''}>关键词</option>
                    <option value="regex" ${ruleData.rule_type === 'regex' ? 'selected' : ''}>正则表达式</option>
                    <option value="tag" ${ruleData.rule_type === 'tag' ? 'selected' : ''}>标签</option>
                    <option value="language" ${ruleData.rule_type === 'language' ? 'selected' : ''}>语言</option>
                </select>
            </div>

            <div class="form-group">
                <label for="match-type">匹配方式 *</label>
                <select id="match-type" name="match_type" class="form-control" required>
                    <option value="include" ${ruleData.match_type === 'include' ? 'selected' : ''}>通过（匹配的文章会通过）</option>
                    <option value="exclude" ${ruleData.match_type === 'exclude' ? 'selected' : ''}>过滤（匹配的文章会被过滤）</option>
                </select>
            </div>

            <div class="form-group">
                <label for="rule-pattern">模式 *</label>
                <input type="text" id="rule-pattern" name="pattern" class="form-control" required value="${App.escapeHtml(ruleData.pattern)}">
            </div>

            <div class="form-group">
                <label for="rule-priority">优先级</label>
                <input type="number" id="rule-priority" name="priority" class="form-control" value="${ruleData.priority}" min="0" max="100">
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="enabled" ${ruleData.enabled ? 'checked' : ''}>
                    启用此规则
                </label>
            </div>

            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.modal.hide()">取消</button>
                <button type="submit" class="btn btn-primary">更新规则</button>
            </div>
        </form>
    `;

    App.modal.show('编辑过滤规则', content);
}

async function handleFilterRuleSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const validation = App.form.validate(form);

    if (!validation.valid) {
        App.showToast('请修正表单中的错误', 'error');
        return;
    }

    const data = App.form.serialize(form);

    try {
        const response = await App.api.post('/api/filter-rules', data);

        if (response.success) {
            App.showToast('过滤规则创建成功', 'success');
            App.modal.hide();
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '创建过滤规则失败', 'error');
        }
    } catch (error) {
        console.error('创建过滤规则错误:', error);
        App.showToast('创建过滤规则失败', 'error');
    }
}

async function handleFilterRuleUpdate(event, ruleId) {
    event.preventDefault();
    const form = event.target;
    const validation = App.form.validate(form);

    if (!validation.valid) {
        App.showToast('请修正表单中的错误', 'error');
        return;
    }

    const data = App.form.serialize(form);

    try {
        const response = await App.api.put(`/api/filter-rules/${ruleId}`, data);

        if (response.success) {
            App.showToast('过滤规则更新成功', 'success');
            App.modal.hide();
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '更新过滤规则失败', 'error');
        }
    } catch (error) {
        console.error('更新过滤规则错误:', error);
        App.showToast('更新过滤规则失败', 'error');
    }
}

async function toggleFilterRule(ruleId) {
    try {
        const response = await App.api.post(`/api/filter-rules/${ruleId}/toggle`);

        if (response.success) {
            App.showToast(response.message, 'success');
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '切换状态失败', 'error');
        }
    } catch (error) {
        console.error('切换状态错误:', error);
        App.showToast('切换状态失败', 'error');
    }
}

async function deleteFilterRule(ruleId) {
    const ruleData = window.ruleData.find(r => r.id === ruleId);
    const ruleName = ruleData ? ruleData.name : '未知';

    App.modal.confirm(
        `确定要删除过滤规则 "${App.escapeHtml(ruleName)}" 吗？`,
        async () => {
            try {
                const response = await App.api.delete(`/api/filter-rules/${ruleId}`);

                if (response.success) {
                    App.showToast('过滤规则删除成功', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    App.showToast(response.error || '删除过滤规则失败', 'error');
                }
            } catch (error) {
                console.error('删除过滤规则错误:', error);
                App.showToast('删除过滤规则失败', 'error');
            }
        },
        { title: '删除过滤规则', danger: true }
    );
}

// ============================================================================
// Entry Batch Operations
// ============================================================================

function getSelectedEntryIds() {
    const checkboxes = document.querySelectorAll('.entry-checkbox:checked');
    return Array.from(checkboxes).map(cb => parseInt(cb.value));
}

async function batchDeleteEntries() {
    const entryIds = getSelectedEntryIds();

    if (entryIds.length === 0) {
        App.showToast('请至少选择一篇文章', 'error');
        return;
    }

    App.modal.confirm(
        `确定要删除选中的 ${entryIds.length} 篇文章吗？`,
        async () => {
            try {
                const response = await App.api.post('/api/entries/batch/delete', { entry_ids: entryIds });

                if (response.success) {
                    App.showToast(response.message || '文章删除成功', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    App.showToast(response.error || '删除文章失败', 'error');
                }
            } catch (error) {
                console.error('删除文章错误:', error);
                App.showToast('删除文章失败', 'error');
            }
        },
        { title: '删除文章', danger: true }
    );
}

async function batchFetchContent() {
    const entryIds = getSelectedEntryIds();

    if (entryIds.length === 0) {
        App.showToast('请至少选择一篇文章', 'error');
        return;
    }

    App.showToast('正在提取内容...这可能需要一些时间', 'info');

    try {
        const response = await App.api.post('/api/entries/batch/fetch-content', { entry_ids: entryIds });

        if (response.success) {
            const { success, failed } = response.data;
            App.showToast(`内容提取完成：${success} 篇成功，${failed} 篇失败`, success > 0 ? 'success' : 'error');
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '提取内容失败', 'error');
        }
    } catch (error) {
        console.error('提取内容错误:', error);
        App.showToast('提取内容失败', 'error');
    }
}

async function batchExtractKeywords() {
    const entryIds = getSelectedEntryIds();

    if (entryIds.length === 0) {
        App.showToast('请至少选择一篇文章', 'error');
        return;
    }

    App.showToast('正在提取关键词...这可能需要一些时间', 'info');

    try {
        const response = await App.api.post('/api/entries/batch/extract-keywords', { entry_ids: entryIds });

        if (response.success) {
            const { success, failed } = response.data;
            App.showToast(`关键词提取完成：${success} 篇成功，${failed} 篇失败`, success > 0 ? 'success' : 'error');
            setTimeout(() => location.reload(), 500);
        } else {
            App.showToast(response.error || '提取关键词失败', 'error');
        }
    } catch (error) {
        console.error('提取关键词错误:', error);
        App.showToast('提取关键词失败', 'error');
    }
}

async function batchSummarize() {
    const entryIds = getSelectedEntryIds();

    if (entryIds.length === 0) {
        App.showToast('请至少选择一篇文章', 'error');
        return;
    }

    App.modal.confirm(
        '为选中的文章生成摘要？AI 摘要可能需要一些时间。',
        async () => {
            App.showToast('正在生成摘要...这可能需要一些时间', 'info');

            try {
                const response = await App.api.post('/api/entries/batch/summarize', { entry_ids: entryIds, method: 'extractive' });

                if (response.success) {
                    const { success, failed } = response.data;
                    App.showToast(`摘要生成完成：${success} 篇成功，${failed} 篇失败`, success > 0 ? 'success' : 'error');
                    setTimeout(() => location.reload(), 500);
                } else {
                    App.showToast(response.error || '生成摘要失败', 'error');
                }
            } catch (error) {
                console.error('生成摘要错误:', error);
                App.showToast('生成摘要失败', 'error');
            }
        },
        { title: '生成摘要' }
    );
}

function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.entry-checkbox');
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
}
