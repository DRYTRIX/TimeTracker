# Kiosk Mode - Inventory & Barcode Scanning Quick Reference

## Overview

Kiosk Mode is a specialized interface for warehouse operations with barcode scanning and integrated time tracking. Perfect for:
- Warehouse kiosk stations
- Receiving/shipping areas
- Stock count stations
- Production floor terminals
- Retail/shop floor operations

## Key Features

### Core Functionality
✅ **Barcode Scanning** - USB scanners, camera-based, or Bluetooth  
✅ **Quick Stock Adjustments** - Scan → Adjust → Done  
✅ **Stock Lookup** - Instant stock level display across warehouses  
✅ **Stock Transfers** - Move items between warehouses  
✅ **Time Tracking** - Start/stop timers while managing inventory  
✅ **Physical Counts** - Count and adjust stock levels  

### UI/UX Features
✅ **Touch-Optimized** - Large buttons (44x44px minimum)  
✅ **Fullscreen Mode** - Hide browser chrome  
✅ **High Contrast** - Readable in warehouse lighting  
✅ **Visual Feedback** - Clear success/error messages  
✅ **Quick Actions** - One-tap common operations  

## Barcode Scanning Options

### 1. USB Keyboard Wedge Scanners (Recommended)
- **How**: Scanner acts as keyboard, Enter triggers lookup
- **Pros**: Simple, fast, reliable, no drivers needed
- **Best for**: Fixed kiosk stations

### 2. Camera-Based Scanning
- **Libraries**: QuaggaJS, ZXing, BarcodeDetector API
- **Pros**: No hardware needed, works on mobile
- **Cons**: Slower, requires camera permission
- **Best for**: Mobile devices, tablets

### 3. Bluetooth Scanners
- **How**: Wireless scanner pairs with device
- **Pros**: Wireless, mobile-friendly
- **Cons**: Requires pairing, battery dependent
- **Best for**: Mobile/portable operations

## Workflow Examples

### Receiving Stock
1. Scan barcode → Item details appear
2. Enter received quantity
3. Select warehouse/location
4. Confirm → Stock updated
5. (Optional) Start timer for receiving work

### Stock Adjustment
1. Scan barcode → Current stock shown
2. Enter adjustment (+/- quantity)
3. Select reason (damaged, found, etc.)
4. Confirm → Movement recorded

### Stock Transfer
1. Scan barcode
2. Select source warehouse
3. Select destination warehouse
4. Enter quantity
5. Confirm → Transfer completed

### Time Tracking
1. Start timer for project/task
2. Perform inventory operations
3. Timer runs in background
4. Stop timer when done

## Implementation Components

### Backend
- **New Blueprint**: `app/routes/kiosk.py`
- **API Endpoints**:
  - `POST /api/kiosk/barcode-lookup` - Find item by barcode
  - `POST /api/kiosk/adjust-stock` - Quick stock adjustment
  - `POST /api/kiosk/transfer-stock` - Transfer between warehouses
  - `POST /api/kiosk/start-timer` - Start time tracking
  - `POST /api/kiosk/stop-timer` - Stop time tracking

### Frontend
- **Templates**:
  - `app/templates/kiosk/login.html` - User selection
  - `app/templates/kiosk/dashboard.html` - Main interface
- **JavaScript**:
  - `app/static/kiosk-barcode.js` - Barcode scanning logic
  - `app/static/kiosk-timer.js` - Timer integration
  - `app/static/kiosk-mode.js` - General kiosk functionality
- **CSS**:
  - `app/static/kiosk-mode.css` - Touch-optimized styles

## UI Layout

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
│  │  Reason:    [Select reason ▼]     │   │
│  │  [Apply Adjustment]                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [Add Stock] [Remove] [Transfer] [Timer]   │
└─────────────────────────────────────────────┘
```

## Integration Points

### Existing Systems
- ✅ **Inventory Models**: `StockItem`, `Warehouse`, `WarehouseStock`, `StockMovement`
- ✅ **Time Tracking**: `TimeEntry`, timer routes
- ✅ **Projects**: Link movements to projects
- ✅ **Permissions**: Use existing permission system

### Database
- **StockItem.barcode**: Already exists (indexed)
- **StockMovement**: Records all changes
- **WarehouseStock**: Tracks stock levels per warehouse

## Configuration

### Admin Settings
- Enable/disable kiosk mode
- Auto-logout timeout (default: 15 min)
- Allow camera scanning
- Require reason for adjustments
- Default warehouse
- Allowed movement types
- User restrictions

### User Preferences
- Default warehouse
- Recent items tracking
- Quick action customization

## Security

- ✅ Authentication follows `AUTH_METHOD` setting:
  - `none`: Username-only login (acceptable for trusted kiosk environments)
  - `local` or `both`: Password authentication required (more secure)
- ✅ Shorter session timeout
- ✅ Auto-logout on inactivity
- ✅ Permission checks for operations
- ✅ Complete audit trail (all movements logged)
- ✅ Cannot delete movements (only adjust)

## Implementation Phases

### Phase 1: MVP
- Kiosk login
- Barcode input (keyboard wedge)
- Barcode lookup
- Item display
- Simple stock adjustment
- Timer display

### Phase 2: Enhanced
- Camera scanning
- Stock transfers
- Multi-warehouse
- Recent items
- Auto-logout
- Fullscreen mode

### Phase 3: Advanced
- Physical count mode
- Bulk operations
- Project linking
- Advanced timer
- Customizable actions

### Phase 4: Polish
- Testing
- Optimization
- Documentation
- Accessibility

## Testing Checklist

- [ ] USB barcode scanners
- [ ] Camera-based scanning (mobile/webcam)
- [ ] Touch devices (tablets)
- [ ] Different screen sizes
- [ ] Network issues/offline
- [ ] Concurrent users
- [ ] Performance (fast scanning)
- [ ] Error handling

## Quick Start Implementation

### 1. Create Kiosk Blueprint
```python
# app/routes/kiosk.py
kiosk_bp = Blueprint('kiosk', __name__)

@kiosk_bp.route('/kiosk')
def kiosk_dashboard():
    # Main kiosk interface
    pass
```

### 2. Register Blueprint
```python
# app/__init__.py
from app.routes.kiosk import kiosk_bp
app.register_blueprint(kiosk_bp)
```

### 3. Create Templates
- `app/templates/kiosk/login.html`
- `app/templates/kiosk/dashboard.html`

### 4. Add Barcode Lookup API
```python
@kiosk_bp.route('/api/kiosk/barcode-lookup', methods=['POST'])
def barcode_lookup():
    # Search by barcode or SKU
    # Return item details and stock levels
    pass
```

### 5. Add JavaScript
- Barcode input handling
- Camera scanning (optional)
- Stock adjustment forms
- Timer integration

## Future Enhancements

- QR code support
- Voice commands
- Batch scanning
- Print labels
- Inventory reports
- Multi-language
- Offline mode
- Scale integration

## Documentation

See `docs/KIOSK_MODE_INVENTORY_ANALYSIS.md` for detailed analysis and implementation guide.

