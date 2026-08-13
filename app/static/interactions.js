/**
 * TimeTracker Micro-Interactions & UI Enhancements
 * Handles loading states, animations, and interactive elements
 */

(function() {
    'use strict';

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        initRippleEffects();
        initLoadingStates();
        initSmoothScrolling();
        initAnimationsOnScroll();
        initCountUpAnimations();
        initTooltipEnhancements();
        initFormEnhancements();
    }

    /**
     * Add ripple effect to buttons
     */
    function initRippleEffects() {
        // Add ripple to all buttons and clickable elements
        const rippleElements = document.querySelectorAll('.btn, .card.hover-lift, a.card');
        
        rippleElements.forEach(element => {
            if (!element.classList.contains('btn-ripple')) {
                element.classList.add('btn-ripple');
            }
        });
    }

    /**
     * Preserve the clicked submit button's name/value before it is disabled.
     * HTML form entry lists are built after the submit event; disabled controls
     * are excluded, so disabling the submitter drops approve/reject (etc.).
     * Issue #709: attendance correction Approve never reached the server.
     */
    function preserveSubmitterValue(form, submitter) {
        if (!form || !submitter || !submitter.name) return;
        const existing = form.querySelector('input[data-tt-submitter-preserve="1"]');
        if (existing) existing.remove();
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = submitter.name;
        hidden.value = submitter.value != null ? submitter.value : '1';
        hidden.setAttribute('data-tt-submitter-preserve', '1');
        form.appendChild(hidden);
    }

    /**
     * Handle loading states for buttons and forms
     */
    function initLoadingStates() {
        // Add loading state to form submissions
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                // Prefer the actual clicked button (e.submitter) over the first
                // submit button in the form — multi-button forms (Approve/Reject)
                // must keep the clicked name/value in the POST body.
                const submitBtn = e.submitter || form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
                    // Don't add loading state if form validation fails
                    if (form.checkValidity()) {
                        preserveSubmitterValue(form, submitBtn);
                        addLoadingState(submitBtn);
                    }
                }
            });
        });

        // Add loading state to AJAX buttons
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('[data-loading]');
            if (btn && !btn.classList.contains('btn-loading')) {
                addLoadingState(btn);
            }
        });
    }

    /**
     * Add loading state to an element.
     * Defer disabling so the browser can still include the submitter in the
     * form entry list if preserveSubmitterValue was not used.
     */
    function addLoadingState(element) {
        const originalText = element.innerHTML;
        element.setAttribute('data-original-text', originalText);
        element.classList.add('btn-loading');
        setTimeout(function() {
            element.disabled = true;
        }, 0);
    }

    /**
     * Remove loading state from an element
     */
    function removeLoadingState(element) {
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.innerHTML = originalText;
            element.removeAttribute('data-original-text');
        }
        element.classList.remove('btn-loading');
        element.disabled = false;
    }

    /**
     * Smooth scrolling for anchor links
     */
    function initSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#' || href === '') return;
                
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Animate elements when they scroll into view
     */
    function initAnimationsOnScroll() {
        const animatedElements = document.querySelectorAll('.fade-in-up, .fade-in-left, .fade-in-right');
        
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translate(0, 0)';
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });

            animatedElements.forEach(el => {
                el.style.opacity = '0';
                observer.observe(el);
            });
        }
    }

    /**
     * Number count-up animations
     */
    function initCountUpAnimations() {
        const numberElements = document.querySelectorAll('[data-count-up]');
        
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        animateCountUp(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.5
            });

            numberElements.forEach(el => observer.observe(el));
        }
    }

    /**
     * Animate number count up
     */
    function animateCountUp(element) {
        const target = parseFloat(element.getAttribute('data-count-up'));
        const duration = parseInt(element.getAttribute('data-duration') || '1000');
        const decimals = (element.getAttribute('data-decimals') || '0');
        
        let current = 0;
        const increment = target / (duration / 16);
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target.toFixed(decimals);
                clearInterval(timer);
            } else {
                element.textContent = current.toFixed(decimals);
            }
        }, 16);
    }

    /**
     * Enhanced tooltips
     */
    function initTooltipEnhancements() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Form enhancements
     */
    function initFormEnhancements() {
        // Auto-grow textareas
        const textareas = document.querySelectorAll('textarea[data-auto-grow]');
        textareas.forEach(textarea => {
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        });

        // Character counter
        const charCountInputs = document.querySelectorAll('[data-char-count]');
        charCountInputs.forEach(input => {
            const maxLength = input.getAttribute('maxlength') || input.getAttribute('data-char-count');
            if (maxLength) {
                const counter = document.createElement('small');
                counter.className = 'form-text text-muted char-counter';
                input.parentNode.appendChild(counter);
                
                const updateCounter = () => {
                    const remaining = maxLength - input.value.length;
                    counter.textContent = `${remaining} characters remaining`;
                    if (remaining < 10) {
                        counter.classList.add('text-warning');
                    } else {
                        counter.classList.remove('text-warning');
                    }
                };
                
                input.addEventListener('input', updateCounter);
                updateCounter();
            }
        });

        // Real-time validation
        const validatedInputs = document.querySelectorAll('[data-validate]');
        validatedInputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid') && this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                }
            });
        });
    }

    /**
     * Show loading skeleton
     */
    function showSkeleton(container) {
        const skeleton = container.querySelector('.skeleton-wrapper');
        if (skeleton) {
            skeleton.style.display = 'block';
        }
    }

    /**
     * Hide loading skeleton
     */
    function hideSkeleton(container) {
        const skeleton = container.querySelector('.skeleton-wrapper');
        if (skeleton) {
            skeleton.style.display = 'none';
        }
    }

    /**
     * Create loading overlay
     */
    function createLoadingOverlay(text = 'Loading...') {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-overlay-content">
                <div class="loading-spinner loading-spinner-lg loading-overlay-spinner"></div>
                <div class="mt-3">${text}</div>
            </div>
        `;
        return overlay;
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info', duration = 3000) {
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 fade-in-right`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, {
                autohide: true,
                delay: duration
            });
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', function() {
                toast.remove();
            });
        } else {
            setTimeout(() => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    }

    /**
     * Create toast container if it doesn't exist
     */
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1080';
        document.body.appendChild(container);
        return container;
    }

    /**
     * Stagger animation for lists
     */
    function staggerAnimation(container, itemSelector = '> *') {
        const items = container.querySelectorAll(itemSelector);
        items.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.animation = `fade-in-up 0.5s ease forwards`;
            item.style.animationDelay = `${index * 0.05}s`;
        });
    }

    /**
     * Success animation
     */
    function showSuccessAnimation(container) {
        const checkmark = document.createElement('div');
        checkmark.className = 'success-checkmark bounce-in';
        checkmark.innerHTML = `
            <div class="check-icon">
                <span class="icon-line line-tip"></span>
                <span class="icon-line line-long"></span>
                <div class="icon-circle"></div>
                <div class="icon-fix"></div>
            </div>
        `;
        
        container.appendChild(checkmark);
        
        setTimeout(() => {
            checkmark.classList.add('fade-out');
            setTimeout(() => checkmark.remove(), 300);
        }, 2000);
    }

    // Export functions for global use
    window.TimeTrackerUI = {
        addLoadingState,
        removeLoadingState,
        showSkeleton,
        hideSkeleton,
        createLoadingOverlay,
        showToast,
        staggerAnimation,
        showSuccessAnimation,
        animateCountUp
    };

})();

