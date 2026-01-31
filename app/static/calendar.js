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
        this.events = [];
        this.tasks = [];
        this.timeEntries = [];
        
        // Filters
        this.showEvents = true;
        this.showTasks = true;
        this.showTimeEntries = true;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadEvents();
        this.updateViewLinks();
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
        
        // Save calendar colors
        document.getElementById('saveCalendarColorsBtn')?.addEventListener('click', () => {
            this.saveCalendarColors();
        });
        
        // Modal close
        document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const eventModal = document.getElementById('eventModal');
                if (eventModal) {
                    eventModal.style.display = 'none';
                    eventModal.classList.remove('show');
                }
            });
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
            // Map to common shape with start/end and extendedProps.item_type for render.
            const rawEvents = data.events || [];
            const rawTasks = data.tasks || [];
            const rawTimeEntries = data.time_entries || [];
            const typeColors = data.typeColors || (window.calendarData && window.calendarData.typeColors) || { event: '#3b82f6', task: '#f59e0b', time_entry: '#10b981' };
            this.events = rawEvents.map(e => ({
                ...e,
                color: e.color != null ? e.color : typeColors.event,
                extendedProps: { ...(e.extendedProps || {}), ...e, item_type: (e.extendedProps && e.extendedProps.item_type) || 'event' }
            }));
            this.tasks = rawTasks.map(t => ({
                id: t.id,
                title: t.title,
                start: t.dueDate,
                end: t.dueDate,
                color: t.color != null ? t.color : typeColors.task,
                extendedProps: { ...t, item_type: 'task' }
            }));
            this.timeEntries = rawTimeEntries.map(e => ({
                ...e,
                color: e.color != null ? e.color : typeColors.time_entry,
                extendedProps: { ...(e.extendedProps || {}), ...e, item_type: (e.extendedProps && e.extendedProps.item_type) || 'time_entry' }
            }));
            
            console.log('API Response:', {
                total: this.events.length + this.tasks.length + this.timeEntries.length,
                events: this.events.length,
                tasks: this.tasks.length,
                time_entries: this.timeEntries.length,
                summary: data.summary,
                rawData: data
            });
            
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
                alert(data.error || 'Failed to save calendar colors');
            }
        } catch (e) {
            console.error('Save calendar colors failed', e);
            alert('Failed to save calendar colors');
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
        
        console.log('Calendar rendering:', {
            viewType: this.viewType,
            eventsCount: this.events.length,
            tasksCount: this.tasks.length,
            timeEntriesCount: this.timeEntries.length,
            showEvents: this.showEvents,
            showTasks: this.showTasks,
            showTimeEntries: this.showTimeEntries
        });
        
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
            const time = `${hour.toString().padStart(2, '0')}:00`;
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
                timedItems.push({
                    type: 'event',
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    event,
                    topPosition: startMinutes,
                    heightMinutes,
                    time: effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
                    title: this.escapeHtml(event.title),
                    color: event.color || '#3b82f6'
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
                const startTime = effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                const endTimeStr = entryEnd ? effectiveEnd.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '';
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
        
        timedItems.forEach(item => {
            const { left, width } = this.columnStyle(item.column, item.totalColumns);
            const style = `left: ${left}; width: ${width}; top: ${item.topPosition}px; height: ${item.heightMinutes}px;`;
            if (item.type === 'event') {
                html += `
                    <div class="event-card event" data-id="${item.event.id}" data-type="event"
                         style="border-left-color: ${item.color}; ${style}"
                         onclick="window.calendar.showEventDetails(${item.event.id}, 'event', event)">
                        <i class="fas fa-calendar mr-2 text-blue-600 dark:text-blue-400"></i>
                        <strong>${item.title}</strong>
                        <br><small>${item.time}</small>
                    </div>
                `;
            } else {
                const durationText = item.entryEnd ? `${item.startTime} - ${item.endTimeStr}` : `${item.startTime} (active)`;
                html += `
                    <div class="event-card time_entry" data-id="${item.entry.id}" data-type="time_entry"
                         style="border-left-color: ${item.color}; ${style}"
                         onclick="window.calendar.showEventDetails(${item.entry.id}, 'time_entry', event)">
                        ⏱ <strong>${item.title}</strong>
                        <br><small>${durationText}</small>
                        ${item.notes}
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
        const timeSlots = Array.from({ length: 24 }, (_, h) => `<div class="week-time-slot">${h.toString().padStart(2, '0')}:00</div>`).join('');
        const dayColumns = days.map(day => {
            const blocks = this.renderWeekDayBlocks(day);
            return `<div class="week-day-column" data-date="${day.toISOString().split('T')[0]}"><div class="week-day-blocks">${blocks}</div></div>`;
        }).join('');
        const dayHeaders = days.map(day => {
            const isToday = this.isToday(day);
            return `<div class="week-day-header-cell ${isToday ? 'today' : ''}">${day.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</div>`;
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
                const timeStr = effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                timedItems.push({
                    type: 'event',
                    startMs: effectiveStart.getTime(),
                    endMs: effectiveEnd.getTime(),
                    event,
                    topPosition: startMinutes,
                    heightMinutes,
                    title: this.escapeHtml(event.title),
                    color: event.color || '#3b82f6',
                    timeStr
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
                const startTime = effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                const endTimeStr = entryEnd ? effectiveEnd.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '';
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
                html += `<div class="week-event-block event" data-id="${item.event.id}" data-type="event" style="border-left-color: ${item.color}; ${style}" onclick="window.calendar.showEventDetails(${item.event.id}, 'event', event)" title="${item.title} (${item.timeStr})"><i class="fas fa-calendar mr-1"></i><strong>${item.title}</strong><br><small>${item.timeStr}</small></div>`;
            } else if (item.type === 'time_entry') {
                const durationText = item.entryEnd ? `${item.startTime} - ${item.endTimeStr}` : `${item.startTime} (active)`;
                html += `<div class="week-event-block time_entry" data-id="${item.entry.id}" data-type="time_entry" style="border-left-color: ${item.color}; ${style}" title="${item.title}" onclick="window.calendar.showEventDetails(${item.entry.id}, 'time_entry', event)"><i class="fas fa-clock mr-1"></i><strong>${item.title}</strong><br><small>${durationText}</small></div>`;
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
                html += `<td class="month-cell ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}" data-date="${currentDate.toISOString()}">`;
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
                    window.location.href = `${window.calendarData.newEventUrl}?date=${date.toISOString().split('T')[0]}`;
                }
            });
        });
    }
    
    renderMonthCellEvents(day) {
        const dayStart = new Date(day);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(day);
        dayEnd.setHours(23, 59, 59, 999);
        
        let html = '<div class="month-events">';
        let count = 0;
        const maxDisplay = 3;
        
        // Events
        if (this.showEvents) {
            this.events.forEach(event => {
                const eventStart = new Date(event.start);
                if (eventStart >= dayStart && eventStart <= dayEnd) {
                    if (count < maxDisplay) {
                        const eventTitle = this.escapeHtml(event.title);
                        const eventColor = event.color || '#3b82f6';
                        html += `<div class="event-badge" style="background-color: ${eventColor}" onclick="window.calendar.showEventDetails(${event.id}, 'event', event); event.stopPropagation();" title="${eventTitle}">📅 ${eventTitle}</div>`;
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
            return dt.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
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
            apiUrl: window.calendarData.apiUrl
        });
        
    }
});

