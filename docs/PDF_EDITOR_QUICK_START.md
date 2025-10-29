# PDF Invoice Editor - Quick Start Guide

## Getting Started in 5 Minutes

This guide will help you create your first custom invoice layout using the enhanced Konva.js-based PDF editor.

## Step 1: Access the Editor

1. Log in as an admin user
2. Navigate to **Admin Panel** → **PDF Layout Designer**
3. You'll see three main sections:
   - **Left**: Element library
   - **Center**: Canvas workspace
   - **Right**: Properties panel

## Step 2: Understanding the Interface

### Element Library (Left Sidebar)

Elements are organized into groups:
- **Basic Elements**: Text, headings, shapes
- **Company Info**: Logo, name, address, contact details
- **Invoice Data**: Numbers, dates, client info, totals
- **Advanced**: QR codes, watermarks, page numbers

### Canvas (Center)

- The white canvas represents your invoice page (A4 size)
- Elements can be clicked, dragged, and resized
- Use toolbar buttons for zoom and alignment

### Properties Panel (Right)

- Shows properties of selected element
- Edit text, colors, fonts, positions
- Control layer order (z-index)

## Step 3: Add Your First Element

1. Click **"Heading"** from Basic Elements
2. The element appears on the canvas
3. Click it to select (you'll see resize handles)
4. In the properties panel (right):
   - Change text to "INVOICE"
   - Set font size to 32
   - Choose a color

## Step 4: Build Your Layout

### Add Company Header

1. Click **"Company Logo"** (if you've uploaded one)
2. Position it in the top-left (drag or use X/Y properties)
3. Click **"Company Name"** and position below logo
4. Add **"Company Details"** for contact info

### Add Invoice Details

1. Click **"Invoice Number"** - place top-right
2. Click **"Invoice Date"** - place below number
3. Click **"Due Date"** - place below date

### Add Client Information

1. Click **"Client Info"** - place left side, below company info
2. Adjust position to your liking

### Add Items Table

1. Click **"Items Table"** 
2. Position in the middle of the page
3. Resize if needed using handles

### Add Totals

1. Click **"Subtotal"** - place below items table
2. Click **"Tax"** - place below subtotal
3. Click **"Total Amount"** - place below tax

## Step 5: Customize with Shapes

### Add a Header Background

1. Click **"Rectangle"** from Basic Elements
2. Position at the very top
3. In properties:
   - Set Fill Color to a light color (e.g., #f3f4f6)
   - Set Stroke Width to 0
   - Adjust width to full page (595px)
   - Set height to 100px
4. Click the down arrow in Layer Order to send behind text

### Add Divider Lines

1. Click **"Line"** from Basic Elements
2. Position where you want a separator
3. Adjust stroke width and color in properties
4. Resize by dragging endpoints

## Step 6: Use Keyboard Shortcuts

Speed up your workflow:

- **Arrow Keys**: Move selected element (1px)
- **Shift+Arrows**: Move selected element (10px)
- **Ctrl+D**: Duplicate selected element
- **Delete**: Remove selected element

## Step 7: Align Elements

1. Select an element
2. Use toolbar alignment buttons:
   - Left/Center/Right for horizontal
   - Top/Middle/Bottom for vertical

## Step 8: Preview Your Design

1. Click **"Generate Preview"** button (top)
2. Preview appears in the right panel (below properties)
3. Review how it looks with actual data
4. Make adjustments as needed

## Step 9: Save Your Design

1. Click **"Save Design"** button (top)
2. Your layout is saved and will be used for all invoices
3. You can come back anytime to edit

## Step 10: Test with Real Invoice

1. Go to **Invoices** → Create a new invoice
2. Fill in details and add items
3. Click **"Preview"** or **"Generate PDF"**
4. See your custom layout in action!

## Common Tasks

### Changing Text Content

1. Select text element
2. In properties panel, find "Text Content"
3. Edit the text directly
4. Note: Keep Jinja2 variables (e.g., `{{ invoice.invoice_number }}`)

### Changing Colors

1. Select element
2. Find color picker in properties
3. Click to open color selector
4. Choose your color

### Resizing Elements

**Method 1**: Visual
- Click element to select
- Drag corner handles

**Method 2**: Precise
- Select element
- Use Width/Height fields in properties

### Moving Elements Precisely

1. Select element
2. In properties panel:
   - Set exact X position (horizontal)
   - Set exact Y position (vertical)

### Creating a Watermark

1. Click **"Watermark"** from Advanced
2. Position in center of page
3. In properties:
   - Set large font size (60-80)
   - Set opacity to 0.1-0.2
   - Choose light gray color
4. Send to back using Layer Order buttons

### Duplicating Sections

1. Select element (e.g., a line)
2. Press **Ctrl+D** to duplicate
3. Move to new position
4. Repeat as needed

## Tips & Tricks

### Tip 1: Use Alignment Tools
- Select multiple elements
- Use alignment buttons to line them up perfectly

### Tip 2: Work in Layers
- Background elements (shapes, watermarks) go to back
- Text and important info stay on top
- Use Layer Order buttons frequently

### Tip 3: Keep It Simple
- Don't overcrowd the layout
- Use whitespace effectively
- Test with real data before finalizing

### Tip 4: Font Consistency
- Stick to 2-3 fonts maximum
- Use font sizes consistently:
  - Heading: 24-32px
  - Subheading: 16-20px
  - Body: 12-14px
  - Fine print: 10-11px

### Tip 5: Color Harmony
- Use your brand colors
- Keep contrast high for readability
- Avoid too many colors (3-4 max)

## Troubleshooting

### Element Won't Move
- Make sure it's selected (should see handles)
- Try clicking it again
- Use X/Y properties for precise positioning

### Can't See Element
- Check if it's hidden behind another element
- Use Layer Order to bring to front
- Check if opacity is too low

### Text is Cut Off
- Increase width in properties
- Reduce font size
- Enable text wrapping

### Preview Shows Wrong Data
- Preview uses last invoice in database
- Create a test invoice with realistic data
- Generate preview again

## Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| Delete/Backspace | Remove selected element |
| Ctrl+C | Copy element |
| Ctrl+V | Paste element |
| Ctrl+D | Duplicate element |
| Arrow Keys | Move 1px |
| Shift+Arrows | Move 10px |
| Click Background | Deselect |

## Next Steps

Once comfortable with the basics:

1. Explore all element types
2. Create multiple layout variations
3. Use shapes for creative designs
4. Add QR codes for payment links
5. Experiment with opacity and layers

## Getting Help

- See [Full Feature Documentation](./PDF_EDITOR_ENHANCED_FEATURES.md)
- Check [PDF Layout Customization](./PDF_LAYOUT_CUSTOMIZATION.md)
- Review [Invoice System Guide](./ENHANCED_INVOICE_SYSTEM_README.md)

## Example Layout Ideas

### Minimal Layout
- Simple text elements only
- Clean lines
- Lots of whitespace

### Professional Layout
- Company logo in header
- Colored header background
- Clear sections with dividers

### Creative Layout
- Circular logo frame
- Angled divider lines
- Watermark in background

### Modern Layout
- Bold typography
- Minimal colors
- QR code for payments

Happy designing! 🎨

