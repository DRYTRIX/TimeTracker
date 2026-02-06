/**
 * Quick Actions Floating Menu
 * Floating action button with quick access to common actions
 */

class QuickActionsMenu {
    constructor() {
        this.isOpen = false;
        this.button = null;
        this.menu = null;
        this.actions = this.defineActions();
        this.init();
    }

    init() {
        this.createButton();
        this.createMenu();
        this.attachEventListeners();
        
        // Show/hide based on scroll
        this.handleScroll();
        window.addEventListener('scroll', () => this.handleScroll());
    }

    defineActions() {
        return [
            {
                id: 'start-timer',
                icon: 'fas fa-play',
                label: 'Start Timer',
                color: 'bg-green-500 hover:bg-green-600',
                action: () => this.startTimer(),
                shortcut: 't s'
            },
            {
                id: 'log-time',
                icon: 'fas fa-clock',
                label: 'Log Time',
                color: 'bg-blue-500 hover:bg-blue-600',
                action: () => window.location.href = '/timer/manual_entry',
                shortcut: 't l'
            },
            {
                id: 'new-project',
                icon: 'fas fa-folder-plus',
                label: 'New Project',
                color: 'bg-purple-500 hover:bg-purple-600',
                action: () => window.location.href = '/projects/create',
                shortcut: 'c p'
            },
            {
                id: 'new-task',
                icon: 'fas fa-tasks',
                label: 'New Task',
                color: 'bg-orange-500 hover:bg-orange-600',
                action: () => window.location.href = '/tasks/create',
                shortcut: 'c t'
            },
            {
                id: 'new-client',
                icon: 'fas fa-user-plus',
                label: 'New Client',
                color: 'bg-indigo-500 hover:bg-indigo-600',
                action: () => window.location.href = '/clients/create',
                shortcut: 'c c'
            },
            {
                id: 'quick-report',
                icon: 'fas fa-chart-line',
                label: 'Quick Report',
                color: 'bg-pink-500 hover:bg-pink-600',
                action: () => window.location.href = '/reports/',
                shortcut: 'g r'
            }
        ];
    }

    createButton() {
        this.button = document.createElement('button');
        this.button.id = 'quickActionsButton';
        this.button.className = 'fixed bottom-6 right-6 z-40 w-14 h-14 bg-primary text-white rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-200 flex items-center justify-center group';
        this.button.setAttribute('aria-label', 'Quick actions');
        this.button.innerHTML = `
            <i class="fas fa-bolt text-xl transition-transform duration-200 group-hover:rotate-12"></i>
        `;
        document.body.appendChild(this.button);
    }

    createMenu() {
        this.menu = document.createElement('div');
        this.menu.id = 'quickActionsMenu';
        this.menu.className = 'fixed bottom-24 right-6 z-40 hidden';
        
        let menuHTML = '<div class="flex flex-col gap-2">';
        
        this.actions.forEach((action, index) => {
            menuHTML += `
                <button
                    data-action="${action.id}"
                    class="${action.color} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 transition-all duration-200 hover:scale-105 hover:shadow-xl min-w-[200px] group"
                    style="animation: slideInRight 0.3s ease-out ${index * 0.05}s both;"
                    title="${action.shortcut ? 'Shortcut: ' + action.shortcut : ''}"
                >
                    <i class="${action.icon} text-lg group-hover:scale-110 transition-transform"></i>
                    <span class="font-medium flex-1 text-left">${action.label}</span>
                    ${action.shortcut ? `<kbd class="text-xs opacity-75 bg-white/20 px-2 py-1 rounded">${action.shortcut}</kbd>` : ''}
                </button>
            `;
        });
        
        menuHTML += '</div>';
        this.menu.innerHTML = menuHTML;
        document.body.appendChild(this.menu);

        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            #quickActionsButton.open i {
                transform: rotate(45deg);
            }
            
            @media (max-width: 768px) {
                #quickActionsMenu {
                    right: 1rem;
                    bottom: 5.5rem;
                }
                #quickActionsMenu button {
                    min-width: calc(100vw - 2rem);
                }
            }
        `;
        document.head.appendChild(style);
    }

    attachEventListeners() {
        // Toggle menu
        this.button.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Action buttons
        this.menu.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const actionId = e.currentTarget.dataset.action;
                const action = this.actions.find(a => a.id === actionId);
                if (action) {
                    action.action();
                    this.close();
                }
            });
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.menu.contains(e.target) && e.target !== this.button) {
                this.close();
            }
        });

        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.menu.classList.remove('hidden');
        this.button.classList.add('open');
        
        // Animate button
        this.button.style.transform = 'rotate(45deg)';
    }

    close() {
        this.isOpen = false;
        this.menu.classList.add('hidden');
        this.button.classList.remove('open');
        
        // Reset button
        this.button.style.transform = 'rotate(0deg)';
    }

    handleScroll() {
        const scrollY = window.scrollY;
        
        // Hide when scrolling down, show when scrolling up
        if (scrollY > this.lastScrollY && scrollY > 200) {
            this.button.style.transform = 'translateY(100px)';
        } else {
            this.button.style.transform = this.isOpen ? 'rotate(45deg)' : 'translateY(0)';
        }
        
        this.lastScrollY = scrollY;
    }

    startTimer() {
        // Try to find and click start timer button
        const startBtn = document.querySelector('#openStartTimer, button[onclick*="startTimer"]');
        if (startBtn) {
            startBtn.click();
        } else {
            window.location.href = '/timer/manual_entry';
        }
    }

    // Add custom action
    addAction(action) {
        this.actions.push(action);
        this.recreateMenu();
    }

    // Remove action
    removeAction(actionId) {
        this.actions = this.actions.filter(a => a.id !== actionId);
        this.recreateMenu();
    }

    recreateMenu() {
        this.menu.remove();
        this.createMenu();
        this.attachEventListeners();
    }
}

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    window.quickActionsMenu = new QuickActionsMenu();
});

