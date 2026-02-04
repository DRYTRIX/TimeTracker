/**
 * Advanced Keyboard Shortcuts System
 * Customizable, context-aware keyboard shortcuts
 */

class KeyboardShortcutManager {
    constructor() {
        this.shortcuts = new Map();
        this.contexts = new Map();
        this.currentContext = 'global';
        this.recording = false;
        this.customShortcuts = this.loadCustomShortcuts();
        this.initDefaultShortcuts();
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        this.detectContext();
        
        // Listen for context changes
        document.addEventListener('focusin', () => this.detectContext());
        window.addEventListener('popstate', () => this.detectContext());
    }

    /**
     * Register a keyboard shortcut
     */
    register(key, callback, options = {}) {
        const {
            context = 'global',
            description = '',
            category = 'General',
            preventDefault = true,
            stopPropagation = false
        } = options;

        const shortcutKey = this.normalizeKey(key);
        
        if (!this.shortcuts.has(context)) {
            this.shortcuts.set(context, new Map());
        }

        this.shortcuts.get(context).set(shortcutKey, {
            callback,
            description,
            category,
            preventDefault,
            stopPropagation,
            originalKey: key
        });
    }

    /**
     * Initialize default shortcuts
     */
    initDefaultShortcuts() {
        // Global shortcuts
        this.register('Ctrl+K', () => this.openCommandPalette(), {
            description: 'Open command palette',
            category: 'Navigation'
        });

        this.register('Ctrl+/', () => this.toggleSearch(), {
            description: 'Toggle search',
            category: 'Navigation'
        });

        this.register('Ctrl+B', () => this.toggleSidebar(), {
            description: 'Toggle sidebar',
            category: 'Navigation'
        });

        this.register('Ctrl+D', () => this.toggleDarkMode(), {
            description: 'Toggle dark mode',
            category: 'Appearance'
        });

        this.register('Shift+/', () => this.showShortcutsPanel(), {
            description: 'Show keyboard shortcuts',
            category: 'Help',
            preventDefault: true
        });

        // Navigation shortcuts
        this.register('g d', () => this.navigateTo('/main/dashboard'), {
            description: 'Go to Dashboard',
            category: 'Navigation'
        });

        this.register('g p', () => this.navigateTo('/projects/'), {
            description: 'Go to Projects',
            category: 'Navigation'
        });

        this.register('g t', () => this.navigateTo('/tasks/'), {
            description: 'Go to Tasks',
            category: 'Navigation'
        });

        this.register('g r', () => this.navigateTo('/reports/'), {
            description: 'Go to Reports',
            category: 'Navigation'
        });

        this.register('g i', () => this.navigateTo('/invoices/'), {
            description: 'Go to Invoices',
            category: 'Navigation'
        });

        // Creation shortcuts
        this.register('c p', () => this.createProject(), {
            description: 'Create new project',
            category: 'Actions'
        });

        this.register('c t', () => this.createTask(), {
            description: 'Create new task',
            category: 'Actions'
        });

        this.register('c c', () => this.createClient(), {
            description: 'Create new client',
            category: 'Actions'
        });

        // Timer shortcuts
        this.register('t s', () => this.startTimer(), {
            description: 'Start timer',
            category: 'Timer'
        });

        this.register('t p', () => this.pauseTimer(), {
            description: 'Pause timer',
            category: 'Timer'
        });

        this.register('t l', () => this.logTime(), {
            description: 'Log time manually',
            category: 'Timer'
        });

        // Table shortcuts (context-specific)
        this.register('Ctrl+A', () => this.selectAllRows(), {
            context: 'table',
            description: 'Select all rows',
            category: 'Table'
        });

        this.register('Delete', () => this.deleteSelected(), {
            context: 'table',
            description: 'Delete selected rows',
            category: 'Table'
        });

        this.register('Escape', () => this.clearSelection(), {
            context: 'table',
            description: 'Clear selection',
            category: 'Table'
        });

        // Modal shortcuts
        this.register('Escape', () => this.closeModal(), {
            context: 'modal',
            description: 'Close modal',
            category: 'Modal'
        });

        this.register('Enter', () => this.submitForm(), {
            context: 'modal',
            description: 'Submit form',
            category: 'Modal',
            preventDefault: false
        });

        // Editing shortcuts
        this.register('Ctrl+S', () => this.saveForm(), {
            context: 'editing',
            description: 'Save changes',
            category: 'Editing'
        });

        this.register('Ctrl+Z', () => this.undo(), {
            description: 'Undo',
            category: 'Editing'
        });

        this.register('Ctrl+Shift+Z', () => this.redo(), {
            description: 'Redo',
            category: 'Editing'
        });

        // Quick actions
        this.register('Shift+?', () => this.showQuickActions(), {
            description: 'Show quick actions',
            category: 'Actions'
        });
    }

    /**
     * Handle key press
     */
    handleKeyPress(e) {
        // AGGRESSIVE DEBUG LOGGING
        const debugInfo = {
            key: e.key,
            target: e.target,
            tagName: e.target.tagName,
            classList: e.target.classList ? Array.from(e.target.classList) : [],
            isContentEditable: e.target.isContentEditable
        };
        console.log('[KS-Advanced] Key pressed:', debugInfo);
        
        // When palette is open, do not trigger a second open; let commands.js handle focus
        const palette = document.getElementById('commandPaletteModal');
        const paletteOpen = palette && !palette.classList.contains('hidden');

        // Check if typing in input field
        const isTypingInInput = this.isTyping(e);
        console.log('[KS-Advanced] isTyping result:', isTypingInInput);

        // If typing in input/textarea, ONLY allow specific global combos
        if (isTypingInInput) {
            console.log('[KS-Advanced] BLOCKED - User is typing in input field');
            // Allow Ctrl+/ to focus search even when typing
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.toggleSearch();
                return;
            }
            // Allow Ctrl+K to open/focus palette even when typing
            else if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                if (paletteOpen) {
                    // Just refocus input when already open
                    const inputExisting = document.getElementById('commandPaletteInput');
                    if (inputExisting) setTimeout(() => inputExisting.focus(), 50);
                } else {
                    this.openCommandPalette();
                }
                return;
            }
            // Allow Shift+? for shortcuts panel
            else if (e.key === '?' && e.shiftKey) {
                e.preventDefault();
                this.showShortcutsPanel();
                return;
            }
            // Block ALL other shortcuts when typing
            console.log('[KS-Advanced] Blocking shortcut - in input field');
            return;
        }
        
        console.log('[KS-Advanced] NOT blocked - processing shortcut');

        const key = this.getKeyCombo(e);
        const normalizedKey = this.normalizeKey(key);

        // Debug logging (can be removed in production)
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            console.log('Keyboard shortcut detected:', {
                key: e.key,
                combo: key,
                normalized: normalizedKey,
                ctrlKey: e.ctrlKey,
                metaKey: e.metaKey
            });
        }

        // Prevent duplicate open when palette already visible (Ctrl+K, ?, etc.)
        if (paletteOpen) {
            // If user hits palette keys while open, just refocus and exit
            if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'k' || e.key === '?')) {
                e.preventDefault();
                const inputExisting = document.getElementById('commandPaletteInput');
                if (inputExisting) setTimeout(() => inputExisting.focus(), 50);
                return;
            }
        }

        // Check custom shortcuts first
        if (this.customShortcuts.has(normalizedKey)) {
            const customAction = this.customShortcuts.get(normalizedKey);
            this.executeAction(customAction);
            e.preventDefault();
            return;
        }

        // Check context-specific shortcuts
        const contextShortcuts = this.shortcuts.get(this.currentContext);
        if (contextShortcuts && contextShortcuts.has(normalizedKey)) {
            const shortcut = contextShortcuts.get(normalizedKey);
            if (shortcut.preventDefault) e.preventDefault();
            if (shortcut.stopPropagation) e.stopPropagation();
            shortcut.callback(e);
            return;
        }

        // Check global shortcuts
        const globalShortcuts = this.shortcuts.get('global');
        if (globalShortcuts && globalShortcuts.has(normalizedKey)) {
            const shortcut = globalShortcuts.get(normalizedKey);
            if (shortcut.preventDefault) e.preventDefault();
            if (shortcut.stopPropagation) e.stopPropagation();
            shortcut.callback(e);
        }
    }

    /**
     * Get key combination from event
     */
    getKeyCombo(e) {
        const parts = [];
        
        if (e.ctrlKey || e.metaKey) parts.push('Ctrl');
        if (e.altKey) parts.push('Alt');
        if (e.shiftKey) parts.push('Shift');
        
        let key = e.key;
        if (key === ' ') key = 'Space';
        
        // Don't uppercase special characters like /, ?, etc.
        if (key.length === 1 && key.match(/[a-zA-Z0-9]/)) {
            key = key.toUpperCase();
        }
        
        parts.push(key);
        
        return parts.join('+');
    }

    /**
     * Normalize key for consistent matching
     */
    normalizeKey(key) {
        return key.replace(/\s+/g, ' ').toLowerCase();
    }

    /**
     * Check if user is typing in an input field
     */
    isTyping(e) {
        const target = e.target;
        const tagName = target.tagName.toLowerCase();
        
        console.log('[KS-Advanced isTyping] Checking:', {
            tagName: tagName,
            isContentEditable: target.isContentEditable,
            classList: target.classList ? Array.from(target.classList) : []
        });
        
        // Check standard input elements
        if (tagName === 'input' || 
            tagName === 'textarea' || 
            tagName === 'select' ||
            target.isContentEditable) {
            console.log('[KS-Advanced isTyping] TRUE - standard input');
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
                console.log('[KS-Advanced isTyping] TRUE - inside editor:', selector);
                return true;
            }
        }
        
        console.log('[KS-Advanced isTyping] FALSE - not in input');
        return false;
    }

    /**
     * Detect current context
     */
    detectContext() {
        // Check for modal
        if (document.querySelector('.modal:not(.hidden), [role="dialog"]:not(.hidden)')) {
            this.currentContext = 'modal';
            return;
        }

        // Check for table
        if (document.activeElement.closest('table[data-enhanced]')) {
            this.currentContext = 'table';
            return;
        }

        // Check for editing
        if (document.activeElement.closest('form[data-auto-save]')) {
            this.currentContext = 'editing';
            return;
        }

        this.currentContext = 'global';
    }

    /**
     * Show shortcuts panel
     */
    showShortcutsPanel() {
        if (typeof window.openKeyboardShortcutsModal === 'function') {
            window.openKeyboardShortcutsModal();
            return;
        }
        const panel = document.createElement('div');
        panel.className = 'fixed inset-0 z-50 overflow-y-auto';
        panel.innerHTML = `
            <div class="flex items-center justify-center min-h-screen px-4">
                <div class="fixed inset-0 bg-black/50" onclick="this.parentElement.parentElement.remove()"></div>
                <div class="relative bg-card-light dark:bg-card-dark rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
                    <div class="p-6 border-b border-border-light dark:border-border-dark flex items-center justify-between">
                        <h2 class="text-2xl font-bold">Keyboard Shortcuts</h2>
                        <button onclick="this.closest('.fixed').remove()" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="p-6 overflow-y-auto max-h-[60vh]">
                        ${this.renderShortcutsList()}
                    </div>
                    <div class="p-4 border-t border-border-light dark:border-border-dark flex justify-between items-center bg-gray-50 dark:bg-gray-800">
                        <button onclick="shortcutManager.customizeShortcuts()" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90">
                            <i class="fas fa-cog mr-2"></i>Customize
                        </button>
                        <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
    }

    /**
     * Render shortcuts list
     */
    renderShortcutsList() {
        const categories = {};
        
        // Organize by category
        this.shortcuts.forEach((contextShortcuts) => {
            contextShortcuts.forEach((shortcut, key) => {
                if (!categories[shortcut.category]) {
                    categories[shortcut.category] = [];
                }
                categories[shortcut.category].push({
                    key: shortcut.originalKey,
                    description: shortcut.description
                });
            });
        });

        let html = '';
        Object.keys(categories).sort().forEach(category => {
            html += `
                <div class="mb-6">
                    <h3 class="text-lg font-semibold mb-3 text-primary">${category}</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        ${categories[category].map(s => `
                            <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                                <span class="text-sm">${s.description}</span>
                                <kbd class="px-2 py-1 text-xs font-mono bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">${s.key}</kbd>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        return html;
    }

    /**
     * Load custom shortcuts from localStorage
     */
    loadCustomShortcuts() {
        try {
            const saved = localStorage.getItem('custom_shortcuts');
            return saved ? new Map(JSON.parse(saved)) : new Map();
        } catch {
            return new Map();
        }
    }

    /**
     * Save custom shortcuts
     */
    saveCustomShortcuts() {
        localStorage.setItem('custom_shortcuts', JSON.stringify([...this.customShortcuts]));
    }

    // Action implementations
    openCommandPalette() {
        const modal = document.getElementById('commandPaletteModal');
        if (modal) {
            // If already open, just focus
            if (!modal.classList.contains('hidden')) {
                const inputExisting = document.getElementById('commandPaletteInput');
                if (inputExisting) setTimeout(() => inputExisting.focus(), 50);
                return;
            }
            modal.classList.remove('hidden');
            const input = document.getElementById('commandPaletteInput');
            if (input) setTimeout(() => input.focus(), 100);
        }
    }

    toggleSearch() {
        // Prefer the main header search input
        let searchInput = document.getElementById('search');
        if (!searchInput) {
            searchInput = document.querySelector('form.navbar-search input[type="search"], input[type="search"], input[name="q"], .search-enhanced input');
        }
        if (searchInput) {
            // Ensure parent sections are visible (e.g., if search is in a collapsed container)
            try { searchInput.closest('.hidden')?.classList.remove('hidden'); } catch(_) {}
            searchInput.focus();
            if (typeof searchInput.select === 'function') searchInput.select();
        }
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const btn = document.getElementById('sidebarCollapseBtn');
        if (btn) btn.click();
    }

    toggleDarkMode() {
        const btn = document.getElementById('theme-toggle');
        if (btn) btn.click();
    }

    navigateTo(url) {
        window.location.href = url;
    }

    createProject() {
        const btn = document.querySelector('a[href*="create_project"]');
        if (btn) btn.click();
        else this.navigateTo('/projects/create');
    }

    createTask() {
        const btn = document.querySelector('a[href*="create_task"]');
        if (btn) btn.click();
        else this.navigateTo('/tasks/create');
    }

    createClient() {
        this.navigateTo('/clients/create');
    }

    startTimer() {
        const btn = document.querySelector('#openStartTimer, button[onclick*="startTimer"]');
        if (btn) btn.click();
    }

    pauseTimer() {
        const btn = document.querySelector('button[onclick*="pauseTimer"], button[onclick*="stopTimer"]');
        if (btn) btn.click();
    }

    logTime() {
        this.navigateTo('/timer/manual_entry');
    }

    selectAllRows() {
        const checkbox = document.querySelector('.select-all-checkbox');
        if (checkbox) {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change'));
        }
    }

    deleteSelected() {
        if (window.bulkDelete) {
            window.bulkDelete();
        }
    }

    clearSelection() {
        if (window.clearSelection) {
            window.clearSelection();
        }
    }

    closeModal() {
        const modal = document.querySelector('.modal:not(.hidden), [role="dialog"]:not(.hidden)');
        if (modal) {
            const closeBtn = modal.querySelector('[data-close], .close, button[onclick*="close"]');
            if (closeBtn) closeBtn.click();
            else modal.classList.add('hidden');
        }
    }

    submitForm() {
        const form = document.querySelector('form:not(.filter-form)');
        if (form && document.activeElement.tagName !== 'TEXTAREA') {
            form.submit();
        }
    }

    saveForm() {
        const form = document.querySelector('form[data-auto-save]');
        if (form) {
            // Trigger auto-save
            form.dispatchEvent(new Event('submit'));
        }
    }

    undo() {
        if (window.undoManager) {
            window.undoManager.undo();
        }
    }

    redo() {
        if (window.undoManager) {
            window.undoManager.redo();
        }
    }

    showQuickActions() {
        if (window.quickActionsMenu) {
            window.quickActionsMenu.toggle();
        }
    }

    executeAction(action) {
        // Execute custom action
        console.log('Executing custom action:', action);
    }

    customizeShortcuts() {
        window.toastManager?.info('Shortcut customization coming soon!');
    }
}

// Initialize
window.shortcutManager = new KeyboardShortcutManager();

console.log('Advanced keyboard shortcuts loaded. Press ? to see all shortcuts.');

