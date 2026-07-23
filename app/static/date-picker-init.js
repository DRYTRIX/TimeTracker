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

    function initUserDateInputs() {
        if (typeof flatpickr === 'undefined') return;
        var inputs = document.querySelectorAll('input.user-date-input[type="date"]');
        var altFormat = getFlatpickrAltFormat();
        var firstDay = getFirstDayOfWeek();
        inputs.forEach(function (el) {
            if (el._flatpickr) return;
            flatpickr(el, {
                dateFormat: 'Y-m-d',
                altInput: true,
                altFormat: altFormat,
                altInputClass: 'form-input',
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

    // Test / debug hook
    window.__timePickerUses24hr = timePickerUses24hr;

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
