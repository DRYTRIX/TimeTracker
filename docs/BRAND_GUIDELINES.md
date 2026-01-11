# TimeTracker Brand Guidelines

## Overview

This document outlines the brand identity, visual guidelines, and usage rules for TimeTracker. Following these guidelines ensures consistent branding across all platforms and touchpoints.

## Logo

### Primary Logo

The primary TimeTracker logo features a rounded square with a gradient background (blue to cyan), containing a stylized clock with a checkmark.

**File:** `app/static/images/timetracker-logo.svg`

**Usage:**
- Primary branding element
- Headers and navigation
- Application icons
- Marketing materials

### Logo Variations

#### Light Background Variant
**File:** `app/static/images/timetracker-logo-light.svg`
- Use on light backgrounds
- Standard web application

#### Dark Background Variant
**File:** `app/static/images/timetracker-logo-dark.svg`
- Use on dark backgrounds
- Dark mode interfaces

#### Icon-Only Variant
**File:** `app/static/images/timetracker-logo-icon.svg`
- Square format
- Favicons and app icons
- Small spaces where full logo doesn't fit

#### Horizontal Variant
**File:** `app/static/images/timetracker-logo-horizontal.svg`
- Logo with text side-by-side
- Wide headers
- Marketing materials

### Logo Usage Rules

**DO:**
- Maintain minimum clear space (equal to 20% of logo height)
- Use appropriate variant for background color
- Scale proportionally
- Use SVG format when possible for scalability

**DON'T:**
- Stretch or distort the logo
- Rotate the logo
- Change colors (except approved variants)
- Add effects (shadows, outlines) without approval
- Place on busy backgrounds without sufficient contrast
- Use at sizes smaller than 24px height

### Minimum Sizes

- **Web:** 32px height minimum
- **Print:** 0.5 inches height minimum
- **Mobile:** 24px height minimum

## Color Palette

### Primary Colors

**Primary Blue**
- Hex: `#4A90E2`
- RGB: `74, 144, 226`
- Usage: Primary actions, links, highlights
- WCAG AA compliant on white backgrounds

**Secondary Cyan**
- Hex: `#50E3C2`
- RGB: `80, 227, 194`
- Usage: Secondary actions, accents, gradients
- WCAG AA compliant on dark backgrounds

**Theme Blue**
- Hex: `#3b82f6`
- RGB: `59, 130, 246`
- Usage: PWA theme color, browser chrome

### Gradient

The brand uses a gradient from Primary Blue to Secondary Cyan:
- Start: `#4A90E2` (Primary Blue)
- End: `#50E3C2` (Secondary Cyan)
- Direction: Diagonal (135deg) or horizontal as needed

### Status Colors

**Success (Green)**
- Hex: `#4CAF50`
- Usage: Success messages, positive indicators

**Warning (Orange)**
- Hex: `#FF9800`
- Usage: Warnings, caution messages

**Error (Red)**
- Hex: `#E53935`
- Usage: Error messages, destructive actions

### Background Colors

**Light Mode:**
- Background: `#F7F9FB`
- Card: `#FFFFFF`
- Secondary: `#f5f5f5`

**Dark Mode:**
- Background: `#1A202C`
- Card: `#2D3748`
- Secondary: `#4A5568`

### Text Colors

**Light Mode:**
- Primary Text: `#2D3748`
- Secondary Text: `#A0AEC0`
- Muted Text: `#718096`

**Dark Mode:**
- Primary Text: `#E2E8F0`
- Secondary Text: `#718096`
- Muted Text: `#A0AEC0`

## Typography

### Font Families

**Primary (System Fonts):**
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
```

**Usage:**
- Body text
- UI elements
- Default text throughout application

### Font Weights

- **Regular (400):** Body text, descriptions
- **Medium (500):** Labels, buttons
- **Semibold (600):** Headings, emphasis
- **Bold (700):** Primary headings, strong emphasis

### Font Sizes

**Headings:**
- H1: 2.5rem (40px) - Page titles
- H2: 2rem (32px) - Section titles
- H3: 1.5rem (24px) - Subsection titles
- H4: 1.25rem (20px) - Card titles

**Body:**
- Large: 1.125rem (18px) - Important text
- Base: 1rem (16px) - Standard text
- Small: 0.875rem (14px) - Secondary text
- XS: 0.75rem (12px) - Labels, captions

## Spacing

### Spacing Scale

Based on 4px base unit:
- 4px (0.25rem) - Tight spacing
- 8px (0.5rem) - Compact spacing
- 16px (1rem) - Standard spacing
- 24px (1.5rem) - Comfortable spacing
- 32px (2rem) - Generous spacing
- 48px (3rem) - Section spacing
- 64px (4rem) - Large section spacing

### Border Radius

- **Small:** 4px (0.25rem) - Buttons, inputs
- **Medium:** 8px (0.5rem) - Cards, containers
- **Large:** 12px (0.75rem) - Modals, large cards
- **XLarge:** 16px (1rem) - Hero sections

## Iconography

### Icon Library

**Font Awesome 6.4.0**
- Primary icon library
- Consistent style and sizing
- Extensive icon set

### Icon Usage

- **Size:** 16px for inline, 24px for standalone
- **Color:** Inherit text color or use brand colors
- **Spacing:** 8px margin from adjacent text

## Imagery

### Style Guidelines

- Clean, professional photography
- Minimal, uncluttered compositions
- Consistent lighting and color grading
- Focus on productivity and professionalism

### Screenshots

- Use actual application screenshots
- Maintain consistent browser chrome
- Include realistic data
- Highlight key features clearly

## Application Icons

### Desktop Application

**Windows:**
- Format: `.ico`
- Sizes: 16x16, 32x32, 48x48, 256x256
- File: `desktop/assets/icon.ico`

**macOS:**
- Format: `.icns`
- Size: 512x512 (multi-resolution)
- File: `desktop/assets/icon.icns`

**Linux:**
- Format: `.png`
- Size: 512x512
- File: `desktop/assets/icon.png`

### Web Application

**Favicon:**
- Format: `.ico` and `.svg`
- Sizes: 16x16, 32x32, 48x48
- File: `app/static/images/favicon.ico`

**Apple Touch Icon:**
- Format: `.png`
- Size: 180x180
- File: `app/static/images/apple-touch-icon.png`

**Android Chrome Icons:**
- Format: `.png`
- Sizes: 192x192, 512x512
- Files: `app/static/images/android-chrome-*.png`

## Social Media

### Open Graph Image

- **Size:** 1200x630px
- **Format:** PNG
- **File:** `app/static/images/og-image.png`
- **Content:** Logo, tagline, key visual elements

### Twitter Card

- Use large image card format
- Same image as Open Graph
- Include app name and tagline

## Voice and Tone

### Brand Voice

- **Professional:** Maintain business-appropriate language
- **Clear:** Use simple, direct communication
- **Helpful:** Focus on user benefits
- **Confident:** Express expertise without arrogance

### Writing Style

- Use active voice
- Keep sentences concise
- Avoid jargon when possible
- Use second person ("you") for user-facing text

## Platform-Specific Guidelines

### Web Application

- Responsive design for all screen sizes
- Dark mode support
- PWA capabilities
- Accessible (WCAG 2.1 AA)

### Desktop Application

- Native platform look and feel
- Consistent branding with web app
- Platform-appropriate icons
- Smooth animations and transitions

## Do's and Don'ts

### DO

✅ Use brand colors consistently
✅ Maintain logo clear space
✅ Use appropriate logo variant for context
✅ Follow spacing guidelines
✅ Test on multiple devices and platforms
✅ Ensure accessibility compliance
✅ Keep designs clean and professional

### DON'T

❌ Modify logo colors or design
❌ Use outdated logo versions
❌ Place logo on low-contrast backgrounds
❌ Mix different design systems
❌ Use non-brand colors for primary actions
❌ Compromise accessibility for aesthetics
❌ Use unlicensed fonts or assets

## Asset Management

### File Organization

- Logos: `app/static/images/timetracker-logo-*.svg`
- Icons: `app/static/images/*.png`, `desktop/assets/*`
- Social: `app/static/images/og-image.png`
- Screenshots: `assets/screenshots/`

### File Formats

- **Vector:** SVG for logos and icons
- **Raster:** PNG for screenshots, social images
- **Icons:** ICO, ICNS, PNG for platform-specific needs

### Version Control

- All brand assets in repository
- Document changes in commit messages
- Maintain asset inventory
- Archive old versions when updating

## Updates and Maintenance

### Review Schedule

- Quarterly brand audit
- Annual comprehensive review
- Update as needed for new platforms

### Change Process

1. Document proposed changes
2. Review with team
3. Update guidelines
4. Update all assets
5. Communicate changes

## Contact

For questions about brand usage or to request new assets, please refer to the project documentation or create an issue on GitHub.

---

**Last Updated:** 2024
**Version:** 1.0
