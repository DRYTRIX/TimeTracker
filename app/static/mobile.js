/* Mobile Enhancements for TimeTracker
   Works with the app's sidebar navigation and Tailwind CSS UI */

const MobileUtils = {
    TOUCH_TARGET_MIN: 44,
    MOBILE_BREAKPOINT: 1024,
    SMALL_MOBILE_BREAKPOINT: 480,

    isMobile() {
        return window.innerWidth < this.MOBILE_BREAKPOINT;
    },
    isSmallMobile() {
        return window.innerWidth <= this.SMALL_MOBILE_BREAKPOINT;
    },
    isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    },
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent);
    }
};

class MobileSidebar {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.toggleBtn = document.getElementById('mobileSidebarBtn');
        this.overlay = document.getElementById('sidebarOverlay');
        if (!this.sidebar) return;
        this.init();
    }

    init() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggle());
        }
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.close());
        }
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
        });

        this.sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (MobileUtils.isMobile()) this.close();
            });
        });
    }

    toggle() {
        this.sidebar.classList.toggle('-translate-x-full');
        if (this.overlay) this.overlay.classList.toggle('hidden');
    }

    close() {
        this.sidebar.classList.add('-translate-x-full');
        if (this.overlay) this.overlay.classList.remove('hidden');
        this.overlay && this.overlay.classList.add('hidden');
    }
}

class MobileForms {
    constructor() {
        this.init();
    }

    init() {
        if (MobileUtils.isIOS()) {
            document.querySelectorAll('input, select, textarea').forEach(el => {
                const computed = window.getComputedStyle(el);
                if (parseFloat(computed.fontSize) < 16) {
                    el.style.fontSize = '16px';
                }
            });
        }

        document.querySelectorAll('input, select, textarea').forEach(el => {
            el.addEventListener('focus', () => {
                if (MobileUtils.isMobile()) {
                    setTimeout(() => {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 300);
                }
            });
        });

        this.initFileInputs();
        this.initCharCounters();
        this.initSubmitButtons();
    }

    initFileInputs() {
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', () => {
                const preview = document.getElementById(input.id + '-preview');
                const filenameEl = document.getElementById(input.id + '-filename');
                if (preview && filenameEl && input.files.length > 0) {
                    filenameEl.textContent = input.files[0].name;
                    preview.classList.remove('hidden');
                }
            });

            const dropZone = input.closest('label');
            if (dropZone) {
                ['dragenter', 'dragover'].forEach(evt => {
                    dropZone.addEventListener(evt, (e) => {
                        e.preventDefault();
                        dropZone.classList.add('drag-over');
                    });
                });
                ['dragleave', 'drop'].forEach(evt => {
                    dropZone.addEventListener(evt, (e) => {
                        e.preventDefault();
                        dropZone.classList.remove('drag-over');
                    });
                });
                dropZone.addEventListener('drop', (e) => {
                    if (e.dataTransfer.files.length) {
                        input.files = e.dataTransfer.files;
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            }
        });
    }

    initCharCounters() {
        document.querySelectorAll('.char-counter[data-for]').forEach(counter => {
            const textarea = document.getElementById(counter.dataset.for);
            if (textarea) {
                textarea.addEventListener('input', () => {
                    counter.textContent = textarea.value.length;
                });
            }
        });
    }

    initSubmitButtons() {
        document.querySelectorAll('button[data-loading-text]').forEach(btn => {
            const form = btn.closest('form');
            if (form) {
                form.addEventListener('submit', () => {
                    if (form.checkValidity && !form.checkValidity()) return;
                    const original = btn.innerHTML;
                    btn.dataset.originalHtml = original;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>' + btn.dataset.loadingText;
                    btn.disabled = true;
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = original;
                    }, 15000);
                });
            }
        });
    }
}

class MobileViewport {
    constructor() {
        this.init();
    }

    init() {
        this.handleViewportChange();
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => this.handleViewportChange(), 200);
        });
        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.handleViewportChange(), 150);
        });
    }

    handleViewportChange() {
        document.body.classList.toggle('mobile-view', MobileUtils.isMobile());
        document.body.classList.toggle('small-mobile-view', MobileUtils.isSmallMobile());
    }
}

class MobilePerformance {
    constructor() {
        this.init();
    }

    init() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        observer.unobserve(img);
                    }
                });
            });
            document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
        }

        document.querySelectorAll('img:not([loading])').forEach(img => {
            img.loading = 'lazy';
        });
    }
}

class MobileOffline {
    constructor() {
        this.offlineToastId = null;
        this.init();
    }

    init() {
        window.addEventListener('offline', () => {
            if (window.toastManager) {
                this.offlineToastId = window.toastManager.warning(
                    'Some features may not work properly.',
                    "You're offline",
                    0
                );
            }
        });
        window.addEventListener('online', () => {
            if (window.toastManager && this.offlineToastId) {
                window.toastManager.dismiss(this.offlineToastId);
                this.offlineToastId = null;
                window.toastManager.success('Connection restored', "You're online", 3000);
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (window._mobileInitDone) return;
    window._mobileInitDone = true;

    new MobileSidebar();
    new MobileForms();
    new MobileViewport();
    new MobilePerformance();
    new MobileOffline();
});

window.MobileUtils = MobileUtils;
