/**
 * Kiosk Mode - Barcode Scanning Functionality
 * Supports USB keyboard wedge scanners and camera-based scanning
 */

let currentItem = null;
let currentStockLevels = [];
let cameraStream = null;
let cameraScannerActive = false;
let barcodeDetector = null;
let lastAdjustment = null; // Store last adjustment for undo

/**
 * Clear all item-related content from the UI
 * This should be called before any new lookup or when clearing the display
 */
function clearItemContent() {
    // Clear state
    currentItem = null;
    currentStockLevels = [];
    lastAdjustment = null;
    
    // Hide sections
    const itemSection = document.getElementById('item-section');
    const operationsSection = document.getElementById('operations-section');
    const stockLevelsDiv = document.getElementById('stock-levels');
    const loadingSkeleton = document.getElementById('item-loading-skeleton');
    
    if (itemSection) {
        itemSection.style.display = 'none';
        // Clear all item detail fields
        const itemName = document.getElementById('item-name');
        const itemSku = document.getElementById('item-sku');
        const itemBarcode = document.getElementById('item-barcode');
        const itemUnit = document.getElementById('item-unit');
        const itemUnitDisplay = document.getElementById('item-unit-display');
        const itemCategory = document.getElementById('item-category');
        
        if (itemName) itemName.textContent = '';
        if (itemSku) itemSku.textContent = '';
        if (itemBarcode) itemBarcode.textContent = '—';
        if (itemUnit) itemUnit.textContent = '—';
        if (itemUnitDisplay) itemUnitDisplay.textContent = '—';
        if (itemCategory) itemCategory.textContent = '—';
    }
    
    if (operationsSection) {
        operationsSection.style.display = 'none';
    }
    
    if (stockLevelsDiv) {
        stockLevelsDiv.innerHTML = '';
    }
    
    if (loadingSkeleton) {
        loadingSkeleton.classList.add('hidden');
    }
    
    // Hide undo button
    const undoBtn = document.getElementById('adjust-undo-btn');
    if (undoBtn) {
        undoBtn.classList.add('hidden');
    }
    
    // Reset form values
    const adjustQuantity = document.getElementById('adjust-quantity');
    if (adjustQuantity) {
        adjustQuantity.value = '0';
    }
    
    const transferQuantity = document.getElementById('transfer-quantity');
    if (transferQuantity) {
        transferQuantity.value = '1';
    }
}

// Check if BarcodeDetector API is available
if ('BarcodeDetector' in window) {
    try {
        barcodeDetector = new BarcodeDetector({
            formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39', 'code_93', 'codabar', 'qr_code']
        });
    } catch (e) {
        console.warn('BarcodeDetector not supported:', e);
    }
}

// Make utility functions globally available immediately (before DOMContentLoaded)
// These need to be available when onclick handlers execute
(function() {
    window.adjustQuantity = function(delta) {
        const quantityInput = document.getElementById('adjust-quantity');
        if (quantityInput) {
            const current = parseFloat(quantityInput.value) || 0;
            const newValue = Math.max(0, current + delta);
            quantityInput.value = newValue.toFixed(2);
        }
    };

    window.lookupItem = async function(itemId, barcode) {
        if (barcode) {
            const barcodeInput = document.getElementById('barcode-input');
            if (barcodeInput) {
                barcodeInput.value = barcode;
                // lookupBarcode will be defined below, but we'll call it after DOM is ready
                setTimeout(() => {
                    if (window.lookupBarcode) {
                        window.lookupBarcode(barcode);
                    }
                }, 100);
            }
        } else {
            console.warn('Item lookup by ID not implemented, need barcode');
        }
    };
    
    // Placeholder functions that will be replaced when the full script loads
    window.toggleCameraScanner = function() {
        console.warn('toggleCameraScanner not yet loaded');
    };
    
    window.stopCameraScanner = function() {
        console.warn('stopCameraScanner not yet loaded');
    };
    
    window.stopTimer = function() {
        console.warn('stopTimer not yet loaded');
    };
})();

// Initialize barcode input
document.addEventListener('DOMContentLoaded', function() {
    const barcodeInput = document.getElementById('barcode-input');
    if (!barcodeInput) return;

    // Auto-focus on barcode input
    barcodeInput.focus();

    // Handle keyboard wedge scanner (USB scanners send Enter after barcode)
    barcodeInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const barcode = this.value.trim();
            if (barcode) {
                if (window.lookupBarcode) {
                    window.lookupBarcode(barcode);
                }
                this.value = ''; // Clear for next scan
            }
        }
    });

    // Handle manual entry with delay (for camera scanning)
    let inputTimeout;
    let lastLookupBarcode = '';
    barcodeInput.addEventListener('input', function() {
        clearTimeout(inputTimeout);
        const barcode = this.value.trim();
        
        // Clear status and content if input is cleared
        const statusDiv = document.getElementById('barcode-status');
        if (!barcode && statusDiv) {
            statusDiv.innerHTML = '';
            statusDiv.className = '';
        }
        
        // Clear item content when input is cleared
        if (!barcode) {
            clearItemContent();
        }
        
        // If barcode is long enough and looks like a barcode, try lookup after delay
        // Also check if it's different from last lookup to avoid duplicate lookups
        if (barcode.length >= 8 && barcode !== lastLookupBarcode) {
            inputTimeout = setTimeout(function() {
                const currentBarcode = barcodeInput.value.trim();
                if (currentBarcode === barcode && window.lookupBarcode && currentBarcode.length >= 8) {
                    lastLookupBarcode = currentBarcode;
                    window.lookupBarcode(currentBarcode);
                }
            }, 800); // Increased delay to 800ms for better debouncing
        }
    });
});

/**
 * Look up item by barcode or SKU
 */
async function lookupBarcode(barcode, retryCount = 0) {
    if (!barcode) return;

    const barcodeInput = document.getElementById('barcode-input');
    const statusDiv = document.getElementById('barcode-status');
    
    // Clear previous item content immediately - MUST be synchronous
    clearItemContent();
    
    // Show loading skeleton
    const loadingSkeleton = document.getElementById('item-loading-skeleton');
    if (loadingSkeleton) {
        loadingSkeleton.classList.remove('hidden');
    }
    
    // Show loading
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="flex items-center justify-center gap-2 text-primary"><i class="fas fa-spinner fa-spin"></i><span>Looking up...</span></div>';
        statusDiv.className = 'bg-primary/10 dark:bg-primary/20 text-primary rounded-xl p-3 border border-primary/20';
    }
    
    // Disable input
    if (barcodeInput) {
        barcodeInput.disabled = true;
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch('/api/kiosk/barcode-lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            credentials: 'same-origin',
            signal: controller.signal,
            body: JSON.stringify({ barcode: barcode })
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            const error = await response.json();
            // Retry on network errors (status 0 or 500-599) up to 2 times
            if (retryCount < 2 && (response.status === 0 || (response.status >= 500 && response.status < 600))) {
                await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1))); // Exponential backoff
                return lookupBarcode(barcode, retryCount + 1);
            }
            throw new Error(error.error || 'Item not found');
        }

        const data = await response.json();
        
        // Hide loading skeleton
        const loadingSkeleton = document.getElementById('item-loading-skeleton');
        if (loadingSkeleton) {
            loadingSkeleton.classList.add('hidden');
        }
        
        displayItem(data.item, data.stock_levels);
        
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="flex items-center justify-center gap-2 text-green-600 dark:text-green-400"><i class="fas fa-check-circle"></i><span>Item found</span></div>';
            statusDiv.className = 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded-xl p-3 border border-green-200 dark:border-green-800';
            setTimeout(() => {
                statusDiv.innerHTML = '';
                statusDiv.className = '';
            }, 2000);
        }
    } catch (error) {
        console.error('Barcode lookup error:', error);
        const errorMessage = error.name === 'AbortError' 
            ? 'Request timed out. Please try again.' 
            : (error.message || 'Item not found');
        
        // Clear all content on error
        clearItemContent();
            
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="flex items-center justify-center gap-2 text-red-600 dark:text-red-400"><i class="fas fa-exclamation-circle"></i><span>' + errorMessage + '</span></div>';
            statusDiv.className = 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl p-3 border border-red-200 dark:border-red-800';
        }
        showError(errorMessage);
    } finally {
        // Re-enable input and focus
        if (barcodeInput) {
            barcodeInput.disabled = false;
            barcodeInput.focus();
        }
    }
}

/**
 * Display item information
 */
function displayItem(item, stockLevels) {
    // Update state first
    currentItem = item;
    currentStockLevels = stockLevels;

    // Hide loading skeleton
    const loadingSkeleton = document.getElementById('item-loading-skeleton');
    if (loadingSkeleton) {
        loadingSkeleton.classList.add('hidden');
    }

    // Check if we're on the scan tab before showing content
    const barcodeSection = document.getElementById('barcode-scanner-section');
    const isScanTab = barcodeSection && barcodeSection.style.display !== 'none';
    
    // Only show content if we're on the scan tab
    if (!isScanTab) {
        return; // Don't display if not on scan tab
    }

    // Show item section
    const itemSection = document.getElementById('item-section');
    const operationsSection = document.getElementById('operations-section');
    if (itemSection) itemSection.style.display = 'block';
    if (operationsSection) operationsSection.style.display = 'block';

    // Update item details
    document.getElementById('item-name').textContent = item.name;
    document.getElementById('item-sku').textContent = item.sku;
    const barcodeEl = document.getElementById('item-barcode');
    if (barcodeEl) {
        barcodeEl.textContent = item.barcode || '—';
    }
    const unitEl = document.getElementById('item-unit');
    if (unitEl) {
        unitEl.textContent = item.unit || 'pcs';
    }
    const unitDisplayEl = document.getElementById('item-unit-display');
    if (unitDisplayEl) {
        unitDisplayEl.textContent = item.unit || 'pcs';
    }
    document.getElementById('item-category').textContent = item.category || '—';

    // Update stock levels
    const stockLevelsDiv = document.getElementById('stock-levels');
    if (stockLevelsDiv) {
        if (stockLevels && stockLevels.length > 0) {
            stockLevelsDiv.innerHTML = '<div class="flex items-center gap-3 mb-6"><div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center"><i class="fas fa-warehouse text-primary"></i></div><h4 class="text-lg font-bold text-gray-900 dark:text-white">Stock Levels</h4></div>' + 
                '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">' +
                stockLevels.map(stock => {
                    const isLowStock = stock.quantity_available <= 0;
                    const isMediumStock = stock.quantity_available > 0 && stock.quantity_available < 10;
                    const statusBg = isLowStock ? 'bg-red-50 dark:bg-red-900/20' : (isMediumStock ? 'bg-yellow-50 dark:bg-yellow-900/20' : 'bg-green-50 dark:bg-green-900/20');
                    const statusBorder = isLowStock ? 'border-red-200 dark:border-red-800' : (isMediumStock ? 'border-yellow-200 dark:border-yellow-800' : 'border-green-200 dark:border-green-800');
                    const statusIconColor = isLowStock ? 'text-red-600 dark:text-red-400' : (isMediumStock ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400');
                    const statusTextColor = isLowStock ? 'text-red-600 dark:text-red-400' : (isMediumStock ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400');
                    const statusDotColor = isLowStock ? 'bg-red-500' : (isMediumStock ? 'bg-yellow-500' : 'bg-green-500');
                    
                    // Calculate progress percentage (assuming max stock of 1000 for visualization, or use a reasonable max)
                    const maxStock = Math.max(stock.quantity_on_hand, 100, 1000);
                    const progressPercent = Math.min((stock.quantity_on_hand / maxStock) * 100, 100);
                    const availablePercent = Math.min((stock.quantity_available / maxStock) * 100, 100);
                    
                    return `
                    <div class="bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900/50 border-2 ${statusBorder} rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg ${statusBg} flex items-center justify-center">
                                    <i class="fas fa-warehouse ${statusIconColor}" aria-hidden="true"></i>
                                </div>
                                <div>
                                    <div class="font-bold text-lg text-gray-900 dark:text-white">${stock.warehouse_name}</div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400 font-mono">${stock.warehouse_code}</div>
                                </div>
                            </div>
                            <div class="w-3 h-3 rounded-full ${statusDotColor} shadow-sm" aria-hidden="true"></div>
                        </div>
                        <div class="space-y-3">
                            <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg px-3 py-2">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
                                        <i class="fas fa-box text-xs" aria-hidden="true"></i>
                                        On Hand
                                    </span>
                                    <span class="font-bold text-lg text-gray-900 dark:text-white">${stock.quantity_on_hand} ${item.unit}</span>
                                </div>
                                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                                    <div class="h-full bg-gray-400 dark:bg-gray-600 rounded-full transition-all duration-300" style="width: ${progressPercent}%" role="progressbar" aria-valuenow="${stock.quantity_on_hand}" aria-valuemin="0" aria-valuemax="${maxStock}" aria-label="On hand: ${stock.quantity_on_hand} ${item.unit}"></div>
                                </div>
                            </div>
                            <div class="${statusBg} rounded-lg px-3 py-2">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="text-xs font-semibold ${statusTextColor} uppercase tracking-wide flex items-center gap-1.5">
                                        <i class="fas fa-check-circle text-xs" aria-hidden="true"></i>
                                        Available
                                    </span>
                                    <span class="font-bold text-lg ${statusTextColor}">${stock.quantity_available} ${item.unit}</span>
                                </div>
                                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                                    <div class="h-full ${statusDotColor} rounded-full transition-all duration-300" style="width: ${availablePercent}%" role="progressbar" aria-valuenow="${stock.quantity_available}" aria-valuemin="0" aria-valuemax="${maxStock}" aria-label="Available: ${stock.quantity_available} ${item.unit}"></div>
                                </div>
                            </div>
                            ${stock.location ? `<div class="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700"><div class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5"><i class="fas fa-map-marker-alt" aria-hidden="true"></i><span>${stock.location}</span></div></div>` : ''}
                        </div>
                    </div>
                `;
                }).join('') + '</div>';
        } else {
            stockLevelsDiv.innerHTML = '<div class="text-center text-gray-500 dark:text-gray-400 py-12 bg-gray-50 dark:bg-gray-900/50 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700"><div class="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-4"><i class="fas fa-inbox text-2xl text-gray-400"></i></div><div class="font-medium">No stock levels found</div><div class="text-sm mt-1">This item is not stocked in any warehouse</div></div>';
        }
    }

    // Set default warehouse in adjust form if available
    if (stockLevels && stockLevels.length > 0) {
        const adjustWarehouse = document.getElementById('adjust-warehouse');
        if (adjustWarehouse) {
            adjustWarehouse.value = stockLevels[0].warehouse_id;
        }
    }

    // Scroll to item section
    if (itemSection) {
        itemSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * Adjust stock quantity (already defined globally above)
 */

/**
 * Handle stock adjustment form submission
 */
document.addEventListener('DOMContentLoaded', function() {
    const adjustForm = document.getElementById('adjust-form');
    if (adjustForm) {
        adjustForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!currentItem) {
                showError('Please scan an item first');
                return;
            }

            const warehouseId = document.getElementById('adjust-warehouse').value;
            const quantity = parseFloat(document.getElementById('adjust-quantity').value);
            const reason = document.getElementById('adjust-reason').value;

            if (!warehouseId || quantity === 0) {
                showError('Please select warehouse and enter quantity');
                return;
            }

            // Set loading state
            const submitBtn = document.getElementById('adjust-submit-btn');
            const submitIcon = document.getElementById('adjust-submit-icon');
            const submitText = document.getElementById('adjust-submit-text');
            const submitSpinner = document.getElementById('adjust-submit-spinner');
            
            if (submitBtn) {
                submitBtn.disabled = true;
                if (submitIcon) submitIcon.classList.add('hidden');
                if (submitText) submitText.textContent = 'Processing...';
                if (submitSpinner) submitSpinner.classList.remove('hidden');
            }
            
            // Store current state for undo
            const previousQuantity = currentStockLevels.find(s => s.warehouse_id === parseInt(warehouseId))?.quantity_on_hand || 0;
            
            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                const response = await fetch('/api/kiosk/adjust-stock', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken || ''
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        stock_item_id: currentItem.id,
                        warehouse_id: parseInt(warehouseId),
                        quantity: quantity,
                        reason: reason
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to adjust stock');
                }

                const data = await response.json();
                
                // Store adjustment for undo
                lastAdjustment = {
                    movement_id: data.movement_id,
                    stock_item_id: currentItem.id,
                    warehouse_id: parseInt(warehouseId),
                    previous_quantity: previousQuantity,
                    adjustment_quantity: quantity,
                    new_quantity: data.new_quantity
                };
                
                // Show undo button
                const undoBtn = document.getElementById('adjust-undo-btn');
                if (undoBtn) {
                    undoBtn.classList.remove('hidden');
                }
                
                // Update aria-live region
                const ariaLive = document.getElementById('aria-live-status');
                if (ariaLive) {
                    ariaLive.textContent = data.message || 'Stock adjusted successfully';
                }
                
                showSuccess(data.message || 'Stock adjusted successfully');
                
                // Reset form
                document.getElementById('adjust-quantity').value = '0';
                
                // Refresh stock levels
                if (currentItem.barcode) {
                    lookupBarcode(currentItem.barcode);
                } else {
                    lookupBarcode(currentItem.sku);
                }
            } catch (error) {
                console.error('Adjust stock error:', error);
                showErrorWithRetry(error.message || 'Failed to adjust stock', () => {
                    adjustForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                });
            } finally {
                // Reset loading state
                if (submitBtn) {
                    submitBtn.disabled = false;
                    if (submitIcon) submitIcon.classList.remove('hidden');
                    if (submitText) submitText.textContent = 'Apply Adjustment';
                    if (submitSpinner) submitSpinner.classList.add('hidden');
                }
            }
        });
    }

    // Handle transfer form
    const transferForm = document.getElementById('transfer-form');
    if (transferForm) {
        transferForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!currentItem) {
                showError('Please scan an item first');
                return;
            }

            const fromWarehouseId = document.getElementById('transfer-from').value;
            const toWarehouseId = document.getElementById('transfer-to').value;
            const quantity = parseFloat(document.getElementById('transfer-quantity').value);

            if (fromWarehouseId === toWarehouseId) {
                showError('Source and destination warehouses must be different');
                return;
            }

            if (!quantity || quantity <= 0) {
                showError('Quantity must be greater than zero');
                return;
            }

            // Set loading state
            const submitBtn = document.getElementById('transfer-submit-btn');
            const submitIcon = document.getElementById('transfer-submit-icon');
            const submitText = document.getElementById('transfer-submit-text');
            const submitSpinner = document.getElementById('transfer-submit-spinner');
            
            if (submitBtn) {
                submitBtn.disabled = true;
                if (submitIcon) submitIcon.classList.add('hidden');
                if (submitText) submitText.textContent = 'Processing...';
                if (submitSpinner) submitSpinner.classList.remove('hidden');
            }
            
            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                const response = await fetch('/api/kiosk/transfer-stock', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken || ''
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        stock_item_id: currentItem.id,
                        from_warehouse_id: parseInt(fromWarehouseId),
                        to_warehouse_id: parseInt(toWarehouseId),
                        quantity: quantity
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to transfer stock');
                }

                const data = await response.json();
                
                // Update aria-live region
                const ariaLive = document.getElementById('aria-live-status');
                if (ariaLive) {
                    ariaLive.textContent = data.message || 'Stock transferred successfully';
                }
                
                showSuccess(data.message || 'Stock transferred successfully');
                
                // Reset form
                document.getElementById('transfer-quantity').value = '1';
                
                // Refresh stock levels
                if (currentItem.barcode) {
                    lookupBarcode(currentItem.barcode);
                } else {
                    lookupBarcode(currentItem.sku);
                }
            } catch (error) {
                console.error('Transfer stock error:', error);
                showErrorWithRetry(error.message || 'Failed to transfer stock', () => {
                    transferForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                });
            } finally {
                // Reset loading state
                if (submitBtn) {
                    submitBtn.disabled = false;
                    if (submitIcon) submitIcon.classList.remove('hidden');
                    if (submitText) submitText.textContent = 'Transfer Stock';
                    if (submitSpinner) submitSpinner.classList.add('hidden');
                }
            }
        });
    }
    
    // Handle undo button
    const undoBtn = document.getElementById('adjust-undo-btn');
    if (undoBtn) {
        undoBtn.addEventListener('click', async function() {
            if (!lastAdjustment) return;
            
            if (!window.showConfirm || !(await window.showConfirm('Are you sure you want to undo the last adjustment?', {
                title: 'Undo Adjustment',
                confirmText: 'Undo',
                cancelText: 'Cancel',
                variant: 'warning'
            }))) {
                return;
            }
            
            // Reverse the adjustment
            const reverseQuantity = -lastAdjustment.adjustment_quantity;
            
            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                const response = await fetch('/api/kiosk/adjust-stock', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken || ''
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        stock_item_id: lastAdjustment.stock_item_id,
                        warehouse_id: lastAdjustment.warehouse_id,
                        quantity: reverseQuantity,
                        reason: 'Undo previous adjustment'
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Failed to undo adjustment');
                }
                
                const data = await response.json();
                showSuccess('Adjustment undone successfully');
                lastAdjustment = null;
                undoBtn.classList.add('hidden');
                
                // Refresh stock levels
                if (currentItem && currentItem.barcode) {
                    lookupBarcode(currentItem.barcode);
                } else if (currentItem && currentItem.sku) {
                    lookupBarcode(currentItem.sku);
                }
            } catch (error) {
                console.error('Undo error:', error);
                showError(error.message || 'Failed to undo adjustment');
            }
        });
    }
});

/**
 * Show error message with retry button
 */
function showErrorWithRetry(message, retryCallback) {
    if (window.showToast) {
        // Create a custom error notification with retry
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-4 shadow-lg z-50 max-w-md';
        errorDiv.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                    <i class="fas fa-exclamation-circle text-red-600 dark:text-red-400 text-xl"></i>
                </div>
                <div class="flex-1">
                    <p class="text-sm font-medium text-red-800 dark:text-red-200">${message}</p>
                    ${retryCallback ? `<button onclick="this.closest('div').remove(); (${retryCallback.toString()})()" class="mt-2 text-xs font-semibold text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 underline focus:outline-none focus:ring-2 focus:ring-red-500 rounded px-2 py-1">Retry</button>` : ''}
                </div>
                <button onclick="this.closest('div').remove()" class="flex-shrink-0 text-red-400 hover:text-red-600 dark:hover:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-500 rounded p-1" aria-label="Close">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 10000);
        
        // Update aria-live alert
        const ariaAlert = document.getElementById('aria-live-alert');
        if (ariaAlert) {
            ariaAlert.textContent = message;
        }
    } else {
        showError(message);
    }
}

/**
 * Show error message
 */
function showError(message) {
    // Use toast notifications if available, otherwise create simple notification
    if (window.showToast) {
        window.showToast(message, 'error');
        
        // Update aria-live alert
        const ariaAlert = document.getElementById('aria-live-alert');
        if (ariaAlert) {
            ariaAlert.textContent = message;
        }
    } else {
        // Create or update error notification
        let errorDiv = document.getElementById('kiosk-error-notification');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'kiosk-error-notification';
            errorDiv.className = 'fixed top-4 right-4 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg z-50';
            document.body.appendChild(errorDiv);
        }
        
        errorDiv.innerHTML = '<i class="fas fa-exclamation-circle mr-2"></i>' + message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    // Use toast notifications if available, otherwise create simple notification
    if (window.showToast) {
        window.showToast(message, 'success');
    } else {
        // Create or update success notification
        let successDiv = document.getElementById('kiosk-success-notification');
        if (!successDiv) {
            successDiv = document.createElement('div');
            successDiv.id = 'kiosk-success-notification';
            successDiv.className = 'fixed top-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50';
            document.body.appendChild(successDiv);
        }
        
        successDiv.innerHTML = '<i class="fas fa-check-circle mr-2"></i>' + message;
        successDiv.style.display = 'block';
        
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    }
}

/**
 * Toggle camera scanner
 */
async function toggleCameraScanner() {
    const container = document.getElementById('camera-scanner-container');
    const preview = document.getElementById('camera-preview');
    const btn = document.getElementById('camera-scan-btn');
    
    if (!container || !preview) return;
    
    if (cameraScannerActive) {
        stopCameraScanner();
    } else {
        // Check if camera scanning is allowed
        try {
            const response = await fetch('/api/kiosk/settings', { credentials: 'same-origin' });
            if (response.ok) {
                const data = await response.json();
                if (!data.kiosk_allow_camera_scanning) {
                    showError('Camera scanning is disabled in settings');
                    return;
                }
            }
        } catch (e) {
            console.warn('Could not check camera settings:', e);
        }
        
        try {
            // Request camera access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // Use back camera on mobile
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            cameraStream = stream;
            preview.srcObject = stream;
            container.classList.remove('hidden');
            cameraScannerActive = true;
            
            if (btn) {
                btn.classList.add('text-primary');
            }
            
            // Start scanning
            startCameraScanning(preview);
        } catch (error) {
            console.error('Camera access error:', error);
            showError('Could not access camera. Please check permissions.');
        }
    }
}

/**
 * Stop camera scanner
 */
function stopCameraScanner() {
    const container = document.getElementById('camera-scanner-container');
    const preview = document.getElementById('camera-preview');
    const btn = document.getElementById('camera-scan-btn');
    
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    if (preview) {
        preview.srcObject = null;
    }
    
    if (container) {
        container.classList.add('hidden');
    }
    
    if (btn) {
        btn.classList.remove('text-primary');
    }
    
    cameraScannerActive = false;
}

/**
 * Start camera-based barcode scanning
 */
function startCameraScanning(videoElement) {
    if (!videoElement) return;
    
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    function scanFrame() {
        if (!cameraScannerActive || !videoElement.videoWidth) {
            return;
        }
        
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        context.drawImage(videoElement, 0, 0);
        
        if (barcodeDetector) {
            // Use native BarcodeDetector API
            barcodeDetector.detect(canvas)
                .then(barcodes => {
                    if (barcodes.length > 0) {
                        const barcode = barcodes[0].rawValue;
                        if (barcode) {
                            // Stop camera and lookup barcode
                            stopCameraScanner();
                            lookupBarcode(barcode);
                        }
                    }
                })
                .catch(err => {
                    console.error('Barcode detection error:', err);
                });
        } else {
            // Fallback: Use ZXing library if available
            if (window.ZXing) {
                try {
                    const codeReader = new ZXing.BrowserMultiFormatReader();
                    codeReader.decodeFromVideoDevice(null, videoElement, (result, err) => {
                        if (result) {
                            stopCameraScanner();
                            lookupBarcode(result.text);
                        }
                    });
                } catch (e) {
                    console.warn('ZXing not available:', e);
                }
            }
        }
        
        // Continue scanning
        if (cameraScannerActive) {
            requestAnimationFrame(scanFrame);
        }
    }
    
    // Start scanning loop
    scanFrame();
}

// Make remaining functions globally available
window.showError = showError;
window.showSuccess = showSuccess;
window.toggleCameraScanner = toggleCameraScanner;
window.stopCameraScanner = stopCameraScanner;
// Make functions globally available
window.lookupBarcode = lookupBarcode;
window.clearItemContent = clearItemContent;

