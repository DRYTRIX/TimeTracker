# Command Palette Usage Guide

## Overview

The TimeTracker command palette is a powerful keyboard-driven interface that allows you to quickly navigate and execute commands without using the mouse. It's inspired by similar features in modern applications like VS Code, Sublime Text, and GitHub.

## Opening the Command Palette

You can open the command palette in multiple ways:

### Primary Method
- **Press `?` (question mark key)** - Simply press the `?` key anywhere in the application
  - Quick, easy to remember
  - Doesn't require modifier keys
  - Works on all keyboard layouts

### Alternative Methods
- **Click the command palette button** in the navigation bar (terminal icon)
- **Use the help menu** dropdown

## Quick Search

To quickly access the search functionality:
- **Press `Ctrl+K` (Windows/Linux)** or **`Cmd+K` (Mac)** - Focuses the search box
  - Works from anywhere in the application
  - Instantly ready to search projects, tasks, clients, and more

## Using the Command Palette

Once opened, you can:

1. **Type to search** - Start typing to filter available commands
2. **Navigate** - Use arrow keys (↑/↓) to move between commands
3. **Execute** - Press `Enter` to run the selected command or click on it
4. **Cancel** - Press `Esc` or click outside the palette to close

## Available Commands

### Navigation Commands
- **Go to Dashboard** (`g d`) - Navigate to the main dashboard
- **Go to Projects** (`g p`) - View all projects
- **Go to Tasks** (`g t`) - View all tasks
- **Go to Reports** (`g r`) - View reports and analytics
- **Go to Invoices** (`g i`) - View invoices
- **Go to Analytics** - View analytics dashboard
- **Open Calendar** - View the time tracking calendar

### Action Commands
- **New Time Entry** (`n e`) - Create a new manual time entry
- **New Project** (`n p`) - Create a new project
- **New Task** (`n t`) - Create a new task
- **New Client** (`n c`) - Create a new client
- **Start Timer** - Start a new timer
- **Stop Timer** - Stop the currently running timer

### General Commands
- **Toggle Theme** (`Ctrl+Shift+L`) - Switch between light and dark mode
- **Open Help** - View keyboard shortcuts help

## Keyboard Sequences

Some commands can be triggered directly without opening the palette using key sequences:

- **`g d`** - Go to Dashboard
- **`g p`** - Go to Projects
- **`g t`** - Go to Tasks
- **`g r`** - Go to Reports

Type the first letter, then the second letter in quick succession (within 1 second).

## Tips and Tricks

1. **Fuzzy Search** - You don't need to type the exact command name. Type keywords related to what you want to do.
2. **Category Filtering** - Commands are organized by category (Navigation, Actions, Timer, General)
3. **First-Time Hint** - A tooltip will appear on your first visit showing you how to use the command palette
4. **Accessibility** - Full keyboard navigation support with visual focus indicators
5. **Theme Support** - The command palette automatically adapts to light and dark themes

## Keyboard Shortcuts Reference

Press `Shift+?` to view the complete keyboard shortcuts help modal with all available commands.

## Mobile Support

On mobile devices:
- Command palette can be accessed via the help menu
- Touch-friendly interface for selecting commands
- Keyboard shortcuts are hidden to save space

## Implementation Details

The command palette features:
- Fast, responsive search
- Smooth animations and transitions
- Glass morphism effects
- Backdrop blur for better focus
- Color-coded command categories
- Visual keyboard shortcut hints
- Auto-completion and suggestions

## Examples

### Example 1: Quick Navigation
1. Press `?`
2. Type "proj"
3. See "Go to Projects" highlighted
4. Press `Enter`

### Example 2: Creating a New Task
1. Press `?`
2. Type "new task"
3. Select "New Task"
4. You're taken to the task creation page

### Example 3: Using Sequences
1. Press `g` (wait briefly)
2. Press `d`
3. Immediately navigate to Dashboard

## Customization

The command palette can be extended with custom commands programmatically:

```javascript
// Register a custom command
window.keyboardShortcuts.registerShortcut({
    id: 'my-custom-command',
    category: 'Custom',
    title: 'My Custom Action',
    description: 'Does something custom',
    icon: 'fas fa-star',
    keys: ['c', 'a'],
    action: () => {
        // Your custom action here
    }
});
```

## Troubleshooting

### Command Palette Won't Open
- Make sure you're not typing in a text input field
- Check that JavaScript is enabled
- Try refreshing the page

### Shortcuts Not Working
- Some shortcuts may conflict with browser shortcuts
- Try using the alternative `?` key method
- Check your keyboard language settings

### Visual Issues
- Clear your browser cache
- Make sure you're using a modern browser (Chrome, Firefox, Safari, Edge)
- Check if dark/light theme is causing issues

## Browser Support

The command palette works best on:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

Requires:
- JavaScript enabled
- CSS backdrop-filter support (for blur effects)

## Feedback

If you have suggestions for new commands or improvements to the command palette, please open an issue on the GitHub repository or contact support.

---

**Pro Tip:** Use the command palette regularly to speed up your workflow. Most power users find they can navigate 2-3x faster using keyboard shortcuts compared to clicking through menus!
