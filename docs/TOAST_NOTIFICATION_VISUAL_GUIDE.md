# Toast Notification Visual Guide

## 📍 Positioning

### Desktop View
```
┌─────────────────────────────────────────────────────┐
│  Navigation Bar                                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Main Content Area                                  │
│                                                      │
│                                                      │
│                                                      │
│                                                      │
│                                   ┌──────────────┐  │
│                                   │   Toast 3    │  │
│                                   └──────────────┘  │
│                                   ┌──────────────┐  │
│                                   │   Toast 2    │  │
│                                   └──────────────┘  │
│                                   ┌──────────────┐  │
│  Footer                           │   Toast 1    │  │
└───────────────────────────────────└──────────────┘──┘
                                    ↑
                                24px from bottom-right
```

### Mobile View
```
┌──────────────────┐
│  Navigation      │
├──────────────────┤
│                  │
│  Main Content    │
│                  │
│                  │
├──────────────────┤
│ ┌──────────────┐ │
│ │   Toast 2    │ │
│ └──────────────┘ │
│ ┌──────────────┐ │
│ │   Toast 1    │ │
│ └──────────────┘ │
├──────────────────┤
│  [≣] [+] [✓] [☰]│← Mobile Tab Bar
└──────────────────┘
   ↑
 80px from bottom
 (above tab bar)
```

## 🎨 Notification Anatomy

### Success Toast
```
┌───────────────────────────────────────────┐
│██│ ✓ │ Operation Complete               │×│
│██│   │ Your changes have been saved     │ │
│██│   │ successfully.                    │ │
│██└───┴──────────────────────────────────┴─┘
└▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓┘
 ← Progress bar (green, animated)

Legend:
██ = Green accent bar (4px, gradient)
✓  = Check circle icon (green)
×  = Close button
▓  = Progress bar showing time remaining
```

### Error Toast
```
┌───────────────────────────────────────────┐
│██│ ⚠ │ Error                            │×│
│██│   │ Failed to save changes.          │ │
│██│   │ Please try again.                │ │
│██└───┴──────────────────────────────────┴─┘
└▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓┘
 ← Progress bar (red, animated)

██ = Red accent bar
⚠  = Exclamation circle icon (red)
```

### Warning Toast
```
┌───────────────────────────────────────────┐
│██│ △ │ Warning                          │×│
│██│   │ Please review the highlighted    │ │
│██│   │ fields before continuing.        │ │
│██└───┴──────────────────────────────────┴─┘
└▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓┘
 ← Progress bar (orange, animated)

██ = Orange accent bar
△  = Exclamation triangle icon (orange)
```

### Info Toast
```
┌───────────────────────────────────────────┐
│██│ ⓘ │ Information                      │×│
│██│   │ New features are available.      │ │
│██│   │ Check the changelog!             │ │
│██└───┴──────────────────────────────────┴─┘
└▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓┘
 ← Progress bar (blue, animated)

██ = Blue accent bar
ⓘ  = Info circle icon (blue)
```

## 🎭 States & Interactions

### Default State
```
┌────────────────────────────┐
│▌✓│ Success               │×│  ← Normal appearance
│▌ │ Operation completed   │ │
└▌─┴───────────────────────┴─┘
 ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░
 ← Progress bar animating
```

### Hover State
```
┌────────────────────────────┐
│▌▌✓│ Success              │✕│  ← Accent bar wider
│▌▌ │ Operation completed  │ │  ← Shadow darker
└▌▌─┴──────────────────────┴─┘  ← Close button larger
 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
 ← Progress paused
```

### Focus State
```
╔════════════════════════════╗
║▌✓│ Success               │×║  ← Blue outline (2px)
║▌ │ Operation completed   │ ║  ← for accessibility
╚▌═╧═══════════════════════╧═╝
 ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░
```

## 📐 Dimensions

### Toast Card
- **Width (Desktop)**: 320px - 420px
- **Width (Mobile)**: calc(100% - 32px)
- **Min Height**: 64px
- **Max Height**: None (auto-fits content)
- **Border Radius**: 12px
- **Padding**: 12px

### Components
- **Accent Bar**: 4px wide (6px on hover)
- **Icon Area**: 48px wide
- **Icon Size**: 20px
- **Close Button**: 36px × 36px
- **Progress Bar**: 3px height
- **Gap Between Toasts**: 12px

### Typography
- **Title**: 14px, weight 600
- **Message**: 13px, weight 400
- **Line Height**: 1.4 (title), 1.5 (message)
- **Font**: Inter (fallback: system-ui)

## 🌈 Color Palette

### Light Theme
```
Success:
  Accent:  #10b981 → #059669 (gradient)
  Icon:    #10b981
  Text:    #0f172a

Error:
  Accent:  #ef4444 → #dc2626 (gradient)
  Icon:    #ef4444
  Text:    #0f172a

Warning:
  Accent:  #f59e0b → #d97706 (gradient)
  Icon:    #f59e0b
  Text:    #0f172a

Info:
  Accent:  #3b82f6 → #2563eb (gradient)
  Icon:    #3b82f6
  Text:    #0f172a

Background: #ffffff
Title:      #0f172a
Message:    #64748b
```

### Dark Theme
```
Success:
  Accent:  #10b981 → #059669 (gradient)
  Icon:    #34d399 (lighter)
  Text:    #f1f5f9

Error:
  Accent:  #ef4444 → #dc2626 (gradient)
  Icon:    #f87171 (lighter)
  Text:    #f1f5f9

Warning:
  Accent:  #f59e0b → #d97706 (gradient)
  Icon:    #fbbf24 (lighter)
  Text:    #f1f5f9

Info:
  Accent:  #3b82f6 → #2563eb (gradient)
  Icon:    #60a5fa (lighter)
  Text:    #f1f5f9

Background: #1e293b
Title:      #f1f5f9
Message:    #cbd5e1
```

## 🎬 Animation Timeline

### Slide In (300ms)
```
0ms                  150ms                300ms
│                     │                     │
├─ Opacity: 0        ├─ Opacity: 0.5      ├─ Opacity: 1
├─ X: 120%           ├─ X: 60%            ├─ X: 0%
└─ Scale: 0.8        └─ Scale: 0.9        └─ Scale: 1
```

### Auto-dismiss (5000ms default)
```
0ms              Progress Bar             5000ms
│◄────────────────────────────────────────►│
├─ Full width                    Empty ────┤
└─ Show toast                    Hide toast┘
```

### Slide Out (300ms)
```
0ms                  150ms                300ms
│                     │                     │
├─ Opacity: 1        ├─ Opacity: 0.5      ├─ Opacity: 0
├─ X: 0%             ├─ X: 60%            ├─ X: 120%
└─ Scale: 1          └─ Scale: 0.9        └─ Scale: 0.8
```

## 📏 Spacing & Layout

### Single Toast
```
┌──────────────────────────────┐
│ ┌──┬────────────────────┬──┐ │← 24px from edge
│ │██│ ✓ Title           │× │ │
│ │██│   Message here    │  │ │
│ └──┴────────────────────┴──┘ │
│  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░  │
└──────────────────────────────┘
```

### Multiple Toasts (Stacked)
```
┌──────────────────────────────┐
│ ┌──────────────────────────┐ │← Newest (top)
│ │ Toast 3                  │ │
│ └──────────────────────────┘ │
│          ↓ 12px gap           │
│ ┌──────────────────────────┐ │
│ │ Toast 2                  │ │
│ └──────────────────────────┘ │
│          ↓ 12px gap           │
│ ┌──────────────────────────┐ │
│ │ Toast 1                  │ │← Oldest (bottom)
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

### Content Padding
```
┌───────────────────────────────┐
│█│←48px→│                   │36px││
│█│  ✓   │ ←12px→ Title     │ × │
│█│      │        Message   │   │
└─┴──────┴──────────────────┴───┘
 4px     Icon    Content    Close
```

## 🎯 Responsive Breakpoints

### Desktop (> 768px)
```
Screen: 1920px wide
┌──────────────────────────────────────────────────┐
│                                                   │
│                              ┌─────────────────┐ │
│                              │    420px wide   │ │
│                              └─────────────────┘ │
└───────────────────────────────────────────────24px
```

### Tablet (576px - 768px)
```
Screen: 768px wide
┌──────────────────────────────────────┐
│                                       │
│                  ┌──────────────────┐ │
│                  │   ~350px wide    │ │
│                  └──────────────────┘ │
└───────────────────────────────────24px
```

### Mobile (< 576px)
```
Screen: 375px wide
┌───────────────────────┐
│ ←16px→         ←16px→ │
│ ┌───────────────────┐ │
│ │  Full width - 32px│ │
│ └───────────────────┘ │
│         ↑ 80px        │
└───────────────────────┘
       Tab Bar
```

## 🔍 Icon Details

### Success Icon
```
    ✓
   ╱ ╲     - Font Awesome: fa-check-circle
  ╱___╲    - Size: 20px
 (     )   - Color: #10b981 (light) / #34d399 (dark)
  ╲___╱    - Weight: Solid (900)
```

### Error Icon
```
   ⚠       - Font Awesome: fa-exclamation-circle
  ╱!╲      - Size: 20px
 ( ! )     - Color: #ef4444 (light) / #f87171 (dark)
  ╲!╱      - Weight: Solid (900)
```

### Warning Icon
```
   △       - Font Awesome: fa-exclamation-triangle
  ╱!╲      - Size: 20px
 ╱   ╲     - Color: #f59e0b (light) / #fbbf24 (dark)
└─────┘    - Weight: Solid (900)
```

### Info Icon
```
   ⓘ       - Font Awesome: fa-info-circle
  (i)      - Size: 20px
   │       - Color: #3b82f6 (light) / #60a5fa (dark)
           - Weight: Solid (900)
```

## 🎨 Shadow & Depth

### Light Theme Shadows
```
Default:
  shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.1)
  shadow-md: 0 10px 15px -3px rgba(0,0,0,0.1)
  shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.1)

Hover:
  shadow-md: 0 12px 20px -3px rgba(0,0,0,0.15)
```

### Dark Theme Shadows
```
Default:
  shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.3)
  shadow-md: 0 10px 15px -3px rgba(0,0,0,0.3)
  shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.4)

Hover:
  shadow-md: 0 12px 20px -3px rgba(0,0,0,0.5)
```

## ♿ Accessibility Details

### ARIA Attributes
```html
<div class="toast-notification"
     role="alert"
     aria-live="polite"      ← For info/success
     aria-live="assertive"   ← For errors
     aria-atomic="true">
  ...
</div>
```

### Keyboard Navigation
```
Tab      → Focus close button
Enter    → Close notification
Escape   → Close notification (if focused)
```

### Screen Reader Announcement
```
Success: "Success. Operation completed successfully."
Error:   "Error. Failed to save changes."
Warning: "Warning. Please review your input."
Info:    "Information. New updates available."
```

## 📱 Touch Targets

### Minimum Sizes (Mobile)
```
Close Button:  36px × 36px  ✓ (meets 44px target with margin)
Toast Height:  Min 64px     ✓ (comfortable touch)
Tap Area:      Full card    ✓ (entire toast hoverable)
```

## 🎯 Use Case Examples

### Form Submission Success
```
┌───────────────────────────────────┐
│▌✓│ Saved                        │×│
│▌ │ Your profile has been        │ │
│▌ │ updated successfully.        │ │
└▌─┴──────────────────────────────┴─┘
 ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░
 Duration: 5 seconds
```

### Error Message
```
┌───────────────────────────────────┐
│▌⚠│ Error                        │×│
│▌ │ Unable to save changes.      │ │
│▌ │ Please check your connection.│ │
└▌─┴──────────────────────────────┴─┘
 ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░
 Duration: 7 seconds
```

### Processing (Persistent)
```
┌───────────────────────────────────┐
│▌ⓘ│ Processing                   │×│
│▌ │ Please wait while we process │ │
│▌ │ your request...              │ │
└▌─┴──────────────────────────────┴─┘
 (No progress bar - manual dismiss)
```

---

**Note**: This visual guide uses ASCII art for illustration. Actual implementation uses modern CSS with smooth gradients, shadows, and animations.

For live examples, open: `docs/TOAST_NOTIFICATION_DEMO.html`
