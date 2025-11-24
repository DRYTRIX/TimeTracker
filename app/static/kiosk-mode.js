/**
 * Kiosk Mode - General Functionality
 * Fullscreen, tabs, auto-logout, keyboard shortcuts, etc.
 */

// Tab switching
document.addEventListener('DOMContentLoaded', function() {
    // Handle tab switching
    const tabs = document.querySelectorAll('.kiosk-tab');
    const tabContents = document.querySelectorAll('.kiosk-tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // Show/hide barcode scanner section
            const barcodeSection = document.getElementById('barcode-scanner-section');
            if (barcodeSection) {
                if (targetTab === 'scan') {
                    barcodeSection.style.display = 'block';
                } else {
                    barcodeSection.style.display = 'none';
                }
            }

            // Hide operations section for scan tab, show for others
            const operationsSection = document.getElementById('operations-section');
            if (operationsSection) {
                if (targetTab === 'scan') {
                    operationsSection.style.display = 'none';
                } else {
                    operationsSection.style.display = 'block';
                }
            }
            
            // Clear any item display when switching to scan
            if (targetTab === 'scan') {
                const itemSection = document.getElementById('item-section');
                if (itemSection) {
                    itemSection.style.display = 'none';
                }
                // Clear barcode status
                const barcodeStatus = document.getElementById('barcode-status');
                if (barcodeStatus) {
                    barcodeStatus.innerHTML = '';
                }
            }

            // Remove active class from all tabs and contents
            tabs.forEach(t => {
                t.classList.remove('border-primary', 'text-primary');
                t.classList.add('border-transparent', 'text-gray-600', 'dark:text-gray-400');
            });
            tabContents.forEach(c => {
                c.style.display = 'none';
            });

            // Add active class to clicked tab and corresponding content
            this.classList.remove('border-transparent', 'text-gray-600', 'dark:text-gray-400');
            this.classList.add('border-primary', 'text-primary');
            const targetContent = document.getElementById('tab-' + targetTab);
            if (targetContent) {
                targetContent.style.display = 'block';
            }
            
            // Update navigation menu active state - use data-tab attribute
            const navItems = document.querySelectorAll('nav a.nav-link');
            navItems.forEach(item => {
                // Remove all state classes
                item.classList.remove('text-primary', 'border-primary', 'text-gray-700', 'dark:text-gray-300', 'border-transparent');
                // Add default inactive state
                item.classList.add('text-gray-700', 'dark:text-gray-300', 'border-transparent');
            });
            
            // Find and activate the corresponding nav item by data-tab attribute
            const navItem = Array.from(navItems).find(item => {
                const tabAttr = item.getAttribute('data-tab');
                return tabAttr === targetTab;
            });
            if (navItem) {
                // Remove inactive classes
                navItem.classList.remove('text-gray-700', 'dark:text-gray-300', 'border-transparent');
                // Add active classes
                navItem.classList.add('text-primary', 'border-primary');
            }
        });
    });
    
    // Activate first tab by default
    if (tabs.length > 0) {
        tabs[0].click();
    }

    // Initialize keyboard shortcuts
    initKeyboardShortcuts();

    // Auto-logout on inactivity (will fetch timeout from settings)
    initAutoLogout();

    // Prevent navigation away (optional)
    window.addEventListener('beforeunload', function(e) {
        // Only warn if there's an active timer
        const timerDisplay = document.getElementById('kiosk-timer-display');
        if (timerDisplay && timerDisplay.textContent.includes(':')) {
            e.preventDefault();
            e.returnValue = 'You have an active timer. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        // Enter fullscreen
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

/**
 * Initialize auto-logout on inactivity
 * Fetches timeout from settings API
 */
async function initAutoLogout() {
    let inactivityTimeout;
    let timeoutMinutes = 15; // Default fallback
    
    // Fetch timeout from settings
    try {
        const response = await fetch('/api/kiosk/settings', { credentials: 'same-origin' });
        if (response.ok) {
            const data = await response.json();
            timeoutMinutes = data.kiosk_auto_logout_minutes || 15;
        }
    } catch (e) {
        console.warn('Could not fetch auto-logout settings, using default:', e);
    }
    
    const timeoutMs = timeoutMinutes * 60 * 1000;
    let warningShown = false;

    function resetInactivityTimer() {
        clearTimeout(inactivityTimeout);
        warningShown = false;
        
        // Show warning at 80% of timeout
        const warningTimeout = setTimeout(() => {
            if (!warningShown) {
                warningShown = true;
                // Show non-blocking warning
                if (window.showToast) {
                    window.showToast(`You will be logged out in ${Math.ceil(timeoutMinutes * 0.2)} minutes due to inactivity.`, 'warning', 10000);
                }
            }
        }, timeoutMs * 0.8);
        
        inactivityTimeout = setTimeout(async () => {
            clearTimeout(warningTimeout);
            if (window.showConfirm) {
                const confirmed = await window.showConfirm('You have been inactive. Logout now?', {
                    title: 'Auto-logout',
                    confirmText: 'Logout',
                    cancelText: 'Stay',
                    variant: 'warning'
                });
                if (confirmed) {
                    window.location.href = '/kiosk/logout';
                } else {
                    resetInactivityTimer(); // Reset if user cancels
                }
            } else {
                // Fallback to native confirm
                if (confirm('You have been inactive. Logout now?')) {
                    window.location.href = '/kiosk/logout';
                } else {
                    resetInactivityTimer(); // Reset if user cancels
                }
            }
        }, timeoutMs);
    }

    // Reset timer on user activity
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click', 'keydown'];
    events.forEach(event => {
        document.addEventListener(event, resetInactivityTimer, true);
    });

    // Start timer
    resetInactivityTimer();
}

/**
 * Initialize keyboard shortcuts
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+K or Cmd+K: Focus barcode input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const barcodeInput = document.getElementById('barcode-input');
            if (barcodeInput) {
                barcodeInput.focus();
                barcodeInput.select();
            }
            return;
        }
        
        // Escape: Clear barcode input or close camera scanner
        if (e.key === 'Escape') {
            const barcodeInput = document.getElementById('barcode-input');
            const cameraContainer = document.getElementById('camera-scanner-container');
            
            if (cameraContainer && !cameraContainer.classList.contains('hidden')) {
                if (window.stopCameraScanner) {
                    window.stopCameraScanner();
                }
                e.preventDefault();
                return;
            }
            
            if (barcodeInput && document.activeElement === barcodeInput) {
                barcodeInput.value = '';
                barcodeInput.blur();
                e.preventDefault();
                return;
            }
        }
        
        // Number keys 1-3: Switch tabs (when not typing in input)
        if (e.key >= '1' && e.key <= '3' && !e.ctrlKey && !e.metaKey) {
            const activeElement = document.activeElement;
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA' && activeElement.tagName !== 'SELECT') {
                const tabIndex = parseInt(e.key) - 1;
                const tabs = document.querySelectorAll('.kiosk-tab');
                if (tabs[tabIndex]) {
                    tabs[tabIndex].click();
                    e.preventDefault();
                }
            }
        }
        
        // Ctrl+Enter or Cmd+Enter: Submit active form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeElement = document.activeElement;
            if (activeElement && activeElement.form) {
                const form = activeElement.form;
                if (form.id === 'adjust-form' || form.id === 'transfer-form' || form.id === 'timer-form') {
                    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    e.preventDefault();
                }
            }
        }
        
        // ?: Show keyboard shortcuts help
        if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const activeElement = document.activeElement;
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                const helpDiv = document.getElementById('keyboard-help');
                if (helpDiv) {
                    helpDiv.classList.toggle('hidden');
                    e.preventDefault();
                }
            }
        }
    });
}

/**
 * Make functions available globally
 */
window.toggleFullscreen = toggleFullscreen;
window.initKeyboardShortcuts = initKeyboardShortcuts;

