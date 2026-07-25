/**
 * Initialize Flatpickr on date/time inputs so they display using the user's
 * preferred formats (userPrefs.dateFormat / userPrefs.timeFormat) while still
 * submitting YYYY-MM-DD and HH:MM (24h) to the server.
 *
 * Date: class "user-date-input" on input[type="date"]
 * Time: class "user-time-input" on input[type="time"]
 */
(function () {
    function getFlatpickrAltFormat() {
        var key = (window.userPrefs && window.userPrefs.dateFormat) ? window.userPrefs.dateFormat : 'YYYY-MM-DD';
        switch (key) {
            case 'MM/DD/YYYY': return 'm/d/Y';
            case 'DD/MM/YYYY': return 'd/m/Y';
            case 'DD.MM.YYYY': return 'd.m.Y';
            case 'YYYY-MM-DD':
            default: return 'Y-m-d';
        }
    }

    function getFirstDayOfWeek() {
        if (window.userPrefs && typeof window.userPrefs.weekStartDay === 'number' && window.userPrefs.weekStartDay >= 0 && window.userPrefs.weekStartDay <= 6) {
            return window.userPrefs.weekStartDay;
        }
        return 1;
    }

    /**
     * Whether Flatpickr time pickers should use 24-hour clock.
     * Exposed for tests: window.__timePickerUses24hr
     */
    function timePickerUses24hr() {
        return !(window.userPrefs && window.userPrefs.timeFormat === '12h');
    }

    function getTimeAltFormat() {
        return timePickerUses24hr() ? 'H:i' : 'h:i K';
    }

    /**
     * Parse a free-typed time string into { hours, minutes } (24h).
     * Supports HH:MM, H:MM, compact HHMM/HMM, and optional AM/PM.
     * Exposed for tests: window.__parseUserTimeInput
     *
     * @param {string} dateStr
     * @param {boolean} use24hr
     * @returns {{ hours: number, minutes: number } | null}
     */
    function parseUserTimeInput(dateStr, use24hr) {
        if (dateStr == null) return null;
        var raw = String(dateStr).trim();
        if (!raw) return null;

        var isPm = false;
        var isAm = false;
        var withoutMeridiem = raw.replace(/\s*(am|pm|a\.m\.|p\.m\.)\s*/i, function (_match, token) {
            var t = token.replace(/\./g, '').toLowerCase();
            if (t === 'pm') isPm = true;
            if (t === 'am') isAm = true;
            return ' ';
        }).trim();

        var hours;
        var minutes;
        var colonMatch = withoutMeridiem.match(/^(\d{1,2})\s*[:.]\s*(\d{1,2})$/);
        if (colonMatch) {
            hours = parseInt(colonMatch[1], 10);
            minutes = parseInt(colonMatch[2], 10);
        } else {
            var digits = withoutMeridiem.replace(/\D/g, '');
            if (digits.length === 3) {
                // HMM → H:MM (e.g. 934 → 09:34)
                hours = parseInt(digits.slice(0, 1), 10);
                minutes = parseInt(digits.slice(1), 10);
            } else if (digits.length === 4) {
                // HHMM → HH:MM (e.g. 1234 → 12:34) — the #704 follow-up case
                hours = parseInt(digits.slice(0, 2), 10);
                minutes = parseInt(digits.slice(2), 10);
            } else if (digits.length === 1 || digits.length === 2) {
                hours = parseInt(digits, 10);
                minutes = 0;
            } else {
                return null;
            }
        }

        if (isNaN(hours) || isNaN(minutes)) return null;
        if (minutes < 0 || minutes > 59) return null;

        if (isAm || isPm) {
            // 12h clock with meridiem: hour must be 1–12 (or 0 for midnight)
            if (hours === 0) hours = 12;
            if (hours < 1 || hours > 12) return null;
            if (isPm && hours < 12) hours += 12;
            if (isAm && hours === 12) hours = 0;
        } else if (use24hr) {
            if (hours < 0 || hours > 23) return null;
        } else {
            // 12h UI without meridiem: allow 0–23 so compact "1330" still works
            if (hours < 0 || hours > 23) return null;
        }

        return { hours: hours, minutes: minutes };
    }

    /**
     * Flatpickr parseDate for time-only pickers.
     * @param {string} dateStr
     * @param {string} format
     * @returns {Date | undefined}
     */
    function parseTimeDate(dateStr, format) {
        var use24hr = timePickerUses24hr();
        // Wire format is always H:i (24h) for the hidden input
        var prefer24 = use24hr || format === 'H:i';
        var parsed = parseUserTimeInput(dateStr, prefer24);
        if (!parsed) return undefined;
        var d = new Date();
        d.setHours(parsed.hours, parsed.minutes, 0, 0);
        return d;
    }

    /**
     * Flatpickr formatDate for time-only pickers.
     * @param {Date} date
     * @param {string} format
     * @returns {string}
     */
    function formatTimeDate(date, format) {
        if (!(date instanceof Date) || isNaN(date.getTime())) return '';
        var hours24 = date.getHours();
        var minutes = date.getMinutes();
        var mm = minutes < 10 ? '0' + minutes : String(minutes);

        if (format === 'H:i') {
            var hh = hours24 < 10 ? '0' + hours24 : String(hours24);
            return hh + ':' + mm;
        }

        // Display format for 12h: h:i K
        var hours12 = hours24 % 12;
        if (hours12 === 0) hours12 = 12;
        var meridiem = hours24 >= 12 ? 'PM' : 'AM';
        return hours12 + ':' + mm + ' ' + meridiem;
    }

    function initUserDateInputs() {
        if (typeof flatpickr === 'undefined') return;
        var inputs = document.querySelectorAll('input.user-date-input[type="date"]');
        var altFormat = getFlatpickrAltFormat();
        var firstDay = getFirstDayOfWeek();
        inputs.forEach(function (el) {
            if (el._flatpickr) return;
            // Preserve existing classes on the visible alt input (form-input, form-control, sizing).
            var altClass = (el.className || 'form-input').replace(/\buser-date-input\b/g, '').trim() || 'form-input';
            flatpickr(el, {
                dateFormat: 'Y-m-d',
                altInput: true,
                altFormat: altFormat,
                altInputClass: altClass,
                allowInput: false,
                locale: { firstDayOfWeek: firstDay }
            });
        });
    }

    function initUserTimeInputs() {
        if (typeof flatpickr === 'undefined') return;
        var inputs = document.querySelectorAll('input.user-time-input[type="time"]');
        var use24hr = timePickerUses24hr();
        var altFormat = getTimeAltFormat();
        inputs.forEach(function (el) {
            if (el._flatpickr) return;
            // Preserve existing classes on the visible alt input (form-input, form-control, sizing).
            var altClass = (el.className || 'form-input').replace(/\buser-time-input\b/g, '').trim() || 'form-input';
            flatpickr(el, {
                enableTime: true,
                noCalendar: true,
                dateFormat: 'H:i',
                time_24hr: use24hr,
                altInput: true,
                altFormat: altFormat,
                altInputClass: altClass,
                allowInput: true,
                parseDate: parseTimeDate,
                formatDate: formatTimeDate,
                // type=time fights Flatpickr; hide the native control, show altInput.
                onReady: function (_selectedDates, _dateStr, instance) {
                    if (instance.input) {
                        instance.input.style.display = 'none';
                    }
                }
            });
        });
    }

    function initAll() {
        initUserDateInputs();
        initUserTimeInputs();
    }

    // Test / debug hooks
    window.__timePickerUses24hr = timePickerUses24hr;
    window.__parseUserTimeInput = parseUserTimeInput;

    function onReady() {
        initAll();
        // Re-run when new content is added (e.g. modals)
        if (typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function () {
                initAll();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', onReady);
    } else {
        onReady();
    }
})();
