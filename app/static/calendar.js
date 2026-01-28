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
    }
    
    setupEventListeners() {
        // View navigation
        document.getElementById('todayBtn')?.addEventListener('click', () => {
            this.currentDate = new Date();
            this.loadEvents();
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
        
        // Modal close
        document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('eventModal').style.display = 'none';
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
            this.events = rawEvents.map(e => ({
                ...e,
                extendedProps: { ...e, item_type: 'event' }
            }));
            this.tasks = rawTasks.map(t => ({
                id: t.id,
                title: t.title,
                start: t.dueDate,
                end: t.dueDate,
                extendedProps: { ...t, item_type: 'task' }
            }));
            this.timeEntries = rawTimeEntries.map(e => ({
                ...e,
                extendedProps: { ...e, item_type: 'time_entry' }
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
        } catch (error) {
            console.error('Error loading events:', error);
            this.container.innerHTML = '<div class="text-center text-red-500 py-12">Error loading calendar data</div>';
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
    
    renderDayEvents() {
        const dayStart = new Date(this.currentDate);
        dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(this.currentDate);
        dayEnd.setHours(23, 59, 59, 999);
        
        let html = '<div class="day-events-container">';
        
        // Render events
        if (this.showEvents) {
            this.events.forEach(event => {
                const eventStart = new Date(event.start);
                const eventEnd = event.end ? new Date(event.end) : null;
                
                // Check if event overlaps with current day
                if (eventStart <= dayEnd && (eventEnd ? eventEnd >= dayStart : true)) {
                    const effectiveStart = eventStart < dayStart ? dayStart : eventStart;
                    const effectiveEnd = eventEnd ? (eventEnd > dayEnd ? dayEnd : eventEnd) : new Date(effectiveStart.getTime() + 60 * 60 * 1000); // Default 1 hour if no end
                    
                    // Calculate position: each hour = 60px, each minute = 1px
                    const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                    const topPosition = startMinutes;
                    
                    // Calculate height based on duration
                    const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                    // Ensure height is at least 30px and doesn't exceed container (1440px)
                    const heightMinutes = Math.max(30, Math.min(1440 - topPosition, durationMinutes));
                    
                    const time = effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                    const eventTitle = this.escapeHtml(event.title);
                    const eventColor = event.color || '#3b82f6';
                    html += `
                        <div class="event-card event" data-id="${event.id}" data-type="event" 
                             style="border-left-color: ${eventColor}; top: ${topPosition}px; height: ${heightMinutes}px;" 
                             onclick="window.calendar.showEventDetails(${event.id}, 'event')">
                            <i class="fas fa-calendar mr-2 text-blue-600 dark:text-blue-400"></i>
                            <strong>${eventTitle}</strong>
                            <br><small>${time}</small>
                        </div>
                    `;
                }
            });
        }
        
        // Render tasks
        if (this.showTasks) {
            this.tasks.forEach(task => {
                const taskTitle = this.escapeHtml(task.title);
                const priorityIcons = { urgent: '🔴', high: '🟠', medium: '🟡', low: '🟢' };
                const priorityIcon = priorityIcons[task.extendedProps?.priority] || '📋';
                html += `
                    <div class="event-card task" data-id="${task.id}" data-type="task" onclick="window.open('/tasks/${task.id}', '_blank')">
                        ${priorityIcon} <strong>${taskTitle}</strong>
                        <br><small>Due: ${task.start}</small>
                        <br><small class="text-xs">Status: ${task.extendedProps?.status || 'Unknown'}</small>
                    </div>
                `;
            });
        }
        
        // Render time entries
        if (this.showTimeEntries) {
            this.timeEntries.forEach(entry => {
                const entryStart = new Date(entry.start);
                const entryEnd = entry.end ? new Date(entry.end) : null;
                
                // Check if entry overlaps with current day
                const entryEndForDay = entryEnd || new Date(entryStart.getTime() + 30 * 60 * 1000); // Default 30 min if no end
                const effectiveStart = entryStart < dayStart ? dayStart : entryStart;
                const effectiveEnd = entryEndForDay > dayEnd ? dayEnd : entryEndForDay;
                
                if (effectiveStart <= dayEnd && effectiveEnd >= dayStart) {
                    // Calculate position: each hour = 60px, each minute = 1px
                    const startMinutes = effectiveStart.getHours() * 60 + effectiveStart.getMinutes();
                    const topPosition = startMinutes;
                    
                    // Calculate height based on duration
                    let heightMinutes;
                    if (entryEnd) {
                        const durationMinutes = (effectiveEnd - effectiveStart) / (1000 * 60);
                        // Ensure height is at least 30px and doesn't exceed container (1440px)
                        heightMinutes = Math.max(30, Math.min(1440 - topPosition, durationMinutes));
                    } else {
                        // Active timer without end time - show as minimum height with indicator
                        // But don't exceed container bounds
                        heightMinutes = Math.min(30, 1440 - topPosition);
                    }
                    
                    const startTime = effectiveStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                    const endTimeStr = entryEnd ? effectiveEnd.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '';
                    const entryTitle = this.escapeHtml(entry.title);
                    // Check both entry.notes and entry.extendedProps.notes for compatibility
                    const notesText = entry.notes || entry.extendedProps?.notes || '';
                    const notes = notesText ? `<br><small class="text-xs">${this.escapeHtml(notesText)}</small>` : '';
                    const durationText = entryEnd ? `${startTime} - ${endTimeStr}` : `${startTime} (active)`;
                    
                    html += `
                        <div class="event-card time_entry" data-id="${entry.id}" data-type="time_entry" 
                             style="top: ${topPosition}px; height: ${heightMinutes}px;">
                            ⏱ <strong>${entryTitle}</strong>
                            <br><small>${durationText}</small>
                            ${notes}
                        </div>
                    `;
                }
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
        
        let html = '<div class="calendar-week-view"><table class="week-table"><thead><tr>';
        html += '<th class="hour-label-header"></th>'; // Empty header for hour labels column
        days.forEach(day => {
            const isToday = this.isToday(day);
            html += `<th class="${isToday ? 'today' : ''}">${day.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</th>`;
        });
        
        html += '</tr></thead><tbody>';
        
        // Time slots for each day
        for (let hour = 0; hour < 24; hour++) {
            html += '<tr>';
            html += `<td class="hour-label-cell">${hour.toString().padStart(2, '0')}:00</td>`;
            days.forEach(day => {
                html += `<td class="week-cell" data-date="${day.toISOString()}" data-hour="${hour}">`;
                html += this.renderWeekCellEvents(day, hour);
                html += '</td>';
            });
            html += '</tr>';
        }
        
        html += '</tbody></table></div>';
        this.container.innerHTML = html;
    }
    
    spanningItemOverlapsCell(item, cellStart, cellEnd) {
        const itemStart = new Date(item.start);
        const itemEnd = item.end ? new Date(item.end) : null;
        if (!itemEnd || itemEnd <= itemStart) {
            return itemStart >= cellStart && itemStart < cellEnd;
        }
        return itemStart < cellEnd && itemEnd > cellStart;
    }

    getSpanningItemPositionInCell(item, cellStart, cellEnd) {
        const itemStart = new Date(item.start);
        const itemEnd = item.end ? new Date(item.end) : null;
        if (!itemEnd || itemEnd <= itemStart) {
            const minutes = itemStart.getMinutes();
            const seconds = itemStart.getSeconds();
            const topPercent = ((minutes * 60 + seconds) / 3600) * 100;
            return { top: topPercent, height: 10 };
        }
        const segmentStart = itemStart > cellStart ? itemStart : cellStart;
        const segmentEnd = itemEnd < cellEnd ? itemEnd : cellEnd;
        const cellDuration = cellEnd - cellStart;
        const topOffset = segmentStart - cellStart;
        const segmentDuration = segmentEnd - segmentStart;
        const topPercent = (topOffset / cellDuration) * 100;
        const heightPercent = (segmentDuration / cellDuration) * 100;
        const minHeightPercent = Math.max(heightPercent, 4);
        const height = Math.min(minHeightPercent, 100 - topPercent);
        return {
            top: Math.max(0, topPercent),
            height: Math.max(4, height)
        };
    }
    
    renderWeekCellEvents(day, hour) {
        const cellStart = new Date(day);
        cellStart.setHours(hour, 0, 0, 0);
        const cellEnd = new Date(day);
        cellEnd.setHours(hour + 1, 0, 0, 0);
        
        let html = '';
        
        // Check events - span by start/end and align with timestamps
        if (this.showEvents) {
            this.events.forEach(event => {
                if (event.allDay) return;
                if (!this.spanningItemOverlapsCell(event, cellStart, cellEnd)) return;
                const position = this.getSpanningItemPositionInCell(event, cellStart, cellEnd);
                const eventTitle = this.escapeHtml(event.title);
                const eventColor = event.color || '#3b82f6';
                const eventStart = new Date(event.start);
                const eventEnd = event.end ? new Date(event.end) : null;
                let timeRange = eventStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                if (eventEnd) timeRange += ' - ' + eventEnd.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                const showText = position.height >= 15;
                const displayText = showText ? `\uD83D\uDCC5 ${eventTitle}` : '\uD83D\uDCC5';
                html += `<div class="event-chip" style="position: absolute; top: ${position.top}%; height: ${position.height}%; background-color: ${eventColor}; z-index: 1;" onclick="window.calendar.showEventDetails(${event.id}, 'event')" title="${eventTitle} (${timeRange})">${displayText}</div>`;
            });
        }
        
        // Check tasks (only if they're due this hour)
        if (this.showTasks) {
            this.tasks.forEach(task => {
                const taskDate = new Date(task.start);
                if (taskDate.toDateString() !== day.toDateString() || hour !== 9) return;
                const taskTitle = this.escapeHtml(task.title);
                html += `<div class="event-chip task-chip" style="background-color: #f59e0b" onclick="window.open('/tasks/${task.id}', '_blank'); event.stopPropagation();" title="${taskTitle}">\uD83D\uDCCB ${taskTitle}</div>`;
            });
        }
        
        // Check time entries - span by start/end and align with timestamps
        if (this.showTimeEntries) {
            this.timeEntries.forEach(entry => {
                if (!this.spanningItemOverlapsCell(entry, cellStart, cellEnd)) return;
                const position = this.getSpanningItemPositionInCell(entry, cellStart, cellEnd);
                const entryTitle = this.escapeHtml(entry.title);
                const entryStart = new Date(entry.start);
                const entryEnd = entry.end ? new Date(entry.end) : null;
                let timeRange = entryStart.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                if (entryEnd) timeRange += ' - ' + entryEnd.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                const showText = position.height >= 15;
                const displayText = showText ? `\u23F1 ${entryTitle}` : '\u23F1';
                html += `<div class="event-chip time-entry-chip" style="position: absolute; top: ${position.top}%; height: ${position.height}%; background-color: #10b981; opacity: 0.8; cursor: default; z-index: 1;" onclick="event.stopPropagation();" title="${entryTitle} (${timeRange})">${displayText}</div>`;
            });
        }
        
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
                        html += `<div class="event-badge" style="background-color: ${eventColor}" onclick="window.calendar.showEventDetails(${event.id}, 'event'); event.stopPropagation();" title="${eventTitle}">📅 ${eventTitle}</div>`;
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
                        html += `<div class="event-badge task-badge" onclick="window.open('/tasks/${task.id}', '_blank'); event.stopPropagation();" title="${taskTitle}">📋 ${taskTitle}</div>`;
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
                        html += `<div class="event-badge time-entry-badge" onclick="event.stopPropagation();" title="${entryTitle}">⏱ ${entryTitle}</div>`;
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
    
    async showEventDetails(id, type) {
        // Navigate to the appropriate detail page
        if (type === 'event') {
            window.location.href = `/calendar/event/${id}`;
        } else if (type === 'task') {
            window.location.href = `/tasks/${id}`;
        } else if (type === 'time_entry') {
            // Time entries are displayed for context only - they're not clickable
            // Users can manage time entries via the Timer/Reports sections
            console.log('Time entry clicked:', id);
        }
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

