// MindWeaver - Web UI JavaScript

// ============================================================================
// App Namespace
// ============================================================================

const App = {};

// ============================================================================
// API Client
// ============================================================================

App.api = {
    /**
     * Make a GET request
     */
    get: async function(url, data = null) {
        const options = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            const params = new URLSearchParams(data).toString();
            url += (url.includes('?') ? '&' : '?') + params;
        }

        const response = await fetch(url, options);
        return await response.json();
    },

    /**
     * Make a POST request
     */
    post: async function(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        return await response.json();
    },

    /**
     * Make a PUT request
     */
    put: async function(url, data = {}) {
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        return await response.json();
    },

    /**
     * Make a DELETE request
     */
    delete: async function(url) {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        return await response.json();
    },
};

// ============================================================================
// Toast Notification System
// ============================================================================

App.showToast = function(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = {
        success: '✓',
        error: '✕',
        info: 'ℹ',
    }[type] || 'ℹ';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${App.escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto remove after duration
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, duration);
};

App.hideToast = function() {
    const container = document.getElementById('toast-container');
    if (container) {
        container.innerHTML = '';
    }
};

// ============================================================================
// Modal Manager
// ============================================================================

App.modal = {
    show: function(title, content, options = {}) {
        const overlay = document.getElementById('modal-container');
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        if (!overlay || !titleEl || !bodyEl) {
            console.error('Modal elements not found');
            return;
        }

        titleEl.textContent = title;
        bodyEl.innerHTML = content;
        overlay.style.display = 'flex';

        // Add footer with actions if provided
        if (options.actions) {
            const footer = document.createElement('div');
            footer.className = 'modal-footer';
            footer.innerHTML = options.actions;
            bodyEl.parentElement.appendChild(footer);
        }

        // Close on overlay click
        overlay.onclick = function(e) {
            if (e.target === overlay) {
                App.modal.hide();
            }
        };
    },

    hide: function() {
        const overlay = document.getElementById('modal-container');
        if (overlay) {
            overlay.style.display = 'none';

            // Remove footer if exists
            const footer = overlay.querySelector('.modal-footer');
            if (footer) footer.remove();
        }
    },

    confirm: function(message, onConfirm, options = {}) {
        const content = `
            <p>${App.escapeHtml(message)}</p>
            ${options.details ? `<p class="text-muted">${App.escapeHtml(options.details)}</p>` : ''}
        `;

        const actions = `
            <button type="button" class="btn btn-secondary" onclick="App.modal.hide()">Cancel</button>
            <button type="button" class="btn ${options.danger ? 'btn-danger' : 'btn-primary'}" id="confirm-btn">Confirm</button>
        `;

        this.show(options.title || 'Confirm', content, { actions });

        document.getElementById('confirm-btn').onclick = function() {
            App.modal.hide();
            if (onConfirm) onConfirm();
        };
    },
};

// ============================================================================
// Form Helpers
// ============================================================================

App.form = {
    serialize: function(form) {
        const formData = new FormData(form);
        const data = {};
        for (const [key, value] of formData.entries()) {
            // Handle checkboxes - return true for checked
            if (form.querySelector(`[name="${key}"][type="checkbox"]`)) {
                data[key] = true;
            } else {
                data[key] = value;
            }
        }
        // Handle unchecked checkboxes - add them as false
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (!data.hasOwnProperty(checkbox.name)) {
                data[checkbox.name] = false;
            }
        });
        return data;
    },

    validate: function(form) {
        const errors = [];
        const requiredFields = form.querySelectorAll('[required]');

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                errors.push(`${field.previousElementSibling?.textContent || field.name} is required`);
                field.classList.add('error');
            } else {
                field.classList.remove('error');
            }
        });

        // Validate email format
        const emailField = form.querySelector('input[type="email"]');
        if (emailField && emailField.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailField.value)) {
                errors.push('Please enter a valid email address');
                emailField.classList.add('error');
            }
        }

        // Validate URL format
        const urlField = form.querySelector('input[type="url"]');
        if (urlField && urlField.value) {
            try {
                new URL(urlField.value);
            } catch {
                errors.push('Please enter a valid URL');
                urlField.classList.add('error');
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors,
        };
    },

    showErrors: function(form, errors) {
        // Clear existing errors
        form.querySelectorAll('.form-error').forEach(el => el.remove());

        errors.forEach(error => {
            const errorEl = document.createElement('div');
            errorEl.className = 'form-error';
            errorEl.textContent = error;
            errorEl.style.color = 'var(--error-color)';
            errorEl.style.fontSize = '0.75rem';
            errorEl.style.marginTop = '0.25rem';
        });
    },
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Normalize ISO date string from backend to ensure UTC interpretation.
 * Backend returns naive ISO strings like "2025-01-15T10:30:00" without timezone info.
 * JavaScript treats these as local time, but they are actually UTC.
 * This function appends 'Z' if no timezone info is present.
 */
App.normalizeUtcDate = function(dateStr) {
    if (!dateStr) return dateStr;
    // Check if the date string already has timezone info (Z, +08:00, -05:00, etc.)
    // Match: ends with Z, or +/-HH:MM, or +/-HHMM
    const hasTimezone = /(Z|[+-]\d{2}:\d{2}|[+-]\d{4})$/i.test(dateStr);
    if (!hasTimezone) {
        // No timezone info, treat as UTC by appending 'Z'
        return dateStr + 'Z';
    }
    return dateStr;
};

App.formatDate = function(dateStr) {
    const normalizedDateStr = App.normalizeUtcDate(dateStr);
    const date = new Date(normalizedDateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
};

App.formatRelativeTime = function(dateStr) {
    const normalizedDateStr = App.normalizeUtcDate(dateStr);
    const date = new Date(normalizedDateStr);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 7) {
        return App.formatDate(dateStr);
    } else if (days > 0) {
        return `${days}天前`;
    } else if (hours > 0) {
        return `${hours}小时前`;
    } else if (minutes > 0) {
        return `${minutes}分钟前`;
    } else {
        return '刚刚';
    }
};

App.truncate = function(text, length) {
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
};

App.escapeHtml = function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

App.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// ============================================================================
// Initialize when DOM is ready
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('MindWeaver Web UI loaded');

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    // Add loading states to buttons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            if (this.tagName === 'A' && !this.hasAttribute('target')) {
                this.style.opacity = '0.7';
            }
        });
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            App.modal.hide();
        }
    });
});

// ============================================================================
// Export for potential use in templates
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = App;
}
