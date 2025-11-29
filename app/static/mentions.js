/**
 * @Mentions UI Component
 * Autocomplete mentions in chat, comments, and text areas
 */

class MentionsInput {
    constructor(textarea, options = {}) {
        this.textarea = textarea;
        this.options = {
            trigger: options.trigger || '@',
            minLength: options.minLength || 1,
            maxItems: options.maxItems || 10,
            ...options
        };

        this.mentionStart = null;
        this.mentionQuery = '';
        this.mentionsList = null;
        this.selectedIndex = -1;
        this.users = [];
        this.currentMention = null;

        this.init();
    }

    init() {
        // Create mentions dropdown container
        this.mentionsList = document.createElement('div');
        this.mentionsList.className = 'mentions-dropdown hidden';
        this.mentionsList.id = `mentions-${this.textarea.id || Date.now()}`;
        document.body.appendChild(this.mentionsList);

        // Load users
        this.loadUsers();

        // Bind events
        this.textarea.addEventListener('input', (e) => this.handleInput(e));
        this.textarea.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.textarea.addEventListener('blur', () => {
            // Delay to allow click events on dropdown
            setTimeout(() => this.hideDropdown(), 200);
        });
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/users/search');
            const data = await response.json();
            this.users = data.users || [];
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    handleInput(e) {
        const text = e.target.value;
        const cursorPos = e.target.selectionStart;

        // Find mention trigger before cursor
        const textBeforeCursor = text.substring(0, cursorPos);
        const lastTriggerIndex = textBeforeCursor.lastIndexOf(this.options.trigger);

        if (lastTriggerIndex === -1) {
            this.hideDropdown();
            return;
        }

        // Check if there's whitespace between trigger and cursor (mention is complete)
        const textAfterTrigger = textBeforeCursor.substring(lastTriggerIndex + 1);
        if (textAfterTrigger.match(/[\s\n]/)) {
            this.hideDropdown();
            return;
        }

        // Extract query
        this.mentionQuery = textAfterTrigger.toLowerCase();
        
        if (this.mentionQuery.length < this.options.minLength) {
            this.hideDropdown();
            return;
        }

        // Filter users
        const filtered = this.users.filter(user => {
            const username = (user.username || '').toLowerCase();
            const displayName = (user.display_name || '').toLowerCase();
            return username.includes(this.mentionQuery) || 
                   displayName.includes(this.mentionQuery);
        }).slice(0, this.options.maxItems);

        if (filtered.length === 0) {
            this.hideDropdown();
            return;
        }

        // Show dropdown
        this.mentionStart = lastTriggerIndex;
        this.currentMention = {
            start: lastTriggerIndex,
            end: cursorPos,
            query: this.mentionQuery
        };
        this.showDropdown(filtered);
    }

    showDropdown(users) {
        const rect = this.textarea.getBoundingClientRect();
        const position = this.getCaretPosition();

        this.mentionsList.innerHTML = users.map((user, index) => {
            const isSelected = index === this.selectedIndex ? 'selected' : '';
            return `
                <div class="mention-item ${isSelected}" data-index="${index}" data-user-id="${user.id}" data-username="${user.username}">
                    <div class="mention-avatar">
                        ${user.avatar_url ? `<img src="${user.avatar_url}" alt="${user.display_name || user.username}">` : `<div class="mention-initials">${(user.display_name || user.username).substring(0, 2).toUpperCase()}</div>`}
                    </div>
                    <div class="mention-info">
                        <div class="mention-name">${this.highlightMatch(user.display_name || user.username, this.mentionQuery)}</div>
                        <div class="mention-username">@${user.username}</div>
                    </div>
                </div>
            `;
        }).join('');

        // Position dropdown
        this.mentionsList.style.position = 'absolute';
        this.mentionsList.style.top = `${rect.top + position.top + 20}px`;
        this.mentionsList.style.left = `${rect.left + position.left}px`;
        this.mentionsList.classList.remove('hidden');

        // Bind click events
        this.mentionsList.querySelectorAll('.mention-item').forEach(item => {
            item.addEventListener('click', () => {
                const userId = item.dataset.userId;
                const username = item.dataset.username;
                this.insertMention(username, userId);
            });
        });
    }

    hideDropdown() {
        this.mentionsList.classList.add('hidden');
        this.selectedIndex = -1;
        this.currentMention = null;
    }

    handleKeydown(e) {
        if (!this.currentMention || this.mentionsList.classList.contains('hidden')) {
            return;
        }

        const items = this.mentionsList.querySelectorAll('.mention-item');
        if (items.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.updateSelection(items);
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection(items);
                break;

            case 'Enter':
            case 'Tab':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    const item = items[this.selectedIndex];
                    const userId = item.dataset.userId;
                    const username = item.dataset.username;
                    this.insertMention(username, userId);
                }
                break;

            case 'Escape':
                e.preventDefault();
                this.hideDropdown();
                break;
        }
    }

    updateSelection(items) {
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    insertMention(username, userId) {
        const text = this.textarea.value;
        const mention = `@${username} `;

        // Replace mention query with full mention
        const before = text.substring(0, this.currentMention.start);
        const after = text.substring(this.currentMention.end);
        const newText = before + mention + after;

        this.textarea.value = newText;
        this.textarea.dispatchEvent(new Event('input', { bubbles: true }));

        // Set cursor position after mention
        const newPos = this.currentMention.start + mention.length;
        this.textarea.setSelectionRange(newPos, newPos);
        this.textarea.focus();

        // Hide dropdown
        this.hideDropdown();

        // Trigger custom event
        this.textarea.dispatchEvent(new CustomEvent('mention', {
            detail: { username, userId }
        }));
    }

    getCaretPosition() {
        // Calculate approximate caret position (simplified)
        const textBeforeCursor = this.textarea.value.substring(0, this.textarea.selectionStart);
        const lines = textBeforeCursor.split('\n');
        return {
            top: (lines.length - 1) * 20, // Approximate line height
            left: lines[lines.length - 1].length * 8 // Approximate char width
        };
    }

    highlightMatch(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
}

// Auto-initialize mentions on elements with data-mentions attribute
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-mentions]').forEach(element => {
        new MentionsInput(element);
    });
});

// CSS (inject into page)
const mentionsCSS = `
.mentions-dropdown {
    position: absolute;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    max-height: 300px;
    overflow-y: auto;
    z-index: 1000;
    min-width: 250px;
}

.mentions-dropdown.hidden {
    display: none;
}

.mention-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.mention-item:hover,
.mention-item.selected {
    background-color: #f3f4f6;
}

.mention-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    overflow: hidden;
    margin-right: 8px;
    flex-shrink: 0;
}

.mention-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.mention-initials {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #6366f1;
    color: white;
    font-size: 12px;
    font-weight: 600;
}

.mention-info {
    flex: 1;
    min-width: 0;
}

.mention-name {
    font-weight: 500;
    font-size: 14px;
    color: #111827;
}

.mention-username {
    font-size: 12px;
    color: #6b7280;
}
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = mentionsCSS;
document.head.appendChild(style);

