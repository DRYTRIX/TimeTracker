/**
 * OIDC Setup Wizard JavaScript
 * Handles step navigation, validation, connection testing, and configuration generation
 */

(function() {
    'use strict';

    let currentStep = 1;
    const totalSteps = 5;
    let connectionTestResult = null;
    let generatedConfig = null;

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeWizard();
    });

    function initializeWizard() {
        // Set up event listeners
        document.getElementById('next-btn').addEventListener('click', handleNext);
        document.getElementById('prev-btn').addEventListener('click', handlePrevious);
        document.getElementById('test-connection-btn').addEventListener('click', handleTestConnection);
        document.getElementById('generate-config-btn').addEventListener('click', handleGenerateConfig);
        
        // Set up copy buttons (will be created dynamically)
        document.addEventListener('click', function(e) {
            if (e.target.closest('.copy-btn')) {
                const btn = e.target.closest('.copy-btn');
                const targetId = btn.getAttribute('data-target');
                copyToClipboard(targetId, btn);
            }
        });

        // Update UI for initial step
        updateStepUI();
    }

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
                return true; // Step 5 doesn't need validation
            default:
                return true;
        }
    }

    function validateStep1() {
        const issuer = document.getElementById('issuer').value.trim();
        const clientId = document.getElementById('client_id').value.trim();
        const clientSecret = document.getElementById('client_secret').value.trim();
        const authMethod = document.getElementById('auth_method').value;

        if (!issuer) {
            showError('issuer', 'Issuer URL is required');
            return false;
        }

        // Validate URL format
        try {
            const url = new URL(issuer);
            if (!['http:', 'https:'].includes(url.protocol)) {
                showError('issuer', 'URL must use http or https');
                return false;
            }
        } catch (e) {
            showError('issuer', 'Invalid URL format');
            return false;
        }

        if (!clientId) {
            showError('client_id', 'Client ID is required');
            return false;
        }

        if (!clientSecret) {
            showError('client_secret', 'Client Secret is required');
            return false;
        }

        if (!authMethod || !['oidc', 'both'].includes(authMethod)) {
            showError('auth_method', 'Authentication method is required');
            return false;
        }

        clearErrors();
        return true;
    }

    function validateStep2() {
        // Step 2 validation is handled by connection test
        if (!connectionTestResult) {
            alert('Please test the connection before proceeding.');
            return false;
        }
        if (!connectionTestResult.success) {
            const proceed = confirm(
                'Connection test failed. You can still proceed, but OIDC may not work correctly. Continue anyway?'
            );
            return proceed;
        }
        return true;
    }

    function validateStep3() {
        // Step 3 has no required fields, all optional
        return true;
    }

    function validateStep4() {
        // Step 4 has no required fields, all optional
        return true;
    }

    function showError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.add('border-red-500');
            // Create or update error message
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
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500'));
    }

    function updateStepUI() {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.classList.add('hidden');
        });

        // Show current step
        const currentStepEl = document.querySelector(`.wizard-step[data-step="${currentStep}"]`);
        if (currentStepEl) {
            currentStepEl.classList.remove('hidden');
        }

        // Update progress indicators
        document.querySelectorAll('.step-indicator').forEach((indicator, index) => {
            const stepNum = index + 1;
            if (stepNum < currentStep) {
                // Completed step
                indicator.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-400');
                indicator.classList.add('bg-green-500', 'text-white');
            } else if (stepNum === currentStep) {
                // Current step
                indicator.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-400');
                indicator.classList.add('bg-primary', 'text-white');
            } else {
                // Future step
                indicator.classList.remove('bg-primary', 'bg-green-500', 'text-white');
                indicator.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-400');
            }
        });

        // Update connectors
        document.querySelectorAll('.step-connector').forEach((connector, index) => {
            const stepNum = index + 1;
            if (stepNum < currentStep) {
                connector.classList.remove('bg-gray-200', 'dark:bg-gray-700');
                connector.classList.add('bg-green-500');
            } else {
                connector.classList.remove('bg-green-500');
                connector.classList.add('bg-gray-200', 'dark:bg-gray-700');
            }
        });

        // Update navigation buttons
        document.getElementById('prev-btn').classList.toggle('hidden', currentStep === 1);
        document.getElementById('next-btn').textContent = currentStep === totalSteps ? 'Finish' : 'Next →';
        document.getElementById('next-btn').innerHTML = currentStep === totalSteps 
            ? '<i class="fas fa-check mr-2"></i>Finish'
            : 'Next<i class="fas fa-arrow-right ml-2"></i>';

        // Special handling for step 2
        if (currentStep === 2 && connectionTestResult) {
            displayConnectionResults(connectionTestResult);
        }

        // Special handling for step 5
        if (currentStep === 5 && generatedConfig) {
            displayConfigResults(generatedConfig);
        }
    }

    async function handleTestConnection() {
        const issuer = document.getElementById('issuer').value.trim();
        
        if (!issuer) {
            alert('Please enter an Issuer URL first.');
            return;
        }

        const btn = document.getElementById('test-connection-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Testing...';

        const resultsDiv = document.getElementById('connection-test-results');
        resultsDiv.innerHTML = '<div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"><p class="text-sm text-blue-800 dark:text-blue-200"><i class="fas fa-spinner fa-spin mr-2"></i>Testing connection...</p></div>';

        try {
            const response = await fetch('/admin/oidc/setup-wizard/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ issuer: issuer })
            });

            const result = await response.json();
            connectionTestResult = result;
            displayConnectionResults(result);
        } catch (error) {
            connectionTestResult = {
                success: false,
                error: 'Network error: ' + error.message
            };
            displayConnectionResults(connectionTestResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    function displayConnectionResults(result) {
        const resultsDiv = document.getElementById('connection-test-results');
        const metadataPreview = document.getElementById('metadata-preview');
        const metadataContent = document.getElementById('metadata-content');

        if (result.success) {
            resultsDiv.innerHTML = `
                <div class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg mb-4">
                    <p class="text-sm text-green-800 dark:text-green-200">
                        <i class="fas fa-check-circle mr-2"></i>
                        Connection successful! DNS resolved and metadata endpoint is accessible.
                    </p>
                </div>
            `;

            if (result.metadata) {
                metadataPreview.classList.remove('hidden');
                metadataContent.textContent = JSON.stringify(result.metadata, null, 2);
            }
        } else {
            let errorDetails = '';
            if (!result.dns_resolved) {
                errorDetails += '<p class="mt-2"><strong>DNS Resolution:</strong> Failed to resolve ' + result.hostname + '</p>';
            }
            if (result.error) {
                errorDetails += '<p class="mt-2"><strong>Error:</strong> ' + escapeHtml(result.error) + '</p>';
            }

            resultsDiv.innerHTML = `
                <div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
                    <p class="text-sm text-red-800 dark:text-red-200">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        Connection test failed.
                    </p>
                    ${errorDetails}
                    <p class="mt-2 text-xs">
                        See <a href="/docs/TROUBLESHOOTING_OIDC_DNS.html" target="_blank" class="underline">troubleshooting guide</a> for solutions.
                    </p>
                </div>
            `;
            metadataPreview.classList.add('hidden');
        }
    }

    async function handleGenerateConfig() {
        // Collect all form data
        const config = {
            issuer: document.getElementById('issuer').value.trim(),
            client_id: document.getElementById('client_id').value.trim(),
            client_secret: document.getElementById('client_secret').value.trim(),
            auth_method: document.getElementById('auth_method').value,
            username_claim: document.getElementById('username_claim').value.trim(),
            email_claim: document.getElementById('email_claim').value.trim(),
            full_name_claim: document.getElementById('full_name_claim').value.trim(),
            groups_claim: document.getElementById('groups_claim').value.trim(),
            admin_group: document.getElementById('admin_group').value.trim(),
            admin_emails: document.getElementById('admin_emails').value.trim(),
            scopes: document.getElementById('scopes').value.trim(),
            redirect_uri: document.getElementById('redirect_uri').value.trim(),
            post_logout_redirect: document.getElementById('post_logout_redirect').value.trim(),
        };

        const btn = document.getElementById('generate-config-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';

        try {
            const response = await fetch('/admin/oidc/setup-wizard/generate-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            const result = await response.json();
            if (result.success) {
                generatedConfig = result;
                displayConfigResults(result);
            } else {
                alert('Failed to generate configuration: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    function displayConfigResults(result) {
        const preview = document.getElementById('config-preview');
        const envContent = document.getElementById('env-content');
        const dockerContent = document.getElementById('docker-content');

        envContent.textContent = result.env_content;
        dockerContent.textContent = result.docker_compose_content;

        preview.classList.remove('hidden');
    }

    function copyToClipboard(elementId, button) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const text = element.textContent;
        
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
                button.classList.add('bg-green-500');
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('bg-green-500');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy to clipboard');
            });
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
            } catch (err) {
                alert('Failed to copy to clipboard');
            }
            document.body.removeChild(textarea);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
