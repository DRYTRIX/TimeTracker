/**
 * Onboarding System for TimeTracker
 * Interactive product tours and first-time user experience
 */

class OnboardingManager {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.storageKey = 'onboarding_completed';
    }

    /**
     * Initialize onboarding
     */
    init(steps) {
        if (this.isCompleted()) {
            return;
        }

        this.steps = steps;
        this.createOverlay();
        this.createTooltip();
        this.showStep(0);
    }

    /**
     * Create overlay element
     */
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'onboarding-overlay';
        this.overlay.innerHTML = `
            <style>
                .onboarding-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.7);
                    z-index: 9998;
                    backdrop-filter: blur(2px);
                    animation: fadeIn 0.3s ease-out;
                }
                
                .onboarding-highlight {
                    position: absolute;
                    border: 3px solid #3b82f6;
                    border-radius: 8px;
                    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.7);
                    z-index: 9999;
                    transition: all 0.3s ease-out;
                    pointer-events: none;
                }
                
                .onboarding-tooltip {
                    position: fixed;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
                    padding: 24px;
                    max-width: 400px;
                    z-index: 10000;
                    animation: slideInUp 0.3s ease-out;
                }
                
                .dark .onboarding-tooltip {
                    background: #2d3748;
                    color: #e2e8f0;
                }
                
                .onboarding-tooltip-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 12px;
                }
                
                .onboarding-tooltip-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #1e293b;
                }
                
                .dark .onboarding-tooltip-title {
                    color: #e2e8f0;
                }
                
                .onboarding-tooltip-close {
                    background: none;
                    border: none;
                    font-size: 20px;
                    color: #9ca3af;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .onboarding-tooltip-close:hover {
                    color: #ef4444;
                }
                
                .onboarding-tooltip-body {
                    color: #64748b;
                    line-height: 1.6;
                    margin-bottom: 20px;
                }
                
                .dark .onboarding-tooltip-body {
                    color: #94a3b8;
                }
                
                .onboarding-tooltip-footer {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                
                .onboarding-tooltip-progress {
                    font-size: 14px;
                    color: #9ca3af;
                }
                
                .onboarding-tooltip-buttons {
                    display: flex;
                    gap: 8px;
                }
                
                .onboarding-btn {
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: none;
                    font-size: 14px;
                }
                
                .onboarding-btn-skip {
                    background: #f3f4f6;
                    color: #6b7280;
                }
                
                .dark .onboarding-btn-skip {
                    background: #374151;
                    color: #9ca3af;
                }
                
                .onboarding-btn-skip:hover {
                    background: #e5e7eb;
                }
                
                .dark .onboarding-btn-skip:hover {
                    background: #4b5563;
                }
                
                .onboarding-btn-primary {
                    background: #3b82f6;
                    color: white;
                }
                
                .onboarding-btn-primary:hover {
                    background: #2563eb;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                
                @keyframes slideInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            </style>
        `;
        document.body.appendChild(this.overlay);
    }

    /**
     * Create tooltip element
     */
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'onboarding-tooltip';
        document.body.appendChild(this.tooltip);
    }

    /**
     * Show a specific step
     */
    showStep(index) {
        if (index < 0 || index >= this.steps.length) {
            this.complete();
            return;
        }

        this.currentStep = index;
        const step = this.steps[index];

        // Find target element
        const target = document.querySelector(step.target);
        if (!target) {
            console.warn(`Onboarding target not found: ${step.target}`);
            this.showStep(index + 1);
            return;
        }

        // Highlight target
        this.highlightElement(target);

        // Position tooltip
        this.positionTooltip(target, step);

        // Update tooltip content
        this.updateTooltip(step, index);

        // Scroll target into view
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    /**
     * Highlight target element
     */
    highlightElement(element) {
        let highlight = document.querySelector('.onboarding-highlight');
        
        if (!highlight) {
            highlight = document.createElement('div');
            highlight.className = 'onboarding-highlight';
            document.body.appendChild(highlight);
        }

        const rect = element.getBoundingClientRect();
        const padding = 8;

        highlight.style.top = `${rect.top - padding + window.scrollY}px`;
        highlight.style.left = `${rect.left - padding}px`;
        highlight.style.width = `${rect.width + padding * 2}px`;
        highlight.style.height = `${rect.height + padding * 2}px`;
    }

    /**
     * Position tooltip relative to target
     */
    positionTooltip(element, step) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const position = step.position || 'bottom';

        let top, left;

        switch (position) {
            case 'top':
                top = rect.top - tooltipRect.height - 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - 20;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + 20;
                break;
            default:
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        }

        // Keep within viewport
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        if (left < 10) left = 10;
        if (left + tooltipRect.width > viewportWidth - 10) {
            left = viewportWidth - tooltipRect.width - 10;
        }
        if (top < 10) top = 10;
        if (top + tooltipRect.height > viewportHeight - 10) {
            top = viewportHeight - tooltipRect.height - 10;
        }

        this.tooltip.style.top = `${top + window.scrollY}px`;
        this.tooltip.style.left = `${left}px`;
    }

    /**
     * Update tooltip content
     */
    updateTooltip(step, index) {
        const isLast = index === this.steps.length - 1;
        
        this.tooltip.innerHTML = `
            <div class="onboarding-tooltip-header">
                <h3 class="onboarding-tooltip-title">${step.title}</h3>
                <button class="onboarding-tooltip-close" onclick="onboardingManager.skip()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="onboarding-tooltip-body">
                ${step.content}
            </div>
            <div class="onboarding-tooltip-footer">
                <span class="onboarding-tooltip-progress">
                    ${index + 1} / ${this.steps.length}
                </span>
                <div class="onboarding-tooltip-buttons">
                    <button class="onboarding-btn onboarding-btn-skip" onclick="onboardingManager.skip()">
                        Skip Tour
                    </button>
                    ${index > 0 ? `
                        <button class="onboarding-btn onboarding-btn-skip" onclick="onboardingManager.previous()">
                            <i class="fas fa-arrow-left mr-1"></i> Back
                        </button>
                    ` : ''}
                    <button class="onboarding-btn onboarding-btn-primary" onclick="onboardingManager.next()">
                        ${isLast ? 'Finish' : 'Next'} <i class="fas fa-arrow-right ml-1"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Go to next step
     */
    next() {
        this.showStep(this.currentStep + 1);
    }

    /**
     * Go to previous step
     */
    previous() {
        this.showStep(this.currentStep - 1);
    }

    /**
     * Skip the tour
     */
    skip() {
        if (confirm('Are you sure you want to skip the tour? You can restart it later from the Help menu.')) {
            this.complete();
        }
    }

    /**
     * Complete the tour
     */
    complete() {
        // Remove elements
        if (this.overlay) this.overlay.remove();
        if (this.tooltip) this.tooltip.remove();
        document.querySelector('.onboarding-highlight')?.remove();

        // Mark as completed
        localStorage.setItem(this.storageKey, 'true');

        // Show success message
        if (window.toastManager) {
            window.toastManager.success('Tour completed! You\'re all set to start tracking time.');
        }

        // Trigger completion callback if provided
        if (this.onComplete) {
            this.onComplete();
        }
    }

    /**
     * Check if onboarding is completed
     */
    isCompleted() {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    /**
     * Reset onboarding (for testing)
     */
    reset() {
        localStorage.removeItem(this.storageKey);
    }
}

// Default tour steps for TimeTracker
const defaultTourSteps = [
    {
        target: '#sidebar',
        title: 'Welcome to TimeTracker! 👋',
        content: 'Let\'s take a quick tour to help you get started. This is your main navigation where you can access all features.',
        position: 'right'
    },
    {
        target: 'a[href*="dashboard"]',
        title: 'Dashboard',
        content: 'Your dashboard shows an overview of your time tracking, active timers, and recent activities.',
        position: 'right'
    },
    {
        target: 'a[href*="projects"]',
        title: 'Projects',
        content: 'Create and manage projects here. Projects help you organize your work and track time for different clients.',
        position: 'right'
    },
    {
        target: 'a[href*="tasks"]',
        title: 'Tasks',
        content: 'Break down your projects into tasks. You can track time against specific tasks and monitor progress.',
        position: 'right'
    },
    {
        target: 'a[href*="timer"]',
        title: 'Time Tracking',
        content: 'Start timers or manually log your time here. TimeTracker keeps running even if you close your browser!',
        position: 'right'
    },
    {
        target: 'a[href*="reports"]',
        title: 'Reports & Analytics',
        content: 'View detailed reports, charts, and analytics about your time usage and project progress.',
        position: 'right'
    },
    {
        target: '#themeToggle',
        title: 'Theme Toggle',
        content: 'Switch between light and dark mode based on your preference. Your choice is saved automatically.',
        position: 'bottom'
    }
];

// Initialize global onboarding manager
window.onboardingManager = new OnboardingManager();

// Auto-start onboarding for new users
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is on dashboard and hasn't completed onboarding
    if (window.location.pathname === '/main/dashboard' || window.location.pathname === '/') {
        setTimeout(() => {
            if (!window.onboardingManager.isCompleted()) {
                window.onboardingManager.init(defaultTourSteps);
            }
        }, 1000);
    }
});

// Add restart tour button to help menu
function restartTour() {
    window.onboardingManager.reset();
    window.onboardingManager.init(defaultTourSteps);
}

