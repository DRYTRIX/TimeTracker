# Enhanced Keyboard Shortcuts System

## Overview

The Enhanced Keyboard Shortcuts System provides a comprehensive, customizable keyboard navigation experience for the TimeTracker application. It goes beyond a simple command palette to offer context-aware shortcuts, visual cheat sheets, usage statistics, and full customization capabilities.

## Features

### 1. **Command Palette** (`Ctrl+K` or `Cmd+K`)
- Quick access to all application commands
- Fuzzy search with instant results
- Keyboard navigation with arrow keys
- Categories: Navigation, Actions, Timer, Create, and more

### 2. **Keyboard Shortcuts Cheat Sheet** (`Shift+?`)
- Visual display of all available shortcuts
- Search and filter by name, description, or keys
- Categorized view (Navigation, Create, Timer, Table, Form, Modal, etc.)
- Usage statistics for each shortcut
- Print-friendly layout
- Responsive design for mobile and desktop

### 3. **Context-Aware Shortcuts**
Shortcuts automatically adapt based on your current context:
- **Global**: Available everywhere
- **Table**: Special shortcuts when working with tables
- **Form**: Enhanced form editing shortcuts
- **Modal**: Modal-specific actions

### 4. **Settings & Customization**
- Enable/disable shortcuts globally or individually
- Customize key combinations
- Adjust sequence timeout
- View usage statistics and most-used shortcuts
- Reset to defaults

### 5. **Usage Analytics**
- Track how often you use each shortcut
- See your most-used shortcuts
- View recent usage history
- Identify opportunities to improve your workflow

## Available Shortcuts

### Navigation Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `g` `d` | Go to Dashboard | Navigate to main dashboard |
| `g` `p` | Go to Projects | View all projects |
| `g` `t` | Go to Tasks | View all tasks |
| `g` `c` | Go to Clients | View all clients |
| `g` `r` | Go to Reports | View reports and analytics |
| `g` `i` | Go to Invoices | View all invoices |
| `g` `a` | Go to Analytics | View analytics dashboard |
| `g` `k` | Go to Kanban | View kanban board |
| `g` `s` | Go to Settings | Open settings page |

### Creation Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `c` `p` | Create Project | Create a new project |
| `c` `t` | Create Task | Create a new task |
| `c` `c` | Create Client | Create a new client |
| `c` `e` | Create Time Entry | Create a new time entry |
| `c` `i` | Create Invoice | Create a new invoice |

### Timer Controls

| Shortcut | Action | Description |
|----------|--------|-------------|
| `t` `s` | Start Timer | Start a new timer |
| `t` `p` | Pause/Stop Timer | Pause or stop the active timer |
| `t` `l` | Log Time | Manually log time |
| `t` `b` | Bulk Time Entry | Create multiple time entries |
| `t` `v` | View Calendar | Open time calendar view |

### Global Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+K` or `Cmd+K` | Command Palette | Open command palette |
| `Ctrl+/` or `Cmd+/` | Search | Focus search box |
| `Shift+?` | Keyboard Shortcuts | Show shortcuts cheat sheet |
| `Ctrl+B` or `Cmd+B` | Toggle Sidebar | Show/hide the sidebar |
| `Ctrl+Shift+D` | Toggle Dark Mode | Switch between themes |
| `Alt+N` | Notifications | View notifications |
| `Alt+H` | Help | Open help page |
| `Alt+1` | Jump to Main | Jump to main content |

### Table Shortcuts (Context: Table)

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+A` | Select All Rows | Select all rows in the table |
| `Delete` | Delete Selected | Delete selected rows |
| `Escape` | Clear Selection | Clear table selection |
| `j` | Next Row | Move to next row |
| `k` | Previous Row | Move to previous row |

### Form Shortcuts (Context: Form)

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+S` | Save Form | Save the current form |
| `Ctrl+Enter` | Submit Form | Submit the current form |
| `Escape` | Cancel | Cancel form editing |

### Modal Shortcuts (Context: Modal)

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Escape` | Close Modal | Close the active modal |
| `Enter` | Confirm | Confirm modal action |

## Usage Guide

### Basic Usage

1. **Opening the Command Palette**
   - Press `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac)
   - Type to search for commands
   - Use arrow keys to navigate
   - Press `Enter` to execute

2. **Viewing All Shortcuts**
   - Press `Shift+?` to open the cheat sheet
   - Search for specific shortcuts
   - Filter by category
   - Click on shortcuts to see details

3. **Using Key Sequences**
   - Press the first key (e.g., `g`)
   - Within 1 second, press the second key (e.g., `d`)
   - The action executes immediately

### Customization

1. **Access Settings**
   - Navigate to Settings → Keyboard Shortcuts
   - Or press `g` `s` and navigate to Keyboard Shortcuts

2. **Enable/Disable Shortcuts**
   - Toggle "Enable Keyboard Shortcuts" to turn on/off globally
   - Individual shortcuts can be disabled in customization

3. **Adjust Sequence Timeout**
   - Change how long to wait between key presses in sequences
   - Default: 1000ms (1 second)
   - Range: 500ms to 3000ms

4. **View Statistics**
   - See which shortcuts you use most
   - View recent usage history
   - Track total usage count

### Context-Aware Behavior

The system automatically detects your current context and activates appropriate shortcuts:

**When working with tables:**
- Use `j` and `k` to navigate rows
- Press `Ctrl+A` to select all
- Press `Delete` to delete selected items

**When editing forms:**
- Press `Ctrl+S` to save
- Press `Ctrl+Enter` to submit
- Press `Escape` to cancel

**When modals are open:**
- Press `Escape` to close
- Press `Enter` to confirm (when applicable)

## Advanced Features

### Keyboard Navigation Detection
The system adds a `keyboard-navigation` class to the body when you use Tab navigation, improving accessibility and focus indicators.

### Input Field Handling
Most shortcuts are disabled when typing in input fields, except for:
- `Ctrl+K` - Command palette (always available)
- `Ctrl+/` - Search (always available)
- `Shift+?` - Shortcuts help (always available)
- `Escape` - Cancel/close (always available)
- `Ctrl+S` - Save (in forms)
- `Ctrl+Enter` - Submit (in forms)

### Onboarding
First-time users see a helpful hint about keyboard shortcuts 5 seconds after page load. This hint:
- Appears once per browser
- Can be dismissed
- Auto-hides after 10 seconds
- Teaches the most important shortcuts

### Print Support
The cheat sheet is print-friendly:
- Click "Print" in the cheat sheet footer
- Automatically formats for printing
- Removes interactive elements
- Optimizes layout for paper

## Technical Details

### Architecture

The system consists of multiple components:

1. **keyboard-shortcuts-enhanced.js**
   - Main keyboard shortcuts manager
   - Context detection
   - Shortcut registration and execution
   - Statistics tracking

2. **keyboard-shortcuts-advanced.js**
   - Legacy advanced shortcuts
   - Integrates with enhanced system

3. **commands.js**
   - Command palette implementation
   - Command registry
   - Search and filtering

4. **keyboard-shortcuts.css**
   - Styling for cheat sheet
   - Modal animations
   - Keyboard key styles
   - Responsive design

### Data Storage

The system stores data in `localStorage`:

- `tt_shortcuts_custom_shortcuts`: Custom key bindings
- `tt_shortcuts_disabled_shortcuts`: Disabled shortcuts list
- `tt_shortcuts_shortcut_stats`: Usage statistics
- `tt_shortcuts_shortcuts_onboarding_seen`: Onboarding hint status

### Context Detection

Contexts are automatically detected based on:
- Active modal presence (`.modal:not(.hidden)`)
- Table focus (`table[data-enhanced]`)
- Form focus (`form[data-enhanced]`)
- Default: `global` context

### Extensibility

Add custom shortcuts programmatically:

```javascript
// Register a new shortcut
window.enhancedKeyboardShortcuts.register('Ctrl+Shift+X', {
    name: 'Custom Action',
    description: 'My custom action',
    category: 'Custom',
    icon: 'fa-star',
    action: () => {
        console.log('Custom action executed!');
    }
});
```

## Accessibility

The system follows accessibility best practices:

- **Keyboard-only navigation**: All features accessible via keyboard
- **Focus management**: Clear focus indicators
- **Screen reader support**: ARIA labels and descriptions
- **High contrast mode**: Supports high contrast preferences
- **Reduced motion**: Respects `prefers-reduced-motion`
- **Skip links**: `Alt+1` to jump to main content

## Browser Compatibility

Supported browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Opera 76+

Features used:
- LocalStorage
- KeyboardEvent API
- Flexbox/Grid
- CSS custom properties
- Modern JavaScript (ES6+)

## Performance

The system is optimized for performance:
- Minimal DOM manipulation
- Event delegation
- Debounced search
- Lazy rendering
- No dependencies (vanilla JavaScript)

## Troubleshooting

### Shortcuts not working?

1. **Check if shortcuts are enabled**
   - Go to Settings → Keyboard Shortcuts
   - Ensure "Enable Keyboard Shortcuts" is on

2. **Check browser compatibility**
   - Use a modern browser (see Browser Compatibility)
   - Update your browser to the latest version

3. **Check for conflicts**
   - Some browser extensions may intercept keyboard shortcuts
   - Try disabling extensions temporarily

4. **Clear localStorage**
   - Open browser console (F12)
   - Run: `localStorage.clear()`
   - Refresh the page

### Cheat sheet not opening?

1. **Check the key combination**
   - Make sure to press Shift AND ? (question mark)
   - Some keyboards require different combinations

2. **Check console for errors**
   - Open browser console (F12)
   - Look for JavaScript errors

### Custom shortcuts not saving?

1. **Check localStorage**
   - Ensure localStorage is not disabled
   - Check if storage quota is exceeded

2. **Check browser privacy settings**
   - Some privacy modes block localStorage
   - Try in regular browsing mode

## FAQ

**Q: Can I disable specific shortcuts?**
A: Yes! Go to Settings → Keyboard Shortcuts → Customization tab and toggle individual shortcuts.

**Q: Can I change key combinations?**
A: Currently, key combinations are fixed. Full customization is planned for a future update.

**Q: Do shortcuts work on mobile?**
A: The system is designed for keyboard use, but the command palette (`Ctrl+K`) is touch-friendly on tablets.

**Q: Can I export my shortcuts configuration?**
A: Not yet, but this feature is planned for a future update.

**Q: Are shortcuts synchronized across devices?**
A: Currently, shortcuts are stored locally. Cloud sync is planned for the future.

**Q: How do I reset shortcuts to defaults?**
A: Go to Settings → Keyboard Shortcuts and click "Reset to Defaults".

## Future Enhancements

Planned features:
- [ ] Full key combination customization
- [ ] Cloud synchronization
- [ ] Import/export shortcuts configuration
- [ ] Macro recording (multi-step shortcuts)
- [ ] Global shortcuts (across browser tabs)
- [ ] Voice command integration
- [ ] Gamification (achievements for power users)
- [ ] Shortcuts for specific pages
- [ ] Plugin system for custom shortcuts

## Contributing

Found a bug or have a feature request? Please open an issue on GitHub!

## License

This feature is part of the TimeTracker application and follows the same license.

---

**Last Updated**: October 2025
**Version**: 2.0

