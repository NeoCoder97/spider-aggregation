/**
 * MindWeaver Data Table
 * Provides a reusable data table component with pagination, sorting, filtering
 */

class DataTable {
    constructor(options) {
        this.options = {
            container: null,
            columns: [],
            dataUrl: '',
            loadData: null, // Alternative to dataUrl - function to load data
            rowId: 'id',
            selectable: true,
            sortable: true,
            pagination: true,
            pageSize: 20,
            rowActions: null,
            batchActions: null,
            emptyMessage: '暂无数据',
            onRowClick: null,
            initialParams: {}
        };

        Object.assign(this.options, options);

        this.state = {
            data: [],
            page: 1,
            pageSize: this.options.pageSize,
            total: 0,
            sortColumn: null,
            sortDirection: null,
            selectedIds: new Set(),
            filters: {},
            loading: false
        };

        this.container = typeof this.options.container === 'string'
            ? document.querySelector(this.options.container)
            : this.options.container;

        if (!this.container) {
            console.error('DataTable: container not found');
            return;
        }

        this.init();
    }

    init() {
        this.render();
        this.loadData();
        this.attachEvents();
    }

    render() {
        const { columns, selectable, emptyMessage } = this.options;

        this.container.innerHTML = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            ${selectable ? '<th class="checkbox-cell"><input type="checkbox" id="select-all"></th>' : ''}
                            ${columns.map(col => `
                                <th class="${col.sortable !== false && this.options.sortable ? 'sortable' : ''}"
                                    data-column="${col.key}">
                                    ${col.label}
                                    ${col.sortable !== false && this.options.sortable ? `
                                        <svg class="sort-asc" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M7 14l5-5 5 5z"/></svg>
                                        <svg class="sort-desc" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M7 10l5 5 5-5z"/></svg>
                                    ` : ''}
                                </th>
                            `).join('')}
                            ${this.options.rowActions ? '<th class="actions-cell">操作</th>' : ''}
                        </tr>
                    </thead>
                    <tbody id="table-body">
                        <tr>
                            <td colspan="${columns.length + (selectable ? 1 : 0) + (this.options.rowActions ? 1 : 0)}" class="text-center">
                                <div class="empty-state">
                                    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>
                                    </svg>
                                    <p>加载中...</p>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                ${this.options.pagination ? `
                <div class="table-footer">
                    <div class="table-footer-left">
                        <span id="table-info">显示 0 - 0 条，共 0 条</span>
                    </div>
                    <div class="pagination" id="pagination"></div>
                </div>
                ` : ''}
            </div>
        `;

        this.tbody = this.container.querySelector('#table-body');
        this.pagination = this.container.querySelector('#pagination');
        this.tableInfo = this.container.querySelector('#table-info');
        this.selectAllCheckbox = this.container.querySelector('#select-all');
    }

    async loadData() {
        if (this.state.loading) return;

        // Save scroll position before loading
        const scrollTop = this._saveScrollPosition();

        this.state.loading = true;
        this.renderLoading();

        try {
            let response;

            if (this.options.loadData) {
                // Use custom data loader
                const data = await this.options.loadData({
                    page: this.state.page,
                    pageSize: this.state.pageSize,
                    sort: this.state.sortColumn,
                    direction: this.state.sortDirection,
                    filters: this.state.filters
                });
                response = { success: true, data: data.items, total: data.total };
            } else {
                // Use API URL
                const params = {
                    page: this.state.page,
                    page_size: this.state.pageSize,
                    ...this.options.initialParams,
                    ...this.state.filters
                };

                if (this.state.sortColumn) {
                    params.sort_by = this.state.sortColumn;
                    params.sort_direction = this.state.sortDirection || 'asc';
                }

                response = await API.get(this.options.dataUrl, params);
            }

            if (response.success || response.data) {
                this.state.data = response.data || response.items || [];
                this.state.total = response.total || 0;
                this.renderData();
                this.renderPagination();
                // Restore scroll position after rendering
                this._restoreScrollPosition(scrollTop);
            } else {
                this.renderError(response.error || '加载失败');
            }
        } catch (error) {
            console.error('DataTable: load error', error);
            this.renderError('加载失败');
        } finally {
            this.state.loading = false;
        }
    }

    _saveScrollPosition() {
        // Save window scroll position
        return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop;
    }

    _restoreScrollPosition(scrollTop) {
        // Use setTimeout to ensure DOM is fully rendered
        requestAnimationFrame(() => {
            window.scrollTo(0, scrollTop);
        });
    }

    renderLoading() {
        const colSpan = this.options.columns.length +
            (this.options.selectable ? 1 : 0) +
            (this.options.rowActions ? 1 : 0);

        this.tbody.innerHTML = `
            <tr>
                <td colspan="${colSpan}" class="text-center">
                    <div class="loading-state">
                        <div class="spinner"></div>
                    </div>
                </td>
            </tr>
        `;
    }

    renderError(message) {
        const colSpan = this.options.columns.length +
            (this.options.selectable ? 1 : 0) +
            (this.options.rowActions ? 1 : 0);

        this.tbody.innerHTML = `
            <tr>
                <td colspan="${colSpan}" class="text-center">
                    <div class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                        </svg>
                        <p>${message}</p>
                        <button class="btn btn-secondary" onclick="location.reload()">重新加载</button>
                    </div>
                </td>
            </tr>
        `;
    }

    renderData() {
        if (this.state.data.length === 0) {
            this.renderEmpty();
            return;
        }

        const { columns, selectable, rowActions, rowId } = this.options;

        this.tbody.innerHTML = this.state.data.map(row => {
            const id = row[rowId];
            const isSelected = this.state.selectedIds.has(id);

            return `
                <tr data-id="${id}" class="${isSelected ? 'selected' : ''}">
                    ${selectable ? `
                        <td class="checkbox-cell">
                            <input type="checkbox" class="row-checkbox" data-id="${id}" ${isSelected ? 'checked' : ''}>
                        </td>
                    ` : ''}
                    ${columns.map(col => `
                        <td>
                            ${col.render ? col.render(row, col) : this.renderCell(row, col)}
                        </td>
                    `).join('')}
                    ${rowActions ? `
                        <td class="actions-cell">
                            ${this.renderRowActions(row)}
                        </td>
                    ` : ''}
                </tr>
            `;
        }).join('');

        this.updateTableInfo();
    }

    renderEmpty() {
        const colSpan = this.options.columns.length +
            (this.options.selectable ? 1 : 0) +
            (this.options.rowActions ? 1 : 0);

        this.tbody.innerHTML = `
            <tr>
                <td colspan="${colSpan}" class="text-center">
                    <div class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>
                        </svg>
                        <p>${this.options.emptyMessage}</p>
                    </div>
                </td>
            </tr>
        `;
    }

    renderCell(row, col) {
        const value = row[col.key];
        if (value == null) return '-';

        // Format based on column type
        switch (col.type) {
            case 'date':
                return new Date(value).toLocaleString('zh-CN');
            case 'datetime':
                return new Date(value).toLocaleString('zh-CN');
            case 'boolean':
                return value ?
                    '<span class="badge badge-success">是</span>' :
                    '<span class="badge badge-default">否</span>';
            case 'status':
                const statusClass = value === 'active' ? 'success' : 'default';
                const statusText = value === 'active' ? '启用' : '禁用';
                return `<span class="badge badge-${statusClass}">${statusText}</span>`;
            default:
                const maxLength = col.maxLength || 100;
                if (String(value).length > maxLength) {
                    return `<span title="${value}">${String(value).substring(0, maxLength)}...</span>`;
                }
                return value;
        }
    }

    renderRowActions(row) {
        if (!this.options.rowActions) return '';

        return this.options.rowActions(row).map(action => {
            const icon = action.icon || '';
            const label = action.label || '';
            const className = action.danger ? 'action-btn danger' : 'action-btn';

            return `
                <button class="${className}" title="${label}" data-action="${action.name}">
                    ${icon}
                </button>
            `;
        }).join('');
    }

    renderPagination() {
        if (!this.pagination) return;

        const { page, pageSize, total } = this.state;
        const totalPages = Math.ceil(total / pageSize);
        const start = (page - 1) * pageSize + 1;
        const end = Math.min(page * pageSize, total);

        // Update info
        if (this.tableInfo) {
            this.tableInfo.textContent = total > 0
                ? `显示 ${start} - ${end} 条，共 ${total} 条`
                : '暂无数据';
        }

        if (totalPages <= 1) {
            this.pagination.innerHTML = '';
            return;
        }

        let html = '';

        // Previous button
        html += `
            <button ${page === 1 ? 'disabled' : ''} data-page="${page - 1}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                </svg>
            </button>
        `;

        // Page numbers
        const maxVisible = 7;
        let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            html += `<button data-page="1">1</button>`;
            if (startPage > 2) {
                html += `<span class="page-info">...</span>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<span class="page-info">...</span>`;
            }
            html += `<button data-page="${totalPages}">${totalPages}</button>`;
        }

        // Next button
        html += `
            <button ${page === totalPages ? 'disabled' : ''} data-page="${page + 1}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                </svg>
            </button>
        `;

        this.pagination.innerHTML = html;
    }

    updateTableInfo() {
        if (!this.tableInfo) return;

        const { page, pageSize, total } = this.state;
        const start = total > 0 ? (page - 1) * pageSize + 1 : 0;
        const end = Math.min(page * pageSize, total);

        this.tableInfo.textContent = total > 0
            ? `显示 ${start} - ${end} 条，共 ${total} 条`
            : '暂无数据';
    }

    attachEvents() {
        // Row selection
        this.container.addEventListener('change', (e) => {
            if (e.target.classList.contains('row-checkbox')) {
                this.toggleRow(parseInt(e.target.dataset.id));
            }
        });

        // Select all
        this.selectAllCheckbox?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.selectAll();
            } else {
                this.clearSelection();
            }
        });

        // Row click
        if (this.options.onRowClick) {
            this.tbody.addEventListener('click', (e) => {
                const tr = e.target.closest('tr');
                if (tr && !e.target.matches('button, a, input')) {
                    const id = parseInt(tr.dataset.id);
                    this.options.onRowClick(id, this.state.data.find(r => r[this.options.rowId] === id));
                }
            });
        }

        // Pagination
        this.pagination?.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-page]');
            if (btn && !btn.disabled) {
                this.goToPage(parseInt(btn.dataset.page));
            }
        });

        // Sorting
        this.container.addEventListener('click', (e) => {
            const th = e.target.closest('th.sortable');
            if (th) {
                const column = th.dataset.column;
                this.sort(column);
            }
        });

        // Row actions
        this.tbody?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (btn) {
                const action = btn.dataset.action;
                const tr = btn.closest('tr');
                const id = parseInt(tr.dataset.id);
                const row = this.state.data.find(r => r[this.options.rowId] === id);
                this.handleRowAction(action, id, row);
            }
        });
    }

    handleRowAction(action, id, row) {
        const actionConfig = this.options.rowActions?.(row).find(a => a.name === action);
        if (actionConfig?.onClick) {
            // Execute the onClick function (stored as string or function)
            if (typeof actionConfig.onClick === 'function') {
                actionConfig.onClick(row, action);
            } else if (typeof actionConfig.onClick === 'string') {
                // Execute string as JavaScript code
                new Function(actionConfig.onClick)();
            }
        }
    }

    toggleRow(id) {
        if (this.state.selectedIds.has(id)) {
            this.state.selectedIds.delete(id);
        } else {
            this.state.selectedIds.add(id);
        }
        this.updateRowSelection();
    }

    toggleSelectAll() {
        if (this.state.selectedIds.size === this.state.data.length) {
            this.clearSelection();
        } else {
            this.selectAll();
        }
    }

    selectAll() {
        this.state.data.forEach(row => {
            this.state.selectedIds.add(row[this.options.rowId]);
        });
        this.updateRowSelection();
    }

    clearSelection() {
        this.state.selectedIds.clear();
        this.updateRowSelection();
    }

    updateRowSelection() {
        // Update checkboxes
        this.container.querySelectorAll('.row-checkbox').forEach(checkbox => {
            const id = parseInt(checkbox.dataset.id);
            checkbox.checked = this.state.selectedIds.has(id);
        });

        // Update row styles
        this.tbody.querySelectorAll('tr').forEach(tr => {
            const id = parseInt(tr.dataset.id);
            tr.classList.toggle('selected', this.state.selectedIds.has(id));
        });

        // Update select all checkbox
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.checked = this.state.data.length > 0 &&
                this.state.selectedIds.size === this.state.data.length;
        }

        // Trigger selection change callback
        if (this.options.onSelectionChange) {
            this.options.onSelectionChange(Array.from(this.state.selectedIds));
        }
    }

    sort(column) {
        if (this.state.sortColumn === column) {
            // Toggle direction
            this.state.sortDirection = this.state.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortColumn = column;
            this.state.sortDirection = 'asc';
        }

        this.updateSortIndicators();
        this.loadData();
    }

    updateSortIndicators() {
        this.container.querySelectorAll('th.sortable').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
            th.querySelector('.sort-asc')?.setAttribute('style', 'display:none');
            th.querySelector('.sort-desc')?.setAttribute('style', 'display:none');
        });

        const currentTh = this.container.querySelector(`th[data-column="${this.state.sortColumn}"]`);
        if (currentTh) {
            currentTh.classList.add(`sort-${this.state.sortDirection}`);
            currentTh.querySelector(`.sort-${this.state.sortDirection}`)?.setAttribute('style', 'display:inline-block');
        }
    }

    goToPage(page) {
        this.state.page = page;
        this.clearSelection();
        this.loadData();
    }

    refresh() {
        this.clearSelection();
        this.loadData();
    }

    setFilters(filters) {
        this.state.filters = filters;
        this.state.page = 1;
        this.loadData();
    }

    getSelectedIds() {
        return Array.from(this.state.selectedIds);
    }

    getSelectedRows() {
        return this.state.data.filter(row =>
            this.state.selectedIds.has(row[this.options.rowId])
        );
    }
}

// Make DataTable available globally
window.DataTable = DataTable;
