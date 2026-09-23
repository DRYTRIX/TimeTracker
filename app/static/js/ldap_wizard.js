/**
 * LDAP setup wizard: step navigation, connection test, config generation.
 */
(function () {
    'use strict';

    let currentStep = 1;
    const totalSteps = 5;
    let connectionTestResult = null;
    let generatedConfig = null;

    function getEndpoints() {
        const el = document.getElementById('ldap-wizard-endpoints');
        if (!el) {
            return { test: '', validate: '', generate: '' };
        }
        return {
            test: el.dataset.testUrl || '',
            validate: el.dataset.validateUrl || '',
            generate: el.dataset.generateUrl || '',
        };
    }

    function collectPayload() {
        const ssl = document.getElementById('LDAP_USE_SSL');
        const tls = document.getElementById('LDAP_USE_TLS');
        const authSel = document.getElementById('auth_method');
        return {
            LDAP_HOST: document.getElementById('LDAP_HOST').value.trim(),
            LDAP_PORT: document.getElementById('LDAP_PORT').value.trim(),
            LDAP_USE_SSL: !!(ssl && ssl.checked),
            LDAP_USE_TLS: !!(tls && tls.checked),
            LDAP_BIND_DN: document.getElementById('LDAP_BIND_DN').value.trim(),
            LDAP_BIND_PASSWORD: document.getElementById('LDAP_BIND_PASSWORD').value,
            LDAP_BASE_DN: document.getElementById('LDAP_BASE_DN').value.trim(),
            LDAP_USER_DN: document.getElementById('LDAP_USER_DN').value.trim(),
            LDAP_USER_OBJECT_CLASS: document.getElementById('LDAP_USER_OBJECT_CLASS').value.trim(),
            LDAP_USER_LOGIN_ATTR: document.getElementById('LDAP_USER_LOGIN_ATTR').value.trim(),
            LDAP_USER_EMAIL_ATTR: document.getElementById('LDAP_USER_EMAIL_ATTR').value.trim(),
            LDAP_USER_FNAME_ATTR: document.getElementById('LDAP_USER_FNAME_ATTR').value.trim(),
            LDAP_USER_LNAME_ATTR: document.getElementById('LDAP_USER_LNAME_ATTR').value.trim(),
            LDAP_GROUP_DN: document.getElementById('LDAP_GROUP_DN').value.trim(),
            LDAP_GROUP_OBJECT_CLASS: document.getElementById('LDAP_GROUP_OBJECT_CLASS').value.trim(),
            LDAP_ADMIN_GROUP: document.getElementById('LDAP_ADMIN_GROUP').value.trim(),
            LDAP_REQUIRED_GROUP: document.getElementById('LDAP_REQUIRED_GROUP').value.trim(),
            LDAP_TLS_CA_CERT_FILE: document.getElementById('LDAP_TLS_CA_CERT_FILE').value.trim(),
            LDAP_TIMEOUT: document.getElementById('LDAP_TIMEOUT').value.trim(),
            AUTH_METHOD: authSel ? authSel.value : 'ldap',
        };
    }

    document.addEventListener('DOMContentLoaded', function () {
        const nextBtn = document.getElementById('ldap-next-btn');
        const prevBtn = document.getElementById('ldap-prev-btn');
        const testBtn = document.getElementById('ldap-test-connection-btn');
        const genBtn = document.getElementById('ldap-generate-config-btn');
        if (nextBtn) nextBtn.addEventListener('click', handleNext);
        if (prevBtn) prevBtn.addEventListener('click', handlePrevious);
        if (testBtn) testBtn.addEventListener('click', handleTestConnection);
        if (genBtn) genBtn.addEventListener('click', handleGenerateConfig);

        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.copy-btn');
            if (btn) {
                const targetId = btn.getAttribute('data-target');
                copyToClipboard(targetId, btn);
            }
        });

        updateStepUI();
    });

    function handleNext() {
        if (validateCurrentStep()) {
            if (currentStep < totalSteps) {
                currentStep++;
                updateStepUI();
            }
        }
    }

    function handlePrevious() {
        if (currentStep > 1) {
            currentStep--;
            updateStepUI();
        }
    }

    function validateCurrentStep() {
        clearErrors();
        switch (currentStep) {
            case 1:
                return validateStep1();
            case 2:
                return validateStep2();
            case 3:
                return validateStep3();
            case 4:
                return validateStep4();
            case 5:
                return validateStep5();
            default:
                return true;
        }
    }

    function validateStep1() {
        const host = document.getElementById('LDAP_HOST').value.trim();
        if (!host) {
            showError('LDAP_HOST', 'Host is required');
            return false;
        }
        return true;
    }

    function validateStep2() {
        if (!document.getElementById('LDAP_BIND_DN').value.trim()) {
            showError('LDAP_BIND_DN', 'Bind DN is required');
            return false;
        }
        if (!document.getElementById('LDAP_BIND_PASSWORD').value) {
            showError('LDAP_BIND_PASSWORD', 'Bind password is required');
            return false;
        }
        return true;
    }

    function validateStep3() {
        if (!document.getElementById('LDAP_BASE_DN').value.trim()) {
            showError('LDAP_BASE_DN', 'Base DN is required');
            return false;
        }
        if (!document.getElementById('LDAP_USER_LOGIN_ATTR').value.trim()) {
            showError('LDAP_USER_LOGIN_ATTR', 'Login attribute is required');
            return false;
        }
        return true;
    }

    function validateStep4() {
        const m = document.getElementById('auth_method').value;
        if (m !== 'ldap' && m !== 'all') {
            showError('auth_method', 'Choose ldap or all');
            return false;
        }
        return true;
    }

    function validateStep5() {
        return true;
    }

    function showError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.add('border-red-500');
            let errorDiv = field.parentElement.querySelector('.error-message');
            if (!errorDiv) {
                errorDiv = document.createElement('p');
                errorDiv.className = 'error-message text-red-500 text-xs mt-1';
                field.parentElement.appendChild(errorDiv);
            }
            errorDiv.textContent = message;
        }
    }

    function clearErrors() {
        document.querySelectorAll('.error-message').forEach(function (el) {
            el.remove();
        });
        document.querySelectorAll('.border-red-500').forEach(function (el) {
            el.classList.remove('border-red-500');
        });
    }

    function updateStepUI() {
        document.querySelectorAll('.wizard-step').forEach(function (step) {
            step.classList.add('hidden');
        });
        const currentEl = document.querySelector('.wizard-step[data-step="' + currentStep + '"]');
        if (currentEl) {
            currentEl.classList.remove('hidden');
        }

        document.querySelectorAll('.step-indicator').forEach(function (indicator, index) {
            const stepNum = index + 1;
            indicator.classList.remove(
                'bg-gray-200',
                'dark:bg-gray-700',
                'text-gray-600',
                'dark:text-gray-400',
                'bg-primary',
                'bg-green-500',
                'text-white'
            );
            if (stepNum < currentStep) {
                indicator.classList.add('bg-green-500', 'text-white');
            } else if (stepNum === currentStep) {
                indicator.classList.add('bg-primary', 'text-white');
            } else {
                indicator.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-400');
            }
        });

        document.querySelectorAll('.step-connector').forEach(function (connector, index) {
            const stepNum = index + 1;
            connector.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'bg-green-500');
            if (stepNum < currentStep) {
                connector.classList.add('bg-green-500');
            } else {
                connector.classList.add('bg-gray-200', 'dark:bg-gray-700');
            }
        });

        const prevBtn = document.getElementById('ldap-prev-btn');
        const nextBtn = document.getElementById('ldap-next-btn');
        if (prevBtn) prevBtn.classList.toggle('hidden', currentStep === 1);
        if (nextBtn) {
            if (currentStep === totalSteps) {
                nextBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Finish';
            } else {
                nextBtn.innerHTML = 'Next<i class="fas fa-arrow-right ml-2"></i>';
            }
        }

        if (currentStep === 5 && connectionTestResult) {
            displayConnectionResults(connectionTestResult);
        }
        if (currentStep === 5 && generatedConfig) {
            displayConfigResults(generatedConfig);
        }
    }

    async function handleTestConnection() {
        const urls = getEndpoints();
        if (!urls.test) return;

        const btn = document.getElementById('ldap-test-connection-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Testing...';

        const resultsDiv = document.getElementById('ldap-connection-test-results');
        resultsDiv.innerHTML =
            '<div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"><p class="text-sm text-blue-800 dark:text-blue-200"><i class="fas fa-spinner fa-spin mr-2"></i>Testing...</p></div>';

        try {
            const response = await fetch(urls.test, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(collectPayload()),
            });
            const result = await response.json();
            connectionTestResult = result;
            displayConnectionResults(result);
        } catch (err) {
            connectionTestResult = { success: false, message: 'Network error: ' + err.message, user_count: null };
            displayConnectionResults(connectionTestResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function displayConnectionResults(result) {
        const resultsDiv = document.getElementById('ldap-connection-test-results');
        if (!resultsDiv) return;
        if (result.success) {
            const cnt =
                result.user_count != null
                    ? '<p class="mt-2 text-sm">' +
                      escapeHtml(String(result.user_count)) +
                      ' ' +
                      (result.user_count === 1 ? 'user entry' : 'user entries') +
                      ' (sample count under user search base).</p>'
                    : '';
            resultsDiv.innerHTML =
                '<div class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">' +
                '<p class="text-sm text-green-800 dark:text-green-200"><i class="fas fa-check-circle mr-2"></i>' +
                escapeHtml(result.message || 'OK') +
                '</p>' +
                cnt +
                '</div>';
        } else {
            resultsDiv.innerHTML =
                '<div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">' +
                '<p class="text-sm text-red-800 dark:text-red-200"><i class="fas fa-exclamation-triangle mr-2"></i>' +
                escapeHtml(result.message || result.error || 'Connection failed') +
                '</p></div>';
        }
    }

    async function handleGenerateConfig() {
        const urls = getEndpoints();
        if (!urls.validate || !urls.generate) return;

        const btn = document.getElementById('ldap-generate-config-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';

        const payload = collectPayload();

        try {
            const valRes = await fetch(urls.validate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const valJson = await valRes.json();
            if (!valJson.valid) {
                const msg = (valJson.errors && valJson.errors[0] && valJson.errors[0].message) || 'Validation failed';
                ttAlert(msg);
                return;
            }

            const response = await fetch(urls.generate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (result.success) {
                generatedConfig = result;
                displayConfigResults(result);
            } else {
                ttAlert(result.error || 'Failed to generate configuration');
            }
        } catch (err) {
            ttAlert('Network error: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    function displayConfigResults(result) {
        const preview = document.getElementById('ldap-config-preview');
        const envContent = document.getElementById('ldap-env-content');
        const dockerContent = document.getElementById('ldap-docker-content');
        if (envContent) envContent.textContent = result.env_content || '';
        if (dockerContent) dockerContent.textContent = result.docker_compose_content || '';
        if (preview) preview.classList.remove('hidden');
    }

    function copyToClipboard(elementId, button) {
        const element = document.getElementById(elementId);
        if (!element || !button) return;
        const text = element.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () {
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
                button.classList.add('bg-green-500');
                setTimeout(function () {
                    button.innerHTML = originalText;
                    button.classList.remove('bg-green-500');
                }, 2000);
            });
        }
    }
})();
