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

        // Disable tour on mobile devices (width < 768px)
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            // Mark as completed to prevent future attempts
            localStorage.setItem(this.storageKey, 'true');
            return;
        }

        this.steps = steps;
        this.createOverlay();
        this.createTooltip();
        
        // Add resize handler to handle window resizing during tour
        this.resizeHandler = () => {
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                // If window is resized to mobile size, cancel the tour
                this.complete();
            }
        };
        window.addEventListener('resize', this.resizeHandler);
        
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
                    pointer-events: none;
                }
                
                .onboarding-overlay * {
                    pointer-events: none;
                }
                
                .onboarding-highlight {
                    position: fixed;
                    border: 4px solid #3b82f6;
                    border-radius: 8px;
                    z-index: 10000 !important;
                    transition: all 0.3s ease-out;
                    pointer-events: none;
                    background: transparent;
                    box-shadow: 
                        0 0 0 0 rgba(59, 130, 246, 0),
                        0 0 20px rgba(59, 130, 246, 0.6),
                        0 0 40px rgba(59, 130, 246, 0.4),
                        inset 0 0 20px rgba(59, 130, 246, 0.2);
                }
                
                .onboarding-highlight::before {
                    content: '';
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.8);
                    z-index: 9999;
                    pointer-events: none;
                    mask: radial-gradient(ellipse at center, transparent 0%, transparent 100%);
                    -webkit-mask: radial-gradient(ellipse at center, transparent 0%, transparent 100%);
                }
                
                .onboarding-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 9998;
                    backdrop-filter: blur(2px);
                    animation: fadeIn 0.3s ease-out;
                    pointer-events: none;
                }
                
                .onboarding-mask {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.6);
                    z-index: 9999;
                    pointer-events: none;
                    transition: all 0.3s ease-out;
                }
                
                .onboarding-tooltip {
                    position: fixed;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
                    padding: 24px;
                    max-width: 400px;
                    min-width: 300px;
                    z-index: 10001 !important;
                    animation: slideInUp 0.3s ease-out;
                    display: block;
                    visibility: visible;
                    transition: opacity 0.2s ease-out;
                    pointer-events: auto;
                }
                
                /* Mobile responsive styles (for future use if tour is enabled on mobile) */
                @media (max-width: 768px) {
                    .onboarding-tooltip {
                        max-width: calc(100vw - 32px);
                        min-width: unset;
                        width: calc(100vw - 32px);
                        padding: 20px;
                        left: 16px !important;
                        right: 16px !important;
                        top: auto !important;
                        bottom: 20px !important;
                        transform: translateY(0) !important;
                    }
                    
                    .onboarding-tooltip-header {
                        margin-bottom: 10px;
                    }
                    
                    .onboarding-tooltip-title {
                        font-size: 16px;
                    }
                    
                    .onboarding-tooltip-body {
                        font-size: 14px;
                        margin-bottom: 16px;
                    }
                    
                    .onboarding-tooltip-footer {
                        flex-direction: column;
                        gap: 12px;
                    }
                    
                    .onboarding-tooltip-buttons {
                        width: 100%;
                        flex-direction: column;
                    }
                    
                    .onboarding-btn {
                        width: 100%;
                        padding: 12px 16px;
                    }
                    
                    .onboarding-tooltip-progress {
                        text-align: center;
                        width: 100%;
                    }
                }
                
                .onboarding-tooltip * {
                    pointer-events: auto;
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
                
                .onboarding-tooltip-body kbd {
                    display: inline-block;
                    padding: 2px 6px;
                    font-size: 0.875rem;
                    font-family: monospace;
                    background: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                    color: #334155;
                }
                
                .dark .onboarding-tooltip-body kbd {
                    background: #1e293b;
                    border-color: #334155;
                    color: #e2e8f0;
                }
                
                .onboarding-tooltip-body strong {
                    color: #1e293b;
                    font-weight: 600;
                }
                
                .dark .onboarding-tooltip-body strong {
                    color: #e2e8f0;
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

        // Find target element with better selector handling
        let target = null;
        
        // Try to find the element
        const elements = document.querySelectorAll(step.target);
        
        if (elements.length === 0) {
            console.warn(`Onboarding target not found: ${step.target}`);
            // Try once more after a short delay in case element is still loading
            setTimeout(() => {
                const retryElements = document.querySelectorAll(step.target);
                if (retryElements.length > 0) {
                    target = retryElements[0];
                    this.displayStep(target, step, index);
                } else {
                    console.warn(`Onboarding target still not found after retry: ${step.target}, skipping step`);
                    this.showStep(index + 1);
                }
            }, 200);
            return;
        }
        
        // If multiple elements found, prefer visible ones or first one
        for (const el of elements) {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            // Check if element is visible (not hidden by display:none or visibility:hidden)
            if (rect.width > 0 && rect.height > 0 && 
                style.display !== 'none' && 
                style.visibility !== 'hidden' &&
                style.opacity !== '0') {
                target = el;
                break;
            }
        }
        
        // If no visible element found, use first one anyway
        if (!target && elements.length > 0) {
            target = elements[0];
            
            // Try to make it visible if it's in a hidden dropdown
            const dropdown = target.closest('[id*="Dropdown"]');
            if (dropdown && dropdown.classList.contains('hidden')) {
                dropdown.classList.remove('hidden');
            }
        }
        
        if (!target) {
            console.warn(`Onboarding target not accessible: ${step.target}`);
            this.showStep(index + 1);
            return;
        }
        
        this.displayStep(target, step, index);
    }
    
    /**
     * Display a step for a given target element
     */
    displayStep(target, step, index) {
        // Ensure element is visible (expand dropdowns, etc.)
        const dropdown = target.closest('[id*="Dropdown"]');
        if (dropdown && dropdown.classList.contains('hidden')) {
            dropdown.classList.remove('hidden');
        }
        
        // Scroll target into view first
        target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });

        // Wait for scroll animation to complete, then proceed
        setTimeout(() => {
            // Update tooltip content first (so we can measure it)
            this.updateTooltip(step, index);

            // Wait for tooltip to render with content, then position both highlight and tooltip
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    // Get fresh element position after scroll
                    const finalRect = target.getBoundingClientRect();
                    const style = window.getComputedStyle(target);
                    
                    // Validate that element is actually visible
                    if (finalRect.width === 0 || finalRect.height === 0) {
                        console.warn('Target element has zero dimensions, but continuing anyway');
                        // Don't skip - just proceed with positioning
                    }
                    
                    // Highlight target after content is rendered
                    this.highlightElement(target);
                    
                    // Position tooltip
                    this.positionTooltip(target, step);
                });
            });
        }, 400);
    }

    /**
     * Highlight target element
     */
    highlightElement(element) {
        let highlight = document.querySelector('.onboarding-highlight');
        let mask = document.querySelector('.onboarding-mask');
        
        if (!highlight) {
            highlight = document.createElement('div');
            highlight.className = 'onboarding-highlight';
            document.body.appendChild(highlight);
        }
        
        if (!mask) {
            mask = document.createElement('div');
            mask.className = 'onboarding-mask';
            mask.style.cssText = `
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.6);
                z-index: 9999;
                pointer-events: none;
                transition: opacity 0.3s ease-out;
            `;
            document.body.appendChild(mask);
        }

        // Use getBoundingClientRect which already accounts for scroll
        const rect = element.getBoundingClientRect();
        
        const padding = 10;
        
        // Calculate highlight position
        const highlightTop = Math.round(rect.top - padding);
        const highlightLeft = Math.round(rect.left - padding);
        const highlightWidth = Math.round(rect.width + padding * 2);
        const highlightHeight = Math.round(rect.height + padding * 2);

        // Use fixed positioning to match viewport coordinates
        highlight.style.position = 'fixed';
        highlight.style.top = `${highlightTop}px`;
        highlight.style.left = `${highlightLeft}px`;
        highlight.style.width = `${highlightWidth}px`;
        highlight.style.height = `${highlightHeight}px`;
        highlight.style.display = 'block';
        highlight.style.zIndex = '10000';
        highlight.style.visibility = 'visible';
        
        // Create a mask that reveals the highlighted area
        // Use CSS radial gradient for the cutout
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        // Make cutout larger than the highlight for better visibility
        const ellipseWidth = Math.max(highlightWidth * 2, 200);
        const ellipseHeight = Math.max(highlightHeight * 2, 200);
        
        // Apply mask to overlay mask element using CSS radial gradient
        // In CSS mask-image: white/opaque = visible (shows), black/transparent = hidden (hides)
        // We want: hide overlay at center (reveal element), show overlay at edges (cover everything else)
        // So: transparent at center (hides overlay), white at edges (shows overlay)
        const overlayMask = document.querySelector('.onboarding-mask');
        if (overlayMask) {
            // Radial gradient: transparent at center (hides overlay, reveals element), white at edges (shows overlay, covers background)
            const maskGradient = `radial-gradient(ellipse ${ellipseWidth}px ${ellipseHeight}px at ${centerX}px ${centerY}px, transparent 0%, transparent 50%, rgba(255,255,255,0.2) 65%, rgba(255,255,255,0.6) 80%, white 100%)`;
            overlayMask.style.maskImage = maskGradient;
            overlayMask.style.webkitMaskImage = maskGradient;
            overlayMask.style.maskSize = '100% 100%';
            overlayMask.style.maskPosition = '0 0';
            overlayMask.style.maskRepeat = 'no-repeat';
        }
        
        // Also apply mask to the base overlay
        const baseOverlay = document.querySelector('.onboarding-overlay');
        if (baseOverlay) {
            const overlayGradient = `radial-gradient(ellipse ${ellipseWidth}px ${ellipseHeight}px at ${centerX}px ${centerY}px, transparent 0%, transparent 50%, rgba(255,255,255,0.2) 65%, rgba(255,255,255,0.6) 80%, white 100%)`;
            baseOverlay.style.maskImage = overlayGradient;
            baseOverlay.style.webkitMaskImage = overlayGradient;
            baseOverlay.style.maskSize = '100% 100%';
            baseOverlay.style.maskPosition = '0 0';
            baseOverlay.style.maskRepeat = 'no-repeat';
        }
    }

    /**
     * Position tooltip relative to target
     */
    positionTooltip(element, step) {
        // Get element position first - getBoundingClientRect already accounts for scroll
        const rect = element.getBoundingClientRect();
        
        // Validate element is visible
        if (rect.width === 0 || rect.height === 0) {
            console.warn('Cannot position tooltip: element has zero dimensions');
            return;
        }
        
        // Ensure tooltip is positioned off-screen for measurement
        this.tooltip.style.position = 'fixed';
        this.tooltip.style.top = '-9999px';
        this.tooltip.style.left = '-9999px';
        this.tooltip.style.visibility = 'hidden';
        this.tooltip.style.display = 'block';
        this.tooltip.style.opacity = '0';
        this.tooltip.style.transform = 'scale(0)';
        
        // Force a reflow to ensure tooltip is rendered
        void this.tooltip.offsetWidth;
        
        // Now measure the tooltip
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const position = step.position || 'bottom';

        // If tooltip has no dimensions, use default dimensions
        const tooltipWidth = tooltipRect.width > 0 ? tooltipRect.width : 400;
        const tooltipHeight = tooltipRect.height > 0 ? tooltipRect.height : 200;
        
        let top, left;

        // Calculate position based on preference
        // All coordinates are relative to viewport (from getBoundingClientRect)
        switch (position) {
            case 'top':
                top = rect.top - tooltipHeight - 20;
                left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
                left = rect.left - tooltipWidth - 20;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
                left = rect.right + 20;
                break;
            default:
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        }

        // Keep within viewport
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const padding = 10;

        // Adjust horizontal position if needed
        if (left < padding) {
            left = padding;
        } else if (left + tooltipWidth > viewportWidth - padding) {
            left = Math.max(padding, viewportWidth - tooltipWidth - padding);
        }

        // Adjust vertical position if needed
        if (top < padding) {
            // If tooltip would go above viewport, try bottom instead
            if (position === 'top') {
                top = rect.bottom + 20;
            } else {
                top = padding;
            }
        } else if (top + tooltipHeight > viewportHeight - padding) {
            // If tooltip would go below viewport, try top instead
            if (position === 'bottom') {
                top = Math.max(padding, rect.top - tooltipHeight - 20);
            } else {
                top = Math.max(padding, viewportHeight - tooltipHeight - padding);
            }
        }

        // Validate final coordinates are reasonable
        if (isNaN(top) || isNaN(left) || top < 0 || left < 0) {
            console.error('Invalid tooltip position calculated:', { top, left, rect });
            // Fallback to center of viewport
            top = (viewportHeight - tooltipHeight) / 2;
            left = (viewportWidth - tooltipWidth) / 2;
        }

        // Apply final position using fixed positioning (viewport coordinates)
        this.tooltip.style.position = 'fixed';
        this.tooltip.style.top = `${Math.round(top)}px`;
        this.tooltip.style.left = `${Math.round(left)}px`;
        this.tooltip.style.visibility = 'visible';
        this.tooltip.style.display = 'block';
        this.tooltip.style.opacity = '1';
        this.tooltip.style.transform = 'scale(1)';
        this.tooltip.style.zIndex = '10001'; // Ensure it's above overlay (z-index 9998) and highlight (10000)
    }

    /**
     * Update tooltip content
     */
    updateTooltip(step, index) {
        const isLast = index === this.steps.length - 1;
        
        // Store reference to manager for event handlers
        const manager = this;
        
        this.tooltip.innerHTML = `
            <div class="onboarding-tooltip-header">
                <h3 class="onboarding-tooltip-title">${step.title}</h3>
                <button class="onboarding-tooltip-close" data-action="skip">
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
                    <button class="onboarding-btn onboarding-btn-skip" data-action="skip">
                        Skip Tour
                    </button>
                    ${index > 0 ? `
                        <button class="onboarding-btn onboarding-btn-skip" data-action="previous">
                            <i class="fas fa-arrow-left mr-1"></i> Back
                        </button>
                    ` : ''}
                    <button class="onboarding-btn onboarding-btn-primary" data-action="next">
                        ${isLast ? 'Finish' : 'Next'} <i class="fas fa-arrow-right ml-1"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Attach event listeners using event delegation
        this.tooltip.querySelectorAll('[data-action]').forEach(btn => {
            const action = btn.getAttribute('data-action');
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (action === 'skip') {
                    manager.skip();
                } else if (action === 'next') {
                    manager.next();
                } else if (action === 'previous') {
                    manager.previous();
                }
            });
        });
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
    async skip() {
        // Temporarily lower the mask and overlay z-index so the confirmation dialog (z-index 2000) appears above them
        const mask = document.querySelector('.onboarding-mask');
        const highlight = document.querySelector('.onboarding-highlight');
        const originalMaskZ = mask?.style.zIndex;
        const originalOverlayZ = this.overlay?.style.zIndex;
        const originalHighlightZ = highlight?.style.zIndex;
        
        // Lower mask and overlay z-index so confirmation dialog (z-index 2000) appears above
        if (mask) {
            mask.style.zIndex = '1500';
        }
        if (this.overlay) {
            this.overlay.style.zIndex = '1500';
        }
        if (highlight) {
            highlight.style.zIndex = '1501';
        }
        
        const confirmed = await showConfirm(
            'Are you sure you want to skip the tour? You can restart it later from the Help menu.',
            {
                title: 'Skip Tour',
                confirmText: 'Skip',
                cancelText: 'Continue Tour',
                variant: 'warning'
            }
        );
        
        // Restore original z-index values
        if (mask) {
            if (originalMaskZ) {
                mask.style.zIndex = originalMaskZ;
            } else {
                mask.style.zIndex = '';
            }
        }
        if (this.overlay) {
            if (originalOverlayZ) {
                this.overlay.style.zIndex = originalOverlayZ;
            } else {
                this.overlay.style.zIndex = '';
            }
        }
        if (highlight) {
            if (originalHighlightZ) {
                highlight.style.zIndex = originalHighlightZ;
            } else {
                highlight.style.zIndex = '';
            }
        }
        
        if (confirmed) {
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
        document.querySelector('.onboarding-mask')?.remove();

        // Remove resize listener if it exists
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }

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
        content: 'Let\'s take a quick tour to help you get started. This is your main navigation where you can access all features. <strong>Tip:</strong> You can collapse the sidebar by clicking the arrow icon to maximize your workspace.',
        position: 'right'
    },
    {
        target: 'a[href*="dashboard"]',
        title: 'Dashboard',
        content: 'Your command center! View today\'s hours, active timers, recent entries, top projects, and activity timeline. <strong>Pro tip:</strong> Customize widgets to see what matters most to you. You can also see your time tracking at a glance without navigating away.',
        position: 'right'
    },
    {
        target: 'a[href*="timer"]',
        title: 'Time Tracking',
        content: 'Start timers or manually log your time. <strong>Key features:</strong><br>• Timers run server-side (even if browser closes!)<br>• Press <kbd>T</kbd> to quickly toggle timer<br>• Use bulk entry for multiple days<br>• Save time entry templates for recurring work<br>• Idle detection auto-pauses after inactivity',
        position: 'right'
    },
    {
        target: 'a[href*="projects"]',
        title: 'Projects',
        content: 'Organize your work with projects. <strong>What you can do:</strong><br>• Link projects to clients for billing<br>• Set hourly rates per project<br>• Track billable vs non-billable hours<br>• Monitor project budgets and costs<br>• Add project descriptions with Markdown<br>• Archive completed projects',
        position: 'right'
    },
    {
        target: 'a[href*="clients"]',
        title: 'Clients',
        content: 'Manage your clients and their information. Store contact details, billing rates, and company information. Clients are automatically linked to projects for streamlined invoicing and reporting.',
        position: 'right'
    },
    {
        target: 'a[href*="tasks"]',
        title: 'Tasks',
        content: 'Break down projects into manageable tasks. <strong>Features:</strong><br>• Track time against specific tasks<br>• Set priorities and due dates<br>• Assign tasks to team members<br>• Monitor progress with status tracking<br>• Use estimates vs actuals for planning<br>• Add comments for collaboration',
        position: 'right'
    },
    {
        target: 'a[href*="kanban"]',
        title: 'Kanban Board',
        content: 'Visual task management with drag-and-drop! Move tasks between columns (To Do, In Progress, Review, Done) to track progress. Perfect for agile workflows and visual project management. <strong>Power feature:</strong> Customize columns to match your workflow.',
        position: 'right'
    },
    {
        target: 'a[href*="calendar"]',
        title: 'Calendar View',
        content: 'Visualize your time entries on a calendar. See your schedule at a glance, spot gaps, and plan your time more effectively. Drag and drop entries to reschedule them quickly.',
        position: 'right'
    },
    {
        target: 'a[href*="reports"]',
        title: 'Reports & Analytics',
        content: 'Gain insights into your time usage. <strong>Available reports:</strong><br>• Time breakdown by project, user, or date<br>• Billable vs non-billable analysis<br>• Export to PDF or CSV<br>• Custom date ranges<br>• Save filters for quick access<br>• Visual charts and graphs',
        position: 'right'
    },
    {
        target: 'a[href*="invoices"]',
        title: 'Invoicing',
        content: 'Generate professional invoices from your tracked time. <strong>Features:</strong><br>• Auto-generate from time entries<br>• Add custom line items and expenses<br>• Tax calculations<br>• PDF export with branding<br>• Track payment status<br>• Send invoices to clients',
        position: 'right'
    },
    {
        target: 'a[href*="analytics"]',
        title: 'Analytics Dashboard',
        content: 'Deep insights into your productivity and time patterns. View trends, project analytics, and performance metrics. Identify your most productive times and optimize your workflow.',
        position: 'right'
    },
    {
        target: '#search',
        title: 'Global Search',
        content: 'Quickly find anything! Search across projects, tasks, clients, and time entries. <strong>Keyboard shortcut:</strong> Press <kbd>Ctrl+/</kbd> (or <kbd>Cmd+/</kbd> on Mac) to focus the search bar instantly.',
        position: 'bottom'
    },
    {
        target: 'button[onclick*="openCommandPalette"]',
        title: 'Command Palette',
        content: 'Power user feature! Press <kbd>Ctrl+K</kbd> (or <kbd>Cmd+K</kbd> on Mac) to open the command palette. Navigate to any feature, execute actions, and access shortcuts without using your mouse. <strong>Try it:</strong> Press <kbd>Ctrl+K</kbd> now!',
        position: 'bottom'
    },
    {
        target: '#theme-toggle',
        title: 'Theme Toggle',
        content: 'Switch between light and dark mode. Your preference is saved automatically. <strong>Keyboard shortcut:</strong> Press <kbd>Ctrl+Shift+L</kbd> to toggle themes quickly.',
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
            // Skip on mobile devices (width < 768px)
            const isMobile = window.innerWidth <= 768;
            if (!isMobile && !window.onboardingManager.isCompleted()) {
                window.onboardingManager.init(defaultTourSteps);
            } else if (isMobile) {
                // Mark as completed on mobile to prevent future attempts
                localStorage.setItem('onboarding_completed', 'true');
            }
        }, 1000);
    }
});

// Add restart tour button to help menu
function restartTour() {
    window.onboardingManager.reset();
    window.onboardingManager.init(defaultTourSteps);
}

