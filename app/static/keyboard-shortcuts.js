/**
 * Keyboard Shortcuts & Command Palette System
 * Provides power user features for quick navigation and actions
 */

(function() {
    'use strict';

    class KeyboardShortcuts {
        constructor(options = {}) {
            this.options = {
                commandPaletteKey: options.commandPaletteKey || 'k',
                helpKey: options.helpKey || '?',
                shortcuts: options.shortcuts || this.getDefaultShortcuts(),
                ...options
            };

            this.commandPalette = null;
            this.currentFocus = 0;
            this.filteredCommands = [];
            this.isCommandPaletteOpen = false;

            this.init();
        }

        init() {
            this.createCommandPalette();
            this.bindGlobalShortcuts();
            this.registerDefaultShortcuts();
            this.detectKeyboardNavigation();
            this.showHintIfFirstVisit();
        }

        getDefaultShortcuts() {
            return [
                // Navigation
                {
                    id: 'go-dashboard',
                    category: 'Navigation',
                    title: 'Go to Dashboard',
                    description: 'Navigate to main dashboard',
                    icon: 'fas fa-tachometer-alt',
                    keys: ['g', 'd'],
                    action: () => window.location.href = '/'
                },
                {
                    id: 'go-projects',
                    category: 'Navigation',
                    title: 'Go to Projects',
                    description: 'View all projects',
                    icon: 'fas fa-project-diagram',
                    keys: ['g', 'p'],
                    action: () => window.location.href = '/projects'
                },
                {
                    id: 'go-tasks',
                    category: 'Navigation',
                    title: 'Go to Tasks',
                    description: 'View all tasks',
                    icon: 'fas fa-tasks',
                    keys: ['g', 't'],
                    action: () => window.location.href = '/tasks'
                },
                {
                    id: 'go-reports',
                    category: 'Navigation',
                    title: 'Go to Reports',
                    description: 'View reports and analytics',
                    icon: 'fas fa-chart-line',
                    keys: ['g', 'r'],
                    action: () => window.location.href = '/reports'
                },
                {
                    id: 'go-invoices',
                    category: 'Navigation',
                    title: 'Go to Invoices',
                    description: 'View invoices',
                    icon: 'fas fa-file-invoice',
                    keys: ['g', 'i'],
                    action: () => window.location.href = '/invoices'
                },

                // Actions
                {
                    id: 'new-entry',
                    category: 'Actions',
                    title: 'New Time Entry',
                    description: 'Create a new time entry',
                    icon: 'fas fa-plus',
                    keys: ['n', 'e'],
                    action: () => window.location.href = '/timer/manual-entry'
                },
                {
                    id: 'new-project',
                    category: 'Actions',
                    title: 'New Project',
                    description: 'Create a new project',
                    icon: 'fas fa-folder-plus',
                    keys: ['n', 'p'],
                    action: () => window.location.href = '/projects/create'
                },
                {
                    id: 'new-task',
                    category: 'Actions',
                    title: 'New Task',
                    description: 'Create a new task',
                    icon: 'fas fa-tasks',
                    keys: ['n', 't'],
                    action: () => window.location.href = '/tasks/create'
                },
                {
                    id: 'new-client',
                    category: 'Actions',
                    title: 'New Client',
                    description: 'Create a new client',
                    icon: 'fas fa-user-plus',
                    keys: ['n', 'c'],
                    action: () => window.location.href = '/clients/create'
                },

                // Timer Controls
                {
                    id: 'toggle-timer',
                    category: 'Timer',
                    title: 'Start/Stop Timer',
                    description: 'Toggle the active timer',
                    icon: 'fas fa-stopwatch',
                    keys: ['t'],
                    action: () => this.toggleTimer()
                },

                // Search & Help
                {
                    id: 'search',
                    category: 'General',
                    title: 'Search',
                    description: 'Focus search box (Ctrl+K)',
                    icon: 'fas fa-search',
                    keys: ['Ctrl', 'K'],
                    ctrl: true,
                    action: () => this.focusSearch()
                },
                {
                    id: 'command-palette',
                    category: 'General',
                    title: 'Command Palette',
                    description: 'Open command palette',
                    icon: 'fas fa-bolt',
                    keys: ['?'],
                    action: () => this.openCommandPalette()
                },
                {
                    id: 'help',
                    category: 'General',
                    title: 'Keyboard Shortcuts Help',
                    description: 'Show all keyboard shortcuts',
                    icon: 'fas fa-keyboard',
                    keys: ['Shift', '?'],
                    shift: true,
                    action: () => this.showHelp()
                },

                // Theme
                {
                    id: 'toggle-theme',
                    category: 'General',
                    title: 'Toggle Theme',
                    description: 'Switch between light and dark mode',
                    icon: 'fas fa-moon',
                    keys: ['Ctrl', 'Shift', 'L'],
                    ctrl: true,
                    shift: true,
                    action: () => this.toggleTheme()
                }
            ];
        }

        registerDefaultShortcuts() {
            this.options.shortcuts.forEach(shortcut => {
                this.registerShortcut(shortcut);
            });
        }

        registerShortcut(shortcut) {
            // Shortcuts are handled in the global listener
            // This method allows external registration
            if (!this.options.shortcuts.find(s => s.id === shortcut.id)) {
                this.options.shortcuts.push(shortcut);
            }
        }

        bindGlobalShortcuts() {
            let keySequence = [];
            let sequenceTimer = null;

            document.addEventListener('keydown', (e) => {
                // Focus search with Ctrl+K or Cmd+K (allowed even in inputs)
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    this.focusSearch();
                    return;
                }

                // Open command palette with ? (allowed even in inputs, but only if Shift is pressed)
                if (e.key === '?' && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
                    e.preventDefault();
                    this.openCommandPalette();
                    return;
                }

                // Help with Shift+? (or Ctrl/Cmd+?) (allowed even in inputs)
                if ((e.key === '?' && e.shiftKey) || (e.key === '/' && e.ctrlKey)) {
                    e.preventDefault();
                    this.showHelp();
                    return;
                }

                // Ignore ALL other shortcuts if typing in input
                if (this.isTyping(e)) {
                    // Clear any existing key sequence when user starts typing
                    keySequence = [];
                    clearTimeout(sequenceTimer);
                    return;
                }

                // Handle key sequences (like 'g' then 'd')
                clearTimeout(sequenceTimer);
                keySequence.push(e.key.toLowerCase());

                sequenceTimer = setTimeout(() => {
                    keySequence = [];
                }, 1000);

                // Check for matching shortcuts
                this.checkShortcuts(keySequence, e);
            });
        }

        checkShortcuts(keySequence, event) {
            for (const shortcut of this.options.shortcuts) {
                if (this.matchesShortcut(keySequence, shortcut, event)) {
                    event.preventDefault();
                    shortcut.action();
                    return;
                }
            }
        }

        matchesShortcut(keySequence, shortcut, event) {
            // Check modifier keys
            if (shortcut.ctrl && !event.ctrlKey && !event.metaKey) return false;
            if (shortcut.shift && !event.shiftKey) return false;
            if (shortcut.alt && !event.altKey) return false;

            // Check key sequence
            if (shortcut.keys.length !== keySequence.length) return false;

            return shortcut.keys.every((key, index) => {
                return key.toLowerCase() === keySequence[index].toLowerCase();
            });
        }

        createCommandPalette() {
            const palette = document.createElement('div');
            palette.className = 'command-palette';
            palette.innerHTML = `
                <div class="command-palette-container">
                    <div class="command-search">
                        <i class="fas fa-search command-search-icon"></i>
                        <input type="text" placeholder="Type a command or search..." autocomplete="off">
                    </div>
                    <div class="command-results"></div>
                    <div class="command-footer">
                        <div class="command-footer-actions">
                            <span class="command-footer-action">
                                <kbd class="command-kbd">↑↓</kbd> Navigate
                            </span>
                            <span class="command-footer-action">
                                <kbd class="command-kbd">↵</kbd> Select
                            </span>
                            <span class="command-footer-action">
                                <kbd class="command-kbd">Esc</kbd> Close
                            </span>
                        </div>
                        <div>
                            <span class="command-footer-action">
                                <kbd class="command-kbd">Shift</kbd>+<kbd class="command-kbd">?</kbd> Help
                            </span>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(palette);
            this.commandPalette = palette;

            this.bindCommandPaletteEvents();
        }

        bindCommandPaletteEvents() {
            const input = this.commandPalette.querySelector('.command-search input');
            const results = this.commandPalette.querySelector('.command-results');

            // Close on background click
            this.commandPalette.addEventListener('click', (e) => {
                if (e.target === this.commandPalette) {
                    this.closeCommandPalette();
                }
            });

            // Input events
            input.addEventListener('input', (e) => {
                this.filterCommands(e.target.value);
            });

            // Keyboard navigation
            input.addEventListener('keydown', (e) => {
                const items = results.querySelectorAll('.command-item');

                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        this.currentFocus++;
                        if (this.currentFocus >= items.length) this.currentFocus = 0;
                        this.setActivePaletteItem(items);
                        break;

                    case 'ArrowUp':
                        e.preventDefault();
                        this.currentFocus--;
                        if (this.currentFocus < 0) this.currentFocus = items.length - 1;
                        this.setActivePaletteItem(items);
                        break;

                    case 'Enter':
                        e.preventDefault();
                        if (items[this.currentFocus]) {
                            items[this.currentFocus].click();
                        }
                        break;

                    case 'Escape':
                        this.closeCommandPalette();
                        break;
                }
            });
        }

        openCommandPalette() {
            this.isCommandPaletteOpen = true;
            this.commandPalette.classList.add('show');
            const input = this.commandPalette.querySelector('.command-search input');
            input.value = '';
            input.focus();
            this.filterCommands('');
        }

        closeCommandPalette() {
            this.isCommandPaletteOpen = false;
            this.commandPalette.classList.remove('show');
            this.currentFocus = 0;
        }

        filterCommands(query) {
            const allCommands = this.options.shortcuts;
            
            if (!query) {
                this.filteredCommands = allCommands;
            } else {
                const lowerQuery = query.toLowerCase();
                this.filteredCommands = allCommands.filter(cmd => {
                    return cmd.title.toLowerCase().includes(lowerQuery) ||
                           cmd.description.toLowerCase().includes(lowerQuery) ||
                           cmd.category.toLowerCase().includes(lowerQuery);
                });
            }

            this.renderCommandResults();
        }

        renderCommandResults() {
            const results = this.commandPalette.querySelector('.command-results');
            
            if (this.filteredCommands.length === 0) {
                results.innerHTML = `
                    <div class="command-empty">
                        <i class="fas fa-search"></i>
                        <p>No commands found</p>
                    </div>
                `;
                return;
            }

            // Group by category
            const grouped = {};
            this.filteredCommands.forEach(cmd => {
                if (!grouped[cmd.category]) {
                    grouped[cmd.category] = [];
                }
                grouped[cmd.category].push(cmd);
            });

            let html = '';
            for (const [category, commands] of Object.entries(grouped)) {
                html += `
                    <div class="command-section">
                        <div class="command-section-title">${category}</div>
                        ${commands.map(cmd => this.renderCommandItem(cmd)).join('')}
                    </div>
                `;
            }

            results.innerHTML = html;
            this.currentFocus = 0;
            this.setActivePaletteItem(results.querySelectorAll('.command-item'));
            this.bindCommandItemEvents();
        }

        renderCommandItem(command) {
            const shortcut = this.formatShortcut(command);
            return `
                <div class="command-item" data-command-id="${command.id}">
                    <div class="command-item-icon">
                        <i class="${command.icon}"></i>
                    </div>
                    <div class="command-item-content">
                        <div class="command-item-title">${command.title}</div>
                        <div class="command-item-description">${command.description}</div>
                    </div>
                    ${shortcut ? `<div class="command-item-shortcut">${shortcut}</div>` : ''}
                </div>
            `;
        }

        formatShortcut(command) {
            if (!command.keys || command.keys.length === 0) return '';
            
            return command.keys.map(key => {
                let displayKey = key;
                if (key === 'Ctrl') displayKey = '⌃';
                if (key === 'Shift') displayKey = '⇧';
                if (key === 'Alt') displayKey = '⌥';
                if (key === 'Meta') displayKey = '⌘';
                
                return `<kbd class="command-kbd">${displayKey}</kbd>`;
            }).join('');
        }

        bindCommandItemEvents() {
            const items = this.commandPalette.querySelectorAll('.command-item');
            items.forEach((item, index) => {
                item.addEventListener('mouseenter', () => {
                    this.currentFocus = index;
                    this.setActivePaletteItem(items);
                });

                item.addEventListener('click', () => {
                    const commandId = item.getAttribute('data-command-id');
                    const command = this.options.shortcuts.find(c => c.id === commandId);
                    if (command) {
                        command.action();
                        this.closeCommandPalette();
                    }
                });
            });
        }

        setActivePaletteItem(items) {
            items.forEach((item, index) => {
                item.classList.remove('active');
                if (index === this.currentFocus) {
                    item.classList.add('active');
                    item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                }
            });
        }

        // Helper methods
        focusSearch() {
            // Find and focus the search input
            const searchInput = document.querySelector('input[type="search"]') ||
                              document.querySelector('[data-enhanced-search]') ||
                              document.querySelector('.search-enhanced input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        toggleTimer() {
            // Find and click the timer button
            const timerBtn = document.querySelector('[data-timer-toggle]') || 
                           document.querySelector('button[type="submit"][form*="timer"]');
            if (timerBtn) {
                timerBtn.click();
            } else {
                window.TimeTrackerUI.showToast(window.i18n?.messages?.noTimerFound || 'No timer found', 'warning');
            }
        }

        toggleTheme() {
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.click();
            }
        }

        showHelp() {
            // Show shortcuts help modal
            this.createHelpModal();
        }

        createHelpModal() {
            let modal = document.getElementById('shortcuts-help-modal');
            
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'shortcuts-help-modal';
                modal.className = 'modal fade shortcuts-help-modal';
                modal.innerHTML = `
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-keyboard me-2"></i>Keyboard Shortcuts
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${this.renderShortcutsHelp()}
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }

            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }

        renderShortcutsHelp() {
            const grouped = {};
            this.options.shortcuts.forEach(shortcut => {
                if (!grouped[shortcut.category]) {
                    grouped[shortcut.category] = [];
                }
                grouped[shortcut.category].push(shortcut);
            });

            let html = '<div class="shortcuts-grid">';
            
            for (const [category, shortcuts] of Object.entries(grouped)) {
                html += `
                    <div class="shortcuts-category">
                        <div class="shortcuts-category-title">
                            <i class="${shortcuts[0].icon}"></i>
                            ${category}
                        </div>
                        ${shortcuts.map(s => `
                            <div class="shortcut-row">
                                <div class="shortcut-label">${s.title}</div>
                                <div class="shortcut-keys">${this.formatShortcut(s)}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            html += '</div>';
            return html;
        }

        isTyping(event) {
            // Delegate to shared utility (typing-utils.js)
            return window.TimeTracker && window.TimeTracker.isTyping
                ? window.TimeTracker.isTyping(event)
                : false;
        }

        detectKeyboardNavigation() {
            // Add class when using keyboard for accessibility
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    document.body.classList.add('keyboard-navigation');
                }
            });

            document.addEventListener('mousedown', () => {
                document.body.classList.remove('keyboard-navigation');
            });
        }

        showHintIfFirstVisit() {
            const hasSeenHint = localStorage.getItem('tt-shortcuts-hint-seen');
            if (!hasSeenHint) {
                setTimeout(() => {
                    this.showShortcutHint();
                    localStorage.setItem('tt-shortcuts-hint-seen', 'true');
                }, 3000);
            }
        }

        showShortcutHint() {
            const hint = document.createElement('div');
            hint.className = 'shortcut-hint';
            hint.innerHTML = `
                <i class="fas fa-keyboard"></i>
                Press <kbd class="command-kbd">?</kbd> for command palette or <kbd class="command-kbd">Ctrl</kbd>+<kbd class="command-kbd">K</kbd> for search
                <button class="shortcut-hint-close">
                    <i class="fas fa-times"></i>
                </button>
            `;

            document.body.appendChild(hint);
            
            setTimeout(() => {
                hint.classList.add('show');
            }, 100);

            hint.querySelector('.shortcut-hint-close').addEventListener('click', () => {
                hint.classList.remove('show');
                setTimeout(() => hint.remove(), 300);
            });

            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (hint.parentNode) {
                    hint.classList.remove('show');
                    setTimeout(() => hint.remove(), 300);
                }
            }, 10000);
        }
    }

    // Auto-initialize
    document.addEventListener('DOMContentLoaded', () => {
        window.keyboardShortcuts = new KeyboardShortcuts();
    });

    // Export for manual use
    window.KeyboardShortcuts = KeyboardShortcuts;

})();

