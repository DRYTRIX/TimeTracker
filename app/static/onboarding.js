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
        this.active = false;
    }

    /**
     * Initialize onboarding
     */
    init(steps) {
        if (this.isCompleted()) {
            return;
        }
        // Guard against double-init: multiple scripts auto-start the tour, and a
        // second overlay would stack above the skip-confirmation dialog, making
        // the tour impossible to dismiss.
        if (this.active) {
            return;
        }
        this.active = true;

        // Mobile: show compact checklist sheet instead of desktop spotlight tour
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            this.showMobileChecklist();
            return;
        }

        this.steps = steps;
        this.createOverlay();
        this.createTooltip();
        
        // Add resize handler to handle window resizing during tour
        this.resizeHandler = () => {
            if (window.innerWidth <= 768) {
                this.complete(true);
                this.showMobileChecklist();
            }
        };
        window.addEventListener('resize', this.resizeHandler);
        
        this.showStep(0);
    }

    /**
     * Compact first-run checklist for mobile (does not auto-complete).
     */
    showMobileChecklist() {
        if (document.getElementById('tt-onboarding-sheet')) return;
        const sheet = document.createElement('div');
        sheet.id = 'tt-onboarding-sheet';
        sheet.setAttribute('role', 'dialog');
        sheet.setAttribute('aria-modal', 'true');
        sheet.setAttribute('aria-labelledby', 'tt-onboarding-sheet-title');
        sheet.innerHTML = `
            <div class="fixed inset-0 z-[9998] bg-black/40" data-dismiss></div>
            <div class="fixed inset-x-0 bottom-0 z-[9999] rounded-t-2xl border border-border-light dark:border-border-dark bg-card-light dark:bg-card-dark p-4 pb-safe shadow-2xl">
                <div class="flex items-start justify-between gap-3 mb-3">
                    <div>
                        <h2 id="tt-onboarding-sheet-title" class="text-base font-semibold text-text-light dark:text-text-dark">Get started</h2>
                        <p class="text-sm text-text-muted-light dark:text-text-muted-dark mt-0.5">Three steps to your first tracked hour.</p>
                    </div>
                    <button type="button" class="p-2 rounded-lg hover:bg-background-light dark:hover:bg-background-dark" data-dismiss aria-label="Dismiss">
                        <i class="fas fa-times" aria-hidden="true"></i>
                    </button>
                </div>
                <ol class="space-y-2 text-sm">
                    <li><a class="flex items-center gap-3 min-h-[44px] px-3 rounded-xl hover:bg-background-light dark:hover:bg-background-dark" href="/clients/create"><span class="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-semibold">1</span><span>Create a client</span></a></li>
                    <li><a class="flex items-center gap-3 min-h-[44px] px-3 rounded-xl hover:bg-background-light dark:hover:bg-background-dark" href="/projects/create"><span class="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-semibold">2</span><span>Create a project</span></a></li>
                    <li><a class="flex items-center gap-3 min-h-[44px] px-3 rounded-xl hover:bg-background-light dark:hover:bg-background-dark" href="/"><span class="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-semibold">3</span><span>Start the timer</span></a></li>
                </ol>
                <button type="button" class="mt-3 w-full btn btn-secondary" data-complete>Got it</button>
            </div>`;
        document.body.appendChild(sheet);
        const dismiss = (complete) => {
            sheet.remove();
            this.active = false;
            if (complete) localStorage.setItem(this.storageKey, 'true');
        };
        sheet.querySelectorAll('[data-dismiss]').forEach((el) => el.addEventListener('click', () => dismiss(false)));
        sheet.querySelector('[data-complete]')?.addEventListener('click', () => dismiss(true));
        sheet.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => dismiss(false)));
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
                    border: 4px solid #4F46E5;
                    border-radius: 8px;
                    /* No !important: skip() must be able to lower these layers
                       below the skip-confirmation dialog via inline styles. */
                    z-index: 10000;
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
                    z-index: 10001;
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
                    background: #4F46E5;
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
        // Don't re-raise the tooltip while the skip confirmation is open
        if (this._skipPending) return;
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
        // Prevent pending step-transition timers from re-raising the tooltip
        // while the confirmation dialog is open.
        this._skipPending = true;
        try {
            await this._showSkipConfirm();
        } finally {
            this._skipPending = false;
        }
    }

    async _showSkipConfirm() {
        // Temporarily lower the tour layers (overlay z-index 9998, mask 9999,
        // highlight 10000, tooltip 10001) so the confirmation dialog (z-index
        // 2000) appears above all of them and stays readable.
        const mask = document.querySelector('.onboarding-mask');
        const highlight = document.querySelector('.onboarding-highlight');
        const originalMaskZ = mask?.style.zIndex;
        const originalOverlayZ = this.overlay?.style.zIndex;
        const originalHighlightZ = highlight?.style.zIndex;
        const originalTooltipZ = this.tooltip?.style.zIndex;

        if (mask) {
            mask.style.zIndex = '1500';
        }
        if (this.overlay) {
            this.overlay.style.zIndex = '1500';
        }
        if (highlight) {
            highlight.style.zIndex = '1501';
        }
        if (this.tooltip) {
            this.tooltip.style.zIndex = '1502';
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
        if (this.tooltip) {
            if (originalTooltipZ) {
                this.tooltip.style.zIndex = originalTooltipZ;
            } else {
                this.tooltip.style.zIndex = '';
            }
        }
        
        if (confirmed) {
            this.complete();
        }
    }

    /**
     * Complete the tour
     * @param {boolean} [silent=false] Skip toast when switching to mobile checklist
     */
    complete(silent = false) {
        // Remove elements
        if (this.overlay) this.overlay.remove();
        if (this.tooltip) this.tooltip.remove();
        document.querySelector('.onboarding-highlight')?.remove();
        document.querySelector('.onboarding-mask')?.remove();
        this.active = false;

        // Remove resize listener if it exists
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }

        // Mark as completed
        localStorage.setItem(this.storageKey, 'true');

        // Show success message
        if (!silent && window.toastManager) {
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

// Short first-run checklist (3 steps). Module-gated selectors are skipped if missing.
const defaultTourSteps = [
    {
        target: 'a[href*="clients"]',
        title: '1. Create a client',
        content: 'Start with a client so projects and invoices have somewhere to bill. Open <strong>Clients</strong> and add your first one.',
        position: 'right'
    },
    {
        target: 'a[href*="projects"]',
        title: '2. Create a project',
        content: 'Projects hold the work you track. Open <strong>Projects</strong>, create one, and link it to your client.',
        position: 'right'
    },
    {
        target: '#floatingTimerBar, a[href="/"], a[href*="dashboard"]',
        title: '3. Start the timer',
        content: 'Use the timer in the top bar or the <strong>Track</strong> item under Time. Live timers run on the server even if you close the browser.',
        position: 'bottom'
    }
];

// Initialize global onboarding manager
window.onboardingManager = new OnboardingManager();

// Auto-start onboarding for new users
document.addEventListener('DOMContentLoaded', () => {
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

