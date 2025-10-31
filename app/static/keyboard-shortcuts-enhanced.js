/**
 * Enhanced Keyboard Shortcuts System
 * Advanced features: Recording, Customization, Context-awareness, Visual Cheat Sheet
 * Version: 2.0
 */

(function() {
    'use strict';

    class EnhancedKeyboardShortcuts {
        constructor() {
            this.shortcuts = new Map();
            this.customShortcuts = this.loadFromStorage('custom_shortcuts') || {};
            this.disabledShortcuts = this.loadFromStorage('disabled_shortcuts') || [];
            this.currentContext = 'global';
            this.recording = null;
            this.keySequence = [];
            this.sequenceTimeout = null;
            this.pressedKeys = new Set();
            this.initialized = false;

            // Statistics
            this.stats = this.loadFromStorage('shortcut_stats') || {};
            
            this.init();
        }

        init() {
            if (this.initialized) return;
            this.initialized = true;

            this.registerDefaultShortcuts();
            this.bindGlobalListeners();
            this.detectContext();
            this.createCheatSheetModal();
            this.setupOnboarding();
            
            console.log('✨ Enhanced Keyboard Shortcuts loaded. Press Shift+? for help');
        }

        /**
         * Register all default shortcuts
         */
        registerDefaultShortcuts() {
            // ============ NAVIGATION ============
            this.register('g d', {
                name: 'Go to Dashboard',
                description: 'Navigate to the main dashboard',
                category: 'Navigation',
                icon: 'fa-tachometer-alt',
                action: () => this.navigate('/')
            });

            this.register('g p', {
                name: 'Go to Projects',
                description: 'View all projects',
                category: 'Navigation',
                icon: 'fa-project-diagram',
                action: () => this.navigate('/projects')
            });

            this.register('g t', {
                name: 'Go to Tasks',
                description: 'View all tasks',
                category: 'Navigation',
                icon: 'fa-tasks',
                action: () => this.navigate('/tasks')
            });

            this.register('g c', {
                name: 'Go to Clients',
                description: 'View all clients',
                category: 'Navigation',
                icon: 'fa-users',
                action: () => this.navigate('/clients')
            });

            this.register('g r', {
                name: 'Go to Reports',
                description: 'View reports and analytics',
                category: 'Navigation',
                icon: 'fa-chart-line',
                action: () => this.navigate('/reports')
            });

            this.register('g i', {
                name: 'Go to Invoices',
                description: 'View all invoices',
                category: 'Navigation',
                icon: 'fa-file-invoice',
                action: () => this.navigate('/invoices')
            });

            this.register('g a', {
                name: 'Go to Analytics',
                description: 'View analytics dashboard',
                category: 'Navigation',
                icon: 'fa-chart-pie',
                action: () => this.navigate('/analytics')
            });

            this.register('g k', {
                name: 'Go to Kanban',
                description: 'View kanban board',
                category: 'Navigation',
                icon: 'fa-columns',
                action: () => this.navigate('/kanban')
            });

            this.register('g s', {
                name: 'Go to Settings',
                description: 'Open settings page',
                category: 'Navigation',
                icon: 'fa-cog',
                action: () => this.navigate('/settings')
            });

            // ============ CREATION ACTIONS ============
            this.register('c p', {
                name: 'Create Project',
                description: 'Create a new project',
                category: 'Create',
                icon: 'fa-folder-plus',
                action: () => this.navigate('/projects/create')
            });

            this.register('c t', {
                name: 'Create Task',
                description: 'Create a new task',
                category: 'Create',
                icon: 'fa-plus-square',
                action: () => this.navigate('/tasks/create')
            });

            this.register('c c', {
                name: 'Create Client',
                description: 'Create a new client',
                category: 'Create',
                icon: 'fa-user-plus',
                action: () => this.navigate('/clients/create')
            });

            this.register('c e', {
                name: 'Create Time Entry',
                description: 'Create a new time entry',
                category: 'Create',
                icon: 'fa-clock',
                action: () => this.navigate('/timer/manual')
            });

            this.register('c i', {
                name: 'Create Invoice',
                description: 'Create a new invoice',
                category: 'Create',
                icon: 'fa-file-invoice-dollar',
                action: () => this.navigate('/invoices/create')
            });

            // ============ TIMER CONTROLS ============
            this.register('t s', {
                name: 'Start Timer',
                description: 'Start a new timer',
                category: 'Timer',
                icon: 'fa-play',
                action: () => this.startTimer()
            });

            this.register('t p', {
                name: 'Pause/Stop Timer',
                description: 'Pause or stop the active timer',
                category: 'Timer',
                icon: 'fa-pause',
                action: () => this.stopTimer()
            });

            this.register('t l', {
                name: 'Log Time',
                description: 'Manually log time',
                category: 'Timer',
                icon: 'fa-edit',
                action: () => this.navigate('/timer/manual')
            });

            this.register('t b', {
                name: 'Bulk Time Entry',
                description: 'Create multiple time entries',
                category: 'Timer',
                icon: 'fa-layer-group',
                action: () => this.navigate('/timer/bulk')
            });

            this.register('t v', {
                name: 'View Calendar',
                description: 'Open time calendar view',
                category: 'Timer',
                icon: 'fa-calendar',
                action: () => this.navigate('/timer/calendar')
            });

            // ============ GLOBAL SHORTCUTS ============
            this.register('Ctrl+k', {
                name: 'Command Palette',
                description: 'Open command palette',
                category: 'Global',
                icon: 'fa-terminal',
                action: () => this.openCommandPalette()
            }, { preventDefault: true });

            this.register('Ctrl+/', {
                name: 'Search',
                description: 'Focus search box',
                category: 'Global',
                icon: 'fa-search',
                action: () => this.focusSearch()
            }, { preventDefault: true });

            this.register('Shift+?', {
                name: 'Keyboard Shortcuts',
                description: 'Show keyboard shortcuts cheat sheet',
                category: 'Global',
                icon: 'fa-keyboard',
                action: () => this.showCheatSheet()
            }, { preventDefault: true });

            this.register('Ctrl+b', {
                name: 'Toggle Sidebar',
                description: 'Show/hide the sidebar',
                category: 'Global',
                icon: 'fa-bars',
                action: () => this.toggleSidebar()
            }, { preventDefault: true });

            this.register('Ctrl+Shift+d', {
                name: 'Toggle Dark Mode',
                description: 'Switch between light and dark themes',
                category: 'Global',
                icon: 'fa-moon',
                action: () => this.toggleTheme()
            }, { preventDefault: true });

            this.register('Alt+n', {
                name: 'Notifications',
                description: 'View notifications',
                category: 'Global',
                icon: 'fa-bell',
                action: () => this.openNotifications()
            }, { preventDefault: true });

            // ============ TABLE SHORTCUTS (Context: table) ============
            this.register('Ctrl+a', {
                name: 'Select All Rows',
                description: 'Select all rows in the table',
                category: 'Table',
                icon: 'fa-check-square',
                context: 'table',
                action: () => this.selectAllRows()
            }, { preventDefault: true });

            this.register('Delete', {
                name: 'Delete Selected',
                description: 'Delete selected rows',
                category: 'Table',
                icon: 'fa-trash',
                context: 'table',
                action: () => this.deleteSelected()
            }, { preventDefault: true });

            this.register('Escape', {
                name: 'Clear Selection',
                description: 'Clear table selection',
                category: 'Table',
                icon: 'fa-times',
                context: 'table',
                action: () => this.clearSelection()
            });

            this.register('j', {
                name: 'Next Row',
                description: 'Move to next row',
                category: 'Table',
                icon: 'fa-arrow-down',
                context: 'table',
                action: () => this.navigateRow('down')
            });

            this.register('k', {
                name: 'Previous Row',
                description: 'Move to previous row',
                category: 'Table',
                icon: 'fa-arrow-up',
                context: 'table',
                action: () => this.navigateRow('up')
            });

            // ============ FORM SHORTCUTS (Context: form) ============
            this.register('Ctrl+s', {
                name: 'Save Form',
                description: 'Save the current form',
                category: 'Form',
                icon: 'fa-save',
                context: 'form',
                action: () => this.saveForm()
            }, { preventDefault: true });

            this.register('Ctrl+Enter', {
                name: 'Submit Form',
                description: 'Submit the current form',
                category: 'Form',
                icon: 'fa-check',
                context: 'form',
                action: () => this.submitForm()
            }, { preventDefault: true });

            this.register('Escape', {
                name: 'Cancel',
                description: 'Cancel form editing',
                category: 'Form',
                icon: 'fa-times',
                context: 'form',
                action: () => this.cancelForm()
            });

            // ============ MODAL SHORTCUTS (Context: modal) ============
            this.register('Escape', {
                name: 'Close Modal',
                description: 'Close the active modal',
                category: 'Modal',
                icon: 'fa-times',
                context: 'modal',
                action: () => this.closeModal()
            });

            this.register('Enter', {
                name: 'Confirm',
                description: 'Confirm modal action',
                category: 'Modal',
                icon: 'fa-check',
                context: 'modal',
                action: () => this.confirmModal()
            }, { preventDefault: false });

            // ============ HELP & ACCESSIBILITY ============
            this.register('Alt+h', {
                name: 'Help',
                description: 'Open help page',
                category: 'Help',
                icon: 'fa-question-circle',
                action: () => this.navigate('/help')
            }, { preventDefault: true });

            this.register('Alt+1', {
                name: 'Jump to Main',
                description: 'Jump to main content',
                category: 'Accessibility',
                icon: 'fa-universal-access',
                action: () => this.jumpToMain()
            }, { preventDefault: true });
        }

        /**
         * Register a keyboard shortcut
         */
        register(keys, config, options = {}) {
            const normalizedKeys = this.normalizeKeys(keys);
            const context = config.context || 'global';

            if (!this.shortcuts.has(context)) {
                this.shortcuts.set(context, new Map());
            }

            this.shortcuts.get(context).set(normalizedKeys, {
                ...config,
                keys: keys,
                normalizedKeys: normalizedKeys,
                preventDefault: options.preventDefault !== false,
                stopPropagation: options.stopPropagation || false,
                enabled: !this.disabledShortcuts.includes(normalizedKeys)
            });
        }

        /**
         * Bind global event listeners
         */
        bindGlobalListeners() {
            document.addEventListener('keydown', (e) => this.handleKeyDown(e));
            document.addEventListener('keyup', (e) => this.handleKeyUp(e));
            document.addEventListener('focusin', () => this.detectContext());
            window.addEventListener('popstate', () => this.detectContext());
            
            // Clear sequence on window blur
            window.addEventListener('blur', () => this.resetSequence());
        }

        /**
         * Handle key down event
         */
        handleKeyDown(e) {
            console.log('[KS-Enhanced] Key pressed:', e.key);
            
            // Track pressed keys
            this.pressedKeys.add(e.key.toLowerCase());

            // Skip if in recording mode
            if (this.recording) {
                this.handleRecording(e);
                return;
            }

            // Check if typing in input first
            const isTyping = this.isTypingContext(e);
            const combo = this.getKeyCombo(e);
            
            console.log('[KS-Enhanced] isTyping:', isTyping, 'combo:', combo);

            // If typing in input, ONLY allow specific combos
            if (isTyping) {
                if (!this.isAllowedInInput(combo)) {
                    console.log('[KS-Enhanced] BLOCKED - typing in input, not allowed combo');
                    // Clear any key sequence when user is typing
                    this.resetSequence();
                    return;
                }
                console.log('[KS-Enhanced] Allowed combo in input:', combo);
            }

            const normalizedCombo = this.normalizeKeys(combo);

            // Check for custom shortcut override
            if (this.customShortcuts[normalizedCombo]) {
                e.preventDefault();
                this.executeShortcut(this.customShortcuts[normalizedCombo]);
                this.recordUsage(normalizedCombo);
                return;
            }

            // Check context-specific shortcuts
            const contextShortcuts = this.shortcuts.get(this.currentContext);
            if (contextShortcuts && contextShortcuts.has(normalizedCombo)) {
                const shortcut = contextShortcuts.get(normalizedCombo);
                if (shortcut.enabled) {
                    if (shortcut.preventDefault) e.preventDefault();
                    if (shortcut.stopPropagation) e.stopPropagation();
                    shortcut.action();
                    this.recordUsage(normalizedCombo);
                    return;
                }
            }

            // Check global shortcuts
            const globalShortcuts = this.shortcuts.get('global');
            if (globalShortcuts && globalShortcuts.has(normalizedCombo)) {
                const shortcut = globalShortcuts.get(normalizedCombo);
                if (shortcut.enabled) {
                    if (shortcut.preventDefault) e.preventDefault();
                    if (shortcut.stopPropagation) e.stopPropagation();
                    shortcut.action();
                    this.recordUsage(normalizedCombo);
                    return;
                }
            }

            // Handle key sequences (like 'g d') - but NOT if typing in input
            if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1 && !isTyping) {
                console.log('[KS-Enhanced] Processing sequence for key:', e.key);
                this.handleSequence(e);
            } else {
                console.log('[KS-Enhanced] NOT processing sequence - modifiers or typing');
            }
        }

        /**
         * Handle key up event
         */
        handleKeyUp(e) {
            this.pressedKeys.delete(e.key.toLowerCase());
        }

        /**
         * Handle key sequences like 'g d' or 'g p'
         */
        handleSequence(e) {
            // Double-check: should never be called if typing, but just in case
            if (this.isTypingContext(e)) {
                this.resetSequence();
                return;
            }

            clearTimeout(this.sequenceTimeout);
            
            this.keySequence.push(e.key.toLowerCase());
            
            // Limit sequence length
            if (this.keySequence.length > 3) {
                this.keySequence.shift();
            }

            // Try to match sequence
            const sequenceStr = this.keySequence.join(' ');
            const normalized = this.normalizeKeys(sequenceStr);

            // Check all contexts for sequence match
            let matched = false;
            for (const [context, shortcuts] of this.shortcuts) {
                if (shortcuts.has(normalized)) {
                    const shortcut = shortcuts.get(normalized);
                    if (shortcut.enabled && (context === 'global' || context === this.currentContext)) {
                        e.preventDefault();
                        shortcut.action();
                        this.recordUsage(normalized);
                        this.resetSequence();
                        matched = true;
                        break;
                    }
                }
            }

            if (!matched) {
                // Reset sequence after timeout
                this.sequenceTimeout = setTimeout(() => {
                    this.resetSequence();
                }, 1000);
            }
        }

        /**
         * Get key combination from event
         */
        getKeyCombo(e) {
            const parts = [];
            
            if (e.ctrlKey || e.metaKey) parts.push('Ctrl');
            if (e.altKey) parts.push('Alt');
            if (e.shiftKey && e.key.length > 1) parts.push('Shift');
            
            let key = e.key;
            if (key === ' ') key = 'Space';
            
            parts.push(key);
            
            return parts.join('+');
        }

        /**
         * Normalize keys for consistent matching
         */
        normalizeKeys(keys) {
            return keys.toLowerCase()
                .replace(/\s+/g, ' ')
                .replace(/command|cmd/gi, 'ctrl')
                .trim();
        }

        /**
         * Check if user is typing in an input field
         */
        isTypingContext(e) {
            const target = e.target;
            const tagName = target.tagName.toLowerCase();
            
            // Check standard input elements
            if (tagName === 'input' || 
                tagName === 'textarea' || 
                tagName === 'select' ||
                target.isContentEditable) {
                return true;
            }
            
            // Check for rich text editors (Toast UI Editor, TinyMCE, CodeMirror, etc.)
            const richEditorSelectors = [
                '.toastui-editor',
                '.toastui-editor-contents',
                '.ProseMirror',
                '.CodeMirror',
                '.ql-editor',  // Quill
                '.tox-edit-area',  // TinyMCE
                '.note-editable',  // Summernote
                '[contenteditable="true"]',
                // Additional Toast UI Editor specific selectors
                '.toastui-editor-ww-container',
                '.toastui-editor-md-container',
                '.te-editor',
                '.te-ww-container',
                '.te-md-container'
            ];
            
            // Check if target is within any rich text editor
            for (const selector of richEditorSelectors) {
                if (target.closest && target.closest(selector)) {
                    return true;
                }
            }
            
            return false;
        }

        /**
         * Check if shortcut is allowed even in input fields
         */
        isAllowedInInput(combo) {
            const allowed = [
                'ctrl+k',
                'ctrl+/',
                'shift+?',
                'escape',
                'ctrl+s',
                'ctrl+enter'
            ];
            return allowed.includes(this.normalizeKeys(combo));
        }

        /**
         * Detect current context based on DOM state
         */
        detectContext() {
            const activeElement = document.activeElement;

            // Check for modal
            if (document.querySelector('.modal:not(.hidden), [role="dialog"]:not(.hidden)') ||
                document.querySelector('.fixed.inset-0[style*="z-index"]')) {
                this.currentContext = 'modal';
                return;
            }

            // Check for table
            if (activeElement && activeElement.closest('table[data-enhanced]')) {
                this.currentContext = 'table';
                return;
            }

            // Check for form
            if (activeElement && activeElement.closest('form[data-enhanced]')) {
                this.currentContext = 'form';
                return;
            }

            this.currentContext = 'global';
        }

        /**
         * Reset key sequence
         */
        resetSequence() {
            this.keySequence = [];
            clearTimeout(this.sequenceTimeout);
        }

        /**
         * Record shortcut usage for statistics
         */
        recordUsage(shortcutKey) {
            if (!this.stats[shortcutKey]) {
                this.stats[shortcutKey] = {
                    count: 0,
                    lastUsed: null
                };
            }
            
            this.stats[shortcutKey].count++;
            this.stats[shortcutKey].lastUsed = new Date().toISOString();
            
            this.saveToStorage('shortcut_stats', this.stats);
        }

        // ============ ACTION IMPLEMENTATIONS ============

        navigate(url) {
            window.location.href = url;
        }

        openCommandPalette() {
            if (window.openCommandPalette) {
                window.openCommandPalette();
            } else {
                const modal = document.getElementById('commandPaletteModal');
                if (modal) {
                    modal.classList.remove('hidden');
                    setTimeout(() => {
                        const input = document.getElementById('commandPaletteInput');
                        if (input) input.focus();
                    }, 100);
                }
            }
        }

        focusSearch() {
            const searchInput = document.getElementById('search') || 
                              document.querySelector('input[type="search"]') ||
                              document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        toggleSidebar() {
            const btn = document.getElementById('sidebarCollapseBtn');
            if (btn) btn.click();
        }

        toggleTheme() {
            const btn = document.getElementById('theme-toggle');
            if (btn) btn.click();
        }

        openNotifications() {
            const btn = document.querySelector('[data-notifications-toggle]');
            if (btn) btn.click();
        }

        async startTimer() {
            const btn = document.querySelector('#openStartTimer');
            if (btn) {
                btn.click();
            } else {
                this.navigate('/timer/manual');
            }
        }

        async stopTimer() {
            try {
                const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                const res = await fetch('/timer/stop', {
                    method: 'POST',
                    headers: { 'X-CSRF-Token': token || '' },
                    credentials: 'same-origin'
                });
                
                if (res.ok) {
                    this.showToast(window.i18n?.messages?.timerStopped || 'Timer stopped', 'info');
                } else {
                    this.showToast(window.i18n?.messages?.timerStopFailed || 'Failed to stop timer', 'warning');
                }
            } catch (e) {
                this.showToast(window.i18n?.messages?.errorStoppingTimer || 'Error stopping timer', 'danger');
            }
        }

        selectAllRows() {
            const checkbox = document.querySelector('.select-all-checkbox');
            if (checkbox) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        deleteSelected() {
            if (window.bulkDelete) {
                window.bulkDelete();
            }
        }

        clearSelection() {
            const checkboxes = document.querySelectorAll('.row-checkbox:checked');
            checkboxes.forEach(cb => {
                cb.checked = false;
                cb.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        navigateRow(direction) {
            const table = document.activeElement.closest('table');
            if (!table) return;

            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const currentRow = document.activeElement.closest('tr');
            const currentIndex = rows.indexOf(currentRow);

            if (currentIndex === -1) {
                if (rows.length > 0) rows[0].focus();
                return;
            }

            const newIndex = direction === 'down' ? 
                Math.min(currentIndex + 1, rows.length - 1) :
                Math.max(currentIndex - 1, 0);

            if (rows[newIndex]) {
                rows[newIndex].focus();
                rows[newIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            }
        }

        saveForm() {
            const form = document.querySelector('form[data-auto-save]');
            if (form) {
                form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            } else {
                this.showToast(window.i18n?.messages?.noFormToSave || 'No form to save', 'warning');
            }
        }

        submitForm() {
            const form = document.activeElement.closest('form');
            if (form && form.requestSubmit) {
                form.requestSubmit();
            } else if (form) {
                form.submit();
            }
        }

        cancelForm() {
            const cancelBtn = document.querySelector('[data-cancel], button[onclick*="cancel"]');
            if (cancelBtn) {
                cancelBtn.click();
            } else {
                window.history.back();
            }
        }

        closeModal() {
            const modal = document.querySelector('.modal:not(.hidden), [role="dialog"]:not(.hidden)');
            if (modal) {
                const closeBtn = modal.querySelector('[data-close], .close, button[data-bs-dismiss]');
                if (closeBtn) {
                    closeBtn.click();
                } else {
                    modal.classList.add('hidden');
                }
            }
        }

        confirmModal() {
            const modal = document.querySelector('.modal:not(.hidden), [role="dialog"]:not(.hidden)');
            if (modal && document.activeElement.tagName !== 'TEXTAREA') {
                const confirmBtn = modal.querySelector('button[type="submit"], [data-confirm]');
                if (confirmBtn) confirmBtn.click();
            }
        }

        jumpToMain() {
            const main = document.getElementById('mainContentAnchor') || 
                        document.querySelector('main') ||
                        document.getElementById('main-content');
            if (main) {
                main.focus();
                main.scrollIntoView({ behavior: 'smooth' });
            }
        }

        showToast(message, type = 'info') {
            if (window.TimeTrackerUI && window.TimeTrackerUI.showToast) {
                window.TimeTrackerUI.showToast(message, type);
            } else if (window.toastManager) {
                window.toastManager[type](message);
            } else {
                console.log(`[${type}] ${message}`);
            }
        }

        // ============ CHEAT SHEET & CUSTOMIZATION ============

        /**
         * Create cheat sheet modal
         */
        createCheatSheetModal() {
            const modal = document.createElement('div');
            modal.id = 'keyboard-shortcuts-cheat-sheet';
            modal.className = 'fixed inset-0 z-[9999] hidden';
            modal.innerHTML = `
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" data-close></div>
                <div class="relative flex items-center justify-center min-h-screen p-4">
                    <div class="relative bg-card-light dark:bg-card-dark rounded-lg shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
                        <!-- Header -->
                        <div class="p-6 border-b border-border-light dark:border-border-dark flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <i class="fas fa-keyboard text-2xl text-primary"></i>
                                <div>
                                    <h2 class="text-2xl font-bold text-text-light dark:text-text-dark">Keyboard Shortcuts</h2>
                                    <p class="text-sm text-text-muted-light dark:text-text-muted-dark mt-1">Master these shortcuts to work faster</p>
                                </div>
                            </div>
                            <button data-close class="p-2 hover:bg-background-light dark:hover:bg-background-dark rounded-lg transition-colors">
                                <i class="fas fa-times text-xl"></i>
                            </button>
                        </div>

                        <!-- Search -->
                        <div class="p-4 border-b border-border-light dark:border-border-dark">
                            <div class="relative">
                                <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-text-muted-light dark:text-text-muted-dark"></i>
                                <input type="text" 
                                       id="shortcuts-search"
                                       placeholder="Search shortcuts..." 
                                       class="w-full pl-10 pr-4 py-2 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg focus:outline-none focus:ring-2 focus:ring-primary">
                            </div>
                        </div>

                        <!-- Tabs -->
                        <div class="border-b border-border-light dark:border-border-dark">
                            <div class="flex overflow-x-auto px-6" id="shortcut-tabs">
                                <button data-category="all" class="px-4 py-3 font-medium border-b-2 border-primary text-primary whitespace-nowrap">All</button>
                            </div>
                        </div>

                        <!-- Content -->
                        <div class="flex-1 overflow-y-auto p-6" id="shortcuts-content">
                            <!-- Content will be dynamically generated -->
                        </div>

                        <!-- Footer -->
                        <div class="p-4 border-t border-border-light dark:border-border-dark flex items-center justify-between bg-background-light dark:bg-background-dark">
                            <div class="text-sm text-text-muted-light dark:text-text-muted-dark">
                                <i class="fas fa-info-circle mr-2"></i>
                                <span id="shortcuts-count">0 shortcuts available</span>
                            </div>
                            <div class="flex gap-2">
                                <button data-customize class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors">
                                    <i class="fas fa-cog mr-2"></i>Customize
                                </button>
                                <button data-print class="px-4 py-2 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                                    <i class="fas fa-print mr-2"></i>Print
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Bind events
            modal.querySelector('[data-close]').addEventListener('click', () => this.hideCheatSheet());
            modal.querySelector('#shortcuts-search').addEventListener('input', (e) => this.filterCheatSheet(e.target.value));
            modal.querySelector('[data-customize]').addEventListener('click', () => this.openCustomization());
            modal.querySelector('[data-print]').addEventListener('click', () => this.printCheatSheet());
            
            // Close on background click
            modal.addEventListener('click', (e) => {
                if (e.target.hasAttribute('data-close')) {
                    this.hideCheatSheet();
                }
            });
        }

        /**
         * Show cheat sheet
         */
        showCheatSheet() {
            const modal = document.getElementById('keyboard-shortcuts-cheat-sheet');
            if (!modal) return;

            modal.classList.remove('hidden');
            this.renderCheatSheet();
            
            setTimeout(() => {
                const searchInput = document.getElementById('shortcuts-search');
                if (searchInput) searchInput.focus();
            }, 100);
        }

        /**
         * Hide cheat sheet
         */
        hideCheatSheet() {
            const modal = document.getElementById('keyboard-shortcuts-cheat-sheet');
            if (modal) modal.classList.add('hidden');
        }

        /**
         * Render cheat sheet content
         */
        renderCheatSheet(filter = '', category = 'all') {
            const content = document.getElementById('shortcuts-content');
            const tabs = document.getElementById('shortcut-tabs');
            if (!content || !tabs) return;

            // Get all shortcuts grouped by category
            const grouped = new Map();
            let totalCount = 0;

            for (const [context, shortcuts] of this.shortcuts) {
                for (const [key, shortcut] of shortcuts) {
                    if (!shortcut.enabled) continue;
                    
                    const cat = shortcut.category || 'Other';
                    if (!grouped.has(cat)) {
                        grouped.set(cat, []);
                    }
                    grouped.set(cat, [...grouped.get(cat), { ...shortcut, context }]);
                    totalCount++;
                }
            }

            // Render tabs
            const categories = ['all', ...Array.from(grouped.keys()).sort()];
            tabs.innerHTML = categories.map(cat => `
                <button data-category="${cat}" 
                        class="px-4 py-3 font-medium border-b-2 ${cat === category ? 'border-primary text-primary' : 'border-transparent text-text-muted-light dark:text-text-muted-dark hover:text-text-light dark:hover:text-text-dark'} whitespace-nowrap transition-colors">
                    ${cat.charAt(0).toUpperCase() + cat.slice(1)}
                </button>
            `).join('');

            // Bind tab clicks
            tabs.querySelectorAll('[data-category]').forEach(tab => {
                tab.addEventListener('click', () => this.renderCheatSheet(filter, tab.dataset.category));
            });

            // Filter shortcuts
            let filteredGroups = grouped;
            if (category !== 'all') {
                filteredGroups = new Map([[category, grouped.get(category) || []]]);
            }

            if (filter) {
                const lowerFilter = filter.toLowerCase();
                filteredGroups = new Map();
                for (const [cat, shortcuts] of grouped) {
                    if (category !== 'all' && cat !== category) continue;
                    const filtered = shortcuts.filter(s => 
                        s.name.toLowerCase().includes(lowerFilter) ||
                        s.description.toLowerCase().includes(lowerFilter) ||
                        s.keys.toLowerCase().includes(lowerFilter)
                    );
                    if (filtered.length > 0) {
                        filteredGroups.set(cat, filtered);
                    }
                }
            }

            // Render content
            if (filteredGroups.size === 0) {
                content.innerHTML = `
                    <div class="text-center py-12 text-text-muted-light dark:text-text-muted-dark">
                        <i class="fas fa-search text-4xl mb-4 opacity-50"></i>
                        <p>No shortcuts found</p>
                    </div>
                `;
            } else {
                content.innerHTML = Array.from(filteredGroups).map(([cat, shortcuts]) => `
                    <div class="mb-8">
                        <h3 class="text-lg font-semibold mb-4 text-primary flex items-center gap-2">
                            <i class="fas ${shortcuts[0]?.icon || 'fa-keyboard'}"></i>
                            ${cat}
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            ${shortcuts.map(s => `
                                <div class="p-4 bg-background-light dark:bg-background-dark rounded-lg border border-border-light dark:border-border-dark hover:border-primary transition-colors">
                                    <div class="flex items-start justify-between gap-3">
                                        <div class="flex-1 min-w-0">
                                            <div class="font-medium text-text-light dark:text-text-dark flex items-center gap-2">
                                                <i class="fas ${s.icon || 'fa-keyboard'} text-sm text-primary"></i>
                                                ${s.name}
                                            </div>
                                            <div class="text-sm text-text-muted-light dark:text-text-muted-dark mt-1">
                                                ${s.description}
                                            </div>
                                            ${s.context !== 'global' ? `<div class="text-xs text-primary mt-1">Context: ${s.context}</div>` : ''}
                                        </div>
                                        <div class="flex-shrink-0">
                                            ${this.formatKeysForDisplay(s.keys)}
                                        </div>
                                    </div>
                                    ${this.stats[s.normalizedKeys] ? `
                                        <div class="mt-2 text-xs text-text-muted-light dark:text-text-muted-dark">
                                            Used ${this.stats[s.normalizedKeys].count} times
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            }

            // Update count
            const countEl = document.getElementById('shortcuts-count');
            if (countEl) {
                countEl.textContent = `${totalCount} shortcuts available`;
            }
        }

        /**
         * Format keys for display
         */
        formatKeysForDisplay(keys) {
            return keys.split('+').map(key => {
                let displayKey = key;
                if (key === 'Ctrl') displayKey = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl';
                if (key === 'Shift') displayKey = '⇧';
                if (key === 'Alt') displayKey = '⌥';
                if (key === 'Enter') displayKey = '↵';
                if (key === 'Space') displayKey = '␣';
                
                return `<kbd class="px-2 py-1 text-xs font-mono bg-card-light dark:bg-card-dark border border-border-light dark:border-border-dark rounded">${displayKey}</kbd>`;
            }).join('<span class="mx-1 text-text-muted-light dark:text-text-muted-dark">+</span>');
        }

        /**
         * Filter cheat sheet
         */
        filterCheatSheet(query) {
            const tabs = document.getElementById('shortcut-tabs');
            const activeTab = tabs?.querySelector('[data-category].border-primary');
            const category = activeTab?.dataset.category || 'all';
            this.renderCheatSheet(query, category);
        }

        /**
         * Open customization UI
         */
        openCustomization() {
            this.navigate('/settings/keyboard-shortcuts');
        }

        /**
         * Print cheat sheet
         */
        printCheatSheet() {
            window.print();
        }

        /**
         * Setup onboarding hint
         */
        setupOnboarding() {
            const seen = this.loadFromStorage('shortcuts_onboarding_seen');
            if (seen) return;

            setTimeout(() => {
                this.showOnboardingHint();
                this.saveToStorage('shortcuts_onboarding_seen', true);
            }, 5000);
        }

        /**
         * Show onboarding hint
         */
        showOnboardingHint() {
            const hint = document.createElement('div');
            hint.className = 'fixed bottom-4 right-4 z-[9998] bg-primary text-white p-4 rounded-lg shadow-2xl max-w-sm animate-slide-in-right';
            hint.innerHTML = `
                <div class="flex items-start gap-3">
                    <i class="fas fa-keyboard text-2xl"></i>
                    <div class="flex-1">
                        <div class="font-semibold mb-1">💡 Pro Tip: Keyboard Shortcuts</div>
                        <div class="text-sm opacity-90">
                            Press <kbd class="px-2 py-1 bg-white/20 rounded">Shift</kbd> + <kbd class="px-2 py-1 bg-white/20 rounded">?</kbd> to see all available keyboard shortcuts
                        </div>
                    </div>
                    <button class="hover:bg-white/20 rounded p-1 transition-colors" data-dismiss>
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;

            document.body.appendChild(hint);

            hint.querySelector('[data-dismiss]').addEventListener('click', () => {
                hint.remove();
            });

            setTimeout(() => {
                hint.remove();
            }, 10000);
        }

        /**
         * Handle shortcut recording
         */
        handleRecording(e) {
            e.preventDefault();
            
            const combo = this.getKeyCombo(e);
            
            if (this.recording.callback) {
                this.recording.callback(combo);
            }
            
            this.recording = null;
        }

        /**
         * Start recording a shortcut
         */
        startRecording(callback) {
            this.recording = { callback };
        }

        /**
         * Storage helpers
         */
        saveToStorage(key, value) {
            try {
                localStorage.setItem(`tt_shortcuts_${key}`, JSON.stringify(value));
            } catch (e) {
                console.warn('Failed to save to storage:', e);
            }
        }

        loadFromStorage(key) {
            try {
                const item = localStorage.getItem(`tt_shortcuts_${key}`);
                return item ? JSON.parse(item) : null;
            } catch (e) {
                return null;
            }
        }

        /**
         * Execute custom shortcut action
         */
        executeShortcut(action) {
            if (typeof action === 'function') {
                action();
            } else if (typeof action === 'string') {
                // Assume it's a URL
                this.navigate(action);
            }
        }
    }

    // Initialize
    if (!window.enhancedKeyboardShortcuts) {
        window.enhancedKeyboardShortcuts = new EnhancedKeyboardShortcuts();
    }

})();

