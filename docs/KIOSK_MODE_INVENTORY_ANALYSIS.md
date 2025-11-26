# Kiosk Mode - Inventory & Barcode Scanning Analysis

## Overview

Kiosk Mode for TimeTracker is a specialized interface designed for warehouse and inventory operations with integrated barcode scanning capabilities. It combines inventory management with time tracking, making it perfect for warehouse workers who need to log time while managing stock.

## Use Cases

1. **Warehouse Kiosk Stations**: Dedicated terminals in warehouses for stock operations
2. **Receiving/Shipping Areas**: Quick check-in/check-out of inventory
3. **Stock Count Stations**: Physical inventory counting with barcode scanners
4. **Production Floor**: Track time while managing materials and inventory
5. **Retail/Shop Floor**: Point-of-sale style inventory management

## Core Features

### 1. **Barcode Scanning Integration**

#### Scanner Support
- **USB Barcode Scanners**: Keyboard wedge mode (appears as keyboard input)
- **Bluetooth Scanners**: Wireless scanning support
- **Camera-Based Scanning**: Use device camera with JavaScript barcode libraries
- **Mobile Device Support**: Use phone/tablet camera for scanning

#### Barcode Lookup
- **Search by Barcode**: Instant lookup of stock items by barcode
- **Auto-Fill Forms**: Automatically populate item details when barcode is scanned
- **Multi-Format Support**: EAN-13, UPC-A, Code 128, QR codes, etc.
- **Fallback to SKU**: If barcode not found, try searching by SKU

#### Implementation Approach
```javascript
// Barcode scanning via input field (keyboard wedge scanners)
// Camera-based scanning (mobile/webcam)
// API endpoint for barcode lookup
```

### 2. **Inventory Operations**

#### Quick Stock Adjustments
- **Scan & Adjust**: Scan barcode → Enter quantity → Adjust stock
- **Add Stock**: Quick add to warehouse
- **Remove Stock**: Quick removal/adjustment
- **Transfer Stock**: Move between warehouses
- **Physical Count**: Count items and adjust to match

#### Stock Lookup
- **Scan to View**: Scan barcode to see current stock levels
- **Multi-Warehouse View**: See stock across all warehouses
- **Location Display**: Show bin/shelf location if configured
- **Low Stock Alerts**: Visual indicators for items below reorder point

#### Stock Movements
- **Record Movements**: Track all inventory changes
- **Movement Types**: Adjustment, transfer, sale, purchase, return, waste
- **Reason Tracking**: Quick reason selection (damaged, expired, etc.)
- **Project Linking**: Link movements to projects if needed

### 3. **Time Tracking Integration**

#### Concurrent Time Tracking
- **Active Timer Display**: Show current active timer (if any)
- **Quick Timer Actions**: Start/stop timer without leaving inventory screen
- **Project Selection**: Link time to projects while managing inventory
- **Task Association**: Optional task selection for time entries

#### Time Logging Options
- **Manual Entry**: Quick time entry form
- **Timer Start/Stop**: Standard timer functionality
- **Bulk Time Entry**: Log time for multiple operations

### 4. **User Interface Design**

#### Touch-Optimized Layout
```
┌─────────────────────────────────────────────┐
│  [User: John]  [Timer: 02:34:15]  [Logout] │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  📷 Barcode Scanner                │   │
│  │  [Scan barcode or enter manually]  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Item: Widget A (SKU: WID-001)     │   │
│  │  Barcode: 1234567890123            │   │
│  │  Current Stock: 45 pcs             │   │
│  │  Location: A-12-B                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Operation: [Adjust ▼]              │   │
│  │  Quantity:  [  -5  ]  [+5  ]       │   │
│  │  Reason:    [Select reason ▼]       │   │
│  │  [Apply Adjustment]                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Quick Actions:                      │   │
│  │  [Add Stock] [Remove] [Transfer]      │   │
│  │  [View History] [Start Timer]        │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### Key UI Elements
- **Large Barcode Input**: Prominent scanning field
- **Item Display Card**: Large, readable item information
- **Touch-Friendly Buttons**: Minimum 44x44px targets
- **Visual Feedback**: Clear success/error messages
- **High Contrast**: Readable in warehouse lighting

### 5. **Workflow Scenarios**

#### Scenario 1: Receiving Stock
1. User logs in (quick selection)
2. Scan barcode of incoming item
3. System shows item details and current stock
4. Enter received quantity
5. Select warehouse/location
6. Confirm and record movement
7. Optionally start timer for receiving work

#### Scenario 2: Stock Adjustment
1. User scans item barcode
2. System shows current stock level
3. User enters adjustment quantity (positive or negative)
4. Select reason (damaged, found, miscounted, etc.)
5. Confirm adjustment
6. System updates stock and records movement

#### Scenario 3: Stock Transfer
1. User scans item barcode
2. Select source warehouse
3. Select destination warehouse
4. Enter transfer quantity
5. Confirm transfer
6. System creates two movements (out from source, in to destination)

#### Scenario 4: Physical Count
1. User scans item barcode
2. System shows current system quantity
3. User enters counted quantity
4. System calculates difference
5. User confirms adjustment
6. System records adjustment movement

#### Scenario 5: Time Tracking While Working
1. User starts timer for project/task
2. Timer runs in background
3. User performs inventory operations
4. Timer continues running
5. User can stop timer when done
6. All operations logged with timestamps

## Technical Implementation

### Backend Components

#### 1. New Blueprint: `app/routes/kiosk.py`

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, StockItem, Warehouse, WarehouseStock, StockMovement, Project, TimeEntry
from app import db

kiosk_bp = Blueprint('kiosk', __name__)

@kiosk_bp.route('/kiosk')
def kiosk_dashboard():
    """Main kiosk interface"""
    if not current_user.is_authenticated:
        return redirect(url_for('kiosk.kiosk_login'))
    
    # Get active timer
    active_timer = current_user.active_timer
    
    # Get default warehouse (from user preference or first active)
    default_warehouse = get_default_warehouse(current_user.id)
    
    # Get recent items (last scanned/used)
    recent_items = get_recent_items(current_user.id, limit=10)
    
    return render_template('kiosk/dashboard.html',
                         active_timer=active_timer,
                         default_warehouse=default_warehouse,
                         recent_items=recent_items)

@kiosk_bp.route('/kiosk/login', methods=['GET', 'POST'])
def kiosk_login():
    """Quick login for kiosk mode"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if username:
            user = User.query.filter_by(username=username, is_active=True).first()
            if user:
                login_user(user, remember=False)
                return redirect(url_for('kiosk.kiosk_dashboard'))
            else:
                flash('User not found', 'error')
    
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template('kiosk/login.html', users=users)

@kiosk_bp.route('/kiosk/logout')
def kiosk_logout():
    """Logout from kiosk mode"""
    logout_user()
    return redirect(url_for('kiosk.kiosk_login'))

@kiosk_bp.route('/api/kiosk/barcode-lookup', methods=['POST'])
@login_required
def barcode_lookup():
    """Look up stock item by barcode"""
    data = request.get_json()
    barcode = data.get('barcode', '').strip()
    
    if not barcode:
        return jsonify({'error': 'Barcode required'}), 400
    
    # Search by barcode first
    item = StockItem.query.filter_by(barcode=barcode, is_active=True).first()
    
    # If not found, try SKU
    if not item:
        item = StockItem.query.filter_by(sku=barcode.upper(), is_active=True).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    # Get stock levels across warehouses
    stock_levels = WarehouseStock.query.filter_by(
        stock_item_id=item.id
    ).all()
    
    return jsonify({
        'item': {
            'id': item.id,
            'sku': item.sku,
            'name': item.name,
            'barcode': item.barcode,
            'unit': item.unit,
            'description': item.description,
            'category': item.category,
            'image_url': item.image_url
        },
        'stock_levels': [{
            'warehouse_id': stock.warehouse_id,
            'warehouse_name': stock.warehouse.name,
            'warehouse_code': stock.warehouse.code,
            'quantity_on_hand': float(stock.quantity_on_hand),
            'quantity_available': float(stock.quantity_available),
            'location': stock.location
        } for stock in stock_levels]
    })

@kiosk_bp.route('/api/kiosk/adjust-stock', methods=['POST'])
@login_required
def adjust_stock():
    """Quick stock adjustment from kiosk"""
    data = request.get_json()
    
    stock_item_id = data.get('stock_item_id')
    warehouse_id = data.get('warehouse_id')
    quantity = Decimal(str(data.get('quantity', 0)))
    reason = data.get('reason', 'Kiosk adjustment')
    notes = data.get('notes', '')
    
    if not stock_item_id or not warehouse_id:
        return jsonify({'error': 'Item and warehouse required'}), 400
    
    # Record movement
    movement, updated_stock = StockMovement.record_movement(
        movement_type='adjustment',
        stock_item_id=stock_item_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        moved_by=current_user.id,
        reason=reason,
        notes=notes,
        update_stock=True
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'movement_id': movement.id,
        'new_quantity': float(updated_stock.quantity_on_hand)
    })

@kiosk_bp.route('/api/kiosk/transfer-stock', methods=['POST'])
@login_required
def transfer_stock():
    """Transfer stock between warehouses"""
    data = request.get_json()
    
    stock_item_id = data.get('stock_item_id')
    from_warehouse_id = data.get('from_warehouse_id')
    to_warehouse_id = data.get('to_warehouse_id')
    quantity = Decimal(str(data.get('quantity', 0)))
    notes = data.get('notes', '')
    
    # Create outbound movement
    out_movement, out_stock = StockMovement.record_movement(
        movement_type='transfer',
        stock_item_id=stock_item_id,
        warehouse_id=from_warehouse_id,
        quantity=-quantity,  # Negative for removal
        moved_by=current_user.id,
        reason='Transfer out',
        notes=notes,
        update_stock=True
    )
    
    # Create inbound movement
    in_movement, in_stock = StockMovement.record_movement(
        movement_type='transfer',
        stock_item_id=stock_item_id,
        warehouse_id=to_warehouse_id,
        quantity=quantity,  # Positive for addition
        moved_by=current_user.id,
        reason='Transfer in',
        notes=notes,
        update_stock=True
    )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'from_quantity': float(out_stock.quantity_on_hand),
        'to_quantity': float(in_stock.quantity_on_hand)
    })

@kiosk_bp.route('/api/kiosk/start-timer', methods=['POST'])
@login_required
def kiosk_start_timer():
    """Start timer from kiosk interface"""
    data = request.get_json()
    project_id = data.get('project_id')
    task_id = data.get('task_id')
    notes = data.get('notes', '')
    
    # Reuse existing timer logic
    from app.routes.timer import start_timer_logic
    return start_timer_logic(project_id, task_id, notes)

@kiosk_bp.route('/api/kiosk/stop-timer', methods=['POST'])
@login_required
def kiosk_stop_timer():
    """Stop timer from kiosk interface"""
    # Reuse existing timer logic
    from app.routes.timer import stop_timer_logic
    return stop_timer_logic()
```

#### 2. Database Schema Additions (Optional)

```python
# Add to User model (optional - for kiosk preferences)
class User(db.Model):
    # ... existing fields ...
    kiosk_default_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    kiosk_recent_items = db.Column(db.Text)  # JSON array of recent item IDs
```

#### 3. Settings Configuration

```python
# Add to Settings model
class Settings(db.Model):
    # ... existing fields ...
    kiosk_mode_enabled = db.Column(db.Boolean, default=False)
    kiosk_auto_logout_minutes = db.Column(db.Integer, default=15)
    kiosk_allow_camera_scanning = db.Column(db.Boolean, default=True)
    kiosk_require_reason_for_adjustments = db.Column(db.Boolean, default=False)
    kiosk_default_movement_type = db.Column(db.String(20), default='adjustment')
```

### Frontend Components

#### 1. Kiosk Dashboard Template: `app/templates/kiosk/dashboard.html`

Features:
- Large barcode input field (auto-focus)
- Item display card (shows after scan)
- Stock adjustment form
- Quick action buttons
- Active timer display
- Recent items list

#### 2. Barcode Scanning JavaScript: `app/static/kiosk-barcode.js`

```javascript
// Keyboard wedge scanner support (USB scanners)
document.getElementById('barcode-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        const barcode = this.value.trim();
        if (barcode) {
            lookupBarcode(barcode);
            this.value = ''; // Clear for next scan
        }
    }
});

// Camera-based scanning (using QuaggaJS or ZXing)
function initCameraScanner() {
    // Initialize camera barcode scanner
    // Use QuaggaJS or similar library
}

// Barcode lookup function
async function lookupBarcode(barcode) {
    try {
        const response = await fetch('/api/kiosk/barcode-lookup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({barcode: barcode})
        });
        
        if (response.ok) {
            const data = await response.json();
            displayItem(data.item, data.stock_levels);
        } else {
            showError('Item not found');
        }
    } catch (error) {
        showError('Error looking up barcode');
    }
}
```

#### 3. Kiosk-Specific CSS: `app/static/kiosk-mode.css`

Features:
- Large touch targets (minimum 44x44px)
- High contrast colors
- Fullscreen layout
- Responsive design
- Visual feedback animations
- Barcode scanner input styling

#### 4. Timer Integration: `app/static/kiosk-timer.js`

```javascript
// Display active timer
function updateTimerDisplay() {
    // Fetch active timer status
    // Display in kiosk header
    // Update every second
}

// Quick timer actions
function startTimer(projectId, taskId) {
    // Start timer via API
    // Update display
}

function stopTimer() {
    // Stop timer via API
    // Show confirmation
}
```

## Barcode Scanning Implementation

### Option 1: Keyboard Wedge Scanners (USB)

**How it works:**
- Scanner acts as keyboard input
- Scan barcode → appears as text in input field
- Press Enter → triggers lookup

**Advantages:**
- Simple implementation
- Works with any USB barcode scanner
- No special drivers needed
- Fast and reliable

**Implementation:**
```javascript
// Auto-focus on barcode input
// Listen for Enter key
// Clear input after processing
```

### Option 2: Camera-Based Scanning

**Libraries:**
- **QuaggaJS**: Popular JavaScript barcode scanner
- **ZXing**: Multi-format barcode library
- **BarcodeDetector API**: Native browser API (limited support)

**Advantages:**
- No hardware needed
- Works on mobile devices
- Can scan from screen/photos

**Disadvantages:**
- Requires camera permission
- Slower than hardware scanners
- Lighting dependent

**Implementation:**
```javascript
// Initialize camera
// Use QuaggaJS to detect barcodes
// Process detected barcode
```

### Option 3: Bluetooth Scanners

**How it works:**
- Scanner pairs with device
- Sends barcode data via Bluetooth
- Appears as keyboard input or serial data

**Advantages:**
- Wireless operation
- Good for mobile devices
- Fast scanning

**Disadvantages:**
- Requires pairing setup
- Battery dependent
- More complex implementation

## Security Considerations

### 1. **Authentication**
- Quick user selection (username-only, acceptable for kiosk)
- Shorter session timeout (default: 15 minutes)
- Auto-logout on inactivity
- No persistent login

### 2. **Permissions**
- Check inventory permissions for operations
- Restrict certain operations to authorized users
- Log all movements with user ID

### 3. **Data Validation**
- Validate all quantities (positive numbers, reasonable limits)
- Check warehouse access permissions
- Verify item exists and is active
- Prevent negative stock (if configured)

### 4. **Audit Trail**
- All movements logged with user, timestamp, reason
- Cannot delete movements (only adjust)
- Complete history available

## Configuration Options

### Admin Settings

1. **Enable Kiosk Mode**: Toggle kiosk mode on/off
2. **Auto-Logout Timeout**: Minutes of inactivity (default: 15)
3. **Allow Camera Scanning**: Enable/disable camera barcode scanning
4. **Require Reason**: Require reason for all adjustments
5. **Default Warehouse**: Set default warehouse for operations
6. **Allowed Movement Types**: Which operations are allowed
7. **Restrict to Users**: Limit kiosk access to specific users

### User Preferences

1. **Default Warehouse**: User's preferred warehouse
2. **Recent Items**: Track recently used items
3. **Quick Actions**: Customize quick action buttons

## Integration Points

### Existing Inventory System
- ✅ Reuse `StockItem` model (barcode field exists)
- ✅ Use `WarehouseStock` for stock levels
- ✅ Leverage `StockMovement` for all changes
- ✅ Use existing movement types and reasons

### Time Tracking System
- ✅ Reuse `TimeEntry` model
- ✅ Use existing timer start/stop logic
- ✅ Integrate with `Project` and `Task` models
- ✅ Leverage WebSocket for real-time updates

### Permissions System
- ✅ Use existing permission checks
- ✅ `view_inventory` - View stock levels
- ✅ `manage_stock_movements` - Create adjustments
- ✅ `transfer_stock` - Transfer between warehouses

## Implementation Phases

### Phase 1: Basic Kiosk Mode (MVP)
- [ ] Kiosk login interface
- [ ] Basic dashboard layout
- [ ] Barcode input field (keyboard wedge)
- [ ] Barcode lookup API
- [ ] Item display after scan
- [ ] Simple stock adjustment
- [ ] Timer display and basic controls

### Phase 2: Enhanced Features
- [ ] Camera-based barcode scanning
- [ ] Stock transfer functionality
- [ ] Multi-warehouse support
- [ ] Recent items list
- [ ] Quick action buttons
- [ ] Auto-logout on inactivity
- [ ] Fullscreen mode

### Phase 3: Advanced Features
- [ ] Physical count mode
- [ ] Bulk operations
- [ ] Project linking for movements
- [ ] Advanced timer integration
- [ ] Customizable quick actions
- [ ] User preferences
- [ ] Admin override

### Phase 4: Polish & Testing
- [ ] Comprehensive testing
- [ ] Touch device optimization
- [ ] Performance optimization
- [ ] Documentation
- [ ] Accessibility improvements
- [ ] Error handling improvements

## Testing Considerations

1. **Barcode Scanners**: Test with various USB scanners
2. **Camera Scanning**: Test on mobile devices and webcams
3. **Touch Devices**: Test on tablets and touch screens
4. **Different Screen Sizes**: Ensure responsive design
5. **Network Issues**: Handle offline/online scenarios
6. **Concurrent Users**: Multiple users on same kiosk
7. **Performance**: Fast response times for scanning
8. **Error Handling**: Invalid barcodes, network errors, etc.

## Future Enhancements

1. **QR Code Support**: For more complex data (batch numbers, etc.)
2. **Voice Commands**: "Add 5 units" after scanning
3. **Batch Scanning**: Scan multiple items in sequence
4. **Print Labels**: Print barcode labels from kiosk
5. **Inventory Reports**: Quick reports on kiosk
6. **Multi-Language**: Support for warehouse workers
7. **Offline Mode**: Work offline, sync when online
8. **Integration with Scales**: Auto-weight for certain items

## Conclusion

Kiosk Mode with inventory and barcode scanning would be a powerful addition to TimeTracker, especially for warehouse operations. The combination of inventory management and time tracking in a single, touch-optimized interface makes it ideal for shared warehouse terminals.

The implementation leverages existing inventory infrastructure while adding specialized kiosk workflows optimized for speed and ease of use.

