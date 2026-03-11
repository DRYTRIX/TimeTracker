# TimeTracker UI Guidelines

This document describes design principles, component usage, layout structure, and styling conventions for the TimeTracker web UI. Use it when adding or changing templates and static assets.

## Design principles

- **Clarity** — One primary action per block; labels and hierarchy make the next step obvious.
- **Consistency** — Use the same components and patterns across pages (page header, cards, empty states, buttons).
- **Minimal friction** — Reduce steps for the core flow: start timer → monitor → stop → review. First-class navigation for Timer and Time entries.
- **Professional appearance** — Clean spacing, readable typography, semantic color use, and accessible contrast.
- **Accessibility** — Keyboard navigation, focus visibility, ARIA where needed, and semantic HTML. See [Frontend Quality Gates](development/FRONTEND_QUALITY_GATES.md) for a11y checks.

## Component usage

### Page header

Use the `page_header` macro from `app/templates/components/ui.html` on every main page:

- **Parameters:** `icon_class`, `title_text`, `subtitle_text` (optional), `actions_html` (optional), `breadcrumbs` (optional).
- **Usage:** One h1-level title per page; put primary actions in `actions_html`; use `breadcrumbs` for deep pages (e.g. list → detail → edit).

### Stat cards and info cards

- **Stat cards:** Use `stat_card` from `components/ui.html` or `components/cards.html` for numeric summaries (e.g. total hours, entry count). Prefer a single row of compact stat cards on dashboards.
- **Info cards:** Use `info_card` for short text summaries when needed.

### Empty states

- **Full empty state:** Use `empty_state` or `empty_state_with_features` from `components/ui.html` for list or section-level “no data” (icon, title, message, primary action).
- **Compact empty state:** Use `empty_state_compact` for table body or inline “no results” (smaller icon and text, same structure).
- Always provide a clear primary action (e.g. “Start timer”, “Create project”, “View all”).

### Buttons

- **Primary:** One main action per block (`btn btn-primary`) — e.g. “Start Timer”, “Save”, “Log Time”.
- **Secondary:** Alternative or cancel (`btn btn-secondary`).
- **Danger:** Destructive actions (`btn btn-danger`).
- **Ghost:** Low emphasis (`btn btn-ghost`). Use for tertiary actions.
- **Sizes:** `btn-sm`, `btn-lg` when needed. Use consistent padding and touch targets (e.g. ≥ 44px for mobile).

### Forms

- **Labels:** Use `form-label`; mark required fields with `*` and optional with “(optional)” in helper text.
- **Inputs:** Use `form-input` from `app/static/src/input.css`. Add `form-input-error` for validation error state.
- **Validation:** Show inline errors below fields; use the existing toast system for submit/API errors.

### Modals and dialogs

- **Pattern:** Overlay + content panel; close on overlay click and Escape. Primary button submits; secondary/cancel closes.
- **Components:** Use `modal` and `confirm_dialog` from `components/ui.html`. Ensure focus is trapped inside when open and restored on close.
- **Start Timer modal:** Same pattern; single primary “Start” action; progressive disclosure (project/client → task → notes/tags) where possible.

### Notifications

- Use the existing **toast** system for success, error, warning, and info. Support optional `actionLink` and `actionLabel` for follow-up (e.g. “View time entries” after stopping the timer).
- Document types and behavior in this file; avoid ad-hoc `alert()` for user feedback.

## Layout structure

- **Content width:** Main content is wrapped in a max-width container (`max-w-7xl`, 1280px) and centered (`mx-auto`) so lines don’t stretch on large screens. Applied in `base.html` to the main content area.
- **Grid:** Use Tailwind grid for dashboards and two-column layouts: e.g. `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3`; main content often `lg:col-span-2`, sidebar `lg:col-span-1`.
- **Spacing:** Use the design tokens in `app/static/src/input.css` (`--spacing-xs` through `--spacing-3xl`). Prefer `gap-4` for card groups, `gap-6` for sections, `p-6` for card padding.

## Styling conventions

- **Tailwind:** Prefer Tailwind utility classes. Design tokens and component classes live in `app/static/src/input.css` (e.g. `form-input`, `btn`, `text-h1`…`text-caption`, status and action classes).
- **Colors:** Use semantic tokens and classes: `primary`, `text-text-light` / `text-text-dark`, `text-text-muted-light` / `text-text-muted-dark`, `bg-card-light` / `bg-card-dark`, `border-border-light` / `border-border-dark`. Use status/action classes (`status-active`, `action-success`, etc.) for badges and feedback.
- **Typography:** Use `.text-h1`…`.text-h6` for headings, `.text-body` / `.text-body-sm` for body text, `.text-label` / `.text-caption` for labels and captions. Page title = h1; section = h2; card title = h3.
- **Dark mode:** Supported via `dark:` variants and `darkMode: 'class'` in Tailwind config. Test both themes when changing UI.

## Keyboard and focus

- **Escape:** Closes modals and dropdowns. Implement in `base-init.js` and feature scripts.
- **Enter:** Submits the primary form in modals and dialogs.
- **Tab order:** Logical and visible; ensure focus ring is visible (e.g. `focus:ring-2 focus:ring-primary`).
- **Skip link:** “Skip to content” is present in `base.html`; keep it and ensure the target is the main content anchor.

## File reference

| Area | Files |
|------|--------|
| Base layout | `app/templates/base.html` |
| Design tokens / Tailwind | `app/static/src/input.css`, `tailwind.config.js` |
| Components | `app/templates/components/ui.html`, `app/templates/components/cards.html` |
| Dashboard | `app/templates/main/dashboard.html` |
| Timer flow | `app/templates/timer/timer_page.html`, Start Timer modal (dashboard), `app/static/floating-timer-bar.js` |
| Time entries | `app/templates/timer/time_entries_overview.html`, `app/templates/timer/_time_entries_list.html` |

For accessibility and quality checks, see [FRONTEND_QUALITY_GATES.md](development/FRONTEND_QUALITY_GATES.md).
