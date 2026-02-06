/* Enhanced Mobile JavaScript for TimeTracker */

// Mobile-specific variables and utilities
const MobileUtils = {
    // Touch target sizes
    TOUCH_TARGET_SIZE: 52,
    MOBILE_BREAKPOINT: 768,
    SMALL_MOBILE_BREAKPOINT: 480,
    
    // Check if device is mobile
    isMobile() {
        return window.innerWidth <= this.MOBILE_BREAKPOINT;
    },
    
    // Check if device is small mobile
    isSmallMobile() {
        return window.innerWidth <= this.SMALL_MOBILE_BREAKPOINT;
    },
    
    // Check if device supports touch
    isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    },
    
    // Check if device is iOS
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent);
    },
    
    // Check if device is Android
    isAndroid() {
        return /Android/.test(navigator.userAgent);
    }
};

// Enhanced mobile navigation handling
class MobileNavigation {
    constructor() {
        this.navbarToggler = document.querySelector('.navbar-toggler');
        this.navbarCollapse = document.querySelector('.navbar-collapse');
        this.navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        this.dropdownItems = document.querySelectorAll('.dropdown-item');
        
        this.init();
    }
    
    init() {
        if (this.navbarToggler && this.navbarCollapse) {
            this.setupEventListeners();
            this.setupTouchHandling();
        }
    }
    
    setupEventListeners() {
        // Close mobile menu when clicking outside
        document.addEventListener('click', (event) => {
            const isClickInsideNavbar = this.navbarToggler.contains(event.target) || 
                                       this.navbarCollapse.contains(event.target);
            
            if (!isClickInsideNavbar && this.navbarCollapse.classList.contains('show')) {
                this.closeMenu();
            }
        });
        
        // Close mobile menu when clicking on nav links that are not dropdown toggles
        this.navLinks.forEach(link => {
            link.addEventListener('click', (ev) => {
                if (!MobileUtils.isMobile()) return;
                // If a dropdown toggle inside the navbar, don't close the whole menu; let dropdown open
                const isDropdownToggle = link.classList.contains('dropdown-toggle');
                if (isDropdownToggle) {
                    // Allow Bootstrap's dropdown to toggle; prevent nav collapse from closing immediately
                    ev.stopPropagation();
                    return;
                }
                this.closeMenu();
            });
        });
        
        // Close mobile menu when a dropdown item is selected (navigate)
        this.dropdownItems.forEach(item => {
            item.addEventListener('click', () => {
                if (MobileUtils.isMobile()) {
                    this.closeMenu();
                }
            });
        });
        
        // Handle escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.navbarCollapse.classList.contains('show')) {
                this.closeMenu();
            }
        });
    }
    
    setupTouchHandling() {
        if (MobileUtils.isTouchDevice()) {
            // Add touch feedback to nav items
            this.navLinks.forEach(link => {
                link.addEventListener('touchstart', () => {
                    link.style.transform = 'scale(0.95)';
                });
                
                link.addEventListener('touchend', () => {
                    link.style.transform = 'scale(1)';
                });
            });
        }
    }
    
    closeMenu() {
        if (this.navbarCollapse.classList.contains('show')) {
            const bsCollapse = new bootstrap.Collapse(this.navbarCollapse);
            bsCollapse.hide();
        }
    }
}

// Enhanced mobile form handling
class MobileForms {
    constructor() {
        this.forms = document.querySelectorAll('form');
        this.inputs = document.querySelectorAll('.form-control, .form-select');
        
        this.init();
    }
    
    init() {
        this.setupFormHandling();
        this.setupInputHandling();
        this.setupMobileOptimizations();
    }
    
    setupFormHandling() {
        this.forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                this.handleFormSubmit(e, form);
            });
        });
    }
    
    setupInputHandling() {
        this.inputs.forEach(input => {
            // Prevent zoom on iOS
            if (MobileUtils.isIOS()) {
                input.style.fontSize = '16px';
            }
            
            // Add focus handling
            input.addEventListener('focus', () => {
                this.handleInputFocus(input);
            });
            
            input.addEventListener('blur', () => {
                this.handleInputBlur(input);
            });
            
            // Add touch handling
            if (MobileUtils.isTouchDevice()) {
                input.addEventListener('touchstart', () => {
                    this.handleInputTouch(input);
                });
            }
        });
    }
    
    setupMobileOptimizations() {
        if (MobileUtils.isMobile()) {
            // Add mobile-specific classes
            this.inputs.forEach(input => {
                input.classList.add('touch-target');
            });
            
            // Improve form layout on mobile
            const formGroups = document.querySelectorAll('.form-group, .mb-3');
            formGroups.forEach(group => {
                group.classList.add('mobile-form-group');
            });
        }
    }
    
    handleFormSubmit(event, form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            // If form is invalid, let browser show native messages and do NOT lock the button
            if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
                return;
            }

            // Store original text if not already stored
            if (!submitBtn.getAttribute('data-original-text')) {
                submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
            }

            // Show loading state and allow native submit
            submitBtn.innerHTML = '<div class="loading-spinner me-2"></div>Processing...';
            submitBtn.disabled = true;
        }
    }
    
    handleInputFocus(input) {
        input.classList.add('focused');
        
        // Scroll to input on mobile
        if (MobileUtils.isMobile()) {
            setTimeout(() => {
                input.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            }, 300);
        }
    }
    
    handleInputBlur(input) {
        input.classList.remove('focused');
    }
    
    handleInputTouch(input) {
        // Add touch feedback
        input.style.transform = 'scale(0.98)';
        setTimeout(() => {
            input.style.transform = 'scale(1)';
        }, 150);
    }
}

// Enhanced mobile table handling
class MobileTables {
    constructor() {
        this.tables = document.querySelectorAll('.table-responsive');
        
        this.init();
    }
    
    init() {
        this.setupMobileTables();
        this.setupTouchHandling();
    }
    
    setupMobileTables() {
        if (MobileUtils.isMobile()) {
            this.tables.forEach(table => {
                this.convertToMobileLayout(table);
            });
        }
    }
    
    convertToMobileLayout(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                this.addMobileLabels(cell, index);
            });
        });
    }
    
    addMobileLabels(cell, index) {
        const labels = ['Project', 'Duration', 'Date', 'Notes', 'Actions'];
        if (labels[index]) {
            cell.setAttribute('data-label', labels[index]);
        }
    }
    
    setupTouchHandling() {
        if (MobileUtils.isTouchDevice()) {
            const tableRows = document.querySelectorAll('tbody tr');
            tableRows.forEach(row => {
                row.addEventListener('touchstart', () => {
                    row.style.transform = 'scale(0.98)';
                });
                
                row.addEventListener('touchend', () => {
                    row.style.transform = 'scale(1)';
                });
            });
        }
    }
}

// Enhanced mobile card handling
class MobileCards {
    constructor() {
        this.cards = document.querySelectorAll('.card');
        
        this.init();
    }
    
    init() {
        this.setupCardHandling();
        this.setupMobileOptimizations();
    }
    
    setupCardHandling() {
        this.cards.forEach(card => {
            // Add mobile-specific classes
            if (MobileUtils.isMobile()) {
                card.classList.add('mobile-card');
            }
            
            // Add hover effects
            if (!MobileUtils.isTouchDevice()) {
                card.addEventListener('mouseenter', () => {
                    this.handleCardHover(card, true);
                });
                
                card.addEventListener('mouseleave', () => {
                    this.handleCardHover(card, false);
                });
            }
            
            // Add touch handling
            if (MobileUtils.isTouchDevice()) {
                card.addEventListener('touchstart', () => {
                    this.handleCardTouch(card, true);
                });
                
                card.addEventListener('touchend', () => {
                    this.handleCardTouch(card, false);
                });
            }
        });
    }
    
    setupMobileOptimizations() {
        if (MobileUtils.isMobile()) {
            // Improve card spacing
            this.cards.forEach(card => {
                card.style.marginBottom = '1rem';
            });
            
            // Add mobile-specific animations
            this.cards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.classList.add('mobile-fade-in');
            });
        }
    }
    
    handleCardHover(card, isHovering) {
        if (isHovering) {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
        } else {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '';
        }
    }
    
    handleCardTouch(card, isTouching) {
        if (isTouching) {
            card.style.transform = 'scale(0.98)';
        } else {
            card.style.transform = 'scale(1)';
        }
    }
}

// Enhanced mobile button handling
class MobileButtons {
    constructor() {
        this.buttons = document.querySelectorAll('.btn');
        
        this.init();
    }
    
    init() {
        this.setupButtonHandling();
        this.setupMobileOptimizations();
    }
    
    setupButtonHandling() {
        this.buttons.forEach(button => {
            // Add touch target class
            button.classList.add('touch-target');
            
            // Add touch handling
            if (MobileUtils.isTouchDevice()) {
                button.addEventListener('touchstart', () => {
                    this.handleButtonTouch(button, true);
                });
                
                button.addEventListener('touchend', () => {
                    this.handleButtonTouch(button, false);
                });
            }
            
            // Add loading state handling
            if (button.type === 'submit') {
                button.addEventListener('click', () => {
                    this.handleButtonClick(button);
                });
            }
        });
    }
    
    setupMobileOptimizations() {
        if (MobileUtils.isMobile()) {
            this.buttons.forEach(button => {
                // Make buttons full width on mobile
                button.style.width = '100%';
                button.style.marginBottom = '0.75rem';
                
                // Improve button sizing
                if (button.classList.contains('btn-sm')) {
                    button.style.minHeight = '44px';
                } else {
                    button.style.minHeight = '52px';
                }
            });
        }
    }
    
    handleButtonTouch(button, isTouching) {
        if (isTouching) {
            button.style.transform = 'scale(0.95)';
        } else {
            button.style.transform = 'scale(1)';
        }
    }
    
    handleButtonClick(button) {
        const form = button.closest('form');
        if (form) {
            // If inside a form, let the form's submit handler manage UI state
            if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
                // Invalid: let browser show native messages
                return;
            }
            // Valid form: do not disable or change button here to avoid blocking native submit
            return;
        }

        // Not inside a form: apply loading state to indicate action
        const originalText = button.innerHTML;
        button.setAttribute('data-original-text', originalText);
        button.innerHTML = '<div class="loading-spinner me-2"></div>Processing...';
        button.disabled = true;
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalText;
        }, 10000);
    }
}

// Enhanced mobile modal handling
class MobileModals {
    constructor() {
        this.modals = document.querySelectorAll('.modal');
        
        this.init();
    }
    
    init() {
        this.setupModalHandling();
        this.setupMobileOptimizations();
    }
    
    setupModalHandling() {
        this.modals.forEach(modal => {
            // Handle modal close on backdrop click
            modal.addEventListener('click', (event) => {
                if (event.target === modal) {
                    this.closeModal(modal);
                }
            });
            
            // Handle escape key
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && modal.classList.contains('show')) {
                    this.closeModal(modal);
                }
            });
        });
    }
    
    setupMobileOptimizations() {
        if (MobileUtils.isMobile()) {
            this.modals.forEach(modal => {
                const dialog = modal.querySelector('.modal-dialog');
                if (dialog) {
                    // Improve mobile modal sizing
                    dialog.style.margin = '0.75rem';
                    dialog.style.maxWidth = 'calc(100% - 1.5rem)';
                }
                
                // Improve mobile modal content
                const content = modal.querySelector('.modal-content');
                if (content) {
                    content.style.borderRadius = '12px';
                }
            });
        }
    }
    
    closeModal(modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        }
    }
}

// Enhanced mobile viewport handling
class MobileViewport {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupViewportHandling();
        this.setupOrientationHandling();
        this.setupResizeHandling();
    }
    
    setupViewportHandling() {
        // Set viewport meta tag for mobile
        if (MobileUtils.isMobile()) {
            this.setViewportMeta();
        }
        
        // Handle initial viewport
        this.handleViewportChange();
    }
    
    setupOrientationHandling() {
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleViewportChange();
            }, 100);
        });
    }
    
    setupResizeHandling() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleViewportChange();
            }, 250);
        });
    }
    
    setViewportMeta() {
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        
        if (MobileUtils.isIOS()) {
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
        } else {
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        }
    }
    
    handleViewportChange() {
        const isMobile = MobileUtils.isMobile();
        const isSmallMobile = MobileUtils.isSmallMobile();
        
        // Update body classes
        document.body.classList.toggle('mobile-view', isMobile);
        document.body.classList.toggle('small-mobile-view', isSmallMobile);
        
        // Update card classes
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.toggle('mobile-card', isMobile);
        });
        
        // Update button classes
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.classList.toggle('mobile-btn', isMobile);
        });
        
        // Update form classes
        const inputs = document.querySelectorAll('.form-control, .form-select');
        inputs.forEach(input => {
            input.classList.toggle('mobile-input', isMobile);
        });
    }
}

// Enhanced mobile performance optimization
class MobilePerformance {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupPerformanceOptimizations();
        this.setupLazyLoading();
    }
    
    setupPerformanceOptimizations() {
        if (MobileUtils.isMobile()) {
            // Reduce animations on mobile
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                document.body.classList.add('reduced-motion');
            }
            
            // Optimize images for mobile
            this.optimizeImages();
            
            // Optimize fonts for mobile
            this.optimizeFonts();
        }
    }
    
    setupLazyLoading() {
        // Lazy load images
        const images = document.querySelectorAll('img[data-src]');
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        }
    }
    
    optimizeImages() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            // Add loading="lazy" for mobile
            if (MobileUtils.isMobile()) {
                img.loading = 'lazy';
            }
            
            // Optimize image rendering
            img.style.imageRendering = 'optimizeQuality';
        });
    }
    
    optimizeFonts() {
        // Preload critical fonts
        if (MobileUtils.isMobile()) {
            const fontLink = document.createElement('link');
            fontLink.rel = 'preload';
            fontLink.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap';
            fontLink.as = 'style';
            document.head.appendChild(fontLink);
        }
    }
}

// Enhanced mobile accessibility
class MobileAccessibility {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupAccessibilityFeatures();
        this.setupKeyboardNavigation();
    }
    
    setupAccessibilityFeatures() {
        // Add ARIA labels for mobile
        if (MobileUtils.isMobile()) {
            this.addMobileAriaLabels();
        }
        
        // Improve focus management
        this.setupFocusManagement();
    }
    
    setupKeyboardNavigation() {
        // Handle keyboard navigation
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                this.handleTabNavigation(event);
            }
        });
    }
    
    addMobileAriaLabels() {
        // Add labels to interactive elements
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            if (!button.getAttribute('aria-label')) {
                const text = button.textContent.trim();
                if (text) {
                    button.setAttribute('aria-label', text);
                }
            }
        });
        
        // Add labels to form inputs
        const inputs = document.querySelectorAll('.form-control, .form-select');
        inputs.forEach(input => {
            const label = input.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                input.setAttribute('aria-labelledby', label.id || 'label-' + Math.random());
            }
        });
    }
    
    setupFocusManagement() {
        // Trap focus in modals
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('keydown', (event) => {
                if (event.key === 'Tab') {
                    this.trapFocusInModal(event, modal);
                }
            });
        });
    }
    
    handleTabNavigation(event) {
        // Handle tab navigation for mobile
        if (MobileUtils.isMobile()) {
            const focusableElements = document.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            if (event.shiftKey && document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            } else if (!event.shiftKey && document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    }
    
    trapFocusInModal(event, modal) {
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (event.shiftKey && document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    }
}

// Enhanced mobile gesture handling
class MobileGestures {
    constructor() {
        this.init();
    }
    
    init() {
        if (MobileUtils.isTouchDevice()) {
            this.setupGestureHandling();
        }
    }
    
    setupGestureHandling() {
        // Swipe gestures for navigation
        this.setupSwipeGestures();
        
        // Pinch to zoom prevention
        this.preventPinchZoom();
        
        // Double tap handling
        this.setupDoubleTapHandling();
    }
    
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        let endX = 0;
        let endY = 0;
        
        document.addEventListener('touchstart', (event) => {
            startX = event.touches[0].clientX;
            startY = event.touches[0].clientY;
        });
        
        document.addEventListener('touchend', (event) => {
            endX = event.changedTouches[0].clientX;
            endY = event.changedTouches[0].clientY;
            
            this.handleSwipe(startX, startY, endX, endY);
        });
    }
    
    handleSwipe(startX, startY, endX, endY) {
        const diffX = startX - endX;
        const diffY = startY - endY;
        
        // Minimum swipe distance
        const minSwipeDistance = 50;
        
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > minSwipeDistance) {
            // Horizontal swipe
            if (diffX > 0) {
                // Swipe left
                this.handleSwipeLeft();
            } else {
                // Swipe right
                this.handleSwipeRight();
            }
        }
    }
    
    handleSwipeLeft() {
        // Navigate between primary sections on swipe
        try {
            // Prefer reports after tasks
            const path = (location.pathname || '/').toLowerCase();
            if (path.startsWith('/')) {
                if (path.startsWith('/')) {
                    if (path === '/' || path.startsWith('/dashboard')) { window.location.href = '/projects'; return; }
                    if (path.startsWith('/projects')) { window.location.href = '/tasks'; return; }
                    if (path.startsWith('/tasks')) { window.location.href = '/reports'; return; }
                }
            }
        } catch (e) { /* no-op */ }
    }
    
    handleSwipeRight() {
        // Navigate backwards between primary sections on swipe
        try {
            const path = (location.pathname || '/').toLowerCase();
            if (path.startsWith('/')) {
                if (path.startsWith('/reports')) { window.location.href = '/tasks'; return; }
                if (path.startsWith('/tasks')) { window.location.href = '/projects'; return; }
                if (path.startsWith('/projects')) { window.location.href = '/'; return; }
            }
        } catch (e) { /* no-op */ }
    }
    
    preventPinchZoom() {
        document.addEventListener('gesturestart', (event) => {
            event.preventDefault();
        });
        
        document.addEventListener('gesturechange', (event) => {
            event.preventDefault();
        });
        
        document.addEventListener('gestureend', (event) => {
            event.preventDefault();
        });
    }
    
    setupDoubleTapHandling() {
        let lastTap = 0;
        
        document.addEventListener('touchend', (event) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < 500 && tapLength > 0) {
                // Double tap detected
                this.handleDoubleTap(event);
            }
            
            lastTap = currentTime;
        });
    }
    
    handleDoubleTap(event) {
        // no-op
    }
}

// Enhanced mobile error handling
class MobileErrorHandling {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupErrorHandling();
        this.setupOfflineHandling();
    }
    
    setupErrorHandling() {
        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleError(event.error);
        });
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason);
        });
    }
    
    setupOfflineHandling() {
        // Handle offline/online events
        window.addEventListener('offline', () => {
            this.handleOffline();
        });
        
        window.addEventListener('online', () => {
            this.handleOnline();
        });
    }
    
    handleError(error) {
        console.error('Mobile error:', error);
        
        // Show user-friendly error message
        if (MobileUtils.isMobile()) {
            this.showMobileError(error);
        }
    }
    
    handleOffline() {
        // Show offline indicator
        this.showOfflineIndicator();
    }
    
    handleOnline() {
        // Hide offline indicator
        this.hideOfflineIndicator();
    }
    
    showMobileError(error) {
        // Use the new toast notification system if available
        if (window.toastManager) {
            const message = error.message || 'Please try again or contact support if the problem persists.';
            window.toastManager.error(
                message,
                'Something went wrong',
                10000
            );
        } else {
            // Fallback to console if toast system not loaded
            console.error('Mobile error:', error);
        }
    }
    
    showOfflineIndicator() {
        // Use the new toast notification system if available
        if (window.toastManager) {
            // Store the toast ID for later dismissal
            this.offlineToastId = window.toastManager.warning(
                'Some features may not work properly.',
                "You're offline",
                0  // Don't auto-dismiss
            );
        }
    }
    
    hideOfflineIndicator() {
        // Dismiss the offline toast if it exists
        if (window.toastManager && this.offlineToastId) {
            window.toastManager.dismiss(this.offlineToastId);
            this.offlineToastId = null;
            // Show a success message that we're back online
            window.toastManager.success('Connection restored', "You're online", 3000);
        }
    }
}

// Initialize all mobile enhancements when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Prevent double initialization
    if (window.mobileEnhancementsInitialized) {
        return;
    }
    
    // Mark as initialized
    window.mobileEnhancementsInitialized = true;
    
    // Initialize all mobile classes
    new MobileNavigation();
    new MobileForms();
    new MobileTables();
    new MobileCards();
    new MobileButtons();
    new MobileModals();
    new MobileViewport();
    new MobilePerformance();
    new MobileAccessibility();
    new MobileGestures();
    new MobileErrorHandling();
    
    // Add mobile-specific body class
    if (MobileUtils.isMobile()) {
        document.body.classList.add('mobile-view');
    }
    
});

// Export for use in other scripts
window.MobileUtils = MobileUtils;
