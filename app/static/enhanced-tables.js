/**
 * Enhanced Data Tables
 * Advanced table features: sorting, filtering, inline editing, pagination
 */

(function() {
    'use strict';

    class EnhancedTable {
        constructor(table, options = {}) {
            this.table = table;
            this.options = {
                sortable: options.sortable !== false,
                filterable: options.filterable !== false,
                paginate: options.paginate !== false,
                pageSize: options.pageSize || 10,
                stickyHeader: options.stickyHeader !== false,
                exportable: options.exportable !== false,
                editable: options.editable || false,
                selectable: options.selectable || false,
                resizable: options.resizable || false,
                ...options
            };

            this.data = [];
            this.filteredData = [];
            this.currentPage = 1;
            this.sortColumn = null;
            this.sortDirection = 'asc';
            this.selectedRows = new Set();

            this.init();
        }

        init() {
            this.extractData();
            this.createWrapper();
            if (this.options.sortable) this.enableSorting();
            if (this.options.resizable) this.enableResizing();
            if (this.options.selectable) this.enableSelection();
            if (this.options.editable) this.enableEditing();
            if (this.options.paginate) this.renderPagination();
            if (this.options.stickyHeader) this.table.classList.add('table-enhanced-sticky');
            
            this.filteredData = [...this.data];
            this.render();
        }

        extractData() {
            const rows = Array.from(this.table.querySelectorAll('tbody tr'));
            this.data = rows.map(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                return {
                    element: row,
                    values: cells.map(cell => cell.textContent.trim()),
                    cells: cells
                };
            });
        }

        createWrapper() {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-enhanced-wrapper';
            
            // Create toolbar
            const toolbar = this.createToolbar();
            wrapper.appendChild(toolbar);
            
            // Wrap table
            const tableContainer = document.createElement('div');
            tableContainer.className = 'table-responsive';
            this.table.classList.add('table-enhanced');
            this.table.parentNode.insertBefore(wrapper, this.table);
            tableContainer.appendChild(this.table);
            wrapper.appendChild(tableContainer);
            
            // Create bulk actions bar
            if (this.options.selectable) {
                const bulkActions = this.createBulkActionsBar();
                wrapper.insertBefore(bulkActions, tableContainer);
            }
            
            this.wrapper = wrapper;
            this.tableContainer = tableContainer;
        }

        createToolbar() {
            const toolbar = document.createElement('div');
            toolbar.className = 'table-toolbar';
            
            toolbar.innerHTML = `
                <div class="table-toolbar-left">
                    ${this.options.filterable ? `
                        <div class="table-search-box">
                            <i class="fas fa-search"></i>
                            <input type="text" placeholder="Search..." class="table-search-input">
                        </div>
                    ` : ''}
                </div>
                <div class="table-toolbar-right">
                    ${this.options.filterable ? `
                        <button class="table-filter-btn">
                            <i class="fas fa-filter"></i>
                            <span>Filters</span>
                        </button>
                    ` : ''}
                    <div class="position-relative">
                        <button class="table-columns-btn">
                            <i class="fas fa-columns"></i>
                            <span>Columns</span>
                        </button>
                        <div class="table-columns-dropdown"></div>
                    </div>
                    ${this.options.exportable ? `
                        <div class="position-relative">
                            <button class="table-export-btn">
                                <i class="fas fa-download"></i>
                                <span>Export</span>
                            </button>
                            <div class="table-export-menu">
                                <div class="table-export-option" data-format="csv">
                                    <i class="fas fa-file-csv"></i>
                                    <span>Export CSV</span>
                                </div>
                                <div class="table-export-option" data-format="json">
                                    <i class="fas fa-file-code"></i>
                                    <span>Export JSON</span>
                                </div>
                                <div class="table-export-option" data-format="print">
                                    <i class="fas fa-print"></i>
                                    <span>Print</span>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
            
            this.bindToolbarEvents(toolbar);
            return toolbar;
        }

        bindToolbarEvents(toolbar) {
            // Search
            const searchInput = toolbar.querySelector('.table-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.handleSearch(e.target.value);
                });
            }
            
            // Columns visibility
            const columnsBtn = toolbar.querySelector('.table-columns-btn');
            if (columnsBtn) {
                columnsBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleColumnsDropdown();
                });
            }
            
            // Export
            const exportBtn = toolbar.querySelector('.table-export-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleExportMenu();
                });
                
                const exportOptions = toolbar.querySelectorAll('.table-export-option');
                exportOptions.forEach(option => {
                    option.addEventListener('click', () => {
                        const format = option.getAttribute('data-format');
                        this.exportData(format);
                    });
                });
            }
            
            // Close dropdowns on outside click
            document.addEventListener('click', () => {
                const columnsDropdown = toolbar.querySelector('.table-columns-dropdown');
                const exportMenu = toolbar.querySelector('.table-export-menu');
                if (columnsDropdown) columnsDropdown.classList.remove('show');
                if (exportMenu) exportMenu.classList.remove('show');
            });
        }

        createBulkActionsBar() {
            const bar = document.createElement('div');
            bar.className = 'table-bulk-actions';
            bar.innerHTML = `
                <div class="table-bulk-actions-info">
                    <span class="selected-count">0</span> items selected
                </div>
                <div class="table-bulk-actions-buttons">
                    <button class="btn btn-sm btn-danger" data-action="delete">
                        <i class="fas fa-trash me-1"></i>Delete
                    </button>
                    <button class="btn btn-sm btn-secondary" data-action="export">
                        <i class="fas fa-download me-1"></i>Export Selected
                    </button>
                </div>
            `;
            
            this.bulkActionsBar = bar;
            return bar;
        }

        enableSorting() {
            const headers = this.table.querySelectorAll('thead th');
            headers.forEach((header, index) => {
                if (header.classList.contains('no-sort')) return;
                
                header.classList.add('sortable');
                header.addEventListener('click', () => {
                    this.sort(index);
                });
            });
        }

        sort(columnIndex) {
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            const header = headers[columnIndex];
            
            // Toggle sort direction
            if (this.sortColumn === columnIndex) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortColumn = columnIndex;
                this.sortDirection = 'asc';
            }
            
            // Update header classes
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            header.classList.add(`sort-${this.sortDirection}`);
            
            // Sort data
            this.filteredData.sort((a, b) => {
                const aVal = a.values[columnIndex];
                const bVal = b.values[columnIndex];
                
                // Try numeric sort first
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                
                let comparison;
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    comparison = aNum - bNum;
                } else {
                    comparison = aVal.localeCompare(bVal);
                }
                
                return this.sortDirection === 'asc' ? comparison : -comparison;
            });
            
            this.render();
        }

        handleSearch(query) {
            if (!query) {
                this.filteredData = [...this.data];
            } else {
                const lowerQuery = query.toLowerCase();
                this.filteredData = this.data.filter(row => {
                    return row.values.some(val => 
                        val.toLowerCase().includes(lowerQuery)
                    );
                });
            }
            
            this.currentPage = 1;
            this.render();
        }

        enableResizing() {
            const headers = this.table.querySelectorAll('thead th');
            headers.forEach((header, index) => {
                if (header.classList.contains('no-resize')) return;
                
                header.classList.add('resizable');
                const resizer = document.createElement('div');
                resizer.className = 'column-resizer';
                header.appendChild(resizer);
                
                let startX, startWidth;
                
                resizer.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    startX = e.pageX;
                    startWidth = header.offsetWidth;
                    resizer.classList.add('resizing');
                    
                    const onMouseMove = (e) => {
                        const diff = e.pageX - startX;
                        header.style.width = `${startWidth + diff}px`;
                    };
                    
                    const onMouseUp = () => {
                        resizer.classList.remove('resizing');
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                    };
                    
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                });
            });
        }

        enableSelection() {
            // Add checkbox column
            const thead = this.table.querySelector('thead tr');
            const tbody = this.table.querySelector('tbody');
            
            // Header checkbox
            const headerCheckbox = document.createElement('th');
            headerCheckbox.className = 'table-checkbox-cell';
            headerCheckbox.innerHTML = '<input type="checkbox" class="table-checkbox table-checkbox-all">';
            thead.insertBefore(headerCheckbox, thead.firstChild);
            
            // Row checkboxes
            this.data.forEach(row => {
                const checkbox = document.createElement('td');
                checkbox.className = 'table-checkbox-cell';
                checkbox.innerHTML = '<input type="checkbox" class="table-checkbox table-checkbox-row">';
                row.element.insertBefore(checkbox, row.element.firstChild);
            });
            
            // Bind events
            const selectAll = this.table.querySelector('.table-checkbox-all');
            selectAll.addEventListener('change', (e) => {
                const checkboxes = this.table.querySelectorAll('.table-checkbox-row');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    const row = cb.closest('tr');
                    if (e.target.checked) {
                        row.classList.add('selected');
                        this.selectedRows.add(row);
                    } else {
                        row.classList.remove('selected');
                        this.selectedRows.delete(row);
                    }
                });
                this.updateBulkActions();
            });
            
            const rowCheckboxes = this.table.querySelectorAll('.table-checkbox-row');
            rowCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const row = e.target.closest('tr');
                    if (e.target.checked) {
                        row.classList.add('selected');
                        this.selectedRows.add(row);
                    } else {
                        row.classList.remove('selected');
                        this.selectedRows.delete(row);
                    }
                    this.updateBulkActions();
                });
            });
        }

        updateBulkActions() {
            if (!this.bulkActionsBar) return;
            
            const count = this.selectedRows.size;
            const countSpan = this.bulkActionsBar.querySelector('.selected-count');
            countSpan.textContent = count;
            
            if (count > 0) {
                this.bulkActionsBar.classList.add('show');
            } else {
                this.bulkActionsBar.classList.remove('show');
            }
        }

        enableEditing() {
            const editableCells = this.table.querySelectorAll('td[data-editable]');
            editableCells.forEach(cell => {
                cell.classList.add('table-cell-editable');
                cell.addEventListener('dblclick', () => {
                    this.editCell(cell);
                });
            });
        }

        editCell(cell) {
            if (cell.classList.contains('table-cell-editing')) return;
            
            const originalValue = cell.textContent.trim();
            const inputType = cell.getAttribute('data-edit-type') || 'text';
            
            cell.classList.add('table-cell-editing');
            
            let input;
            if (inputType === 'textarea') {
                input = document.createElement('textarea');
            } else if (inputType === 'select') {
                input = document.createElement('select');
                const options = cell.getAttribute('data-options').split(',');
                options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.trim();
                    option.textContent = opt.trim();
                    if (opt.trim() === originalValue) option.selected = true;
                    input.appendChild(option);
                });
            } else {
                input = document.createElement('input');
                input.type = inputType;
            }
            
            input.value = originalValue;
            cell.textContent = '';
            cell.appendChild(input);
            input.focus();
            if (inputType === 'text') input.select();
            
            const saveEdit = () => {
                const newValue = input.value;
                cell.textContent = newValue;
                cell.classList.remove('table-cell-editing');
                
                if (newValue !== originalValue) {
                    this.onCellEdit(cell, originalValue, newValue);
                }
            };
            
            const cancelEdit = () => {
                cell.textContent = originalValue;
                cell.classList.remove('table-cell-editing');
            };
            
            input.addEventListener('blur', saveEdit);
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && inputType !== 'textarea') {
                    e.preventDefault();
                    saveEdit();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    cancelEdit();
                }
            });
        }

        onCellEdit(cell, oldValue, newValue) {
            // Trigger custom event
            const event = new CustomEvent('cellEdited', {
                detail: {
                    cell: cell,
                    row: cell.parentNode,
                    oldValue: oldValue,
                    newValue: newValue,
                    column: cell.cellIndex
                }
            });
            this.table.dispatchEvent(event);
        }

        render() {
            const tbody = this.table.querySelector('tbody');
            
            // Clear tbody
            Array.from(tbody.children).forEach(row => {
                row.style.display = 'none';
            });
            
            // Calculate pagination
            const start = (this.currentPage - 1) * this.options.pageSize;
            const end = start + this.options.pageSize;
            const pageData = this.options.paginate ? 
                this.filteredData.slice(start, end) : 
                this.filteredData;
            
            // Show relevant rows
            pageData.forEach(row => {
                row.element.style.display = '';
            });
            
            // Update pagination
            if (this.options.paginate) {
                this.updatePagination();
            }
        }

        renderPagination() {
            const pagination = document.createElement('div');
            pagination.className = 'table-pagination';
            pagination.innerHTML = `
                <div class="table-pagination-info"></div>
                <div class="table-pagination-controls"></div>
            `;
            
            this.wrapper.appendChild(pagination);
            this.pagination = pagination;
        }

        updatePagination() {
            if (!this.pagination) return;
            
            const total = this.filteredData.length;
            const start = (this.currentPage - 1) * this.options.pageSize + 1;
            const end = Math.min(start + this.options.pageSize - 1, total);
            const totalPages = Math.ceil(total / this.options.pageSize);
            
            // Update info
            const info = this.pagination.querySelector('.table-pagination-info');
            info.textContent = `Showing ${start}-${end} of ${total}`;
            
            // Update controls
            const controls = this.pagination.querySelector('.table-pagination-controls');
            controls.innerHTML = `
                <button class="table-pagination-btn" data-page="prev" ${this.currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
                ${this.getPaginationButtons(totalPages)}
                <button class="table-pagination-btn" data-page="next" ${this.currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            `;
            
            // Bind events
            controls.querySelectorAll('.table-pagination-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const page = btn.getAttribute('data-page');
                    if (page === 'prev') {
                        this.goToPage(this.currentPage - 1);
                    } else if (page === 'next') {
                        this.goToPage(this.currentPage + 1);
                    } else {
                        this.goToPage(parseInt(page));
                    }
                });
            });
        }

        getPaginationButtons(totalPages) {
            let buttons = '';
            const maxButtons = 5;
            let start = Math.max(1, this.currentPage - Math.floor(maxButtons / 2));
            let end = Math.min(totalPages, start + maxButtons - 1);
            
            if (end - start < maxButtons - 1) {
                start = Math.max(1, end - maxButtons + 1);
            }
            
            for (let i = start; i <= end; i++) {
                buttons += `
                    <button class="table-pagination-btn ${i === this.currentPage ? 'active' : ''}" data-page="${i}">
                        ${i}
                    </button>
                `;
            }
            
            return buttons;
        }

        goToPage(page) {
            const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);
            if (page < 1 || page > totalPages) return;
            
            this.currentPage = page;
            this.render();
        }

        toggleColumnsDropdown() {
            const dropdown = this.wrapper.querySelector('.table-columns-dropdown');
            dropdown.classList.toggle('show');
            
            if (dropdown.innerHTML === '') {
                this.renderColumnsDropdown(dropdown);
            }
        }

        renderColumnsDropdown(dropdown) {
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            dropdown.replaceChildren();
            headers.forEach((header, index) => {
                if (header.classList.contains('table-checkbox-cell')) return;

                const labelEl = document.createElement('label');
                labelEl.className = 'table-column-toggle';
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = true;
                checkbox.setAttribute('data-column', String(index));
                labelEl.appendChild(checkbox);
                labelEl.appendChild(document.createTextNode(' ' + (header.textContent || '').trim()));
                dropdown.appendChild(labelEl);

                checkbox.addEventListener('change', (e) => {
                    this.toggleColumn(parseInt(e.target.getAttribute('data-column'), 10), e.target.checked);
                });
            });
        }

        toggleColumn(index, show) {
            const headers = this.table.querySelectorAll('thead th');
            const rows = this.table.querySelectorAll('tbody tr');
            
            headers[index].style.display = show ? '' : 'none';
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[index]) {
                    cells[index].style.display = show ? '' : 'none';
                }
            });
        }

        toggleExportMenu() {
            const menu = this.wrapper.querySelector('.table-export-menu');
            menu.classList.toggle('show');
        }

        exportData(format) {
            if (format === 'csv') {
                this.exportCSV();
            } else if (format === 'json') {
                this.exportJSON();
            } else if (format === 'print') {
                window.print();
            }
        }

        exportCSV() {
            const headers = Array.from(this.table.querySelectorAll('thead th'))
                .filter(th => !th.classList.contains('table-checkbox-cell'))
                .map(th => th.textContent.trim());
            
            let csv = headers.join(',') + '\n';
            
            this.filteredData.forEach(row => {
                const values = row.values.map(v => `"${v.replace(/"/g, '""')}"`);
                csv += values.join(',') + '\n';
            });
            
            this.downloadFile(csv, 'table-export.csv', 'text/csv');
        }

        exportJSON() {
            const headers = Array.from(this.table.querySelectorAll('thead th'))
                .filter(th => !th.classList.contains('table-checkbox-cell'))
                .map(th => th.textContent.trim());
            
            const data = this.filteredData.map(row => {
                const obj = {};
                headers.forEach((header, index) => {
                    obj[header] = row.values[index];
                });
                return obj;
            });
            
            this.downloadFile(JSON.stringify(data, null, 2), 'table-export.json', 'application/json');
        }

        downloadFile(content, filename, type) {
            const blob = new Blob([content], { type });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    // Auto-initialize
    document.addEventListener('DOMContentLoaded', () => {
        const tables = document.querySelectorAll('[data-enhanced-table]');
        tables.forEach(table => {
            const options = JSON.parse(table.getAttribute('data-enhanced-table') || '{}');
            new EnhancedTable(table, options);
        });
    });

    // Export for manual initialization
    window.EnhancedTable = EnhancedTable;

})();

