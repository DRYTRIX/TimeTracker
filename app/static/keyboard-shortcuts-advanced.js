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
        /** Registry: id -> { defaultKey, callback, context, description, category, preventDefault, stopPropagation, originalKey } for applying overrides */
        this.registry = [];
        this.customShortcuts = new Map();
        this.initDefaultShortcuts();
        this.applyUserOverrides();
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        this.detectContext();
        document.addEventListener('focusin', () => this.detectContext());
        window.addEventListener('popstate', () => this.detectContext());
    }

    /**
     * Register a keyboard shortcut. options.id is used for backend override mapping.
     */
    register(key, callback, options = {}) {
        const {
            id = null,
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
            originalKey: key,
            id: id || null
        });
        if (id) {
            this.registry.push({
                id,
                defaultKey: shortcutKey,
                callback,
                context,
                description,
                category,
                preventDefault,
                stopPropagation,
                originalKey: key
            });
        }
    }

    /**
     * Initialize default shortcuts. IDs must match backend DEFAULT_SHORTCUTS in keyboard_shortcuts_defaults.py.
     */
    initDefaultShortcuts() {
        this.register('Ctrl+K', () => this.openCommandPalette(), { id: 'global_command_palette', description: 'Open command palette', category: 'Navigation' });
        this.register('Ctrl+/', () => this.toggleSearch(), { id: 'global_search', description: 'Toggle search', category: 'Navigation' });
        this.register('Ctrl+B', () => this.toggleSidebar(), { id: 'global_sidebar', description: 'Toggle sidebar', category: 'Navigation' });
        this.register('Ctrl+D', () => this.toggleDarkMode(), { id: 'appearance_dark_mode', description: 'Toggle dark mode', category: 'Appearance' });
        this.register('Shift+/', () => this.showShortcutsPanel(), { id: 'help_shortcuts_panel', description: 'Show keyboard shortcuts', category: 'Help', preventDefault: true });
        this.register('Shift+?', () => this.showQuickActions(), { id: 'actions_quick_actions', description: 'Show quick actions', category: 'Actions' });
        this.register('g d', () => this.navigateTo('/main/dashboard'), { id: 'nav_dashboard', description: 'Go to Dashboard', category: 'Navigation' });
        this.register('g p', () => this.navigateTo('/projects/'), { id: 'nav_projects', description: 'Go to Projects', category: 'Navigation' });
        this.register('g t', () => this.navigateTo('/tasks/'), { id: 'nav_tasks', description: 'Go to Tasks', category: 'Navigation' });
        this.register('g r', () => this.navigateTo('/reports/'), { id: 'nav_reports', description: 'Go to Reports', category: 'Navigation' });
        this.register('g i', () => this.navigateTo('/invoices/'), { id: 'nav_invoices', description: 'Go to Invoices', category: 'Navigation' });
        this.register('c p', () => this.createProject(), { id: 'create_project', description: 'Create new project', category: 'Actions' });
        this.register('c t', () => this.createTask(), { id: 'create_task', description: 'Create new task', category: 'Actions' });
        this.register('c c', () => this.createClient(), { id: 'create_client', description: 'Create new client', category: 'Actions' });
        this.register('t s', () => this.startTimer(), { id: 'timer_start', description: 'Start timer', category: 'Timer' });
        this.register('t p', () => this.pauseTimer(), { id: 'timer_pause', description: 'Pause timer', category: 'Timer' });
        this.register('t l', () => this.logTime(), { id: 'timer_log', description: 'Log time manually', category: 'Timer' });
        this.register('Ctrl+A', () => this.selectAllRows(), { id: 'table_select_all', context: 'table', description: 'Select all rows', category: 'Table' });
        this.register('Delete', () => this.deleteSelected(), { id: 'table_delete', context: 'table', description: 'Delete selected rows', category: 'Table' });
        this.register('Escape', () => this.clearSelection(), { id: 'table_clear_selection', context: 'table', description: 'Clear selection', category: 'Table' });
        this.register('Escape', () => this.closeModal(), { id: 'modal_close', context: 'modal', description: 'Close modal', category: 'Modal' });
        this.register('Enter', () => this.submitForm(), { id: 'modal_submit', context: 'modal', description: 'Submit form', category: 'Modal', preventDefault: false });
        this.register('Ctrl+S', () => this.saveForm(), { id: 'editing_save', context: 'editing', description: 'Save changes', category: 'Editing' });
        this.register('Ctrl+Z', () => this.undo(), { id: 'editing_undo', description: 'Undo', category: 'Editing' });
        this.register('Ctrl+Shift+Z', () => this.redo(), { id: 'editing_redo', description: 'Redo', category: 'Editing' });
    }

    /**
     * Apply user overrides from window.__KEYBOARD_SHORTCUTS_CONFIG__ or fetch from API.
     * Rebuilds this.shortcuts so effective key per id = overrides[id] || defaultKey.
     */
    applyUserOverrides() {
        const config = window.__KEYBOARD_SHORTCUTS_CONFIG__;
        const overrides = (config && config.overrides) || {};
        this.shortcuts.clear();
        this.registry.forEach((reg) => {
            const effectiveKey = (overrides[reg.id] && this.normalizeKey(overrides[reg.id])) || reg.defaultKey;
            if (!this.shortcuts.has(reg.context)) this.shortcuts.set(reg.context, new Map());
            this.shortcuts.get(reg.context).set(effectiveKey, {
                callback: reg.callback,
                description: reg.description,
                category: reg.category,
                preventDefault: reg.preventDefault,
                stopPropagation: reg.stopPropagation,
                originalKey: effectiveKey,
                id: reg.id
            });
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
        // When palette is open, do not trigger a second open; let commands.js handle focus
        const palette = document.getElementById('commandPaletteModal');
        const paletteOpen = palette && !palette.classList.contains('hidden');

        // Check if typing in input field
        const isTypingInInput = this.isTyping(e);
        // If typing in input/textarea, ONLY allow specific global combos
        if (isTypingInInput) {
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
            return;
        }
        
        const key = this.getKeyCombo(e);
        const normalizedKey = this.normalizeKey(key);

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

        // Check context-specific shortcuts (already include user overrides via applyUserOverrides)
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
     * Normalize key for consistent matching (matches backend keyboard_shortcuts_defaults.normalize_key)
     */
    normalizeKey(key) {
        return String(key || '').trim().toLowerCase().replace(/\s+/g, ' ').replace(/command|cmd/gi, 'ctrl');
    }

    /**
     * Check if user is typing in an input field (delegates to shared utility from typing-utils.js)
     */
    isTyping(e) {
        return window.TimeTracker && window.TimeTracker.isTyping
            ? window.TimeTracker.isTyping(e)
            : false;
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
        let searchInput = document.getElementById('header-search');
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
        // no-op
    }

    customizeShortcuts() {
        window.location.href = '/settings/keyboard-shortcuts';
    }
}

// Initialize
window.shortcutManager = new KeyboardShortcutManager();



