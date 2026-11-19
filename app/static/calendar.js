/**
 * Calendar functionality for TimeTracker
 * Handles day, week, and month views with drag-and-drop support
 */

class Calendar {
    constructor(options) {
        this.viewType = options.viewType || 'month';
        this.currentDate = new Date(options.currentDate || new Date());
        this.container = document.getElementById('calendarContainer');
        this.apiUrl = options.apiUrl;
        this.moveEventUrl = options.moveEventUrl || (window.calendarData && window.calendarData.moveEventUrl) || '';
        this.resizeEventUrl = options.resizeEventUrl || (window.calendarData && window.calendarData.resizeEventUrl) || '';
        this.updateEntryUrl = options.updateEntryUrl || (window.calendarData && window.calendarData.updateEntryUrl) || '/api/entry/';
        this.createEntryUrl = options.createEntryUrl || (window.calendarData && window.calendarData.createEntryUrl) || '/api/entries';
        this.csrfToken = options.csrfToken || (window.calendarData && window.calendarData.csrfToken) || '';
        const snap = parseInt(options.snapMinutes || (window.calendarData && window.calendarData.snapMinutes) || 15, 10);
        this.snapMinutes = [5, 10, 15, 30, 60].includes(snap) ? snap : 15;
        this.events = [];
        this.tasks = [];
        this.timeEntries = [];
        this.holidays = [];
        this.timeOff = [];
        this._dragState = null;
        this._resizeState = null;
        this._selectState = null;

        // Filters
        this.showEvents = true;
        this.showTasks = true;
        this.showTimeEntries = true;
        this.showHolidays = true;
        this.showTimeOff = true;

        this.init();
    }

    formatLocalDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    formatLocalDateTimeInput(date) {
        const pad = (n) => String(n).padStart(2, '0');
        return `${this.formatLocalDate(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    snapToInterval(minutes) {
        const step = this.snapMinutes || 15;
        return Math.round(minutes / step) * step;
    }

    renderDayOverlayBadges(day) {
        const dayKey = this.formatLocalDate(day);
        let html = '';

        if (this.showHolidays) {
            this.holidays.forEach(item => {
                const itemDay = (item.start || '').slice(0, 10);
                if (itemDay === dayKey) {
                    html += `<div class="event-badge holiday-badge day-overlay-badge" style="background-color: ${item.color}22; border-left: 3px solid ${item.color}; color: inherit;" title="${this.escapeHtml(item.title)}">🏖 ${this.escapeHtml(item.title)}</div>`;
                }
            });
        }
        if (this.showTimeOff) {
            this.timeOff.forEach(item => {
                const itemDay = (item.start || '').slice(0, 10);
                if (itemDay === dayKey) {
                    html += `<div class="event-badge time-off-badge day-overlay-badge" style="background-color: ${item.color}22; border-left: 3px solid ${item.color}; color: inherit;" title="${this.escapeHtml(item.title)}">🌴 ${this.escapeHtml(item.title)}</div>`;
                }
            });
        }
        return html;
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.loadEvents();
        this.updateViewLinks();
    }

    setupDragAndDrop() {
        if (!this.container) return;

        this.container.addEventListener('dragstart', (e) => this.onDragStart(e));
        this.container.addEventListener('dragend', (e) => this.onDragEnd(e));
        this.container.addEventListener('dragover', (e) => this.onDragOver(e));
        this.container.addEventListener('dragleave', (e) => this.onDragLeave(e));
        this.container.addEventListener('drop', (e) => this.onDrop(e));
        this.container.addEventListener('mousedown', (e) => this.onPointerDown(e));

        document.addEventListener('mousemove', (e) => this.onPointerMove(e));
        document.addEventListener('mouseup', (e) => this.onPointerUp(e));
    }

    onDragStart(e) {
        const el = e.target.closest('[draggable="true"][data-type]');
        if (!el) return;
        const itemType = el.dataset.type;
        if (itemType !== 'event' && itemType !== 'time_entry') return;
        if (itemType === 'event' && !this.moveEventUrl) return;
        const id = el.dataset.id;
        const start = el.dataset.start;
        const end = el.dataset.end;
        if (!id || !start) return;
        this._dragState = {
            id: parseInt(id, 10),
            itemType,
            start,
            end,
            durationMs: end ? (new Date(end) - new Date(start)) : 60 * 60 * 1000
        };
        el.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(id));
        e.dataTransfer.setData('application/x-calendar-event', JSON.stringify(this._dragState));
    }

    onDragEnd(e) {
        const el = e.target.closest('.dragging');
        if (el) el.classList.remove('dragging');
        this.container.querySelectorAll('.drop-target').forEach(n => n.classList.remove('drop-target'));
        this._clearSlotGhost();
        this._dragState = null;
    }

    _dropTargetFromEvent(e) {
        const step = this.snapMinutes || 15;
        const monthCell = e.target.closest('.month-cell[data-date]');
        if (monthCell) return { kind: 'day', date: monthCell.dataset.date, el: monthCell };

        const weekCol = e.target.closest('.week-day-column[data-date]');
        if (weekCol) {
            const blocks = weekCol.querySelector('.week-day-blocks') || weekCol;
            const rect = blocks.getBoundingClientRect();
            const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
            // 60px per hour → 1px per minute; snap to rounding interval
            const minutes = this.snapToInterval(y);
            return { kind: 'datetime', date: weekCol.dataset.date, minutes: Math.min(24 * 60 - step, minutes), el: weekCol, blocksEl: blocks };
        }

        const dayContainer = e.target.closest('.day-events-container, .events-column');
        if (dayContainer) {
            const container = this.container.querySelector('.day-events-container') || dayContainer;
            const rect = container.getBoundingClientRect();
            const y = Math.max(0, Math.min(1440, e.clientY - rect.top));
            const minutes = this.snapToInterval(y);
            return {
                kind: 'datetime',
                date: this.formatLocalDate(this.currentDate),
                minutes: Math.min(24 * 60 - step, minutes),
                el: container,
                blocksEl: container
            };
        }
        return null;
    }

    onDragOver(e) {
        if (!this._dragState && !(e.dataTransfer && e.dataTransfer.types.includes('application/x-calendar-event'))) {
            return;
        }
        const target = this._dropTargetFromEvent(e);
        if (!target) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        this.container.querySelectorAll('.drop-target').forEach(n => {
            if (n !== target.el) n.classList.remove('drop-target');
        });
        target.el.classList.add('drop-target');

        // Ghost block at the snapped drop slot (not just a full-column wash)
        let state = this._dragState;
        if (!state) {
            try {
                state = JSON.parse(e.dataTransfer.getData('application/x-calendar-event') || 'null');
            } catch (_) {
                state = null;
            }
        }
        if (target.kind === 'datetime' && target.blocksEl && state) {
            const durationMin = Math.max(
                this.snapMinutes || 15,
                Math.round((state.durationMs || 3600000) / 60000)
            );
            const top = target.minutes;
            const height = Math.min(durationMin, 1440 - top);
            const label = this._formatMinutesRange(top, top + height);
            this._showSlotGhost(target.blocksEl, top, height, label, 'drop');
        } else if (target.kind === 'day') {
            this._clearSlotGhost();
        }
    }

    onDragLeave(e) {
        const el = e.target.closest('.drop-target');
        if (el && !el.contains(e.relatedTarget)) {
            el.classList.remove('drop-target');
            this._clearSlotGhost();
        }
    }

    async onDrop(e) {
        e.preventDefault();
        const target = this._dropTargetFromEvent(e);
        this.container.querySelectorAll('.drop-target').forEach(n => n.classList.remove('drop-target'));
        this._clearSlotGhost();
        let state = this._dragState;
        if (!state) {
            try {
                state = JSON.parse(e.dataTransfer.getData('application/x-calendar-event'));
            } catch (_) {
                return;
            }
        }
        if (!state || !target) return;
        if (state.itemType === 'event' && !this.moveEventUrl) return;

        let newStart;
        if (target.kind === 'day') {
            const old = new Date(state.start);
            newStart = new Date(`${target.date}T00:00:00`);
            newStart.setHours(old.getHours(), old.getMinutes(), 0, 0);
        } else {
            const h = Math.floor(target.minutes / 60);
            const m = target.minutes % 60;
            newStart = new Date(`${target.date}T00:00:00`);
            newStart.setHours(h, m, 0, 0);
        }
        const newEnd = new Date(newStart.getTime() + (state.durationMs || 3600000));

        if (state.itemType === 'time_entry') {
            await this.updateTimeEntryTimes(state.id, newStart, newEnd);
        } else {
            await this.postMoveOrResize('move', state.id, {
                start: newStart.toISOString(),
                end: newEnd.toISOString()
            });
        }
        this._dragState = null;
        this.loadEvents();
    }

    onPointerDown(e) {
        if (e.button !== 0) return;
        const handle = e.target.closest('.event-resize-handle');
        if (handle) {
            this.onResizeMouseDown(e, handle);
            return;
        }
        // Drag-select empty area in day/week to create a time entry
        if (e.target.closest('[draggable="true"], .event-card, .week-event-block, .event-badge, a, button, input, select')) {
            return;
        }
        if (this.viewType !== 'day' && this.viewType !== 'week') return;
        const target = this._dropTargetFromEvent(e);
        if (!target || target.kind !== 'datetime' || !target.blocksEl) return;
        e.preventDefault();
        this._selectState = {
            date: target.date,
            startMinutes: target.minutes,
            endMinutes: target.minutes + this.snapMinutes,
            blocksEl: target.blocksEl
        };
        this._renderSelectPreview();
    }

    onResizeMouseDown(e, handle) {
        const resizeHandle = handle || e.target.closest('.event-resize-handle');
        if (!resizeHandle) return;
        e.preventDefault();
        e.stopPropagation();
        const card = resizeHandle.closest('[data-type="event"], [data-type="time_entry"]');
        if (!card) return;
        const itemType = card.dataset.type;
        if (itemType === 'event' && !this.resizeEventUrl) return;
        this._resizeState = {
            id: parseInt(card.dataset.id, 10),
            itemType,
            start: card.dataset.start,
            end: card.dataset.end,
            startY: e.clientY,
            el: card
        };
        card.classList.add('resizing');
    }

    onPointerMove(e) {
        if (this._resizeState) {
            this.onResizeMouseMove(e);
            return;
        }
        if (this._selectState) {
            const target = this._dropTargetFromEvent(e);
            if (!target || target.kind !== 'datetime') return;
            if (target.date !== this._selectState.date) return;
            const step = this.snapMinutes || 15;
            let end = target.minutes;
            if (end <= this._selectState.startMinutes) {
                end = this._selectState.startMinutes + step;
            }
            this._selectState.endMinutes = end;
            this._renderSelectPreview();
        }
    }

    onResizeMouseMove(e) {
        if (!this._resizeState) return;
        const step = this.snapMinutes || 15;
        const deltaPx = e.clientY - this._resizeState.startY;
        const deltaMin = this.snapToInterval(deltaPx);
        const start = new Date(this._resizeState.start);
        let end = new Date(this._resizeState.end || start.getTime() + 3600000);
        end = new Date(end.getTime() + deltaMin * 60 * 1000);
        if (end <= start) end = new Date(start.getTime() + step * 60 * 1000);
        this._resizeState.previewEnd = end;
        const height = Math.max(step, (end - start) / 60000);
        this._resizeState.el.style.height = `${height}px`;
        const startMin = start.getHours() * 60 + start.getMinutes();
        const endMin = end.getHours() * 60 + end.getMinutes();
        this._setBlockTimeBadge(this._resizeState.el, this._formatMinutesRange(startMin, endMin));
    }

    async onPointerUp(e) {
        if (this._resizeState) {
            await this.onResizeMouseUp();
            return;
        }
        if (this._selectState) {
            const state = this._selectState;
            this._selectState = null;
            this._clearSelectPreview();
            if (!state || state.endMinutes <= state.startMinutes) return;
            const start = new Date(`${state.date}T00:00:00`);
            start.setHours(0, 0, 0, 0);
            start.setMinutes(state.startMinutes);
            const end = new Date(`${state.date}T00:00:00`);
            end.setHours(0, 0, 0, 0);
            end.setMinutes(state.endMinutes);
            this.openTimeEntryCreateModal(start, end);
        }
    }

    async onResizeMouseUp() {
        if (!this._resizeState) return;
        const state = this._resizeState;
        this._resizeState = null;
        state.el.classList.remove('resizing');
        this._clearBlockTimeBadge(state.el);
        if (!state.previewEnd) return;
        const start = new Date(state.start);
        if (state.itemType === 'time_entry') {
            await this.updateTimeEntryTimes(state.id, start, state.previewEnd);
        } else {
            await this.postMoveOrResize('resize', state.id, { end: state.previewEnd.toISOString() });
        }
        this.loadEvents();
    }

    _minutesToLabel(totalMinutes) {
        const mins = ((totalMinutes % (24 * 60)) + (24 * 60)) % (24 * 60);
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        const pad = (n) => String(n).padStart(2, '0');
        if (window.userPrefs && window.userPrefs.timeFormat === '12h') {
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;
            return `${h12}:${pad(m)} ${ampm}`;
        }
        return `${pad(h)}:${pad(m)}`;
    }

    _formatMinutesRange(startMin, endMin) {
        return `${this._minutesToLabel(startMin)} – ${this._minutesToLabel(endMin)}`;
    }

    _showSlotGhost(blocksEl, topMinutes, heightMinutes, label, mode) {
        if (!blocksEl) return;
        const kind = mode || 'drop';
        this._clearSlotGhost(blocksEl);
        const ghost = document.createElement('div');
        ghost.className = `time-slot-ghost time-slot-ghost--${kind}`;
        ghost.style.top = `${topMinutes}px`;
        ghost.style.height = `${Math.max(this.snapMinutes || 15, heightMinutes)}px`;
        ghost.innerHTML = `<span class="time-slot-ghost-label">${this.escapeHtml(label || '')}</span>`;
        // Horizontal guide at the snapped start edge
        const line = document.createElement('div');
        line.className = `time-slot-snap-line time-slot-snap-line--${kind}`;
        line.style.top = `${topMinutes}px`;
        blocksEl.appendChild(line);
        blocksEl.appendChild(ghost);
    }

    _clearSlotGhost(scope) {
        const root = scope || this.container;
        if (!root) return;
        root.querySelectorAll('.time-slot-ghost, .time-slot-snap-line').forEach(n => n.remove());
    }

    _setBlockTimeBadge(el, text) {
        if (!el) return;
        let badge = el.querySelector('.time-live-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'time-live-badge';
            el.appendChild(badge);
        }
        badge.textContent = text;
    }

    _clearBlockTimeBadge(el) {
        if (!el) return;
        el.querySelectorAll('.time-live-badge').forEach(n => n.remove());
    }

    _renderSelectPreview() {
        if (!this._selectState || !this._selectState.blocksEl) return;
        const top = Math.min(this._selectState.startMinutes, this._selectState.endMinutes);
        const height = Math.abs(this._selectState.endMinutes - this._selectState.startMinutes);
        const label = this._formatMinutesRange(top, top + Math.max(this.snapMinutes, height));
        this._showSlotGhost(this._selectState.blocksEl, top, Math.max(this.snapMinutes, height), label, 'select');
    }

    _clearSelectPreview() {
        this._clearSlotGhost();
    }

    openTimeEntryCreateModal(start, end) {
        const modal = document.getElementById('timeEntryCreateModal');
        const startInput = document.getElementById('teCreateStart');
        const endInput = document.getElementById('teCreateEnd');
        if (!modal || !startInput || !endInput) return;
        startInput.value = this.formatLocalDateTimeInput(start);
        endInput.value = this.formatLocalDateTimeInput(end);
        modal.style.display = 'flex';
        modal.classList.add('show');
    }

    closeTimeEntryCreateModal() {
        const modal = document.getElementById('timeEntryCreateModal');
        if (!modal) return;
        modal.style.display = 'none';
        modal.classList.remove('show');
    }

    async createTimeEntryFromModal() {
        const projectId = document.getElementById('teCreateProject')?.value;
        const start = document.getElementById('teCreateStart')?.value;
        const end = document.getElementById('teCreateEnd')?.value;
        const notes = (document.getElementById('teCreateNotes')?.value || '').trim() || null;
        const billable = !!document.getElementById('teCreateBillable')?.checked;
        if (!projectId) {
            ttAlert('Please select a project');
            return;
        }
        if (!start || !end) {
            ttAlert('Start and end are required');
            return;
        }
        try {
            const resp = await fetch(this.createEntryUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    project_id: parseInt(projectId, 10),
                    start_time: start,
                    end_time: end,
                    notes,
                    billable
                })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'Failed to create entry');
            }
            this.closeTimeEntryCreateModal();
            this.loadEvents();
        } catch (err) {
            console.error(err);
            ttAlert(err.message || 'Failed to create entry');
        }
    }

    async updateTimeEntryTimes(entryId, start, end) {
        try {
            const resp = await fetch(`${this.updateEntryUrl}${entryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    start_time: start.toISOString(),
                    end_time: end.toISOString()
                })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || !data.success) {
                throw new Error(data.error || 'Failed to update entry');
            }
        } catch (err) {
            console.error(err);
            ttAlert(err.message || 'Failed to update time entry');
        }
    }

    async postMoveOrResize(kind, eventId, body) {
        const base = kind === 'move' ? this.moveEventUrl : this.resizeEventUrl;
        if (!base) return;
        const idNum = typeof eventId === 'number' ? eventId : parseInt(String(eventId), 10);
        if (!Number.isInteger(idNum) || idNum <= 0) {
            console.error('Calendar move/resize rejected: invalid event id');
            return;
        }
        // Template strips /0 from .../events/0/move → .../events/move; restore id before action
        const action = kind === 'move' ? 'move' : 'resize';
        let path;
        try {
            const baseUrl = new URL(base, window.location.origin);
            if (baseUrl.origin !== window.location.origin) {
                console.error('Calendar move/resize rejected: cross-origin base URL');
                return;
            }
            let pathname = baseUrl.pathname.replace(/\/$/, '');
            if (pathname.endsWith(`/${action}`)) {
                pathname = pathname.replace(new RegExp(`/${action}$`), `/${idNum}/${action}`);
            } else {
                pathname = `${pathname}/${idNum}/${action}`;
            }
            baseUrl.pathname = pathname;
            path = baseUrl.href;
            if (new URL(path).origin !== window.location.origin) {
                console.error('Calendar move/resize rejected: non-same-origin final URL');
                return;
            }
        } catch (e) {
            console.error('Calendar move/resize URL build failed', e);
            return;
        }
        try {
            const resp = await fetch(path, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(body)
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                console.error('Calendar move/resize failed', data);
                ttAlert(data.error || 'Failed to update event');
            }
        } catch (err) {
            console.error(err);
            ttAlert('Failed to update event');
        }
    }

    _eventDragAttrs(event) {
        if (!event || !event.id || !event.start) return 'data-type="event"';
        const start = event.start;
        const end = event.end || '';
        return `draggable="true" data-id="${event.id}" data-type="event" data-start="${start}" data-end="${end}"`;
    }

    _timeEntryDragAttrs(entry) {
        if (!entry || !entry.id || !entry.start) return 'data-type="time_entry"';
        const start = entry.start;
        const end = entry.end || '';
        return `draggable="true" data-id="${entry.id}" data-type="time_entry" data-start="${start}" data-end="${end}"`;
    }

    setupEventListeners() {
        // View navigation
        document.getElementById('todayBtn')?.addEventListener('click', () => {
            this.currentDate = new Date();
            this.loadEvents();
            this.updateViewLinks();
        });

        document.getElementById('prevBtn')?.addEventListener('click', () => {
            this.navigatePrevious();
        });

        document.getElementById('nextBtn')?.addEventListener('click', () => {
            this.navigateNext();
        });

        // Filters
        document.getElementById('showEvents')?.addEventListener('change', (e) => {
            this.showEvents = e.target.checked;
            this.render();
        });

        document.getElementById('showTasks')?.addEventListener('change', (e) => {
            this.showTasks = e.target.checked;
            this.render();
        });

        document.getElementById('showTimeEntries')?.addEventListener('change', (e) => {
            this.showTimeEntries = e.target.checked;
            this.render();
        });

        document.getElementById('showHolidays')?.addEventListener('change', (e) => {
            this.showHolidays = e.target.checked;
            this.render();
        });

        document.getElementById('showTimeOff')?.addEventListener('change', (e) => {
            this.showTimeOff = e.target.checked;
            this.render();
        });

        // Save calendar colors
        document.getElementById('saveCalendarColorsBtn')?.addEventListener('click', () => {
            this.saveCalendarColors();
        });

        // Modal close
        document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.getAttribute('data-modal');
                if (targetId === 'timeEntryCreateModal') {
                    this.closeTimeEntryCreateModal();
                    return;
                }
                const eventModal = document.getElementById('eventModal');
                if (eventModal) {
                    eventModal.style.display = 'none';
                    eventModal.classList.remove('show');
                }
                if (targetId) {
                    const other = document.getElementById(targetId);
                    if (other) {
                        other.style.display = 'none';
                        other.classList.remove('show');
                    }
                }
            });
        });

        document.getElementById('teCreateSubmit')?.addEventListener('click', () => {
            this.createTimeEntryFromModal();
        });
    }

    navigatePrevious() {
        switch (this.viewType) {
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() - 1);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() - 7);
                break;
            case 'month':
                this.currentDate.setMonth(this.currentDate.getMonth() - 1);
                break;
        }
        this.loadEvents();
        this.updateViewLinks();
    }

    navigateNext() {
        switch (this.viewType) {
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() + 1);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() + 7);
                break;
            case 'month':
                this.currentDate.setMonth(this.currentDate.getMonth() + 1);
                break;
        }
        this.loadEvents();
        this.updateViewLinks();
    }

    async loadEvents() {
        const { start, end } = this.getDateRange();

        try {
            const url = new URL(this.apiUrl, window.location.origin);
            url.searchParams.append('start', start.toISOString());
            url.searchParams.append('end', end.toISOString());
            url.searchParams.append('include_tasks', 'true');
            url.searchParams.append('include_time_entries', 'true');

            const response = await fetch(url);
            const data = await response.json();

            // Build unified lists from calendar API (events, tasks, time_entries are separate).
            // If API returns merged list (only data.events with item_type), split by item_type.
            const rawEvents = data.events || [];
            const rawTasks = data.tasks || [];
            const rawTimeEntries = data.time_entries || [];
            const typeColors = data.typeColors || (window.calendarData && window.calendarData.typeColors) || { event: '#3b82f6', task: '#f59e0b', time_entry: '#10b981' };

            const getItemType = (e) => (e.extendedProps && e.extendedProps.item_type) || e.type || 'event';
            let eventsForDisplay = rawEvents;
            let tasksForDisplay = rawTasks;
            let timeEntriesForDisplay = rawTimeEntries;
            if (rawTimeEntries.length === 0 && rawTasks.length === 0 && rawEvents.length > 0) {
                // Merged response: split by item_type so time entries show as Time Entry category
                eventsForDisplay = rawEvents.filter(e => getItemType(e) === 'event');
                tasksForDisplay = rawEvents.filter(e => getItemType(e) === 'task');
                timeEntriesForDisplay = rawEvents.filter(e => getItemType(e) === 'time_entry');
            }
            const holidaysFromMerged = rawEvents.filter(e => getItemType(e) === 'holiday');
            const timeOffFromMerged = rawEvents.filter(e => getItemType(e) === 'time_off');

            this.events = eventsForDisplay.map(e => ({
                ...e,
                color: e.color != null ? e.color : typeColors.event,
                extendedProps: { ...(e.extendedProps || {}), ...e, item_type: (e.extendedProps && e.extendedProps.item_type) || 'event' }
            }));
            this.tasks = tasksForDisplay.map(t => {
                const start = t.dueDate != null ? t.dueDate : t.start;
                const end = t.dueDate != null ? t.dueDate : t.end;
                return {
                    id: t.id,
                    title: t.title,
                    start: start,
                    end: end,
                    color: t.color != null ? t.color : typeColors.task,
                    extendedProps: { ...(t.extendedProps || {}), ...t, item_type: 'task' }
                };
            });
            this.timeEntries = timeEntriesForDisplay.map(e => ({
                ...e,
                color: e.color != null ? e.color : typeColors.time_entry,
                extendedProps: { ...(e.extendedProps || {}), ...e, item_type: (e.extendedProps && e.extendedProps.item_type) || 'time_entry' }
            }));
            this.holidays = (data.holidays?.length ? data.holidays : holidaysFromMerged).map(h => ({
                ...h,
                color: h.color || typeColors.holiday || '#9333ea',
                extendedProps: { ...(h.extendedProps || {}), ...h, item_type: 'holiday' }
            }));
            this.timeOff = (data.time_off?.length ? data.time_off : timeOffFromMerged).map(t => ({
                ...t,
                color: t.color || typeColors.time_off || '#ec4899',
                extendedProps: { ...(t.extendedProps || {}), ...t, item_type: 'time_off' }
            }));

            this.render();
            // Update color inputs and legend from API typeColors if present
            if (data.typeColors) {
                const eventsInput = document.getElementById('calendarColorEvents');
                const tasksInput = document.getElementById('calendarColorTasks');
                const entriesInput = document.getElementById('calendarColorTimeEntries');
                if (eventsInput) eventsInput.value = data.typeColors.event || eventsInput.value;
                if (tasksInput) tasksInput.value = data.typeColors.task || tasksInput.value;
                if (entriesInput) entriesInput.value = data.typeColors.time_entry || entriesInput.value;
            }
        } catch (error) {
            console.error('Error loading events:', error);
            this.container.innerHTML = '<div class="text-center text-red-500 py-12">Error loading calendar data</div>';
        }
    }

    async saveCalendarColors() {
        const prefsUrl = window.calendarData?.preferencesUrl;
        const csrfToken = window.calendarData?.csrfToken;
        if (!prefsUrl || !csrfToken) return;
        const eventsInput = document.getElementById('calendarColorEvents');
        const tasksInput = document.getElementById('calendarColorTasks');
        const entriesInput = document.getElementById('calendarColorTimeEntries');
        const payload = {
            calendar_color_events: eventsInput?.value || null,
            calendar_color_tasks: tasksInput?.value || null,
            calendar_color_time_entries: entriesInput?.value || null
        };
        try {
            const resp = await fetch(prefsUrl, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (resp.ok && data.success) {
                this.loadEvents();
            } else {
                ttAlert(data.error || 'Failed to save calendar colors');
            }
        } catch (e) {
            console.error('Save calendar colors failed', e);
            ttAlert('Failed to save calendar colors');
        }
    }

    getDateRange() {
        let start, end;

        switch (this.viewType) {
            case 'day':
                start = new Date(this.currentDate);
                start.setHours(0, 0, 0, 0);
                end = new Date(this.currentDate);
                end.setHours(23, 59, 59, 999);
                break;

            case 'week':
                const day = this.currentDate.getDay();
                const diff = this.currentDate.getDate() - day + (day === 0 ? -6 : 1); // Monday as start
                start = new Date(this.currentDate);
                start.setDate(diff);
                start.setHours(0, 0, 0, 0);
                end = new Date(start);
                end.setDate(start.getDate() + 6);
                end.setHours(23, 59, 59, 999);
                break;

            case 'month':
                start = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
                end = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0, 23, 59, 59, 999);
                break;
        }

        return { start, end };
    }

    updateViewLinks() {
        const viewUrl = window.calendarData?.viewUrl;
        if (!viewUrl) return;
        const y = this.currentDate.getFullYear();
        const m = String(this.currentDate.getMonth() + 1).padStart(2, '0');
        const d = String(this.currentDate.getDate()).padStart(2, '0');
        const dateStr = `${y}-${m}-${d}`;
        ['day', 'week', 'month'].forEach(view => {
            const el = document.querySelector(`[data-view="${view}"]`);
            if (el) el.href = `${viewUrl}?view=${view}&date=${dateStr}`;
        });
    }

    render() {
        this.updateTitle();

        switch (this.viewType) {
            case 'day':
                this.renderDayView();
                break;
            case 'week':
                this.renderWeekView();
                break;
            case 'month':
                this.renderMonthView();
                break;
        }
    }

    updateTitle() {
        const titleEl = document.getElementById('calendarTitle');
        if (!titleEl) return;

        const options = { month: 'long', year: 'numeric' };

        switch (this.viewType) {
            case 'day':
                titleEl.textContent = this.currentDate.toLocaleDateString(undefined, {
                    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
                });
                break;
            case 'week':
                const { start, end } = this.getDateRange();
                titleEl.textContent = `${start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
                break;
            case 'month':
                titleEl.textContent = this.currentDate.toLocaleDateString(undefined, options);
                break;
        }
    }

    renderDayView() {
        const html = `
            <div class="calendar-day-view">
                <div class="time-slots">
                    ${this.renderTimeSlots()}
                </div>
                <div class="events-column">
                    ${this.renderDayEvents()}
                </div>
            </div>
        `;
        this.container.innerHTML = html;
    }

    renderTimeSlots() {
        const slots = [];
        for (let hour = 0; hour < 24; hour++) {
            let time;
            if (window.userPrefs && window.userPrefs.timeFormat === '12h') {
                const ampm = hour >= 12 ? 'PM' : 'AM';
                const h12 = hour % 12 || 12;
                time = `${h12}:00 ${ampm}`;
            } else {
                time = `${hour.toString().padStart(2, '0')}:00`;
            }
            slots.push(`<div class="time-slot" data-hour="${hour}">${time}</div>`);
        }
        return slots.join('');
    }

    /**
     * Assign column indices to items so overlapping items (by time range) get different columns.
     * Items must have startMs and endMs. Mutates and returns items with .column and .totalColumns.
     */
    assignOverlapColumnsByTime(items) {
        if (items.length === 0) return items;
        const sorted = items.slice().sort((a, b) => a.startMs - b.startMs);
        const maxCols = 8;
        const columnsEnd = [];
        sorted.forEach(item => {
            const start = item.startMs;
            const end = item.endMs;
            let col = 0;
            while (col < columnsEnd.length && columnsEnd[col] > start) col++;
            if (col >= maxCols) col = maxCols - 1;
            item.column = col;
            if (col === columnsEnd.length) columnsEnd.push(end);
            else columnsEnd[col] = end;
        });
        const totalColumns = Math.min(columnsEnd.length, maxCols) || 1;
        sorted.forEach(item => { item.totalColumns = totalColumns; });
        return sorted;
    }

    /**
     * Assign column indices to items that have top/height (%). Overlapping vertical ranges get different columns.
     */
    assignOverlapColumnsByPosition(items) {
        if (items.length === 0) return items;
        const sorted = items.slice().sort((a, b) => a.top - b.top);
        const maxCols = 8;
        const columnsEnd = [];
        sorted.forEach(item => {
            const start = item.top;
            const end = item.top + item.height;
            let col = 0;
            while (col < columnsEnd.length && columnsEnd[col] > start) col++;
            if (col >= maxCols) col = maxCols - 1;
            item.column = col;
            if (col === columnsEnd.length) columnsEnd.push(end);
            else columnsEnd[col] = end;
        });
        const totalColumns = Math.min(columnsEnd.length, maxCols) || 1;
        sorted.forEach(item => { item.totalColumns = totalColumns; });
        return sorted;
    }

    /** Return CSS left/width for a column (gap 1% between columns). */
    columnStyle(col, totalCols) {
        if (totalCols <= 1) return { left: '0', width: '100%' };
        const gapPct = 1;
        const widthPct = (100 - (totalCols - 1) * gapPct) / totalCols;
        const leftPct = col * (widthPct + gapPct);
        return { left: leftPct + '%', width: widthPct + '%' };
    }

    renderDayEvents() {
        const dayStart = new Date(this.currentDate);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(this.currentDate);
        dayEnd.setHours(23, 59, 59, 999);

        const timedItems = [];

        if (this.showEvents) {
            this.events.forEach(event => {
                const eventStart = new Date(event.start);
                const eventEnd = event.end ? new Date(event.end) : null;
                if (eventStart > dayEnd || (eventEnd && eventEnd < dayStart)) return;
                const effectiveStart = eventStart < dayStart ? dayStart : eventStart;
                const effectiveEnd = eventEnd ? (eventEnd > dayEnd ? dayEnd : eventEnd) : new Date(effectiveStart.getTime() + 60 * 60 * 1000);
                const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                const heightMinutes = Math.max(30, Math.min(1440 - startMinutes, durationMinutes));
                const blockType = (event.extendedProps && event.extendedProps.item_type) || 'event';
                const startTime = window.formatUserTime(effectiveStart);
                const endTimeStr = eventEnd ? window.formatUserTime(effectiveEnd) : '';
                const notesText = event.notes || (event.extendedProps && event.extendedProps.notes) || '';
                const notes = notesText ? `<br><small class="text-xs">${this.escapeHtml(notesText)}</small>` : '';
                timedItems.push({
                    type: blockType,
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    event,
                    entry: event,
                    topPosition: startMinutes,
                    heightMinutes,
                    time: startTime,
                    title: this.escapeHtml(event.title),
                    color: event.color || (blockType === 'time_entry' ? '#10b981' : '#3b82f6'),
                    startTime,
                    endTimeStr,
                    entryEnd: eventEnd || null,
                    notes
                });
            });
        }

        if (this.showTimeEntries) {
            this.timeEntries.forEach(entry => {
                const entryStart = new Date(entry.start);
                const entryEnd = entry.end ? new Date(entry.end) : null;
                const entryEndForDay = entryEnd || new Date(entryStart.getTime() + 30 * 60 * 1000);
                const effectiveStart = entryStart < dayStart ? dayStart : entryStart;
                const effectiveEnd = entryEndForDay > dayEnd ? dayEnd : entryEndForDay;
                if (effectiveStart > dayEnd || effectiveEnd < dayStart) return;
                const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                let heightMinutes;
                if (entryEnd) {
                    const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                    heightMinutes = Math.max(30, Math.min(1440 - startMinutes, durationMinutes));
                } else {
                    heightMinutes = Math.min(30, 1440 - startMinutes);
                }
                const startTime = window.formatUserTime(effectiveStart);
                const endTimeStr = entryEnd ? window.formatUserTime(effectiveEnd) : '';
                const notesText = entry.notes || entry.extendedProps?.notes || '';
                const notes = notesText ? `<br><small class="text-xs">${this.escapeHtml(notesText)}</small>` : '';
                const entryColor = entry.color || '#10b981';
                timedItems.push({
                    type: 'time_entry',
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    entry,
                    topPosition: startMinutes,
                    heightMinutes,
                    startTime,
                    endTimeStr,
                    entryEnd,
                    title: this.escapeHtml(entry.title),
                    notes,
                    color: entryColor
                });
            });
        }

        this.assignOverlapColumnsByTime(timedItems);

        let html = '<div class="day-events-container">';
        const overlayBadges = this.renderDayOverlayBadges(this.currentDate);
        if (overlayBadges) {
            html += `<div class="day-overlay-banners">${overlayBadges}</div>`;
        }

        timedItems.forEach(item => {
            const { left, width } = this.columnStyle(item.column, item.totalColumns);
            const style = `left: ${left}; width: ${width}; top: ${item.topPosition}px; height: ${item.heightMinutes}px;`;
            const detailType = item.type;
            const detailId = item.event ? item.event.id : item.entry.id;
            if (item.type === 'event') {
                html += `
                    <div class="event-card event" ${this._eventDragAttrs(item.event)}
                         style="border-left-color: ${item.color}; ${style}"
                         onclick="window.calendar.showEventDetails(${item.event.id}, '${detailType}', event)">
                        <i class="fas fa-calendar mr-2 text-blue-600 dark:text-blue-400"></i>
                        <strong>${item.title}</strong>
                        <br><small>${item.time}</small>
                        <div class="event-resize-handle" title="Resize"></div>
                    </div>
                `;
            } else if (item.type === 'time_entry') {
                const durationText = item.entryEnd != null ? `${item.startTime} - ${item.endTimeStr}` : (item.time ? `${item.time} (active)` : '');
                const notes = item.notes != null ? item.notes : '';
                const entryObj = item.entry || { id: detailId, start: item.event?.start, end: item.event?.end };
                html += `
                    <div class="event-card time_entry" ${this._timeEntryDragAttrs(entryObj)}
                         style="border-left-color: ${item.color}; ${style}"
                         onclick="window.calendar.showEventDetails(${detailId}, 'time_entry', event)">
                        ⏱ <strong>${item.title}</strong>
                        <br><small>${durationText}</small>
                        ${notes}
                        <div class="event-resize-handle" title="Resize"></div>
                    </div>
                `;
            }
        });

        if (this.showTasks) {
            this.tasks.forEach(task => {
                const taskTitle = this.escapeHtml(task.title);
                const taskColor = task.color || '#f59e0b';
                const priorityIcons = { urgent: '🔴', high: '🟠', medium: '🟡', low: '🟢' };
                const priorityIcon = priorityIcons[task.extendedProps?.priority] || '📋';
                html += `
                    <div class="event-card task" data-id="${task.id}" data-type="task" style="border-left-color: ${taskColor};" onclick="window.calendar.showEventDetails(${task.id}, 'task', event)">
                        ${priorityIcon} <strong>${taskTitle}</strong>
                        <br><small>Due: ${task.start}</small>
                        <br><small class="text-xs">Status: ${task.extendedProps?.status || 'Unknown'}</small>
                    </div>
                `;
            });
        }

        html += '</div>';
        return html;
    }

    renderWeekView() {
        const { start } = this.getDateRange();
        const days = [];
        for (let i = 0; i < 7; i++) {
            const day = new Date(start);
            day.setDate(start.getDate() + i);
            days.push(day);
        }
        const timeSlots = Array.from({ length: 24 }, (_, h) => {
            let label;
            if (window.userPrefs && window.userPrefs.timeFormat === '12h') {
                const ampm = h >= 12 ? 'PM' : 'AM';
                const h12 = h % 12 || 12;
                label = `${h12}:00 ${ampm}`;
            } else {
                label = `${h.toString().padStart(2, '0')}:00`;
            }
            return `<div class="week-time-slot">${label}</div>`;
        }).join('');
        const dayColumns = days.map(day => {
            const blocks = this.renderWeekDayBlocks(day);
            const overlayBadges = this.renderDayOverlayBadges(day);
            const overlayHtml = overlayBadges
                ? `<div class="day-overlay-banners">${overlayBadges}</div>`
                : '';
            return `<div class="week-day-column" data-date="${this.formatLocalDate(day)}">${overlayHtml}<div class="week-day-blocks">${blocks}</div></div>`;
        }).join('');
        const dayHeaders = days.map(day => {
            const isToday = this.isToday(day);
            return `<div class="week-day-header-cell ${isToday ? 'today' : ''}">${day.toLocaleDateString(undefined, { weekday: 'short' })} ${window.formatUserDate(day)}</div>`;
        }).join('');
        this.container.innerHTML = `
            <div class="calendar-week-view">
                <div class="week-view-header">
                    <div class="week-time-header"></div>
                    ${dayHeaders}
                </div>
                <div class="week-view-body">
                    <div class="week-time-column">${timeSlots}</div>
                    ${dayColumns}
                </div>
            </div>
        `;
    }

    /**
     * Render all event/time-entry blocks for one day as whole blocks (top + height in px), not per-hour.
     */
    renderWeekDayBlocks(day) {
        const dayStart = new Date(day);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(day);
        dayEnd.setHours(23, 59, 59, 999);
        const timedItems = [];
        if (this.showEvents) {
            this.events.forEach(event => {
                if (event.allDay) return;
                const eventStart = new Date(event.start);
                const eventEnd = event.end ? new Date(event.end) : null;
                if (eventStart > dayEnd || (eventEnd && eventEnd < dayStart)) return;
                const effectiveStart = eventStart < dayStart ? dayStart : eventStart;
                const effectiveEnd = eventEnd ? (eventEnd > dayEnd ? dayEnd : eventEnd) : new Date(effectiveStart.getTime() + 60 * 60 * 1000);
                const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                const heightMinutes = Math.max(30, Math.min(1440 - startMinutes, durationMinutes));
                const timeStr = window.formatUserTime(effectiveStart);
                const blockType = (event.extendedProps && event.extendedProps.item_type) || 'event';
                const endTimeStr = eventEnd ? window.formatUserTime(effectiveEnd) : '';
                const durationText = eventEnd ? `${timeStr} - ${endTimeStr}` : timeStr;
                timedItems.push({
                    type: blockType,
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    event,
                    entry: event,
                    topPosition: startMinutes,
                    heightMinutes,
                    title: this.escapeHtml(event.title),
                    color: event.color || (blockType === 'time_entry' ? '#10b981' : '#3b82f6'),
                    timeStr,
                    startTime: timeStr,
                    endTimeStr,
                    entryEnd: eventEnd
                });
            });
        }
        if (this.showTimeEntries) {
            this.timeEntries.forEach(entry => {
                const entryStart = new Date(entry.start);
                const entryEnd = entry.end ? new Date(entry.end) : null;
                const entryEndForDay = entryEnd || new Date(entryStart.getTime() + 30 * 60 * 1000);
                const effectiveStart = entryStart < dayStart ? dayStart : entryStart;
                const effectiveEnd = entryEndForDay > dayEnd ? dayEnd : entryEndForDay;
                if (effectiveStart > dayEnd || effectiveEnd < dayStart) return;
                const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                let heightMinutes;
                if (entryEnd) {
                    const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                    heightMinutes = Math.max(30, Math.min(1440 - startMinutes, durationMinutes));
                } else {
                    heightMinutes = Math.min(30, 1440 - startMinutes);
                }
                const startTime = window.formatUserTime(effectiveStart);
                const endTimeStr = entryEnd ? window.formatUserTime(effectiveEnd) : '';
                const entryColor = entry.color || '#10b981';
                timedItems.push({
                    type: 'time_entry',
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    entry,
                    topPosition: startMinutes,
                    heightMinutes,
                    title: this.escapeHtml(entry.title),
                    startTime,
                    endTimeStr,
                    entryEnd,
                    color: entryColor
                });
            });
        }
        if (this.showTasks) {
            this.tasks.forEach(task => {
                const taskDate = new Date(task.start);
                if (taskDate.toDateString() !== day.toDateString()) return;
                const dueMinutes = 9 * 60;
                const taskColor = task.color || '#f59e0b';
                timedItems.push({
                    type: 'task',
                    startMs: dayStart.getTime() + dueMinutes * 60 * 1000,
                    endMs: dayStart.getTime() + (dueMinutes + 30) * 60 * 1000,
                    task,
                    topPosition: dueMinutes,
                    heightMinutes: 30,
                    title: this.escapeHtml(task.title),
                    color: taskColor
                });
            });
        }
        this.assignOverlapColumnsByTime(timedItems);
        let html = '';
        timedItems.forEach(item => {
            const { left, width } = this.columnStyle(item.column, item.totalColumns);
            const style = `left: ${left}; width: ${width}; top: ${item.topPosition}px; height: ${item.heightMinutes}px;`;
            if (item.type === 'event') {
                html += `<div class="week-event-block event" ${this._eventDragAttrs(item.event)} style="border-left-color: ${item.color}; ${style}" onclick="window.calendar.showEventDetails(${item.event.id}, '${item.type}', event)" title="${item.title} (${item.timeStr})"><i class="fas fa-calendar mr-1"></i><strong>${item.title}</strong><br><small>${item.timeStr}</small><div class="event-resize-handle" title="Resize"></div></div>`;
            } else if (item.type === 'time_entry') {
                const durationText = (item.entryEnd != null && item.startTime != null) ? `${item.startTime} - ${item.endTimeStr}` : (item.startTime || item.timeStr || '');
                const blockId = (item.entry && item.entry.id) != null ? item.entry.id : item.event.id;
                const entryObj = item.entry || { id: blockId, start: item.entry?.start, end: item.entry?.end };
                html += `<div class="week-event-block time_entry" ${this._timeEntryDragAttrs(entryObj)} style="border-left-color: ${item.color}; ${style}" title="${item.title}" onclick="window.calendar.showEventDetails(${blockId}, 'time_entry', event)"><i class="fas fa-clock mr-1"></i><strong>${item.title}</strong><br><small>${durationText}</small><div class="event-resize-handle" title="Resize"></div></div>`;
            } else {
                html += `<div class="week-event-block task" data-id="${item.task.id}" data-type="task" style="border-left-color: ${item.color}; ${style}" onclick="window.calendar.showEventDetails(${item.task.id}, 'task', event); event.stopPropagation();" title="${item.title}">\uD83D\uDCCB ${item.title}</div>`;
            }
        });
        return html;
    }

    renderMonthView() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - (startDate.getDay() === 0 ? 6 : startDate.getDay() - 1));

        let html = '<div class="calendar-month-view"><table class="month-table"><thead><tr>';
        const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        weekdays.forEach(day => {
            html += `<th>${day}</th>`;
        });
        html += '</tr></thead><tbody>';

        const currentDate = new Date(startDate);
        for (let week = 0; week < 6; week++) {
            html += '<tr>';
            for (let day = 0; day < 7; day++) {
                const isCurrentMonth = currentDate.getMonth() === month;
                const isToday = this.isToday(currentDate);
                html += `<td class="month-cell ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}" data-date="${this.formatLocalDate(currentDate)}">`;
                html += `<div class="date-number">${currentDate.getDate()}</div>`;
                html += this.renderMonthCellEvents(currentDate);
                html += '</td>';
                currentDate.setDate(currentDate.getDate() + 1);
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        this.container.innerHTML = html;

        // Add click handlers for cells
        this.container.querySelectorAll('.month-cell').forEach(cell => {
            cell.addEventListener('click', (e) => {
                if (e.target.classList.contains('month-cell') || e.target.classList.contains('date-number')) {
                    const date = new Date(cell.dataset.date);
                    window.location.href = `${window.calendarData.newEventUrl}?date=${this.formatLocalDate(date)}`;
                }
            });
        });
    }

    renderMonthCellEvents(day) {
        const dayStart = new Date(day);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(day);
        dayEnd.setHours(23, 59, 59, 999);
        const dayKey = this.formatLocalDate(day);

        let html = '<div class="month-events">';
        let count = 0;
        const maxDisplay = 3;

        if (this.showHolidays) {
            this.holidays.forEach(item => {
                const itemDay = (item.start || '').slice(0, 10);
                if (itemDay === dayKey) {
                    html += `<div class="event-badge holiday-badge" style="background-color: ${item.color}22; border-left: 3px solid ${item.color}; color: inherit;" title="${this.escapeHtml(item.title)}">🏖 ${this.escapeHtml(item.title)}</div>`;
                }
            });
        }
        if (this.showTimeOff) {
            this.timeOff.forEach(item => {
                const itemDay = (item.start || '').slice(0, 10);
                if (itemDay === dayKey) {
                    html += `<div class="event-badge time-off-badge" style="background-color: ${item.color}22; border-left: 3px solid ${item.color}; color: inherit;" title="${this.escapeHtml(item.title)}">🌴 ${this.escapeHtml(item.title)}</div>`;
                }
            });
        }

        // Events (and any time_entry items that ended up in this.events - use item_type for badge and modal)
        if (this.showEvents) {
            this.events.forEach(event => {
                const eventStart = new Date(event.start);
                if (eventStart >= dayStart && eventStart <= dayEnd) {
                    if (count < maxDisplay) {
                        const eventTitle = this.escapeHtml(event.title);
                        const blockType = (event.extendedProps && event.extendedProps.item_type) || 'event';
                        const eventColor = event.color || (blockType === 'time_entry' ? '#10b981' : '#3b82f6');
                        const badgeIcon = blockType === 'time_entry' ? '⏱' : '📅';
                        const badgeClass = blockType === 'time_entry' ? 'event-badge time-entry-badge' : 'event-badge';
                        html += `<div class="${badgeClass}" ${blockType === 'event' ? this._eventDragAttrs(event) : `data-id="${event.id}" data-type="${blockType}"`} style="background-color: ${eventColor}" onclick="window.calendar.showEventDetails(${event.id}, '${blockType}', event); event.stopPropagation();" title="${eventTitle}">${badgeIcon} ${eventTitle}</div>`;
                    }
                    count++;
                }
            });
        }

        // Tasks
        if (this.showTasks) {
            this.tasks.forEach(task => {
                const taskDate = new Date(task.start);
                if (taskDate.toDateString() === day.toDateString()) {
                    if (count < maxDisplay) {
                        const taskTitle = this.escapeHtml(task.title);
                        const taskColor = task.color || '#f59e0b';
                        html += `<div class="event-badge task-badge" style="background-color: ${taskColor}" onclick="window.calendar.showEventDetails(${task.id}, 'task', event); event.stopPropagation();" title="${taskTitle}">📋 ${taskTitle}</div>`;
                    }
                    count++;
                }
            });
        }

        // Time entries
        if (this.showTimeEntries) {
            this.timeEntries.forEach(entry => {
                const entryStart = new Date(entry.start);
                if (entryStart >= dayStart && entryStart <= dayEnd) {
                    if (count < maxDisplay) {
                        const entryTitle = this.escapeHtml(entry.title);
                        const entryColor = entry.color || '#10b981';
                        html += `<div class="event-badge time-entry-badge" style="background-color: ${entryColor}" onclick="window.calendar.showEventDetails(${entry.id}, 'time_entry', event); event.stopPropagation();" title="${entryTitle}">⏱ ${entryTitle}</div>`;
                    }
                    count++;
                }
            });
        }

        if (count > maxDisplay) {
            html += `<div class="event-badge-more">+${count - maxDisplay} more</div>`;
        }

        html += '</div>';
        return html;
    }

    isToday(date) {
        const today = new Date();
        return date.getDate() === today.getDate() &&
               date.getMonth() === today.getMonth() &&
               date.getFullYear() === today.getFullYear();
    }

    showEventDetails(id, type, clickEvent) {
        const modal = document.getElementById('eventModal');
        const modalTitle = document.querySelector('#eventModal .modal-title');
        const bodyEl = document.getElementById('eventDetails');
        const goToBtn = document.getElementById('eventModalGoToBtn');
        const editEventBtn = document.getElementById('editEventBtn');
        const deleteEventBtn = document.getElementById('deleteEventBtn');
        if (!modal || !bodyEl) return;

        const idStr = String(id);
        let item = null;
        if (type === 'event') {
            item = this.events.find(e => String(e.id) === idStr && (e.extendedProps && e.extendedProps.item_type) === 'event');
        } else if (type === 'task') {
            item = this.tasks.find(t => String(t.id) === idStr) ||
                this.events.find(e => String(e.id) === idStr && (e.extendedProps && e.extendedProps.item_type) === 'task');
        } else if (type === 'time_entry') {
            item = this.timeEntries.find(e => String(e.id) === idStr) ||
                this.events.find(e => String(e.id) === idStr && (e.extendedProps && e.extendedProps.item_type) === 'time_entry') ||
                this.events.find(e => String(e.id) === idStr && (e.extendedProps && (e.extendedProps.type === 'time_entry' || e.extendedProps.duration_hours != null || e.extendedProps.source != null))) ||
                this.events.find(e => String(e.id) === idStr);
        }
        if (!item) {
            bodyEl.innerHTML = '<p class="text-muted">Details not available.</p>';
            if (modalTitle) modalTitle.textContent = type === 'event' ? 'Event' : type === 'task' ? 'Task' : 'Time Entry';
            let detailUrl = type === 'event' ? `/calendar/event/${id}` : type === 'task' ? `/tasks/${id}` : `/timer/edit/${id}`;
            if (goToBtn) { goToBtn.href = detailUrl; goToBtn.style.display = ''; }
            if (editEventBtn) { editEventBtn.href = detailUrl; editEventBtn.style.display = ''; }
            if (deleteEventBtn) deleteEventBtn.style.display = 'none';
            modal.style.display = 'block';
            modal.classList.add('show');
            this._positionModalNearClick(modal, clickEvent);
            return;
        }

        const props = item.extendedProps || {};
        const formatDate = (d) => {
            if (!d) return '—';
            const dt = new Date(d);
            return window.formatUserDateTime(dt);
        };
        // Use effective type for link: registered time (time entries) must go to /timer/edit/, not /calendar/event/
        let effectiveType = props.item_type || props.type || type;
        const looksLikeTimeEntry = props.duration_hours != null || props.source != null || (props.projectId != null && item.start && item.end && !item.allDay);
        if (effectiveType === 'event' && (props.item_type === 'time_entry' || props.type === 'time_entry' || looksLikeTimeEntry)) {
            effectiveType = 'time_entry';
        }
        if (effectiveType !== 'task' && effectiveType !== 'event' && looksLikeTimeEntry) {
            effectiveType = 'time_entry';
        }

        let detailUrl = '#';
        let titleLabel = 'Event';
        if (effectiveType === 'event') {
            detailUrl = `/calendar/event/${item.id}`;
            titleLabel = 'Event Details';
        } else if (effectiveType === 'task') {
            detailUrl = `/tasks/${item.id}`;
            titleLabel = 'Task';
        } else {
            detailUrl = `/timer/edit/${item.id}`;
            titleLabel = 'Time Entry Details';
        }

        if (modalTitle) modalTitle.textContent = titleLabel;
        if (goToBtn) { goToBtn.href = detailUrl; goToBtn.style.display = ''; }
        if (editEventBtn) { editEventBtn.href = detailUrl; editEventBtn.innerHTML = '<i class="fas fa-external-link-alt mr-2"></i>Go to all details'; editEventBtn.style.display = ''; }
        if (deleteEventBtn) deleteEventBtn.style.display = 'none';

        if (type === 'task') {
            const dueStr = item.start ? formatDate(item.start) : (props.dueDate || '—');
            bodyEl.innerHTML = `
                <div class="event-detail-row"><div class="event-detail-label">Title</div><div class="event-detail-value">${this.escapeHtml(item.title || props.title || '')}</div></div>
                <div class="event-detail-row"><div class="event-detail-label">Due</div><div class="event-detail-value">${dueStr}</div></div>
                ${props.status ? `<div class="event-detail-row"><div class="event-detail-label">Status</div><div class="event-detail-value">${this.escapeHtml(props.status)}</div></div>` : ''}
                ${props.project_name ? `<div class="event-detail-row"><div class="event-detail-label">Project</div><div class="event-detail-value">${this.escapeHtml(props.project_name)}</div></div>` : ''}
            `;
        } else {
            const startStr = item.start ? formatDate(item.start) : '—';
            const endStr = item.end ? formatDate(item.end) : '—';
            const duration = (props.duration_hours != null) ? Number(props.duration_hours).toFixed(2) : '—';
            bodyEl.innerHTML = `
                <div class="event-detail-row"><div class="event-detail-label">Project</div><div class="event-detail-value">${this.escapeHtml(props.project_name || '')}</div></div>
                ${props.task_name ? `<div class="event-detail-row"><div class="event-detail-label">Task</div><div class="event-detail-value">${this.escapeHtml(props.task_name)}</div></div>` : ''}
                <div class="event-detail-row"><div class="event-detail-label">Start</div><div class="event-detail-value">${startStr}</div></div>
                <div class="event-detail-row"><div class="event-detail-label">End</div><div class="event-detail-value">${endStr}</div></div>
                <div class="event-detail-row"><div class="event-detail-label">Duration</div><div class="event-detail-value">${duration} hours</div></div>
                ${props.notes ? `<div class="event-detail-row"><div class="event-detail-label">Notes</div><div class="event-detail-value">${this.escapeHtml(props.notes)}</div></div>` : ''}
                ${props.tags ? `<div class="event-detail-row"><div class="event-detail-label">Tags</div><div class="event-detail-value">${this.escapeHtml(props.tags)}</div></div>` : ''}
            `;
        }

        modal.style.display = 'block';
        modal.classList.add('show');
        this._positionModalNearClick(modal, clickEvent);
    }

    _positionModalNearClick(modal, clickEvent) {
        const contentEl = modal && modal.querySelector('.modal-dialog');
        if (!contentEl) return;
        if (!clickEvent || !clickEvent.clientX) {
            contentEl.style.position = '';
            contentEl.style.left = '';
            contentEl.style.top = '';
            return;
        }
        const pad = 16;
        const x = clickEvent.clientX;
        const y = clickEvent.clientY;
        contentEl.style.position = 'fixed';
        requestAnimationFrame(() => {
            const rect = contentEl.getBoundingClientRect();
            let left = x + pad;
            let top = y + pad;
            if (left + rect.width > window.innerWidth - pad) left = window.innerWidth - rect.width - pad;
            if (top + rect.height > window.innerHeight - pad) top = window.innerHeight - rect.height - pad;
            if (left < pad) left = pad;
            if (top < pad) top = pad;
            contentEl.style.left = left + 'px';
            contentEl.style.top = top + 'px';
        });
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text ? text.replace(/[&<>"']/g, m => map[m]) : '';
    }
}

// Initialize calendar when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.calendarData !== 'undefined') {
        window.calendar = new Calendar({
            viewType: window.calendarData.viewType,
            currentDate: window.calendarData.currentDate,
            apiUrl: window.calendarData.apiUrl,
            moveEventUrl: window.calendarData.moveEventUrl,
            resizeEventUrl: window.calendarData.resizeEventUrl,
            updateEntryUrl: window.calendarData.updateEntryUrl,
            createEntryUrl: window.calendarData.createEntryUrl,
            snapMinutes: window.calendarData.snapMinutes,
            csrfToken: window.calendarData.csrfToken
        });

    }
});
