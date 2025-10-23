/**
 * Enhanced Search System
 * Provides instant search, autocomplete, and keyboard navigation
 */

(function() {
    'use strict';

    class EnhancedSearch {
        constructor(input, options = {}) {
            this.input = input;
            this.options = {
                endpoint: options.endpoint || '/api/search',
                minChars: options.minChars || 2,
                debounceDelay: options.debounceDelay || 300,
                maxResults: options.maxResults || 10,
                placeholder: options.placeholder || 'Search...',
                categories: options.categories || ['all'],
                onSelect: options.onSelect || null,
                enableRecent: options.enableRecent !== false,
                enableSuggestions: options.enableSuggestions !== false,
                ...options
            };

            this.results = [];
            this.recentSearches = this.loadRecentSearches();
            this.currentFocus = -1;
            this.debounceTimer = null;
            this.isSearching = false;

            this.init();
        }

        init() {
            this.createSearchUI();
            this.bindEvents();
            // Proactively disable native autofill/auto-complete behaviors
            try {
                this.input.setAttribute('autocomplete', 'off');
                this.input.setAttribute('autocapitalize', 'off');
                this.input.setAttribute('autocorrect', 'off');
                this.input.setAttribute('spellcheck', 'false');
                // Trick some Chromium versions
                this.input.setAttribute('name', 'q_search');
                this.input.setAttribute('data-lpignore', 'true');
            } catch(e) {}
        }

        createSearchUI() {
            // Wrap input in enhanced search container
            const wrapper = document.createElement('div');
            wrapper.className = 'search-enhanced';
            this.input.parentNode.insertBefore(wrapper, this.input);

            // Create input wrapper
            const inputWrapper = document.createElement('div');
            inputWrapper.className = 'search-input-wrapper';
            inputWrapper.innerHTML = `
                <i class="fas fa-search search-icon" aria-hidden="true"></i>
            `;

            // Move input into wrapper
            wrapper.appendChild(inputWrapper);
            inputWrapper.appendChild(this.input);

            // Add actions
            const actions = document.createElement('div');
            actions.className = 'search-actions';
            actions.innerHTML = `
                <button type="button" class="search-clear-btn" style="display: none;" aria-label="{{ _('Clear search') if false else 'Clear search' }}">
                    <i class="fas fa-xmark"></i>
                </button>
                <span class="search-kbd">Ctrl+/</span>
            `;
            inputWrapper.appendChild(actions);

            // Create autocomplete dropdown
            const autocomplete = document.createElement('div');
            autocomplete.className = 'search-autocomplete';
            wrapper.appendChild(autocomplete);

            this.wrapper = wrapper;
            this.inputWrapper = inputWrapper;
            this.autocomplete = autocomplete;
            this.clearBtn = actions.querySelector('.search-clear-btn');
        }

        bindEvents() {
            // Input events
            this.input.addEventListener('input', (e) => this.handleInput(e));
            this.input.addEventListener('focus', () => this.handleFocus());
            this.input.addEventListener('blur', (e) => this.handleBlur(e));
            this.input.addEventListener('keydown', (e) => this.handleKeydown(e));

            // Clear button
            this.clearBtn.addEventListener('click', () => this.clear());

            // Click outside
            document.addEventListener('click', (e) => {
                if (!this.wrapper.contains(e.target)) {
                    this.hideAutocomplete();
                }
            });
        }

        handleInput(e) {
            const value = e.target.value;

            // Show/hide clear button
            this.clearBtn.style.display = value ? 'flex' : 'none';

            // Add has-value class
            if (value) {
                this.inputWrapper.classList.add('has-value');
            } else {
                this.inputWrapper.classList.remove('has-value');
            }

            // Debounced search
            clearTimeout(this.debounceTimer);

            if (value.length === 0) {
                this.showRecentSearches();
                return;
            }

            if (value.length < this.options.minChars) {
                this.hideAutocomplete();
                return;
            }

            this.debounceTimer = setTimeout(() => {
                this.performSearch(value);
            }, this.options.debounceDelay);
        }

        handleFocus() {
            if (this.input.value.length === 0) {
                this.showRecentSearches();
            } else if (this.results.length > 0) {
                this.showAutocomplete();
            }
        }

        handleBlur(e) {
            // Delay to allow click events on autocomplete
            setTimeout(() => {
                if (!this.wrapper.contains(document.activeElement)) {
                    this.hideAutocomplete();
                }
            }, 200);
        }

        handleKeydown(e) {
            const items = this.autocomplete.querySelectorAll('.search-item');

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.currentFocus++;
                    if (this.currentFocus >= items.length) this.currentFocus = 0;
                    this.setActive(items);
                    break;

                case 'ArrowUp':
                    e.preventDefault();
                    this.currentFocus--;
                    if (this.currentFocus < 0) this.currentFocus = items.length - 1;
                    this.setActive(items);
                    break;

                case 'Enter':
                    e.preventDefault();
                    if (this.currentFocus > -1 && items[this.currentFocus]) {
                        items[this.currentFocus].click();
                    }
                    break;

                case 'Escape':
                    this.hideAutocomplete();
                    this.input.blur();
                    break;
            }
        }

        setActive(items) {
            items.forEach((item, index) => {
                item.classList.remove('keyboard-focus');
                if (index === this.currentFocus) {
                    item.classList.add('keyboard-focus');
                    item.scrollIntoView({ block: 'nearest' });
                }
            });
        }

        async performSearch(query) {
            this.isSearching = true;
            this.inputWrapper.classList.add('searching');

            try {
                const params = new URLSearchParams({
                    q: query,
                    limit: this.options.maxResults
                });

                const response = await fetch(`${this.options.endpoint}?${params}`);
                const data = await response.json();

                this.results = data.results || [];
                this.renderResults(query);
                this.saveRecentSearch(query);
            } catch (error) {
                console.error('Search error:', error);
                this.showError();
            } finally {
                this.isSearching = false;
                this.inputWrapper.classList.remove('searching');
            }
        }

        renderResults(query) {
            if (this.results.length === 0) {
                this.showNoResults(query);
                return;
            }

            // Group results by category
            const grouped = this.groupResults(this.results);

            let html = `
                <div class="search-stats">
                    Found <strong>${this.results.length}</strong> results for "${this.highlightQuery(query)}"
                </div>
            `;

            for (const [category, items] of Object.entries(grouped)) {
                html += `
                    <div class="search-section">
                        <div class="search-section-title">${this.formatCategory(category)}</div>
                        ${items.map(item => this.renderItem(item, query)).join('')}
                    </div>
                `;
            }

            this.autocomplete.innerHTML = html;
            this.showAutocomplete();
            this.bindItemEvents();
        }

        renderItem(item, query) {
            const icon = this.getIcon(item.type);
            const title = this.highlightMatch(item.title, query);
            const description = item.description || '';

            return `
                <a href="${item.url}" class="search-item" data-item='${JSON.stringify(item)}'>
                    <div class="search-item-icon">
                        <i class="${icon}"></i>
                    </div>
                    <div class="search-item-content">
                        <div class="search-item-title">${title}</div>
                        ${description ? `<div class="search-item-description">${description}</div>` : ''}
                    </div>
                    <div class="search-item-meta">
                        ${item.badge ? `<span class="search-item-badge">${item.badge}</span>` : ''}
                        <span class="search-kbd">↵</span>
                    </div>
                </a>
            `;
        }

        groupResults(results) {
            const grouped = {};
            results.forEach(result => {
                const category = result.category || 'other';
                if (!grouped[category]) {
                    grouped[category] = [];
                }
                grouped[category].push(result);
            });
            return grouped;
        }

        highlightMatch(text, query) {
            const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
            return text.replace(regex, '<mark>$1</mark>');
        }

        highlightQuery(query) {
            return `<mark>${this.escapeHTML(query)}</mark>`;
        }

        showRecentSearches() {
            if (!this.options.enableRecent || this.recentSearches.length === 0) {
                return;
            }

            let html = `
                <div class="search-section">
                    <div class="search-section-title">Recent Searches</div>
                    <div class="search-recent">
            `;

            this.recentSearches.forEach(search => {
                html += `
                    <div class="search-recent-item" data-query="${this.escapeHTML(search)}">
                        <i class="fas fa-history"></i>
                        ${this.escapeHTML(search)}
                    </div>
                `;
            });

            html += `
                    </div>
                    <div class="search-recent-clear">
                        <button type="button" id="clear-recent-btn">Clear Recent</button>
                    </div>
                </div>
            `;

            this.autocomplete.innerHTML = html;
            this.showAutocomplete();

            // Bind recent item clicks
            this.autocomplete.querySelectorAll('.search-recent-item').forEach(item => {
                item.addEventListener('click', () => {
                    const query = item.getAttribute('data-query');
                    this.input.value = query;
                    this.performSearch(query);
                });
            });

            // Bind clear button
            const clearBtn = this.autocomplete.querySelector('#clear-recent-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearRecentSearches();
                    this.hideAutocomplete();
                });
            }
        }

        showNoResults(query) {
            this.autocomplete.innerHTML = `
                <div class="search-no-results">
                    <i class="fas fa-search"></i>
                    <p>No results found for "${this.escapeHTML(query)}"</p>
                </div>
            `;
            this.showAutocomplete();
        }

        showError() {
            this.autocomplete.innerHTML = `
                <div class="search-no-results">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Something went wrong. Please try again.</p>
                </div>
            `;
            this.showAutocomplete();
        }

        bindItemEvents() {
            this.autocomplete.querySelectorAll('.search-item').forEach((item, index) => {
                item.addEventListener('mouseenter', () => {
                    this.currentFocus = index;
                    this.setActive(this.autocomplete.querySelectorAll('.search-item'));
                });

                item.addEventListener('click', (e) => {
                    if (this.options.onSelect) {
                        e.preventDefault();
                        const itemData = JSON.parse(item.getAttribute('data-item'));
                        this.options.onSelect(itemData);
                    }
                    this.hideAutocomplete();
                });
            });
        }

        showAutocomplete() {
            this.autocomplete.classList.add('show');
            this.currentFocus = -1;
        }

        hideAutocomplete() {
            this.autocomplete.classList.remove('show');
            this.currentFocus = -1;
        }

        clear() {
            this.input.value = '';
            this.clearBtn.style.display = 'none';
            this.inputWrapper.classList.remove('has-value');
            this.hideAutocomplete();
            this.input.focus();
        }

        // Recent searches management
        loadRecentSearches() {
            try {
                return JSON.parse(localStorage.getItem('tt-recent-searches') || '[]');
            } catch {
                return [];
            }
        }

        saveRecentSearch(query) {
            if (!this.options.enableRecent) return;

            let recent = this.recentSearches.filter(s => s !== query);
            recent.unshift(query);
            recent = recent.slice(0, 5); // Keep only 5 recent

            this.recentSearches = recent;
            localStorage.setItem('tt-recent-searches', JSON.stringify(recent));
        }

        clearRecentSearches() {
            this.recentSearches = [];
            localStorage.removeItem('tt-recent-searches');
        }

        // Helpers
        getIcon(type) {
            const icons = {
                project: 'fas fa-project-diagram',
                client: 'fas fa-building',
                task: 'fas fa-tasks',
                entry: 'fas fa-clock',
                invoice: 'fas fa-file-invoice',
                user: 'fas fa-user',
                default: 'fas fa-file'
            };
            return icons[type] || icons.default;
        }

        formatCategory(category) {
            return category.charAt(0).toUpperCase() + category.slice(1) + 's';
        }

        escapeHTML(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
    }

    // Auto-initialize on search inputs
    document.addEventListener('DOMContentLoaded', () => {
        const searchInputs = document.querySelectorAll('[data-enhanced-search]');
        searchInputs.forEach(input => {
            const options = JSON.parse(input.getAttribute('data-enhanced-search') || '{}');
            new EnhancedSearch(input, options);
        });
        // Global hook: ensure Ctrl+/ focuses the main search input and opens recent suggestions when empty
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === '/') {
                const search = document.getElementById('search') || document.querySelector('[data-enhanced-search]');
                if (search) {
                    e.preventDefault();
                    search.focus();
                    if (typeof search.select === 'function') search.select();
                    try {
                        // If enhanced instance attached, show recent when empty
                        if (!search.value) {
                            const wrapper = search.closest('.search-enhanced');
                            const autocomplete = wrapper && wrapper.querySelector('.search-autocomplete');
                            if (autocomplete) {
                                // Fire a synthetic focus to render recents
                                search.dispatchEvent(new Event('focus'));
                            }
                        }
                    } catch(_) {}
                }
            }
        });
    });

    // Export for manual initialization
    window.EnhancedSearch = EnhancedSearch;

})();

