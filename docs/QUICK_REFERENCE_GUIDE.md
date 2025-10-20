# TimeTracker Enhanced UI - Quick Reference Guide

## 🚀 Quick Start

All enhanced features are automatically loaded via `base.html`. No additional setup required!

---

## 📋 Component Library Reference

### Import Components
```jinja
{% from "components/ui.html" import 
    page_header, breadcrumb_nav, stat_card, empty_state, 
    loading_spinner, skeleton_card, badge, button, progress_bar,
    alert, modal, data_table, tabs, timeline_item %}
```

### Page Header with Breadcrumbs
```jinja
{% set breadcrumbs = [
    {'text': 'Parent', 'url': url_for('parent')},
    {'text': 'Current Page'}
] %}

{{ page_header(
    icon_class='fas fa-folder',
    title_text='Page Title',
    subtitle_text='Page description',
    breadcrumbs=breadcrumbs,
    actions_html='<button>Action</button>'
) }}
```

### Stat Cards
```jinja
{{ stat_card('Total Hours', '156.5', 'fas fa-clock', 'blue-500', trend=12.5) }}
```

### Empty States
```jinja
{% set actions %}
    <a href="#" class="btn btn-primary">Create New</a>
{% endset %}

{{ empty_state('fas fa-inbox', 'No Items', 'Description', actions, 'default') }}
```

### Loading States
```jinja
{{ loading_spinner('md', 'Loading...') }}
{{ skeleton_card() }}
```

### Badges
```jinja
{{ badge('Active', 'green-500', 'fas fa-check') }}
```

### Progress Bars
```jinja
{{ progress_bar(75, 100, 'primary', show_label=True) }}
```

### Alerts
```jinja
{{ alert('Success message', 'success', dismissible=True) }}
```

---

## 🔧 Enhanced Tables

### Basic Setup
```html
<table class="w-full" data-enhanced>
    <thead>
        <tr>
            <th data-sortable>Name</th>
            <th data-sortable>Date</th>
            <th data-editable>Status</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Item 1</td>
            <td>2024-01-15</td>
            <td>Active</td>
        </tr>
    </tbody>
</table>
```

### Available Attributes
- `data-enhanced` - Enable enhanced features
- `data-sortable` - Make column sortable
- `data-editable` - Allow inline editing

### Features
- Click header to sort
- Double-click cell to edit
- Bulk selection with checkboxes
- Drag column borders to resize

---

## 🔍 Search & Filters

### Live Search
```html
<input type="search" 
       data-live-search 
       placeholder="Search..." />
```

### Filter Forms
```html
<form method="GET" data-filter-form>
    <input type="text" name="search" />
    <select name="status">
        <option value="">All</option>
        <option value="active">Active</option>
    </select>
    <button type="submit">Filter</button>
</form>
```

Features automatically added:
- Active filter badges
- Clear all button
- Filter persistence

---

## 📊 Charts

### Time Series Chart
```javascript
window.chartManager.createTimeSeriesChart('myChart', {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    datasets: [{
        label: 'Hours Logged',
        data: [120, 150, 180, 140, 200],
        color: '#3b82f6'
    }]
}, {
    yAxisFormat: (value) => `${value}h`
});
```

### Bar Chart
```javascript
window.chartManager.createBarChart('barChart', {
    labels: ['Project A', 'Project B', 'Project C'],
    datasets: [{
        label: 'Hours',
        data: [45, 60, 38]
    }]
});
```

### Doughnut Chart
```javascript
window.chartManager.createDoughnutChart('pieChart', {
    labels: ['Development', 'Meetings', 'Planning'],
    values: [120, 45, 35]
});
```

### Progress Ring
```javascript
window.chartManager.createProgressChart('progressRing', 75, 100, {
    color: '#3b82f6',
    label: 'Completion'
});
```

### Update Chart
```javascript
window.chartManager.updateChart('myChart', {
    labels: newLabels,
    datasets: newDatasets
});
```

### Export Chart
```javascript
window.chartManager.exportChart('myChart', 'report.png');
```

---

## 🔔 Toast Notifications

### Basic Usage
```javascript
window.toastManager.success('Operation successful!');
window.toastManager.error('Something went wrong');
window.toastManager.warning('Be careful!');
window.toastManager.info('Helpful information');
```

### Custom Duration
```javascript
window.toastManager.success('Message', 10000); // 10 seconds
window.toastManager.info('Stays forever', 0); // No auto-dismiss
```

---

## ↩️ Undo/Redo

### Add Undoable Action
```javascript
window.undoManager.addAction(
    'Item deleted',
    (data) => {
        // Undo function
        restoreItem(data.id);
    },
    { id: itemId, name: itemName }
);
```

### Trigger Undo
```javascript
window.undoManager.undo();
```

---

## 📝 Form Auto-Save

### Enable Auto-Save
```html
<form data-auto-save 
      data-auto-save-key="my-form"
      action="/save" 
      method="POST">
    <!-- Form fields -->
</form>
```

### Custom Save Function
```javascript
new FormAutoSave(formElement, {
    debounceMs: 1000,
    storageKey: 'my-form',
    onSave: (data, callback) => {
        fetch('/api/save', {
            method: 'POST',
            body: JSON.stringify(data)
        }).then(() => callback());
    }
});
```

---

## 👁️ Recently Viewed

### Track Item
```javascript
window.recentlyViewed.track({
    url: window.location.href,
    title: 'Project Name',
    type: 'project',
    icon: 'fas fa-folder'
});
```

### Get Recent Items
```javascript
const items = window.recentlyViewed.getItems();
```

---

## ⭐ Favorites

### Toggle Favorite
```javascript
const isFavorite = window.favoritesManager.toggle({
    id: itemId,
    type: 'project',
    title: 'Project Name',
    url: '/projects/123'
});
```

### Check if Favorite
```javascript
const isFav = window.favoritesManager.isFavorite(itemId, 'project');
```

### Get All Favorites
```javascript
const favorites = window.favoritesManager.getFavorites();
```

---

## 🎓 Onboarding Tours

### Define Tour Steps
```javascript
const steps = [
    {
        target: '#dashboard',
        title: 'Welcome!',
        content: 'This is your dashboard',
        position: 'bottom'
    },
    {
        target: '#projects',
        title: 'Projects',
        content: 'Manage your projects here',
        position: 'right'
    }
];
```

### Start Tour
```javascript
window.onboardingManager.init(steps);
```

### Reset Tour
```javascript
window.onboardingManager.reset();
```

---

## 🖱️ Drag & Drop

### Enable Drag & Drop
```html
<div id="sortable-list">
    <div draggable="true">Item 1</div>
    <div draggable="true">Item 2</div>
    <div draggable="true">Item 3</div>
</div>
```

### Initialize Manager
```javascript
new DragDropManager(document.getElementById('sortable-list'), {
    onReorder: (order) => {
        // Save new order
        console.log('New order:', order);
    }
});
```

---

## 🎨 Utility Classes

### Animations
```css
.fade-in              /* Fade in animation */
.fade-in-up           /* Fade in from bottom */
.slide-in-up          /* Slide up */
.zoom-in              /* Zoom in */
.bounce-in            /* Bounce in */
.stagger-animation    /* Stagger children */
```

### Hover Effects
```css
.scale-hover          /* Scale on hover */
.lift-hover           /* Lift with shadow */
.glow-hover           /* Glow effect */
```

### Loading
```css
.loading-spinner      /* Spinner */
.skeleton             /* Skeleton placeholder */
.shimmer              /* Shimmer effect */
```

---

## ⌨️ Keyboard Shortcuts

### Built-in Shortcuts
- `Cmd/Ctrl + Enter` - Submit form
- `Escape` - Close modals
- `Tab` - Navigate fields
- `/` - Focus search (coming)

---

## 📱 PWA Features

### Install Prompt
Automatically shown to users. Customize by editing the service worker registration in `base.html`.

### Offline Support
Automatically enabled. Pages and assets cached for offline use.

### Background Sync
Time entries sync automatically when connection restored.

---

## 🎭 Dark Mode

### Toggle Dark Mode
```javascript
// Toggle via button (already implemented)
document.getElementById('theme-toggle').click();
```

### Check Current Theme
```javascript
const isDark = document.documentElement.classList.contains('dark');
```

---

## 📐 Responsive Breakpoints

```css
/* Mobile first */
@media (min-width: 640px)  { /* sm */ }
@media (min-width: 768px)  { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
@media (min-width: 1536px) { /* 2xl */ }
```

---

## 🧪 Testing

### Run Tests
```bash
pytest tests/test_enhanced_ui.py -v
```

### Test Specific Feature
```bash
pytest tests/test_enhanced_ui.py::TestEnhancedTables -v
```

---

## 🐛 Common Issues

### Table Not Sorting
Ensure `data-enhanced` attribute is on `<table>` and `data-sortable` on `<th>`.

### Charts Not Showing
Check that Chart.js is loaded and canvas has valid ID.

### Auto-save Not Working
Verify `data-auto-save` and `data-auto-save-key` attributes are present.

### Toast Not Appearing
Ensure `window.toastManager` is initialized (automatic on page load).

---

## 💡 Pro Tips

1. **Use breadcrumbs** on all nested pages for better navigation
2. **Add loading states** to all async operations
3. **Use empty states** with clear CTAs
4. **Implement auto-save** on long forms
5. **Add keyboard shortcuts** for power users
6. **Use charts** to visualize complex data
7. **Show toast notifications** for user feedback
8. **Enable PWA** for better mobile experience

---

## 🔗 Quick Links

- [Full Documentation](LAYOUT_IMPROVEMENTS_COMPLETE.md)
- [Implementation Summary](IMPLEMENTATION_COMPLETE_SUMMARY.md)
- [Test Suite](tests/test_enhanced_ui.py)
- [Component Library](app/templates/components/ui.html)

---

## 📞 Need Help?

1. Check the full documentation
2. Review code examples
3. Run the test suite
4. Check browser console for errors
5. Review inline code comments

---

**Last Updated**: October 2025  
**Version**: 3.0.0  
**Quick Reference**: Always up-to-date

