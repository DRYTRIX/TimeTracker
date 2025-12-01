/**
 * Enhanced UI JavaScript
 * Comprehensive UX improvements for TimeTracker
 */

// ============================================
// ENHANCED TABLE FUNCTIONALITY
// ============================================
class EnhancedTable {
    constructor(tableElement) {
        this.table = tableElement;
        this.selectedRows = new Set();
        this.sortState = {};
        this.init();
    }

    init() {
        this.table.classList.add('enhanced-table');
        this.initSorting();
        this.initBulkSelect();
        this.initColumnResize();
        this.initInlineEdit();
    }

    initSorting() {
        const headers = this.table.querySelectorAll('thead th[data-sortable]');
        headers.forEach((header, index) => {
            header.classList.add('sortable');
            header.addEventListener('click', () => this.sortColumn(index, header));
        });
    }

    sortColumn(columnIndex, header) {
        const tbody = this.table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Determine sort direction
        let direction = 'asc';
        if (header.classList.contains('sorted-asc')) {
            direction = 'desc';
        }
        
        // Clear all sort indicators
        this.table.querySelectorAll('th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        
        // Add sort indicator
        header.classList.add(`sorted-${direction}`);
        
        // Sort rows
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex]?.textContent.trim() || '';
            const bValue = b.cells[columnIndex]?.textContent.trim() || '';
            
            // Try numeric comparison first
            const aNum = parseFloat(aValue.replace(/[^0-9.-]/g, ''));
            const bNum = parseFloat(bValue.replace(/[^0-9.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            return direction === 'asc' 
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        });
        
        // Reorder rows
        rows.forEach(row => tbody.appendChild(row));
    }

    initBulkSelect() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;
        
        // Add bulk select checkbox to header
        const thead = this.table.querySelector('thead tr');
        const selectAllTh = document.createElement('th');
        selectAllTh.className = 'px-4 py-3 w-12';
        selectAllTh.innerHTML = '<input type="checkbox" class="select-all-checkbox rounded" />';
        thead.insertBefore(selectAllTh, thead.firstChild);
        
        // Add checkboxes to each row
        tbody.querySelectorAll('tr').forEach((row, index) => {
            const selectTd = document.createElement('td');
            selectTd.className = 'px-4 py-3';
            selectTd.innerHTML = `<input type="checkbox" class="row-checkbox rounded" data-row-index="${index}" />`;
            row.insertBefore(selectTd, row.firstChild);
        });
        
        // Select all functionality
        const selectAllCheckbox = thead.querySelector('.select-all-checkbox');
        selectAllCheckbox?.addEventListener('change', (e) => {
            const checkboxes = tbody.querySelectorAll('.row-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                this.toggleRowSelection(cb.closest('tr'), e.target.checked);
            });
            this.updateBulkActionsBar();
        });
        
        // Individual row selection
        tbody.querySelectorAll('.row-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.toggleRowSelection(e.target.closest('tr'), e.target.checked);
                this.updateBulkActionsBar();
            });
        });
    }

    toggleRowSelection(row, selected) {
        if (selected) {
            row.classList.add('selected');
            this.selectedRows.add(row);
        } else {
            row.classList.remove('selected');
            this.selectedRows.delete(row);
        }
    }

    updateBulkActionsBar() {
        const count = this.selectedRows.size;
        let bar = document.querySelector('.bulk-actions-bar');
        
        if (count > 0) {
            if (!bar) {
                bar = this.createBulkActionsBar();
                document.body.appendChild(bar);
            }
            bar.querySelector('.selection-count').textContent = count;
            setTimeout(() => bar.classList.add('show'), 10);
        } else if (bar) {
            bar.classList.remove('show');
            setTimeout(() => bar.remove(), 300);
        }
    }

    createBulkActionsBar() {
        const bar = document.createElement('div');
        bar.className = 'bulk-actions-bar';
        bar.innerHTML = `
            <span class="text-sm font-medium">
                <span class="selection-count">0</span> items selected
            </span>
            <button class="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors" onclick="bulkDelete()">
                <i class="fas fa-trash mr-1"></i> Delete
            </button>
            <button class="px-3 py-1.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors" onclick="bulkExport()">
                <i class="fas fa-download mr-1"></i> Export
            </button>
            <button class="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" onclick="clearSelection()">
                Cancel
            </button>
        `;
        return bar;
    }

    initColumnResize() {
        const headers = this.table.querySelectorAll('thead th');
        headers.forEach((header, index) => {
            if (index === headers.length - 1) return; // Skip last column
            
            const resizer = document.createElement('div');
            resizer.className = 'column-resizer';
            header.style.position = 'relative';
            header.appendChild(resizer);
            
            let startX, startWidth;
            
            resizer.addEventListener('mousedown', (e) => {
                startX = e.pageX;
                startWidth = header.offsetWidth;
                resizer.classList.add('resizing');
                document.addEventListener('mousemove', resize);
                document.addEventListener('mouseup', stopResize);
                e.preventDefault();
            });
            
            const resize = (e) => {
                const width = startWidth + (e.pageX - startX);
                header.style.width = width + 'px';
            };
            
            const stopResize = () => {
                resizer.classList.remove('resizing');
                document.removeEventListener('mousemove', resize);
                document.removeEventListener('mouseup', stopResize);
            };
        });
    }

    initInlineEdit() {
        this.table.querySelectorAll('[data-editable]').forEach(cell => {
            cell.style.cursor = 'pointer';
            cell.addEventListener('dblclick', () => this.makeEditable(cell));
        });
    }

    makeEditable(cell) {
        const value = cell.textContent.trim();
        const input = document.createElement('input');
        input.type = 'text';
        input.value = value;
        input.className = 'inline-edit-input';
        
        cell.textContent = '';
        cell.appendChild(input);
        input.focus();
        input.select();
        
        const save = () => {
            const newValue = input.value;
            cell.textContent = newValue;
            // Trigger save event
            const event = new CustomEvent('cellEdited', {
                detail: { cell, oldValue: value, newValue }
            });
            this.table.dispatchEvent(event);
        };
        
        input.addEventListener('blur', save);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') {
                cell.textContent = value;
            }
        });
    }

    getSelectedRowData() {
        return Array.from(this.selectedRows).map(row => {
            const cells = Array.from(row.cells).slice(1); // Skip checkbox column
            return cells.map(cell => cell.textContent.trim());
        });
    }
}

// ============================================
// LIVE SEARCH FUNCTIONALITY
// ============================================
class LiveSearch {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            debounceMs: 300,
            minChars: 2,
            onSearch: null,
            showResults: true,
            ...options
        };
        this.debounceTimer = null;
        this.init();
    }

    init() {
        const container = document.createElement('div');
        container.className = 'search-container relative';
        this.input.parentNode.insertBefore(container, this.input);
        container.appendChild(this.input);
        
        // Add search icon
        const icon = document.createElement('i');
        icon.className = 'fas fa-search search-icon absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400';
        container.appendChild(icon);
        
        // Add clear button
        const clearBtn = document.createElement('i');
        clearBtn.className = 'fas fa-times search-clear absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 cursor-pointer';
        container.appendChild(clearBtn);
        
        // Add input padding
        this.input.classList.add('search-input', 'pl-10', 'pr-10');
        
        // Create results dropdown
        if (this.options.showResults) {
            this.resultsDropdown = document.createElement('div');
            this.resultsDropdown.className = 'search-results-dropdown';
            container.appendChild(this.resultsDropdown);
        }
        
        // Event listeners
        this.input.addEventListener('input', (e) => this.handleInput(e));
        clearBtn.addEventListener('click', () => this.clear());
        
        // Show/hide clear button
        this.input.addEventListener('input', () => {
            clearBtn.classList.toggle('show', this.input.value.length > 0);
        });
        
        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target) && this.resultsDropdown) {
                this.resultsDropdown.classList.remove('show');
            }
        });
    }

    handleInput(e) {
        clearTimeout(this.debounceTimer);
        
        const query = e.target.value.trim();
        
        if (query.length < this.options.minChars) {
            if (this.resultsDropdown) {
                this.resultsDropdown.classList.remove('show');
            }
            return;
        }
        
        this.debounceTimer = setTimeout(() => {
            if (this.options.onSearch) {
                this.options.onSearch(query, (results) => {
                    if (this.options.showResults) {
                        this.displayResults(results);
                    }
                });
            }
        }, this.options.debounceMs);
    }

    displayResults(results) {
        if (!this.resultsDropdown) return;
        
        if (results.length === 0) {
            this.resultsDropdown.innerHTML = '<div class="p-4 text-center text-gray-500">No results found</div>';
        } else {
            this.resultsDropdown.innerHTML = results.map(result => `
                <a href="${result.url}" class="search-result-item block">
                    <div class="font-medium text-gray-900 dark:text-gray-100">${result.title}</div>
                    ${result.subtitle ? `<div class="text-sm text-gray-500">${result.subtitle}</div>` : ''}
                </a>
            `).join('');
        }
        
        this.resultsDropdown.classList.add('show');
    }

    clear() {
        this.input.value = '';
        this.input.focus();
        if (this.resultsDropdown) {
            this.resultsDropdown.classList.remove('show');
        }
        if (this.options.onSearch) {
            this.options.onSearch('', () => {});
        }
    }
}

// ============================================
// FILTER MANAGEMENT
// ============================================
class FilterManager {
    constructor(formElement) {
        this.form = formElement;
        this.activeFilters = new Map();
        this.submitTimeout = null;
        this.inputTimeouts = new Map();
        this.init();
    }

    init() {
        // Create filter chips container
        this.chipsContainer = document.createElement('div');
        this.chipsContainer.className = 'filter-chips-container';
        this.form.parentNode.insertBefore(this.chipsContainer, this.form.nextSibling);
        
        // Monitor form changes - auto-submit on dropdown changes
        this.form.querySelectorAll('select').forEach(select => {
            select.addEventListener('change', () => {
                this.updateFilters();
                // Auto-submit on dropdown changes
                this.submitForm();
            });
        });
        
        // Monitor text input fields (search fields) - auto-submit with debouncing
        this.inputTimeouts = new Map();
        this.form.querySelectorAll('input[type="text"], input[type="search"]').forEach(input => {
            input.addEventListener('input', (e) => {
                // Update filter chips immediately for visual feedback
                this.updateFilters();
                
                // Debounce the actual form submission
                const timeoutKey = input.name || input.id;
                if (this.inputTimeouts.has(timeoutKey)) {
                    clearTimeout(this.inputTimeouts.get(timeoutKey));
                }
                
                // Submit after user stops typing (500ms delay)
                const timeout = setTimeout(() => {
                    this.submitForm();
                    this.inputTimeouts.delete(timeoutKey);
                }, 500);
                
                this.inputTimeouts.set(timeoutKey, timeout);
            });
            
            // Also submit on Enter key
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    // Clear any pending timeout
                    const timeoutKey = input.name || input.id;
                    if (this.inputTimeouts.has(timeoutKey)) {
                        clearTimeout(this.inputTimeouts.get(timeoutKey));
                        this.inputTimeouts.delete(timeoutKey);
                    }
                    // Submit immediately
                    this.submitForm();
                }
            });
        });
        
        // Listen to form submit - prevent default and use AJAX instead
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.updateFilters();
            this.submitForm();
        });
        
        // Add quick filters
        this.addQuickFilters();
        
        // Initial render
        this.updateFilters();
    }

    addQuickFilters() {
        const quickFilters = this.form.dataset.quickFilters;
        if (!quickFilters) return;
        
        const filters = JSON.parse(quickFilters);
        const quickFiltersDiv = document.createElement('div');
        quickFiltersDiv.className = 'quick-filters';
        
        filters.forEach(filter => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quick-filter-btn';
            btn.textContent = filter.label;
            btn.addEventListener('click', () => this.applyQuickFilter(filter));
            quickFiltersDiv.appendChild(btn);
        });
        
        this.form.parentNode.insertBefore(quickFiltersDiv, this.form);
    }

    applyQuickFilter(filter) {
        Object.entries(filter.values).forEach(([key, value]) => {
            const input = this.form.querySelector(`[name="${key}"]`);
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = value;
                } else {
                    input.value = value;
                }
            }
        });
        this.form.dispatchEvent(new Event('submit', { bubbles: true }));
    }

    updateFilters() {
        this.activeFilters.clear();
        const formData = new FormData(this.form);
        
        for (const [key, value] of formData.entries()) {
            if (value && value !== 'all' && value !== '') {
                const input = this.form.querySelector(`[name="${key}"]`);
                const label = input?.labels?.[0]?.textContent || key;
                this.activeFilters.set(key, { label, value });
            }
        }
        
        this.renderChips();
    }

    renderChips() {
        this.chipsContainer.innerHTML = '';
        
        if (this.activeFilters.size === 0) {
            this.chipsContainer.style.display = 'none';
            return;
        }
        
        this.chipsContainer.style.display = 'flex';
        
        this.activeFilters.forEach((filter, key) => {
            const chip = document.createElement('span');
            chip.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary/10 dark:bg-primary/20 text-primary border border-primary/20 dark:border-primary/30';
            chip.innerHTML = `
                <span class="font-medium">${filter.label}:</span>
                <span class="ml-1">${filter.value}</span>
                <button type="button" class="ml-2 hover:text-red-600 transition-colors" data-remove-filter="${key}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            this.chipsContainer.appendChild(chip);
        });
        
        // Add clear all button
        if (this.activeFilters.size > 0) {
            const clearAll = document.createElement('button');
            clearAll.type = 'button';
            clearAll.className = 'text-sm text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors';
            clearAll.innerHTML = '<i class="fas fa-times-circle mr-1"></i> Clear all';
            clearAll.addEventListener('click', () => this.clearAll());
            this.chipsContainer.appendChild(clearAll);
        }
        
        // Add remove listeners
        this.chipsContainer.querySelectorAll('[data-remove-filter]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const key = e.currentTarget.dataset.removeFilter;
                this.removeFilter(key);
            });
        });
    }

    removeFilter(key) {
        const input = this.form.querySelector(`[name="${key}"]`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else if (input.tagName === 'SELECT') {
                // For select elements, set to first option (usually "All" or empty)
                if (input.options.length > 0) {
                    input.value = input.options[0].value;
                } else {
                    input.value = '';
                }
            } else {
                input.value = '';
            }
            // Update filters and submit
            this.updateFilters();
            this.submitForm();
        }
    }

    clearAll() {
        // Reset all form fields
        this.form.reset();
        
        // For select elements, ensure they're set to their default (first option)
        this.form.querySelectorAll('select').forEach(select => {
            if (select.options.length > 0) {
                select.value = select.options[0].value;
            }
        });
        
        // Explicitly set status to "all" to show all projects
        const statusSelect = this.form.querySelector('[name="status"]');
        if (statusSelect) {
            statusSelect.value = 'all';
        }
        
        // Clear all text inputs
        this.form.querySelectorAll('input[type="text"], input[type="search"]').forEach(input => {
            input.value = '';
        });
        
        // Update filters and submit
        this.updateFilters();
        this.submitForm();
    }
    
    submitForm() {
        // Ensure the form can be submitted (remove any disabled state from submit button)
        const submitButton = this.form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.style.display = '';
            submitButton.style.visibility = '';
            submitButton.style.opacity = '';
        }
        
        // For GET forms (filter forms), use AJAX to avoid page reload
        if (this.form.method.toUpperCase() === 'GET') {
            // Use a small delay to prevent rapid-fire submissions
            if (this.submitTimeout) {
                clearTimeout(this.submitTimeout);
            }
            this.submitTimeout = setTimeout(() => {
                this.submitViaAjax();
            }, 100);
        } else {
            // For POST forms, dispatch submit event (validation will handle it)
            this.form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
    }
    
    submitViaAjax() {
        // Build query string from form data
        const formData = new FormData(this.form);
        const params = new URLSearchParams();
        
        // Check if this is the time entries form - handle it differently
        const isTimeEntriesForm = this.form.id === 'timeEntriesFilterForm';
        
        // Always include status - default to "all" if not set or empty (for projects page)
        const statusSelect = this.form.querySelector('[name="status"]');
        let statusValue = statusSelect ? statusSelect.value : null;
        // If status is empty or null and we're not on time entries, default to "all"
        if (!isTimeEntriesForm && (!statusValue || statusValue === '')) {
            statusValue = 'all';
        }
        if (statusValue && statusValue !== '') {
            params.append('status', statusValue);
        }
        
        // Process other form fields
        for (const [key, value] of formData.entries()) {
            // Skip status as we already handled it
            if (key === 'status' && statusValue) {
                continue;
            }
            // Include search if it has a value (trimmed)
            else if (key === 'search') {
                const trimmedValue = String(value || '').trim();
                if (trimmedValue) {
                    params.append(key, trimmedValue);
                }
            }
            // Include other fields if they have values
            else if (value && String(value).trim() !== '') {
                params.append(key, String(value).trim());
            }
        }
        
        // Get the form action or current URL
        const url = this.form.action || window.location.pathname;
        const queryString = params.toString();
        // Build full URL - for projects page, always include status parameter if query is empty
        let fullUrl;
        if (!isTimeEntriesForm && !queryString) {
            fullUrl = `${url}?status=all`;
        } else if (queryString) {
            fullUrl = `${url}?${queryString}`;
        } else {
            fullUrl = url;
        }
        
        // Debug: log what we're sending
        console.log('Filter URL:', fullUrl);
        console.log('Search value:', params.get('search'));
        console.log('Status value:', params.get('status'));
        
        // Update URL without page reload
        if (window.history && window.history.pushState) {
            window.history.pushState({}, '', fullUrl);
        }
        
        // Detect container type - check for time entries first, then projects
        const timeEntriesContainer = document.getElementById('timeEntriesListContainer');
        const projectsContainer = document.getElementById('projectsListContainer');
        const projectsWrapper = document.getElementById('projectsContainer');
        const container = timeEntriesContainer || projectsContainer || projectsWrapper;
        
        if (container) {
            container.style.opacity = '0.5';
            container.style.pointerEvents = 'none';
        }
        
        // Fetch filtered results via AJAX
        fetch(fullUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'text/html'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
            }
            return response.text();
        })
        .then(html => {
            // Handle time entries container
            if (timeEntriesContainer) {
                const trimmedHtml = html.trim();
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = trimmedHtml;
                
                const newContainer = tempDiv.querySelector('#timeEntriesListContainer');
                
                if (newContainer) {
                    timeEntriesContainer.innerHTML = newContainer.innerHTML;
                } else {
                    // Fallback: try to extract content using regex
                    const match = trimmedHtml.match(/<div[^>]*id=["']timeEntriesListContainer["'][^>]*>([\s\S]*?)<\/div>\s*$/);
                    if (match && match[1]) {
                        timeEntriesContainer.innerHTML = match[1];
                    } else {
                        timeEntriesContainer.innerHTML = html;
                    }
                }
                
                // Re-initialize bulk actions after content update
                if (typeof updateBulkActions === 'function') {
                    updateBulkActions();
                }
                
                // Update filter chips after content update
                this.updateFilters();
                return;
            }
            
            // Handle projects container (original logic)
            // Debug: log response length
            console.log('Response HTML length:', html.length);
            console.log('Response preview:', html.substring(0, 200));
            // Update the projects list container
            let targetContainer = projectsContainer;
            
            if (!targetContainer && projectsWrapper) {
                // If we don't have the inner container, try to find or create it
                let innerContainer = projectsWrapper.querySelector('#projectsListContainer');
                if (!innerContainer) {
                    innerContainer = document.createElement('div');
                    innerContainer.id = 'projectsListContainer';
                    projectsWrapper.insertBefore(innerContainer, projectsWrapper.firstChild);
                }
                if (innerContainer) {
                    targetContainer = innerContainer;
                }
            }
            
            if (targetContainer) {
                const trimmedHtml = html.trim();
                
                // The partial template returns: <div id="projectsListContainer">...</div>
                // Extract the innerHTML from this div using a simple approach
                
                // Create a temporary container and parse the HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = trimmedHtml;
                
                // Find the projectsListContainer in the parsed HTML
                const responseContainer = tempDiv.querySelector('#projectsListContainer');
                
                if (responseContainer) {
                    // Use the innerHTML directly
                    targetContainer.innerHTML = responseContainer.innerHTML;
                } else {
                    // If the response IS the container (no wrapper), extract content
                    // Try regex to get content between opening and closing div tags
                    const match = trimmedHtml.match(/<div[^>]*id=["']projectsListContainer["'][^>]*>([\s\S]*?)<\/div>\s*$/);
                    if (match && match[1] !== undefined) {
                        targetContainer.innerHTML = match[1];
                    } else {
                        // If all else fails, try to find the first child element
                        const firstChild = tempDiv.firstElementChild;
                        if (firstChild && firstChild.id === 'projectsListContainer') {
                            targetContainer.innerHTML = firstChild.innerHTML;
                        } else {
                            // Last resort: replace entire container
                            targetContainer.outerHTML = trimmedHtml;
                            // Re-find the container after replacement
                            const newContainer = document.getElementById('projectsListContainer');
                            if (newContainer) targetContainer = newContainer;
                        }
                    }
                }
                
                // Re-initialize any scripts that need to run after content update
                if (window.setViewMode) {
                    const savedMode = localStorage.getItem('projectsViewMode') || 'list';
                    setViewMode(savedMode);
                }
                
                // Update filter chips after content update
                this.updateFilters();
            } else {
                console.error('Could not find projectsListContainer or projectsContainer element');
            }
        })
        .catch(error => {
            console.error('Error fetching filtered results:', error);
            // Fallback to regular form submission on error
            if (container) {
                container.style.opacity = '';
                container.style.pointerEvents = '';
            }
            // Optionally show an error message
            if (window.toastManager) {
                window.toastManager.show('Failed to filter results. Please try again.', 'error');
            }
        })
        .finally(() => {
            // Remove loading indicator
            if (container) {
                container.style.opacity = '';
                container.style.pointerEvents = '';
            }
        });
    }
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = {
            success: 'fa-check',
            error: 'fa-times',
            warning: 'fa-exclamation',
            info: 'fa-info'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas ${icons[type]}"></i>
            </div>
            <div class="flex-1">
                <p class="font-medium text-gray-900 dark:text-gray-100">${message}</p>
            </div>
            <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        this.container.appendChild(toast);
        
        // Close button
        toast.querySelector('button').addEventListener('click', () => this.remove(toast));
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }
        
        return toast;
    }

    remove(toast) {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// ============================================
// UNDO/REDO FUNCTIONALITY
// ============================================
class UndoManager {
    constructor() {
        this.history = [];
        this.currentIndex = -1;
    }

    addAction(action, undoFn, data) {
        this.history = this.history.slice(0, this.currentIndex + 1);
        this.history.push({ action, undoFn, data, timestamp: Date.now() });
        this.currentIndex++;
        
        this.showUndoBar(action);
    }

    undo() {
        if (this.currentIndex < 0) return;
        
        const item = this.history[this.currentIndex];
        if (item.undoFn) {
            item.undoFn(item.data);
        }
        this.currentIndex--;
        
        window.toastManager?.success('Action undone');
    }

    showUndoBar(action) {
        let bar = document.querySelector('.undo-bar');
        if (!bar) {
            bar = document.createElement('div');
            bar.className = 'undo-bar';
            bar.innerHTML = `
                <span class="undo-message"></span>
                <button class="px-3 py-1 bg-white/20 rounded hover:bg-white/30 transition-colors" onclick="undoManager.undo()">
                    Undo
                </button>
            `;
            document.body.appendChild(bar);
        }
        
        bar.querySelector('.undo-message').textContent = action;
        bar.classList.add('show');
        
        setTimeout(() => {
            bar.classList.remove('show');
        }, 5000);
    }
}

// ============================================
// FORM AUTO-SAVE
// ============================================
class FormAutoSave {
    constructor(formElement, options = {}) {
        this.form = formElement;
        this.options = {
            debounceMs: 1000,
            storageKey: null,
            onSave: null,
            ...options
        };
        this.debounceTimer = null;
        this.indicator = null;
        this.init();
    }

    init() {
        // Create indicator
        this.indicator = document.createElement('div');
        this.indicator.className = 'autosave-indicator';
        this.indicator.innerHTML = `
            <i class="fas fa-circle-notch fa-spin"></i>
            <span class="autosave-text">Saving...</span>
        `;
        document.body.appendChild(this.indicator);
        
        // Load saved data
        this.load();
        
        // Monitor form changes
        this.form.addEventListener('input', () => this.scheduleAutoSave());
        this.form.addEventListener('change', () => this.scheduleAutoSave());
    }

    scheduleAutoSave() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => this.save(), this.options.debounceMs);
    }

    save() {
        this.showIndicator('saving');
        
        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData.entries());
        
        if (this.options.storageKey) {
            localStorage.setItem(this.options.storageKey, JSON.stringify(data));
        }
        
        if (this.options.onSave) {
            this.options.onSave(data, () => {
                this.showIndicator('saved');
            });
        } else {
            this.showIndicator('saved');
        }
    }

    load() {
        if (!this.options.storageKey) return;
        
        const saved = localStorage.getItem(this.options.storageKey);
        if (!saved) return;
        
        try {
            const data = JSON.parse(saved);
            Object.entries(data).forEach(([key, value]) => {
                const input = this.form.querySelector(`[name="${key}"]`);
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = value === 'on';
                    } else {
                        input.value = value;
                    }
                }
            });
        } catch (e) {
            console.error('Failed to load saved form data:', e);
        }
    }

    showIndicator(state) {
        this.indicator.className = 'autosave-indicator show ' + state;
        this.indicator.querySelector('.autosave-text').textContent = 
            state === 'saving' ? 'Saving...' : 'Saved';
        
        setTimeout(() => {
            this.indicator.classList.remove('show');
        }, 2000);
    }

    clear() {
        if (this.options.storageKey) {
            localStorage.removeItem(this.options.storageKey);
        }
    }
}

// ============================================
// RECENTLY VIEWED TRACKER
// ============================================
class RecentlyViewedTracker {
    constructor(maxItems = 10) {
        this.maxItems = maxItems;
        this.storageKey = 'recently_viewed';
    }

    track(item) {
        let items = this.getItems();
        
        // Remove if exists
        items = items.filter(i => i.url !== item.url);
        
        // Add to beginning
        items.unshift({
            ...item,
            timestamp: Date.now()
        });
        
        // Limit size
        items = items.slice(0, this.maxItems);
        
        localStorage.setItem(this.storageKey, JSON.stringify(items));
    }

    getItems() {
        try {
            return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
        } catch {
            return [];
        }
    }

    clear() {
        localStorage.removeItem(this.storageKey);
    }
}

// ============================================
// FAVORITES MANAGER
// ============================================
class FavoritesManager {
    constructor() {
        this.storageKey = 'favorites';
    }

    toggle(item) {
        let favorites = this.getFavorites();
        const index = favorites.findIndex(f => f.id === item.id && f.type === item.type);
        
        if (index >= 0) {
            favorites.splice(index, 1);
            this.save(favorites);
            return false;
        } else {
            favorites.push(item);
            this.save(favorites);
            return true;
        }
    }

    isFavorite(id, type) {
        return this.getFavorites().some(f => f.id === id && f.type === type);
    }

    getFavorites() {
        try {
            return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
        } catch {
            return [];
        }
    }

    save(favorites) {
        localStorage.setItem(this.storageKey, JSON.stringify(favorites));
    }
}

// ============================================
// DRAG & DROP
// ============================================
class DragDropManager {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = {
            onDrop: null,
            onReorder: null,
            ...options
        };
        this.init();
    }

    init() {
        const items = this.container.querySelectorAll('[draggable="true"]');
        
        items.forEach(item => {
            item.addEventListener('dragstart', (e) => this.handleDragStart(e));
            item.addEventListener('dragend', (e) => this.handleDragEnd(e));
            item.addEventListener('dragover', (e) => this.handleDragOver(e));
            item.addEventListener('drop', (e) => this.handleDrop(e));
        });
    }

    handleDragStart(e) {
        e.currentTarget.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.currentTarget.innerHTML);
    }

    handleDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
    }

    handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        e.dataTransfer.dropEffect = 'move';
        
        const dragging = this.container.querySelector('.dragging');
        const afterElement = this.getDragAfterElement(e.clientY);
        
        if (afterElement == null) {
            this.container.appendChild(dragging);
        } else {
            this.container.insertBefore(dragging, afterElement);
        }
        
        return false;
    }

    handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        
        if (this.options.onDrop) {
            this.options.onDrop(e);
        }
        
        if (this.options.onReorder) {
            const items = Array.from(this.container.querySelectorAll('[draggable="true"]'));
            const order = items.map((item, index) => ({ element: item, index }));
            this.options.onReorder(order);
        }
        
        return false;
    }

    getDragAfterElement(y) {
        const draggableElements = [...this.container.querySelectorAll('[draggable="true"]:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize global managers
    window.toastManager = new ToastManager();
    window.undoManager = new UndoManager();
    window.recentlyViewed = new RecentlyViewedTracker();
    window.favoritesManager = new FavoritesManager();
    
    // Initialize enhanced tables
    document.querySelectorAll('table[data-enhanced]').forEach(table => {
        new EnhancedTable(table);
    });
    
    // Initialize live search
    document.querySelectorAll('input[data-live-search]').forEach(input => {
        new LiveSearch(input, {
            onSearch: (query, callback) => {
                // Custom search implementation
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(r => r.json())
                    .then(callback)
                    .catch(console.error);
            }
        });
    });
    
    // Initialize filter managers (skip forms that have custom handlers)
    document.querySelectorAll('form[data-filter-form]').forEach(form => {
        // Skip forms that have custom AJAX handlers
        if (form.id === 'projectsFilterForm' || 
            form.id === 'tasksFilterForm' || 
            form.id === 'clientsFilterForm' || 
            form.id === 'invoicesFilterForm' ||
            form.id === 'quotesFilterForm') {
            return;
        }
        new FilterManager(form);
    });
    
    // Initialize auto-save forms
    document.querySelectorAll('form[data-auto-save]').forEach(form => {
        new FormAutoSave(form, {
            storageKey: form.dataset.autoSaveKey,
            onSave: (data, callback) => {
                // Custom save implementation
                fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                    },
                    body: JSON.stringify(data)
                })
                .then(() => callback())
                .catch(console.error);
            }
        });
    });
    
    // Count-up animations
    document.querySelectorAll('[data-count-up]').forEach(el => {
        const target = parseFloat(el.dataset.countUp);
        const duration = parseInt(el.dataset.duration || '1000');
        const decimals = parseInt(el.dataset.decimals || '0');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCount(el, 0, target, duration, decimals);
                    observer.unobserve(el);
                }
            });
        });
        
        observer.observe(el);
    });
    
    console.log('Enhanced UI initialized');
});

// ============================================
// UTILITY FUNCTIONS
// ============================================
function animateCount(element, start, end, duration, decimals = 0) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = start + (end - start) * easeOutQuad(progress);
        element.textContent = current.toFixed(decimals);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function easeOutQuad(t) {
    return t * (2 - t);
}

// Global functions for inline event handlers
async function bulkDelete() {
    const confirmed = await showConfirm(
        'Are you sure you want to delete the selected items?',
        {
            title: 'Delete Items',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            variant: 'danger'
        }
    );
    if (confirmed) {
        window.toastManager?.success('Items deleted successfully');
        clearSelection();
    }
}

function bulkExport() {
    const table = document.querySelector('.enhanced-table');
    if (table) {
        const enhancedTable = table.__enhancedTable;
        const data = enhancedTable?.getSelectedRowData() || [];
        console.log('Exporting:', data);
        window.toastManager?.success('Export started');
    }
}

function clearSelection() {
    document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
        cb.checked = false;
        cb.dispatchEvent(new Event('change'));
    });
}

