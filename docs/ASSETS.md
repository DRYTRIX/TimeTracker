# Asset Management Guide

This document provides an inventory of all branding assets and their usage in the TimeTracker application.

## Asset Inventory

### Logo Files

#### Primary Logos
- **`app/static/images/timetracker-logo.svg`** - Main logo (default)
  - Usage: Primary branding, headers, navigation
  - Format: SVG (vector)
  
- **`app/static/images/timetracker-logo-light.svg`** - Light background variant
  - Usage: Light mode interfaces
  - Format: SVG (vector)

- **`app/static/images/timetracker-logo-dark.svg`** - Dark background variant
  - Usage: Dark mode interfaces
  - Format: SVG (vector)

- **`app/static/images/timetracker-logo-icon.svg`** - Icon-only variant
  - Usage: Favicons, app icons, small spaces
  - Format: SVG (vector)

- **`app/static/images/timetracker-logo-horizontal.svg`** - Horizontal layout
  - Usage: Wide headers, marketing materials
  - Format: SVG (vector)

- **`desktop/assets/logo.svg`** - Desktop app logo
  - Usage: Desktop application branding
  - Format: SVG (vector)

### Favicon Files

#### Web Application Favicons
- **`app/static/images/favicon.ico`** - Traditional favicon
  - Status: ⚠️ Needs generation
  - Sizes: 16x16, 32x32, 48x48
  - Usage: Browser tabs, bookmarks

- **`app/static/images/apple-touch-icon.png`** - Apple Touch Icon
  - Status: ⚠️ Needs generation
  - Size: 180x180px
  - Usage: iOS home screen

- **`app/static/images/android-chrome-192x192.png`** - Android Chrome Icon (small)
  - Status: ⚠️ Needs generation
  - Size: 192x192px
  - Usage: Android home screen, PWA

- **`app/static/images/android-chrome-512x512.png`** - Android Chrome Icon (large)
  - Status: ⚠️ Needs generation
  - Size: 512x512px
  - Usage: Android home screen, PWA

### Desktop Application Icons

#### Windows
- **`desktop/assets/icon.ico`** - Windows application icon
  - Status: ⚠️ Needs generation
  - Sizes: 16x16, 32x32, 48x48, 256x256 (multi-resolution)
  - Usage: Windows taskbar, file explorer, installer

#### macOS
- **`desktop/assets/icon.icns`** - macOS application icon
  - Status: ⚠️ Needs generation
  - Size: 512x512px (multi-resolution)
  - Usage: macOS dock, Finder, installer

#### Linux
- **`desktop/assets/icon.png`** - Linux application icon
  - Status: ⚠️ Needs generation
  - Size: 512x512px
  - Usage: Linux launchers, AppImage

### Social Media Assets

#### Open Graph Image
- **`app/static/images/og-image.png`** - Open Graph social sharing image
  - Status: ⚠️ Needs creation
  - Size: 1200x630px
  - Format: PNG
  - Usage: Social media link previews (Twitter, Facebook, LinkedIn)

### Screenshots

- **`assets/screenshots/`** - Application screenshots
  - Status: ✅ Existing
  - Usage: Documentation, marketing, app stores

## Generation Instructions

### Automated Generation

Use the provided script to generate most icons:

```bash
cd TimeTracker
npm install sharp  # If not already installed
node scripts/generate-icons.js
```

This will generate:
- PNG versions of icons
- Basic favicon files
- Desktop icon placeholders

### Manual Generation Required

Some formats require manual conversion:

#### Windows .ico File
1. Use the generated `desktop/assets/icon-256x256.png`
2. Convert using:
   - Online: [CloudConvert](https://cloudconvert.com/png-ico) or [ConvertICO](https://convertio.co/png-ico/)
   - ImageMagick: `convert icon-256x256.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico`
3. Save as `desktop/assets/icon.ico`

#### macOS .icns File
1. Use the generated `desktop/assets/icon-512x512.png`
2. On macOS, create icon set:
   ```bash
   mkdir icon.iconset
   # Copy PNG at various sizes into iconset
   iconutil -c icns icon.iconset -o icon.icns
   ```
3. Or use online converter: [iConvert Icons](https://iconverticons.com/)
4. Save as `desktop/assets/icon.icns`

#### Open Graph Image
1. Create 1200x630px image
2. Include:
   - TimeTracker logo
   - Tagline: "Professional Time Tracking"
   - Brand gradient background
3. Save as `app/static/images/og-image.png`

### Recommended Tools

**Online Converters:**
- [CloudConvert](https://cloudconvert.com/) - Multi-format conversion
- [ConvertICO](https://convertio.co/) - ICO conversion
- [iConvert Icons](https://iconverticons.com/) - ICNS conversion
- [RealFaviconGenerator](https://realfavicongenerator.net/) - Complete favicon set

**Design Tools:**
- Figma - For creating OG images
- Adobe Illustrator - For logo variations
- Canva - For social media graphics

**Command Line:**
- ImageMagick - For batch processing
- Sharp (Node.js) - For programmatic generation

## File Size Guidelines

- **SVG logos:** Keep under 50KB
- **PNG icons:** Optimize, keep under 100KB each
- **ICO files:** Multi-resolution, typically 50-200KB
- **ICNS files:** Multi-resolution, typically 200-500KB
- **OG images:** Optimize, keep under 500KB

## Usage Locations

### Web Application
- **Base template:** `app/templates/base.html`
- **Login page:** `app/templates/auth/login.html`
- **About page:** `app/templates/main/about.html`
- **Manifest:** `app/static/manifest.webmanifest`

### Desktop Application
- **Main window:** `desktop/src/main/window.js`
- **Splash screen:** `desktop/src/renderer/splash.html`
- **Login screen:** `desktop/src/renderer/index.html`
- **Package config:** `desktop/package.json`

## Maintenance

### Version Control
- All assets are tracked in git
- Document changes in commit messages
- Archive old versions when updating

### Updates
1. Update source SVG if logo changes
2. Regenerate all derived assets
3. Update references in code
4. Test on all platforms
5. Update documentation

### Quality Checks
- Verify all sizes render correctly
- Test on target platforms
- Check file sizes
- Validate formats
- Ensure accessibility (contrast, readability)

## Notes

- SVG is preferred for logos (scalable, small file size)
- PNG is used for raster icons and screenshots
- ICO/ICNS are platform-specific formats
- Always maintain aspect ratios
- Use high-quality source images
- Optimize for web delivery

---

**Last Updated:** 2024
**Maintainer:** Development Team
