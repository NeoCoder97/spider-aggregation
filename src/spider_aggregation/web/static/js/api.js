/**
 * MindWeaver API Client
 * Provides a unified interface for making API requests
 */

const API = {
    baseURL: '',

    /**
     * Build URL with query parameters
     */
    buildURL(path, params = {}) {
        const url = new URL(path, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });
        return url.toString();
    },

    /**
     * Parse JSON response
     */
    async parseResponse(response) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    },

    /**
     * Handle API error
     */
    handleError(error, response) {
        if (response) {
            return {
                success: false,
                error: error.message || 'Unknown error',
                status: response.status
            };
        }
        return {
            success: false,
            error: error.message || 'Network error'
        };
    },

    /**
     * GET request
     */
    async get(url, params = {}) {
        try {
            const fullUrl = this.buildURL(url, params);
            const response = await fetch(fullUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await this.parseResponse(response);
        } catch (error) {
            return this.handleError(error, error.response);
        }
    },

    /**
     * POST request
     */
    async post(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await this.parseResponse(response);
        } catch (error) {
            return this.handleError(error, error.response);
        }
    },

    /**
     * PUT request
     */
    async put(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await this.parseResponse(response);
        } catch (error) {
            return this.handleError(error, error.response);
        }
    },

    /**
     * PATCH request
     */
    async patch(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await this.parseResponse(response);
        } catch (error) {
            return this.handleError(error, error.response);
        }
    },

    /**
     * DELETE request
     */
    async delete(url) {
        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await this.parseResponse(response);
        } catch (error) {
            return this.handleError(error, error.response);
        }
    },

    // API Endpoints

    /**
     * Entries
     */
    entries: {
        list(params) {
            return API.get('/api/entries', params);
        },
        get(id) {
            return API.get(`/api/entries/${id}`);
        },
        update(id, data) {
            return API.put(`/api/entries/${id}`, data);
        },
        put(id, data) {
            // Alias for update - for backward compatibility
            return this.update(id, data);
        },
        delete(id) {
            return API.delete(`/api/entries/${id}`);
        },
        batchDelete(ids) {
            return API.post('/api/entries/batch/delete', { ids });
        },
        markRead(id) {
            return API.put(`/api/entries/${id}`, { is_read: true });
        },
        batchMarkRead(ids) {
            return API.post('/api/entries/batch/mark-read', { ids });
        },
        markUnread(id) {
            return API.put(`/api/entries/${id}`, { is_read: false });
        }
    },

    /**
     * Feeds
     */
    feeds: {
        list(params) {
            return API.get('/api/feeds', params);
        },
        get(id) {
            return API.get(`/api/feeds/${id}`);
        },
        create(data) {
            return API.post('/api/feeds', data);
        },
        update(id, data) {
            return API.put(`/api/feeds/${id}`, data);
        },
        delete(id) {
            return API.delete(`/api/feeds/${id}`);
        },
        toggle(id) {
            return API.patch(`/api/feeds/${id}/toggle`);
        },
        fetch(id) {
            return API.post(`/api/feeds/${id}/fetch`);
        },
        validate(data) {
            return API.post('/api/feeds/validate', data);
        }
    },

    /**
     * Categories
     */
    categories: {
        list() {
            return API.get('/api/categories');
        },
        get(id) {
            return API.get(`/api/categories/${id}`);
        },
        create(data) {
            return API.post('/api/categories', data);
        },
        update(id, data) {
            return API.put(`/api/categories/${id}`, data);
        },
        delete(id) {
            return API.delete(`/api/categories/${id}`);
        }
    },

    /**
     * Filter Rules
     */
    filterRules: {
        list() {
            return API.get('/api/filter-rules');
        },
        get(id) {
            return API.get(`/api/filter-rules/${id}`);
        },
        create(data) {
            return API.post('/api/filter-rules', data);
        },
        update(id, data) {
            return API.put(`/api/filter-rules/${id}`, data);
        },
        delete(id) {
            return API.delete(`/api/filter-rules/${id}`);
        }
    },

    /**
     * Scheduler
     */
    scheduler: {
        getStatus() {
            return API.get('/api/scheduler/status');
        },
        start() {
            return API.post('/api/scheduler/start');
        },
        stop() {
            return API.post('/api/scheduler/stop');
        },
        trigger() {
            return API.post('/api/scheduler/fetch-all');
        }
    },

    /**
     * Stats
     */
    stats: {
        get() {
            return API.get('/api/stats');
        }
    },

    /**
     * Settings
     */
    settings: {
        get() {
            return API.get('/api/settings');
        },
        update(data) {
            return API.put('/api/settings', data);
        }
    }
};

// Make API available globally
window.API = API;
