/**
 * Generic Integration Setup Wizard JavaScript
 * Handles step navigation, validation, connection testing, and form submission
 * Reusable across all integration setup wizards
 */

(function() {
    'use strict';

    /**
     * IntegrationWizard class - handles multi-step wizard functionality
     */
    class IntegrationWizard {
        constructor(options) {
            this.currentStep = 1;
            this.totalSteps = options.totalSteps || 5;
            this.provider = options.provider || '';
            this.saveUrl = options.saveUrl || '';
            this.testConnectionUrl = options.testConnectionUrl || null;
            this.connectionTestResult = null;
            this.onStepChangeCallbacks = [];
            this.validationCallbacks = {};
            this.options = options;
        }

        init() {
            this.setupEventListeners();
            this.updateStepUI();
            
            // Call custom initialization if provided
            if (typeof this.options.onInit === 'function') {
                this.options.onInit.call(this);
            }
        }

        setupEventListeners() {
            const nextBtn = document.getElementById('next-btn');
            const prevBtn = document.getElementById('prev-btn');
            const form = document.getElementById('wizard-form');

            if (nextBtn) {
                nextBtn.addEventListener('click', () => this.handleNext());
            }

            if (prevBtn) {
                prevBtn.addEventListener('click', () => this.handlePrevious());
            }

            if (form) {
                form.addEventListener('submit', (e) => this.handleSubmit(e));
            }

            // Copy button support
            document.addEventListener('click', (e) => {
                if (e.target.closest('.copy-btn')) {
                    const btn = e.target.closest('.copy-btn');
                    const targetId = btn.getAttribute('data-target');
                    this.copyToClipboard(targetId, btn);
                }
            });
        }

        handleNext() {
            if (this.validateCurrentStep()) {
                if (this.currentStep < this.totalSteps) {
                    this.currentStep++;
                    this.updateStepUI();
                } else {
                    // On last step, submit the form
                    this.submitForm();
                }
            }
        }

        handlePrevious() {
            if (this.currentStep > 1) {
                this.currentStep--;
                this.updateStepUI();
            }
        }

        validateCurrentStep() {
            // Check if there's a custom validation callback for this step
            if (this.validationCallbacks[this.currentStep]) {
                return this.validationCallbacks[this.currentStep].call(this);
            }

            // Default validation: check required fields in current step
            return this.validateStepFields();
        }

        validateStepFields() {
            const stepElement = document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`);
            if (!stepElement) return true;

            const requiredFields = stepElement.querySelectorAll('input[required], select[required], textarea[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                const value = field.value.trim();
                if (!value) {
                    this.showError(field.id || field.name, 'This field is required');
                    isValid = false;
                } else {
                    this.clearError(field.id || field.name);
                    
                    // Validate URL fields
                    if (field.type === 'url') {
                        try {
                            new URL(value);
                        } catch (e) {
                            this.showError(field.id || field.name, 'Please enter a valid URL');
                            isValid = false;
                        }
                    }

                    // Validate email fields
                    if (field.type === 'email') {
                        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                        if (!emailRegex.test(value)) {
                            this.showError(field.id || field.name, 'Please enter a valid email address');
                            isValid = false;
                        }
                    }
                }
            });

            return isValid;
        }

        validateStep(stepNumber) {
            this.currentStep = stepNumber;
            return this.validateCurrentStep();
        }

        addValidationCallback(stepNumber, callback) {
            this.validationCallbacks[stepNumber] = callback;
        }

        onStepChange(callback) {
            this.onStepChangeCallbacks.push(callback);
        }

        updateStepUI() {
            // Hide all steps
            document.querySelectorAll('.wizard-step').forEach(step => {
                step.classList.add('hidden');
            });

            // Show current step
            const currentStepEl = document.querySelector(`.wizard-step[data-step="${this.currentStep}"]`);
            if (currentStepEl) {
                currentStepEl.classList.remove('hidden');
            }

            // Update progress indicators
            document.querySelectorAll('.step-indicator').forEach((indicator) => {
                const stepNum = parseInt(indicator.getAttribute('data-step'));
                if (stepNum < this.currentStep) {
                    // Completed step
                    indicator.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-400');
                    indicator.classList.add('bg-green-500', 'text-white');
                } else if (stepNum === this.currentStep) {
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
            document.querySelectorAll('.step-connector').forEach((connector) => {
                const stepNum = parseInt(connector.getAttribute('data-step'));
                if (stepNum < this.currentStep) {
                    connector.classList.remove('bg-gray-200', 'dark:bg-gray-700');
                    connector.classList.add('bg-green-500');
                } else {
                    connector.classList.remove('bg-green-500');
                    connector.classList.add('bg-gray-200', 'dark:bg-gray-700');
                }
            });

            // Update navigation buttons
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            
            if (prevBtn) {
                prevBtn.classList.toggle('hidden', this.currentStep === 1);
            }

            if (nextBtn) {
                if (this.currentStep === this.totalSteps) {
                    nextBtn.innerHTML = '<i class="fas fa-check mr-2"></i>' + (this.options.finishText || 'Finish');
                } else {
                    nextBtn.innerHTML = (this.options.nextText || 'Next') + '<i class="fas fa-arrow-right ml-2"></i>';
                }
            }

            // Update hidden step input
            const stepInput = document.getElementById('wizard-step-input');
            if (stepInput) {
                stepInput.value = this.currentStep;
            }

            // Call step change callbacks
            this.onStepChangeCallbacks.forEach(callback => {
                callback.call(this, this.currentStep);
            });

            // Call custom step handler if provided
            if (this.options.onStepChange) {
                this.options.onStepChange.call(this, this.currentStep);
            }
        }

        async testConnection(data) {
            if (!this.testConnectionUrl) {
                console.warn('Test connection URL not configured');
                return null;
            }

            const btn = document.getElementById('test-connection-btn');
            if (btn) {
                const originalText = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Testing...';

                try {
                    const response = await fetch(this.testConnectionUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCSRFToken()
                        },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();
                    this.connectionTestResult = result;
                    return result;
                } catch (error) {
                    console.error('Connection test error:', error);
                    return {
                        success: false,
                        error: 'Network error: ' + error.message
                    };
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            }
            return null;
        }

        displayConnectionResults(result, resultsContainerId = 'connection-test-results') {
            const resultsDiv = document.getElementById(resultsContainerId);
            if (!resultsDiv) return;

            if (result.success) {
                resultsDiv.innerHTML = `
                    <div class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg mb-4">
                        <p class="text-sm text-green-800 dark:text-green-200">
                            <i class="fas fa-check-circle mr-2"></i>
                            Connection test successful!
                        </p>
                    </div>
                `;
            } else {
                let errorDetails = '';
                if (result.error) {
                    errorDetails = `<p class="mt-2 text-xs">${this.escapeHtml(result.error)}</p>`;
                }

                resultsDiv.innerHTML = `
                    <div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
                        <p class="text-sm text-red-800 dark:text-red-200">
                            <i class="fas fa-exclamation-triangle mr-2"></i>
                            Connection test failed.
                        </p>
                        ${errorDetails}
                    </div>
                `;
            }
        }

        showError(fieldId, message) {
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

        clearError(fieldId) {
            const field = document.getElementById(fieldId);
            if (field) {
                field.classList.remove('border-red-500');
                const errorDiv = field.parentElement.querySelector('.error-message');
                if (errorDiv) {
                    errorDiv.remove();
                }
            }
        }

        clearAllErrors() {
            document.querySelectorAll('.error-message').forEach(el => el.remove());
            document.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500'));
        }

        async submitForm() {
            const form = document.getElementById('wizard-form');
            if (!form) return;

            // Collect all form data
            const formData = new FormData(form);
            formData.append('wizard_step', this.currentStep);

            try {
                const response = await fetch(this.saveUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: formData
                });

                const result = await response.json();
                
                if (result.success) {
                    if (result.redirect_url) {
                        window.location.href = result.redirect_url;
                    } else {
                        // Show success message and redirect to manage page
                        window.location.href = `/integrations/${this.provider}/manage`;
                    }
                } else {
                    alert(result.message || 'Failed to save configuration. Please try again.');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                alert('An error occurred while saving. Please try again.');
            }
        }

        handleSubmit(e) {
            e.preventDefault();
            if (this.currentStep === this.totalSteps) {
                this.submitForm();
            } else {
                this.handleNext();
            }
        }

        copyToClipboard(elementId, button) {
            const element = document.getElementById(elementId);
            if (!element) return;

            const text = element.textContent || element.value;
            
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

        getCSRFToken() {
            const tokenElement = document.querySelector('meta[name="csrf-token"]');
            return tokenElement ? tokenElement.getAttribute('content') : '';
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Public API methods
        goToStep(stepNumber) {
            if (stepNumber >= 1 && stepNumber <= this.totalSteps) {
                this.currentStep = stepNumber;
                this.updateStepUI();
            }
        }

        getCurrentStep() {
            return this.currentStep;
        }
    }

    // Make IntegrationWizard available globally
    window.IntegrationWizard = IntegrationWizard;

})();
