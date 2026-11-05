# Toast Notification System

Professional, modern toast notification system for the TimeTracker application.

## Features

- ✨ **Modern Design**: Beautiful toast notifications with smooth animations
- 🎨 **Theme Support**: Automatic light/dark theme integration
- 📱 **Mobile Responsive**: Adapts to mobile screens with proper positioning
- 🎯 **Auto-dismiss**: Configurable auto-dismiss with progress bar
- ⏸️ **Pause on Hover**: Users can pause notifications by hovering
- 🔔 **Multiple Types**: Success, Error, Warning, Info
- ♿ **Accessible**: ARIA labels and keyboard navigation support
- 🎭 **Smooth Animations**: Elegant slide-in/slide-out effects
- 📚 **Stacking**: Multiple notifications stack gracefully

## Usage

### Basic Usage

The toast notification system is automatically initialized on page load. You can use it from anywhere in your JavaScript code.

#### Simple Notifications

```javascript
// Using the convenience methods
toastManager.success('Operation completed successfully!');
toastManager.error('Something went wrong!');
toastManager.warning('Please review your input!');
toastManager.info('New updates available!');
```

#### Advanced Notifications

```javascript
// With custom title and duration
toastManager.success('User created successfully', 'Success', 3000);

// Using the full API
toastManager.show({
    message: 'Your changes have been saved',
    title: 'Saved',
    type: 'success',
    duration: 5000,        // milliseconds (0 = no auto-dismiss)
    dismissible: true      // show close button
});
```

### Backward Compatibility

The old `showToast()` function is still supported:

```javascript
// Legacy syntax still works
showToast('This is a message', 'success');
showToast('Error occurred', 'error');
```

### Notification Types

| Type | Icon | Color | Use Case |
|------|------|-------|----------|
| `success` | ✓ Check | Green | Successful operations |
| `error` | ⚠ Circle | Red | Errors and failures |
| `warning` | △ Triangle | Orange | Warnings and cautions |
| `info` | ⓘ Info | Blue | General information |

### Duration Options

```javascript
// Default: 5000ms (5 seconds)
toastManager.success('Default duration');

// Custom duration
toastManager.success('Quick message', null, 2000);

// No auto-dismiss (user must close manually)
toastManager.show({
    message: 'Important notice',
    type: 'warning',
    duration: 0
});
```

### Flask Flash Messages

Flash messages from Flask are automatically converted to toast notifications:

```python
# In your Python code
from flask import flash

flash('User created successfully', 'success')
flash('Invalid credentials', 'error')
flash('Please verify your email', 'warning')
flash('Session will expire in 5 minutes', 'info')
```

These will automatically appear as toast notifications when the page loads.

## API Reference

### ToastNotificationManager Class

#### Methods

##### `show(options)`

Display a toast notification.

**Parameters:**
- `options.message` (string, required): The notification message
- `options.title` (string, optional): Notification title (defaults based on type)
- `options.type` (string, optional): Type of notification - 'success', 'error', 'warning', 'info' (default: 'info')
- `options.duration` (number, optional): Duration in milliseconds (default: 5000, 0 = no auto-dismiss)
- `options.dismissible` (boolean, optional): Show close button (default: true)
- `options.actionLink` / `options.actionLabel` (string, optional): In-toast link (e.g. “View time entries”)
- `options.onDismiss` (function, optional): Called when the toast is removed; receives a reason string such as `'close'` (user clicked the close button) or `'timeout'` (auto-dismiss). Use for syncing dismiss state with the server (for example smart notifications calling `POST /api/notifications/dismiss`).

**Returns:** Toast ID (can be used to dismiss programmatically)

**Example:**
```javascript
const toastId = toastManager.show({
    message: 'File uploaded successfully',
    title: 'Upload Complete',
    type: 'success',
    duration: 4000
});
```

##### `success(message, title, duration)`

Shortcut for success notifications.

##### `error(message, title, duration)`

Shortcut for error notifications.

##### `warning(message, title, duration)`

Shortcut for warning notifications.

##### `info(message, title, duration)`

Shortcut for info notifications.

##### `dismiss(toastId)`

Dismiss a specific toast notification.

```javascript
const id = toastManager.success('Processing...');
// Later...
toastManager.dismiss(id);
```

##### `dismissAll()`

Dismiss all visible toast notifications.

```javascript
toastManager.dismissAll();
```

## Styling Customization

The toast notifications use CSS custom properties and can be styled in `toast-notifications.css`.

### Key CSS Classes

- `.toast-notification` - Main container
- `.toast-notification.toast-success` - Success variant
- `.toast-notification.toast-error` - Error variant
- `.toast-notification.toast-warning` - Warning variant
- `.toast-notification.toast-info` - Info variant
- `.toast-icon` - Icon container
- `.toast-content` - Message content area
- `.toast-title` - Title text
- `.toast-message` - Message text
- `.toast-close` - Close button
- `.toast-progress` - Progress bar container

## Position

Notifications appear in the **bottom-right corner** of the screen:
- **Desktop**: 24px from bottom and right
- **Mobile**: 16px from sides, 80px from bottom (above tab bar)

## Examples

### Success Operation

```javascript
// After saving a form
fetch('/api/save', { method: 'POST', body: formData })
    .then(response => {
        if (response.ok) {
            toastManager.success('Changes saved successfully', 'Saved');
        } else {
            toastManager.error('Failed to save changes', 'Error');
        }
    });
```

### Timer Operations

```javascript
// Timer started
socket.on('timer_started', (data) => {
    toastManager.success(
        `Timer started for ${data.project_name}`,
        'Timer Started'
    );
});

// Timer stopped
socket.on('timer_stopped', (data) => {
    toastManager.info(
        `Duration: ${data.duration}`,
        'Timer Stopped'
    );
});
```

### Form Validation

```javascript
// After form submission
if (errors.length > 0) {
    toastManager.warning(
        'Please correct the highlighted fields',
        'Validation Error',
        7000
    );
}
```

### Long-running Operations

```javascript
// Show persistent notification
const taskId = toastManager.info(
    'Processing your request...',
    'Please Wait',
    0  // No auto-dismiss
);

// Later, when done
toastManager.dismiss(taskId);
toastManager.success('Processing complete!');
```

## Accessibility

- All notifications have proper ARIA labels
- Role "alert" for screen readers
- Keyboard navigable close buttons
- Respects `prefers-reduced-motion` setting
- Appropriate color contrast ratios
- Focus management

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Migration from Old System

### Before (Old Alert System)
```html
<div class="alert alert-success alert-dismissible fade show">
    Success message
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```

### After (New Toast System)
```javascript
toastManager.success('Success message');
```

All existing flash messages and `showToast()` calls will automatically use the new system!

## Performance

- Efficient DOM management
- Automatic cleanup of dismissed toasts
- Limits to 5 visible toasts maximum
- Smooth 60fps animations
- Minimal memory footprint

## Files

- `app/static/toast-notifications.css` - Styles
- `app/static/toast-notifications.js` - JavaScript implementation
- `app/templates/base.html` - Integration

## Support

For issues or feature requests, please contact the development team.
