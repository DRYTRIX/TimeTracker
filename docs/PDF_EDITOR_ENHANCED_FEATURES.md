# Enhanced PDF Invoice Editor with Konva.js

## Overview

The PDF Invoice Editor has been significantly enhanced to use Konva.js, providing a powerful drag-and-drop interface for designing custom invoice layouts. Users can now add, position, and customize any element with an intuitive visual editor.

## New Features

### 1. Expanded Element Library

The editor now includes a comprehensive set of draggable elements organized into categories:

#### Basic Elements
- **Text**: Generic text field for custom content
- **Heading**: Large, bold text for titles
- **Line**: Horizontal divider line
- **Rectangle**: Customizable rectangular shape
- **Circle**: Customizable circular shape
- **Decorative Image**: Placeholder that you can assign an uploaded image to; appears in the PDF when an image is set. Supports position, size, and opacity. Save the layout after uploading to persist the image with the design.

#### Company Information Elements
- **Company Logo**: Displays uploaded company logo
- **Company Name**: Formatted company name
- **Company Details**: Combined address, email, and phone
- **Company Address**: Dedicated address field
- **Company Email**: Email address with label
- **Company Phone**: Phone number with label
- **Company Website**: Website URL
- **Company Tax ID**: Tax identification number

#### Invoice Data Elements
- **Invoice Number**: Auto-formatted invoice number
- **Invoice Date**: Issue date
- **Due Date**: Payment due date
- **Invoice Status**: Current status (draft, sent, paid, etc.)
- **Client Info**: Combined client information block
- **Client Name**: Client name only
- **Client Address**: Client address only
- **Items Table**: Dynamic table of invoice items
- **Subtotal**: Pre-tax amount
- **Tax**: Tax amount with rate
- **Total Amount**: Final total
- **Notes**: Invoice notes field
- **Terms**: Payment terms

#### Advanced Elements
- **QR Code**: QR code placeholder (for invoice number/link)
- **Barcode**: Barcode placeholder
- **Page Number**: Page numbering
- **Current Date**: Auto-updating current date
- **Watermark**: Large, semi-transparent text overlay

### 2. Properties Panel

The right sidebar now features a comprehensive properties panel that displays editable properties for the selected element:

#### Text Element Properties
- **Position X/Y**: Precise positioning
- **Text Content**: Edit text inline
- **Font Size**: Size in pixels
- **Font Family**: Choose from 6 fonts (Arial, Times New Roman, Courier New, Georgia, Verdana, Helvetica)
- **Font Style**: Normal, Bold, or Italic
- **Text Color**: Color picker
- **Width**: Text box width
- **Opacity**: Transparency slider (0-100%)

#### Shape Element Properties (Rectangle/Circle)
- **Position X/Y**: Precise positioning
- **Fill Color**: Interior color
- **Stroke Color**: Border color
- **Stroke Width**: Border thickness
- **Dimensions**: Width/Height for rectangles, Radius for circles

#### Line Element Properties
- **Stroke Color**: Line color
- **Stroke Width**: Line thickness

#### All Elements
- **Layer Order Controls**: Move up/down/top/bottom in z-index

### 3. Canvas Toolbar

Enhanced toolbar with powerful editing tools:

- **Zoom In/Out**: Scale the canvas view
- **Delete**: Remove selected element
- **Align Left/Center/Right**: Horizontal alignment
- **Align Top/Middle/Bottom**: Vertical alignment

### 4. Keyboard Shortcuts

For power users, the editor supports keyboard shortcuts:

- **Delete/Backspace**: Remove selected element
- **Ctrl+C**: Copy selected element
- **Ctrl+V**: Paste copied element (offset by 20px)
- **Ctrl+D**: Duplicate selected element
- **Arrow Keys**: Move element by 1px
- **Shift+Arrow Keys**: Move element by 10px
- **Click Background**: Deselect all

### 5. Visual Feedback

- **Transform Handles**: Resize and rotate elements with intuitive handles
- **Real-time Updates**: See changes immediately on the canvas
- **Selection Indicator**: Visual highlight of selected elements
- **Snap to Pixel**: Automatic pixel-perfect positioning

### 6. Advanced Canvas Features

#### Layer Management
- Move elements forward/backward in z-index
- Bring to front/send to back
- Visual layer indicators in properties panel

#### Alignment Tools
- Align to left/center/right edge
- Align to top/middle/bottom
- Center elements on canvas

#### Copy/Paste/Duplicate
- Copy elements to clipboard
- Paste with automatic offset
- Duplicate with keyboard shortcut

## Technical Implementation

### Architecture

The enhanced editor uses:
- **Konva.js 9.x**: Canvas-based rendering engine
- **HTML5 Canvas**: High-performance graphics
- **Dynamic Properties Panel**: React-like property binding
- **JSON State Management**: Serialize/deserialize designs

### Code Generation

The editor generates clean HTML and CSS:

```html
<!-- Text elements become divs -->
<div class="element text-element" style="position:absolute;left:50px;top:30px;...">
    Invoice Text
</div>

<!-- Shapes become styled divs -->
<div class="rectangle-element" style="position:absolute;..."></div>

<!-- Images use Jinja2 templates -->
<img src="{{ get_logo_base64(settings.get_logo_path()) }}" style="..." alt="Logo">
```

### State Persistence

Designs are saved as:
1. **design_json**: Complete Konva.js stage state (for re-opening the editor). Custom attributes such as decorative-image `name` and `imageUrl` are injected into the serialized JSON so they survive save/load.
2. **template_json**: ReportLab template (elements list) used for PDF generation. Decorative image elements are only included when they have a non-empty image source, so the PDF is never broken by missing images.
3. **HTML/CSS**: Generated template markup and styles (legacy preview).

**Decorative images:** The editor syncs each decorative image’s `imageUrl` onto its group before generating the template and uses position-based matching when injecting URLs into the saved design JSON. On load, `name` and `imageUrl` are restored from the saved JSON onto the live nodes so decorative images appear correctly even if Konva does not persist custom attributes. Placeholders (no image uploaded) remain visible in the editor but are omitted from the PDF.

## Usage Guide

### Creating a New Layout

1. Navigate to **Admin → PDF Templates → Invoice PDF** (or **Quote PDF** for quote layouts)
2. Click elements from the left sidebar to add them to the canvas
3. Click an element to select it
4. Use the properties panel (right) to customize:
   - Position, size, colors
   - Text content and fonts
   - Layer order
5. Use toolbar buttons for alignment and zoom
6. Click **Generate Preview** to see the rendered result
7. Click **Save Design** to persist changes

### Editing Existing Layouts

1. Existing elements are loaded automatically from saved JSON
2. Click any element to edit its properties
3. Use keyboard shortcuts for faster editing
4. Preview changes before saving

### Best Practices

1. **Start with Structure**: Add heading, company info, and major sections first
2. **Use Alignment Tools**: Keep elements properly aligned
3. **Test with Real Data**: Use "Generate Preview" to see actual invoice data
4. **Layer Management**: Keep important elements on top
5. **Save Frequently**: Use "Save Design" to preserve work

## API Integration

### Backend Routes

The editor integrates with existing routes:

- `GET /admin/pdf-layout`: Load editor with current design
- `POST /admin/pdf-layout`: Save design (HTML, CSS, JSON)
- `POST /admin/pdf-layout/preview`: Generate live preview
- `POST /admin/pdf-layout/reset`: Reset to defaults

### Data Flow

```
User Action → Konva.js Canvas → generateCode() → HTML/CSS → Backend → Database
                                                        ↓
                                              Preview Generation
```

## Extensibility

### Adding New Element Types

To add a new element type:

1. Add to sidebar HTML:
```html
<div class="element-item" data-type="new-element">
    <i class="fas fa-icon"></i>
    <span>New Element</span>
</div>
```

2. Add to templates object:
```javascript
'new-element': { text: 'Default Text', fontSize: 14, ... }
```

3. Handle in `addElement()` if special rendering needed

4. Update `generateCode()` for HTML output

### Custom Properties

Add custom properties by:

1. Extending `updatePropertiesPanel()`
2. Adding input fields for new properties
3. Attaching listeners in `attachPropertyListeners()`

## Troubleshooting

### Decorative Image Missing After Save
If a decorative image disappears when you reopen the layout, ensure you clicked **Save Design** after uploading the image. The editor persists decorative images by syncing the image URL to the design and template before save; if you leave before the save completes or before uploading an image, the placeholder may not be stored correctly. If the PDF preview shows a black or wrong area, the same fix applies: save the layout after assigning the image.

### Element Not Appearing
- Check console for errors
- Verify element type in templates object
- Ensure layer.draw() is called

### Properties Not Updating
- Verify event listeners are attached
- Check selectedElement is not null
- Ensure layer.draw() after changes

### Preview Not Generating
- Check network tab for API errors
- Verify HTML/CSS generation
- Check backend template rendering

## Performance Considerations

- Canvas is rendered at 595x842px (A4 size at 72dpi)
- Large designs with many elements remain performant
- Transformer handles are optimized for smooth interaction
- Properties panel updates use debouncing

## Future Enhancements

Potential additions:
- Image upload for custom backgrounds
- Grid/snap to grid functionality
- Undo/redo history
- Templates/presets library
- Multi-page support
- Export to multiple formats

## Related Documentation

- [PDF Layout Customization Guide](./PDF_LAYOUT_CUSTOMIZATION.md)
- [Invoice System Overview](./ENHANCED_INVOICE_SYSTEM_README.md)
- [Admin Settings Guide](./SETTINGS.md)

