/**
 * Data Tables Enhanced
 * Adds sortable columns, pagination, column visibility, and sticky headers to all tables
 */

(function() {
    'use strict';

    class DataTableEnhanced {
        constructor(table, options = {}) {
            this.table = table;
            this.tableId = table.id || `table-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            if (!table.id) table.id = this.tableId;
            
            this.options = {
                sortable: options.sortable !== false,
                pagination: options.pagination !== false,
                pageSize: options.pageSize || 10,
                pageSizeOptions: options.pageSizeOptions || [10, 25, 50, 100],
                columnVisibility: options.columnVisibility !== false,
                stickyHeader: options.stickyHeader !== false,
                storageKey: options.storageKey || `table-${this.tableId}`,
                ...options
            };

            this.currentPage = 1;
            this.pageSize = this.options.pageSize;
            this.sortColumn = null;
            this.sortDirection = 'asc';
            this.visibleColumns = new Set();
            this.originalData = [];
            
            this.init();
        }

        init() {
            // Extract data from table
            this.extractData();
            
            // Load saved preferences
            this.loadPreferences();
            
            // Initialize features
            if (this.options.sortable) this.initSorting();
            if (this.options.columnVisibility) this.initColumnVisibility();
            if (this.options.stickyHeader) this.initStickyHeader();
            if (this.options.pagination) this.initPagination();
            
            // Apply initial state
            this.render();
        }

        extractData() {
            const tbody = this.table.querySelector('tbody');
            if (!tbody) return;
            
            const rows = Array.from(tbody.querySelectorAll('tr'));
            this.originalData = rows.map(row => ({
                element: row,
                cells: Array.from(row.querySelectorAll('td')),
                values: Array.from(row.querySelectorAll('td')).map(cell => {
                    // Get sortable value (check for data-sort attribute)
                    const sortValue = cell.getAttribute('data-sort');
                    if (sortValue !== null) return sortValue;
                    // Otherwise use text content
                    return cell.textContent.trim();
                })
            }));
        }

        loadPreferences() {
            try {
                const saved = localStorage.getItem(this.options.storageKey);
                if (saved) {
                    const prefs = JSON.parse(saved);
                    if (prefs.pageSize) this.pageSize = prefs.pageSize;
                    if (prefs.visibleColumns) {
                        this.visibleColumns = new Set(prefs.visibleColumns);
                    }
                }
            } catch (e) {
                console.warn('Failed to load table preferences', e);
            }
        }

        savePreferences() {
            try {
                const prefs = {
                    pageSize: this.pageSize,
                    visibleColumns: Array.from(this.visibleColumns)
                };
                localStorage.setItem(this.options.storageKey, JSON.stringify(prefs));
            } catch (e) {
                console.warn('Failed to save table preferences', e);
            }
        }

        initSorting() {
            const thead = this.table.querySelector('thead');
            if (!thead) return;
            
            const headers = Array.from(thead.querySelectorAll('th'));
            
            headers.forEach((header, index) => {
                // Check if column is sortable (has data-sortable attribute or class)
                const isSortable = header.hasAttribute('data-sortable') || 
                                   header.classList.contains('sortable') ||
                                   !header.classList.contains('no-sort');
                
                if (!isSortable) return;
                
                // Skip checkbox columns
                if (header.querySelector('input[type="checkbox"]')) return;
                
                header.classList.add('sortable-column');
                header.style.cursor = 'pointer';
                header.setAttribute('role', 'button');
                header.setAttribute('tabindex', '0');
                header.setAttribute('aria-label', `Sort by ${header.textContent.trim()}`);
                
                // Add sort indicator container
                const indicator = document.createElement('span');
                indicator.className = 'sort-indicator';
                indicator.innerHTML = '<i class="fas fa-sort"></i>';
                header.appendChild(indicator);
                
                // Click handler
                header.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.sort(index);
                });
                
                // Keyboard handler
                header.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        this.sort(index);
                    }
                });
            });
        }

        sort(columnIndex) {
            // Toggle sort direction if same column
            if (this.sortColumn === columnIndex) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortColumn = columnIndex;
                this.sortDirection = 'asc';
            }
            
            // Update visual indicators
            this.updateSortIndicators();
            
            // Sort data
            this.originalData.sort((a, b) => {
                const aVal = a.values[columnIndex] || '';
                const bVal = b.values[columnIndex] || '';
                
                // Try numeric sort
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                
                let comparison = 0;
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    comparison = aNum - bNum;
                } else {
                    // Date sorting (try to parse as date)
                    const aDate = new Date(aVal);
                    const bDate = new Date(bVal);
                    if (!isNaN(aDate.getTime()) && !isNaN(bDate.getTime())) {
                        comparison = aDate - bDate;
                    } else {
                        // String sort
                        comparison = aVal.localeCompare(bVal, undefined, { 
                            numeric: true, 
                            sensitivity: 'base' 
                        });
                    }
                }
                
                return this.sortDirection === 'asc' ? comparison : -comparison;
            });
            
            // Reset to first page
            this.currentPage = 1;
            this.render();
        }

        updateSortIndicators() {
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            headers.forEach((header, index) => {
                const indicator = header.querySelector('.sort-indicator');
                if (!indicator) return;
                
                if (index === this.sortColumn) {
                    indicator.innerHTML = this.sortDirection === 'asc' 
                        ? '<i class="fas fa-sort-up"></i>' 
                        : '<i class="fas fa-sort-down"></i>';
                    indicator.classList.add('active');
                } else {
                    indicator.innerHTML = '<i class="fas fa-sort"></i>';
                    indicator.classList.remove('active');
                }
            });
        }

        initColumnVisibility() {
            // Create column visibility toggle button
            const tableContainer = this.table.closest('.bg-card-light, .bg-card-dark, .card, .table-container') || 
                                   this.table.parentElement;
            
            // Look for existing toolbar (Finance tables have a flex toolbar with buttons before the table)
            const tableWrapper = this.table.closest('.overflow-x-auto, .table-responsive') || this.table;
            let existingToolbarRight = null;
            
            // Check if there's an existing toolbar div before the table wrapper
            if (tableWrapper.parentElement) {
                let sibling = tableWrapper.previousElementSibling;
                while (sibling) {
                    // Look for the flex toolbar div that contains buttons
                    if (sibling.classList.contains('flex') && 
                        sibling.classList.contains('justify-between') && 
                        sibling.classList.contains('items-center')) {
                        // Find the right side container (has flex items-center gap-2)
                        existingToolbarRight = sibling.querySelector('div.flex.items-center.gap-2');
                        if (!existingToolbarRight) {
                            // If no right container found, use the sibling itself
                            existingToolbarRight = sibling;
                        }
                        break;
                    }
                    sibling = sibling.previousElementSibling;
                }
            }
            
            // Check for table-toolbar class as fallback
            let toolbar = existingToolbarRight || tableContainer.querySelector('.table-toolbar');
            
            if (!toolbar) {
                // Create new toolbar
                toolbar = document.createElement('div');
                toolbar.className = 'table-toolbar';
                if (tableWrapper.parentElement) {
                    tableWrapper.parentElement.insertBefore(toolbar, tableWrapper);
                } else {
                    tableContainer.insertBefore(toolbar, this.table);
                }
            }
            
            // Add column visibility button if not exists
            if (!tableContainer.querySelector('.column-visibility-btn')) {
                const btn = document.createElement('button');
                btn.className = 'column-visibility-btn px-3 py-1.5 text-sm bg-background-light dark:bg-background-dark rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors inline-flex items-center gap-2';
                btn.innerHTML = '<i class="fas fa-columns"></i> <span>Columns</span>';
                btn.setAttribute('aria-label', 'Toggle column visibility');
                
                const dropdown = document.createElement('div');
                dropdown.className = 'column-visibility-dropdown hidden absolute right-0 mt-2 w-56 bg-card-light dark:bg-card-dark border border-border-light dark:border-border-dark rounded-md shadow-lg z-50 p-2';
                
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleColumnVisibilityDropdown(dropdown);
                });
                
                // Position dropdown
                const btnContainer = document.createElement('div');
                btnContainer.className = 'relative inline-block';
                btnContainer.appendChild(btn);
                btnContainer.appendChild(dropdown);
                
                // If existing toolbar (Finance tables), append to the right side container
                if (existingToolbarRight) {
                    // Insert at the beginning of the button group (before Export and Bulk Actions)
                    existingToolbarRight.insertBefore(btnContainer, existingToolbarRight.firstChild);
                } else {
                    // New toolbar - create proper structure
                    const toolbarRight = toolbar.querySelector('.table-toolbar-right') || toolbar;
                    if (!toolbar.querySelector('.table-toolbar-right')) {
                        toolbar.style.display = 'flex';
                        toolbar.style.justifyContent = 'space-between';
                        toolbar.style.alignItems = 'center';
                        toolbar.style.marginBottom = '1rem';
                    }
                    toolbarRight.appendChild(btnContainer);
                }
                
                // Close on outside click
                document.addEventListener('click', (e) => {
                    if (!btnContainer.contains(e.target)) {
                        dropdown.classList.add('hidden');
                    }
                });
                
                // Populate dropdown
                this.populateColumnVisibilityDropdown(dropdown);
            }
        }

        populateColumnVisibilityDropdown(dropdown) {
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            
            // Create mapping of visible headers to their original indices
            const columnMap = [];
            headers.forEach((header, index) => {
                if (!header.querySelector('input[type="checkbox"]')) {
                    columnMap.push({ header, index });
                }
            });
            
            dropdown.innerHTML = columnMap.map(({ header, index }) => {
                const isVisible = !this.visibleColumns.has(index) || this.visibleColumns.size === 0;
                const headerText = header.textContent.trim().replace(/\s+/g, ' ');
                return `
                    <label class="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer">
                        <input type="checkbox" 
                               class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary" 
                               data-column="${index}"
                               ${isVisible ? 'checked' : ''}>
                        <span class="text-sm">${headerText}</span>
                    </label>
                `;
            }).join('');
            
            // Bind checkbox events
            dropdown.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const columnIndex = parseInt(e.target.getAttribute('data-column'));
                    this.toggleColumn(columnIndex, e.target.checked);
                });
            });
        }

        toggleColumnVisibilityDropdown(dropdown) {
            dropdown.classList.toggle('hidden');
            if (!dropdown.classList.contains('hidden')) {
                this.populateColumnVisibilityDropdown(dropdown);
            }
        }

        toggleColumn(columnIndex, show) {
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            const rows = Array.from(this.table.querySelectorAll('tbody tr'));
            
            if (show) {
                this.visibleColumns.delete(columnIndex);
            } else {
                this.visibleColumns.add(columnIndex);
            }
            
            headers[columnIndex].style.display = show ? '' : 'none';
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                if (cells[columnIndex]) {
                    cells[columnIndex].style.display = show ? '' : 'none';
                }
            });
            
            this.savePreferences();
        }

        initStickyHeader() {
            const thead = this.table.querySelector('thead');
            if (!thead) return;
            
            // Add sticky header class
            thead.classList.add('sticky-header');
            
            // Add scroll listener to table container
            const tableWrapper = this.table.closest('.table-responsive, .bg-card-light, .bg-card-dark') || 
                                this.table.parentElement;
            
            // Create wrapper if needed
            if (!tableWrapper.classList.contains('table-scroll-container')) {
                const scrollContainer = document.createElement('div');
                scrollContainer.className = 'table-scroll-container';
                scrollContainer.style.maxHeight = '70vh';
                scrollContainer.style.overflowY = 'auto';
                
                this.table.parentNode.insertBefore(scrollContainer, this.table);
                scrollContainer.appendChild(this.table);
            }
            
            // Update sticky header on scroll
            const scrollContainer = this.table.closest('.table-scroll-container') || tableWrapper;
            scrollContainer.addEventListener('scroll', () => {
                this.updateStickyHeader(scrollContainer);
            });
        }

        updateStickyHeader(container) {
            const thead = this.table.querySelector('thead');
            if (!thead) return;
            
            if (container.scrollTop > 0) {
                thead.classList.add('sticky-active');
            } else {
                thead.classList.remove('sticky-active');
            }
        }

        initPagination() {
            // Create pagination controls
            const tableContainer = this.table.closest('.bg-card-light, .bg-card-dark, .card') || 
                                   this.table.parentElement;
            
            let paginationContainer = tableContainer.querySelector('.table-pagination-container');
            if (!paginationContainer) {
                paginationContainer = document.createElement('div');
                paginationContainer.className = 'table-pagination-container flex items-center justify-between mt-4';
                // Insert after table
                const tableWrapper = this.table.closest('.overflow-x-auto, .table-responsive') || this.table.parentElement;
                if (tableWrapper && tableWrapper.nextSibling) {
                    tableWrapper.parentNode.insertBefore(paginationContainer, tableWrapper.nextSibling);
                } else {
                    this.table.parentNode.appendChild(paginationContainer);
                }
            }
            
            this.paginationContainer = paginationContainer;
            this.renderPagination();
        }

        renderPagination() {
            if (!this.paginationContainer) return;
            
            const totalItems = this.originalData.length;
            const totalPages = Math.ceil(totalItems / this.pageSize);
            const start = (this.currentPage - 1) * this.pageSize + 1;
            const end = Math.min(this.currentPage * this.pageSize, totalItems);
            
            // Page size selector
            const pageSizeSelect = `
                <div class="flex items-center gap-2">
                    <label class="text-sm text-text-muted-light dark:text-text-muted-dark">Show:</label>
                    <select class="table-page-size-select px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-background-light dark:bg-background-dark">
                        ${this.options.pageSizeOptions.map(size => 
                            `<option value="${size}" ${size === this.pageSize ? 'selected' : ''}>${size}</option>`
                        ).join('')}
                    </select>
                </div>
            `;
            
            // Pagination info
            const paginationInfo = `
                <div class="text-sm text-text-muted-light dark:text-text-muted-dark">
                    Showing ${start} to ${end} of ${totalItems} entries
                </div>
            `;
            
            // Pagination buttons
            const paginationButtons = this.renderPaginationButtons(totalPages);
            
            this.paginationContainer.innerHTML = `
                ${pageSizeSelect}
                <div class="flex items-center gap-2">
                    ${paginationInfo}
                    ${paginationButtons}
                </div>
            `;
            
            // Bind page size change
            const pageSizeSelectEl = this.paginationContainer.querySelector('.table-page-size-select');
            if (pageSizeSelectEl) {
                pageSizeSelectEl.addEventListener('change', (e) => {
                    this.pageSize = parseInt(e.target.value);
                    this.currentPage = 1;
                    this.savePreferences();
                    this.render();
                });
            }
            
            // Bind pagination button clicks
            this.paginationContainer.querySelectorAll('.pagination-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const page = parseInt(e.target.getAttribute('data-page'));
                    if (!isNaN(page) && page >= 1 && page <= totalPages) {
                        this.goToPage(page);
                    }
                });
            });
        }

        renderPaginationButtons(totalPages) {
            if (totalPages <= 1) return '';
            
            let buttons = '';
            
            // Previous button
            buttons = `
                <button class="pagination-btn px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-background-light dark:bg-background-dark hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed" 
                        data-page="${this.currentPage - 1}"
                        ${this.currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
            `;
            
            // Page numbers
            const maxVisible = 5;
            let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
            let endPage = Math.min(totalPages, startPage + maxVisible - 1);
            
            if (endPage - startPage < maxVisible - 1) {
                startPage = Math.max(1, endPage - maxVisible + 1);
            }
            
            if (startPage > 1) {
                buttons += `<button class="pagination-btn px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-background-light dark:bg-background-dark hover:bg-gray-100 dark:hover:bg-gray-700" data-page="1">1</button>`;
                if (startPage > 2) {
                    buttons += `<span class="px-2 text-text-muted-light dark:text-text-muted-dark">...</span>`;
                }
            }
            
            for (let i = startPage; i <= endPage; i++) {
                buttons += `
                    <button class="pagination-btn px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded ${
                        i === this.currentPage 
                            ? 'bg-primary text-white' 
                            : 'bg-background-light dark:bg-background-dark hover:bg-gray-100 dark:hover:bg-gray-700'
                    }" 
                            data-page="${i}">
                        ${i}
                    </button>
                `;
            }
            
            if (endPage < totalPages) {
                if (endPage < totalPages - 1) {
                    buttons += `<span class="px-2 text-text-muted-light dark:text-text-muted-dark">...</span>`;
                }
                buttons += `<button class="pagination-btn px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-background-light dark:bg-background-dark hover:bg-gray-100 dark:hover:bg-gray-700" data-page="${totalPages}">${totalPages}</button>`;
            }
            
            // Next button
            buttons += `
                <button class="pagination-btn px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-background-light dark:bg-background-dark hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed" 
                        data-page="${this.currentPage + 1}"
                        ${this.currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            `;
            
            return buttons;
        }

        goToPage(page) {
            const totalPages = Math.ceil(this.originalData.length / this.pageSize);
            if (page < 1 || page > totalPages) return;
            
            this.currentPage = page;
            this.render();
            
            // Scroll to top of table
            this.table.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        render() {
            const tbody = this.table.querySelector('tbody');
            if (!tbody) return;
            
            // Hide all rows
            this.originalData.forEach(row => {
                row.element.style.display = 'none';
            });
            
            // Calculate pagination
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            const visibleRows = this.originalData.slice(start, end);
            
            // Show visible rows
            visibleRows.forEach(row => {
                row.element.style.display = '';
            });
            
            // Update pagination UI
            if (this.options.pagination) {
                this.renderPagination();
            }
        }
    }

    // Auto-initialize tables with data-table-enhanced attribute
    document.addEventListener('DOMContentLoaded', () => {
        // Find all tables with data-table-enhanced attribute or class
        const tables = document.querySelectorAll('table[data-table-enhanced], table.table-enhanced, table.table-zebra');
        
        tables.forEach((table, index) => {
            // Skip if already initialized
            if (table.dataset.enhancedTableInitialized) return;
            table.dataset.enhancedTableInitialized = 'true';
            
            // Get options from data attributes
            const options = {
                sortable: table.dataset.sortable !== 'false',
                pagination: table.dataset.pagination !== 'false',
                pageSize: parseInt(table.dataset.pageSize) || 25,
                columnVisibility: table.dataset.columnVisibility !== 'false',
                stickyHeader: table.dataset.stickyHeader !== 'false',
                storageKey: table.dataset.storageKey || `table-${table.id || index}`
            };
            
            new DataTableEnhanced(table, options);
        });
    });

    // Export for manual initialization
    window.DataTableEnhanced = DataTableEnhanced;
})();

