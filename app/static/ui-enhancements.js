/**
 * UI Enhancements - Context Menus, Bulk Selection, Micro-interactions
 */

(function() {
    'use strict';

    let contextMenu = null;
    let selectedItems = new Set();
    let bulkActionsBar = null;

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        initContextMenus();
        initBulkSelection();
        initKeyboardShortcutsIndicator();
        initButtonPressAnimations();
        initSuccessCheckmarks();
        initLoadingSpinners();
    }

    /**
     * Initialize context menus (right-click) on list items
     */
    function initContextMenus() {
        // Create context menu element
        contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.id = 'contextMenu';
        document.body.appendChild(contextMenu);

        // Add context menu items based on element data attributes
        document.addEventListener('contextmenu', function(e) {
            const row = e.target.closest('tr[data-context-menu], [data-context-menu]');
            if (!row) {
                hideContextMenu();
                return;
            }

            e.preventDefault();
            showContextMenu(e, row);
        });

        // Hide context menu on click
        document.addEventListener('click', function(e) {
            if (!contextMenu.contains(e.target)) {
                hideContextMenu();
            }
        });

        // Hide context menu on Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                hideContextMenu();
            }
        });
    }

    /**
     * Show context menu at position
     */
    function showContextMenu(e, element) {
        const menuData = element.getAttribute('data-context-menu');
        if (!menuData) return;

        try {
            const menuItems = JSON.parse(menuData);
            contextMenu.innerHTML = '';

            menuItems.forEach((item, index) => {
                if (item.separator) {
                    const separator = document.createElement('div');
                    separator.className = 'context-menu-separator';
                    contextMenu.appendChild(separator);
                } else {
                    const menuItem = document.createElement('div');
                    menuItem.className = 'context-menu-item' + (item.danger ? ' danger' : '');
                    menuItem.innerHTML = `
                        <i class="${item.icon || 'fas fa-circle'}"></i>
                        <span>${item.label}</span>
                    `;
                    
                    if (item.action) {
                        menuItem.addEventListener('click', function() {
                            executeContextAction(item.action, element);
                            hideContextMenu();
                        });
                    }

                    contextMenu.appendChild(menuItem);
                }
            });

            // Position menu
            const x = e.clientX;
            const y = e.clientY;
            const menuWidth = contextMenu.offsetWidth || 200;
            const menuHeight = contextMenu.offsetHeight || 100;
            const windowWidth = window.innerWidth;
            const windowHeight = window.innerHeight;

            let left = x;
            let top = y;

            // Adjust if menu would overflow right
            if (x + menuWidth > windowWidth) {
                left = x - menuWidth;
            }

            // Adjust if menu would overflow bottom
            if (y + menuHeight > windowHeight) {
                top = y - menuHeight;
            }

            contextMenu.style.left = left + 'px';
            contextMenu.style.top = top + 'px';
            contextMenu.classList.add('show');
        } catch (err) {
            console.error('Error parsing context menu data:', err);
        }
    }

    /**
     * Hide context menu
     */
    function hideContextMenu() {
        if (contextMenu) {
            contextMenu.classList.remove('show');
        }
    }

    /**
     * Execute context menu action
     */
    function executeContextAction(action, element) {
        const actionType = action.type;
        const actionData = action.data || {};

        switch (actionType) {
            case 'edit':
                if (action.url) {
                    window.location.href = action.url;
                }
                break;
            case 'delete':
                if (action.confirm) {
                    const confirmed = confirm(action.confirm);
                    if (confirmed && action.url) {
                        submitForm(action.url, action.method || 'POST');
                    }
                } else if (action.url) {
                    submitForm(action.url, action.method || 'POST');
                }
                break;
            case 'duplicate':
                if (action.url) {
                    window.location.href = action.url;
                }
                break;
            case 'view':
                if (action.url) {
                    window.location.href = action.url;
                }
                break;
            case 'toggle-status':
                if (action.url) {
                    submitForm(action.url, action.method || 'POST');
                }
                break;
            case 'custom':
                if (action.handler && typeof window[action.handler] === 'function') {
                    window[action.handler](element, actionData);
                }
                break;
        }
    }

    /**
     * Submit form (for delete/status actions)
     */
    function submitForm(url, method) {
        const form = document.createElement('form');
        form.method = method;
        form.action = url;
        
        // Add CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]');
        if (csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken.getAttribute('content');
            form.appendChild(csrfInput);
        }

        document.body.appendChild(form);
        form.submit();
    }

    /**
     * Initialize bulk selection with visual feedback
     */
    function initBulkSelection() {
        // Create bulk actions bar
        bulkActionsBar = document.createElement('div');
        bulkActionsBar.className = 'bulk-actions-bar-enhanced';
        bulkActionsBar.innerHTML = `
            <span class="bulk-actions-count" id="bulkActionsCount">0</span>
            <span>items selected</span>
            <div class="flex gap-2 ml-auto">
                <button class="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors" id="bulkActionEdit">Edit</button>
                <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors" id="bulkActionCancel">Cancel</button>
            </div>
        `;
        document.body.appendChild(bulkActionsBar);

        // Listen for checkbox changes
        document.addEventListener('change', function(e) {
            if (e.target.type === 'checkbox' && e.target.classList.contains('task-checkbox')) {
                updateBulkSelection(e.target);
            }
        });

        // Select all checkbox
        document.addEventListener('change', function(e) {
            if (e.target.id === 'selectAll') {
                const checkboxes = document.querySelectorAll('.task-checkbox');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    updateBulkSelection(cb);
                });
            }
        });

        // Bulk action cancel
        const cancelBtn = document.getElementById('bulkActionCancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                clearBulkSelection();
            });
        }

        // Keyboard shortcuts for bulk selection
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + A to select all
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                const table = e.target.closest('table');
                if (table && !isTyping(e)) {
                    e.preventDefault();
                    const checkboxes = table.querySelectorAll('.task-checkbox');
                    checkboxes.forEach(cb => {
                        cb.checked = true;
                        updateBulkSelection(cb);
                    });
                }
            }

            // Delete key to delete selected items
            if (e.key === 'Delete' && !isTyping(e) && selectedItems.size > 0) {
                e.preventDefault();
                const deleteBtn = document.getElementById('bulkActionDelete');
                if (deleteBtn) {
                    deleteBtn.click();
                }
            }
        });
    }

    /**
     * Update bulk selection state
     */
    function updateBulkSelection(checkbox) {
        const itemId = checkbox.value;
        
        if (checkbox.checked) {
            selectedItems.add(itemId);
            checkbox.closest('tr')?.classList.add('table-row-selected');
        } else {
            selectedItems.delete(itemId);
            checkbox.closest('tr')?.classList.remove('table-row-selected');
        }

        updateBulkActionsBar();
    }

    /**
     * Update bulk actions bar visibility
     */
    function updateBulkActionsBar() {
        const count = selectedItems.size;
        const countEl = document.getElementById('bulkActionsCount');
        
        if (countEl) {
            countEl.textContent = count;
        }

        if (bulkActionsBar) {
            if (count > 0) {
                bulkActionsBar.classList.add('show');
            } else {
                bulkActionsBar.classList.remove('show');
            }
        }

        // Update select all checkbox
        const selectAll = document.getElementById('selectAll');
        if (selectAll) {
            const allCheckboxes = document.querySelectorAll('.task-checkbox');
            const checkedCount = document.querySelectorAll('.task-checkbox:checked').length;
            
            if (checkedCount === 0) {
                selectAll.checked = false;
                selectAll.indeterminate = false;
            } else if (checkedCount === allCheckboxes.length) {
                selectAll.checked = true;
                selectAll.indeterminate = false;
            } else {
                selectAll.checked = false;
                selectAll.indeterminate = true;
            }
        }
    }

    /**
     * Clear bulk selection
     */
    function clearBulkSelection() {
        selectedItems.clear();
        document.querySelectorAll('.task-checkbox:checked').forEach(cb => {
            cb.checked = false;
            cb.closest('tr')?.classList.remove('table-row-selected');
        });
        updateBulkActionsBar();
    }

    /**
     * Check if user is typing (delegates to shared utility from typing-utils.js)
     */
    function isTyping(e) {
        return window.TimeTracker && window.TimeTracker.isTyping ? window.TimeTracker.isTyping(e) : false;
    }

    /**
     * Initialize keyboard shortcuts help indicator
     */
    function initKeyboardShortcutsIndicator() {
        // Check if indicator already exists
        let indicator = document.getElementById('keyboardShortcutsIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'keyboardShortcutsIndicator';
            indicator.className = 'keyboard-shortcuts-indicator';
            indicator.innerHTML = '<i class="fas fa-question"></i>';
            indicator.title = 'Keyboard Shortcuts (Shift+?)';
            indicator.setAttribute('aria-label', 'Keyboard Shortcuts');
            document.body.appendChild(indicator);

            indicator.addEventListener('click', function() {
                openKeyboardShortcutsModal();
            });

            // Add tooltip on hover
            indicator.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.1)';
            });

            indicator.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        }

        // Show keyboard shortcut hint on first visit
        const hasSeenHint = localStorage.getItem('keyboardShortcutsHintShown');
        if (!hasSeenHint) {
            setTimeout(() => {
                showKeyboardShortcutsHint();
                localStorage.setItem('keyboardShortcutsHintShown', 'true');
            }, 3000);
        }
    }

    /**
     * Show keyboard shortcuts hint
     */
    function showKeyboardShortcutsHint() {
        if (window.toastManager) {
            window.toastManager.info('Press Shift+? to see all keyboard shortcuts', 5000);
        }
    }

    /**
     * Open keyboard shortcuts modal
     */
    function openKeyboardShortcutsModal() {
        const modal = document.getElementById('keyboardShortcutsModal');
        if (modal && typeof window.openKeyboardShortcutsModal === 'function') {
            window.openKeyboardShortcutsModal();
        } else if (modal) {
            modal.classList.remove('hidden');
        }
    }

    /**
     * Initialize button press animations
     */
    function initButtonPressAnimations() {
        document.addEventListener('click', function(e) {
            const button = e.target.closest('button, .btn, a[class*="btn"]');
            if (button && !button.classList.contains('btn-press')) {
                button.classList.add('btn-press');
                
                // Remove class after animation
                setTimeout(() => {
                    button.classList.remove('btn-press');
                }, 100);
            }
        });
    }

    /**
     * Initialize success checkmarks
     */
    function initSuccessCheckmarks() {
        // Show success checkmark after form submission
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.dataset.showSuccess === 'true') {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    setTimeout(() => {
                        showSuccessCheckmark(submitBtn);
                    }, 500);
                }
            }
        });
    }

    /**
     * Show success checkmark
     */
    function showSuccessCheckmark(element) {
        const checkmark = document.createElement('span');
        checkmark.className = 'success-checkmark';
        
        // Insert checkmark after element
        element.parentNode.insertBefore(checkmark, element.nextSibling);
        
        // Remove after animation
        setTimeout(() => {
            checkmark.style.opacity = '0';
            checkmark.style.transform = 'scale(0.8)';
            setTimeout(() => {
                checkmark.remove();
            }, 300);
        }, 2000);
    }

    /**
     * Initialize loading spinners in buttons
     */
    function initLoadingSpinners() {
        // Add loading state to buttons with data-loading attribute
        document.addEventListener('click', function(e) {
            const button = e.target.closest('[data-loading]');
            if (button && !button.classList.contains('btn-loading')) {
                addButtonLoading(button);
            }
        });

        // Handle async form submissions
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.dataset.async === 'true') {
                e.preventDefault();
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    addButtonLoading(submitBtn);
                    // Handle async submission
                    handleAsyncFormSubmission(form);
                }
            }
        });
    }

    /**
     * Add loading state to button
     */
    function addButtonLoading(button) {
        button.classList.add('btn-loading');
        button.disabled = true;
        
        // Store original content
        if (!button.dataset.originalContent) {
            button.dataset.originalContent = button.innerHTML;
        }
    }

    /**
     * Remove loading state from button
     */
    function removeButtonLoading(button) {
        button.classList.remove('btn-loading');
        button.disabled = false;
        
        // Restore original content
        if (button.dataset.originalContent) {
            button.innerHTML = button.dataset.originalContent;
            delete button.dataset.originalContent;
        }
    }

    /**
     * Handle async form submission
     */
    function handleAsyncFormSubmission(form) {
        const formData = new FormData(form);
        const url = form.action || window.location.href;
        const method = form.method || 'POST';

        fetch(url, {
            method: method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                removeButtonLoading(submitBtn);
                if (data.success) {
                    showSuccessCheckmark(submitBtn);
                    if (window.toastManager) {
                        window.toastManager.success(data.message || 'Operation completed successfully');
                    }
                } else {
                    if (window.toastManager) {
                        window.toastManager.error(data.message || 'Operation failed');
                    }
                }
            }
        })
        .catch(error => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                removeButtonLoading(submitBtn);
            }
            if (window.toastManager) {
                window.toastManager.error('An error occurred. Please try again.');
            }
            console.error('Form submission error:', error);
        });
    }

    // Export functions for global use
    window.UIEnhancements = {
        showContextMenu,
        hideContextMenu,
        updateBulkSelection,
        clearBulkSelection,
        addButtonLoading,
        removeButtonLoading,
        showSuccessCheckmark,
        openKeyboardShortcutsModal
    };

})();

