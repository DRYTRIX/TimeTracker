/**
 * Initialize Flatpickr on date inputs with class "user-date-input" so they
 * display and parse dates using the user's preferred format (userPrefs.dateFormat)
 * while still submitting YYYY-MM-DD to the server.
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

    function onReady() {
        initUserDateInputs();
        // Re-run when new content is added (e.g. modals)
        if (typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function () {
                initUserDateInputs();
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
