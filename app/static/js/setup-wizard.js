/**
 * Initial setup wizard: step navigation and optional validation.
 */
(function() {
    'use strict';

    var currentStep = 1;
    var totalSteps = 6;

    function getProgressLabel() {
        var el = document.getElementById('wizard-progress-label');
        return el ? el.textContent : '';
    }
    function setProgressLabel(text) {
        var el = document.getElementById('wizard-progress-label');
        if (el) el.textContent = text;
    }

    function validateStep2() {
        var timezone = document.getElementById('timezone');
        var currency = document.getElementById('currency');
        if (!timezone || !currency) return true;
        var tzVal = (timezone.value || '').trim();
        var curVal = (currency.value || '').trim();
        if (!tzVal) {
            timezone.focus();
            if (typeof window.showToast === 'function') {
                window.showToast(document.getElementById('wizard-progress-label').getAttribute('data-msg-timezone') || 'Please select a timezone.', 'error');
            } else {
                alert('Please select a timezone.');
            }
            return false;
        }
        if (!curVal) {
            currency.focus();
            if (typeof window.showToast === 'function') {
                window.showToast(document.getElementById('wizard-progress-label').getAttribute('data-msg-currency') || 'Please enter a currency.', 'error');
            } else {
                alert('Please enter a currency.');
            }
            return false;
        }
        return true;
    }

    function validateCurrentStep() {
        if (currentStep === 2) return validateStep2();
        return true;
    }

    function goNext() {
        if (!validateCurrentStep()) return;
        if (currentStep < totalSteps) {
            currentStep++;
            updateStepUI();
        }
    }

    function goBack() {
        if (currentStep > 1) {
            currentStep--;
            updateStepUI();
        }
    }

    function updateStepUI() {
        var steps = document.querySelectorAll('.wizard-step');
        steps.forEach(function(step) {
            var stepNum = parseInt(step.getAttribute('data-step'), 10);
            if (stepNum === currentStep) {
                step.classList.remove('hidden');
                step.setAttribute('aria-current', 'step');
            } else {
                step.classList.add('hidden');
                step.removeAttribute('aria-current');
            }
        });

        var dots = document.querySelectorAll('.setup-progress-dot');
        dots.forEach(function(dot) {
            var stepNum = parseInt(dot.getAttribute('data-step'), 10);
            if (stepNum <= currentStep) {
                dot.classList.remove('bg-gray-200', 'dark:bg-gray-700');
                dot.classList.add('bg-primary');
            } else {
                dot.classList.remove('bg-primary');
                dot.classList.add('bg-gray-200', 'dark:bg-gray-700');
            }
        });

        setProgressLabel('Step ' + currentStep + ' of ' + totalSteps);

        var backBtn = document.getElementById('setup-back-btn');
        var nextBtn = document.getElementById('setup-next-btn');
        var submitBtn = document.getElementById('setup-submit-btn');

        if (backBtn) backBtn.classList.toggle('hidden', currentStep <= 1);
        if (nextBtn) nextBtn.classList.toggle('hidden', currentStep >= totalSteps);
        if (submitBtn) submitBtn.classList.toggle('hidden', currentStep < totalSteps);
    }

    function init() {
        var form = document.getElementById('setup-form');
        if (!form) return;

        var nextBtn = document.getElementById('setup-next-btn');
        var backBtn = document.getElementById('setup-back-btn');
        var submitBtn = document.getElementById('setup-submit-btn');

        if (nextBtn) nextBtn.addEventListener('click', goNext);
        if (backBtn) backBtn.addEventListener('click', goBack);

        updateStepUI();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
