/**
 * Comprehensive Form Validation System
 * Provides real-time validation with inline errors, success feedback, and visual indicators
 */

class FormValidator {
    constructor(formElement, options = {}) {
        this.form = formElement;
        this.options = {
            validateOnBlur: true,
            validateOnInput: true,
            validateOnSubmit: true,
            showSuccessMessages: true,
            showErrorMessages: true,
            debounceDelay: 300,
            ...options
        };
        
        this.fields = new Map();
        this.debounceTimers = new Map();
        
        this.init();
    }
    
    init() {
        if (!this.form) return;
        
        // Prevent duplicate initialization
        if (this.form.dataset.validatorInitialized === 'true') {
            return;
        }
        
        // Find all form fields
        const inputs = this.form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Skip hidden inputs and submit buttons
            if (input.type === 'hidden' || input.type === 'submit' || input.type === 'button') {
                return;
            }
            
            // Skip if already has a validator attached
            if (input.dataset.validatorAttached === 'true') {
                return;
            }
            
            const field = this.setupField(input);
            if (field) {
                this.fields.set(input.name || input.id, field);
                input.dataset.validatorAttached = 'true';
            }
        });
        
        // Mark form as initialized
        this.form.dataset.validatorInitialized = 'true';
        
        // Setup form submission validation
        if (this.options.validateOnSubmit) {
            // Remove existing listener if any
            const existingHandler = this.form._validationSubmitHandler;
            if (existingHandler) {
                this.form.removeEventListener('submit', existingHandler);
            }
            
            const submitHandler = (e) => this.handleSubmit(e);
            this.form._validationSubmitHandler = submitHandler;
            this.form.addEventListener('submit', submitHandler);
        }
    }
    
    setupField(input) {
        const field = {
            element: input,
            name: input.name || input.id,
            label: this.getLabel(input),
            required: input.hasAttribute('required') || input.getAttribute('aria-required') === 'true',
            validators: [],
            errors: [],
            isValid: null,
            errorContainer: null,
            successContainer: null
        };
        
        // Create error and success message containers
        field.errorContainer = this.createMessageContainer(input, 'error');
        field.successContainer = this.createMessageContainer(input, 'success');
        
        // Add visual indicator for required fields
        if (field.required && field.label) {
            this.markAsRequired(field.label);
        }
        
        // Setup validation rules
        this.setupValidationRules(field);
        
        // Setup event listeners
        if (this.options.validateOnInput) {
            input.addEventListener('input', (e) => this.debouncedValidate(field, e));
        }
        
        if (this.options.validateOnBlur) {
            input.addEventListener('blur', (e) => this.validateField(field, e));
        }
        
        // Add initial state
        this.updateFieldState(field);
        
        return field;
    }
    
    getLabel(input) {
        // Try multiple methods to find the label
        const id = input.id;
        const name = input.name;
        
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) return label;
        }
        
        // Try to find label by parent
        const parent = input.closest('div');
        if (parent) {
            const label = parent.querySelector('label');
            if (label) return label;
        }
        
        return null;
    }
    
    markAsRequired(label) {
        if (!label) return;
        
        // Check if already marked with our indicator
        if (label.querySelector('.required-indicator')) return;
        
        // Check if label already has an asterisk or required text
        const labelText = label.textContent || label.innerText || '';
        const labelHTML = label.innerHTML || '';
        
        // Check for existing asterisks or required indicators
        if (labelText.includes('*') || 
            labelHTML.includes('text-red-500') || 
            labelHTML.includes('required-indicator') ||
            label.querySelector('span.text-red-500') ||
            label.querySelector('[class*="red"]')) {
            return; // Already marked
        }
        
        // Only add if label doesn't already have required markers
        const indicator = document.createElement('span');
        indicator.className = 'required-indicator text-red-500 ml-1';
        indicator.textContent = '*';
        indicator.setAttribute('aria-label', 'Required field');
        label.appendChild(indicator);
    }
    
    createMessageContainer(input, type) {
        // Check if container already exists - search more broadly
        const form = input.closest('form');
        const inputId = input.id || input.name;
        const existing = form ? form.querySelector(`.field-message.field-${type}[data-field="${inputId}"]`) : null;
        if (existing) return existing;
        
        // Check if there's already a message container near this input (within same form group)
        const parent = input.closest('.form-group, .mb-4, .mb-6, div');
        if (parent) {
            const nearbyExisting = parent.querySelector(`.field-message.field-${type}[data-field="${inputId}"]`);
            if (nearbyExisting) return nearbyExisting;
            
            // Also check for any existing message container of same type
            const anyExisting = parent.querySelector(`.field-message.field-${type}`);
            if (anyExisting && !anyExisting.getAttribute('data-field')) {
                // Reuse existing if it's not assigned to a specific field
                anyExisting.setAttribute('data-field', inputId || input.name || '');
                return anyExisting;
            }
        }
        
        const container = document.createElement('div');
        container.className = `field-message field-${type} mt-1 text-sm hidden`;
        container.setAttribute('role', type === 'error' ? 'alert' : 'status');
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('data-field', inputId || input.name || '');
        
        // Find the best insertion point - look for existing help text or description
        const inputWrapper = input.parentElement;
        let inserted = false;
        
        // Try to find existing help text (usually <p class="text-xs">)
        let nextSibling = input.nextElementSibling;
        while (nextSibling && !inserted) {
            if (nextSibling.classList && 
                (nextSibling.classList.contains('text-xs') || 
                 nextSibling.classList.contains('text-sm') ||
                 nextSibling.classList.contains('field-message'))) {
                // Insert before help text
                inputWrapper.insertBefore(container, nextSibling);
                inserted = true;
                break;
            }
            nextSibling = nextSibling.nextElementSibling;
        }
        
        // If no help text found, try to insert after the input but within the same wrapper
        if (!inserted) {
            if (inputWrapper && inputWrapper.tagName === 'DIV') {
                // Insert right after input
                if (input.nextSibling) {
                    inputWrapper.insertBefore(container, input.nextSibling);
                } else {
                    inputWrapper.appendChild(container);
                }
                inserted = true;
            }
        }
        
        // Final fallback: append to parent
        if (!inserted) {
            (inputWrapper || input.parentElement).appendChild(container);
        }
        
        return container;
    }
    
    setupValidationRules(field) {
        const input = field.element;
        
        // Required validation
        if (field.required) {
            field.validators.push({
                name: 'required',
                validate: (value) => {
                    const trimmed = typeof value === 'string' ? value.trim() : value;
                    return trimmed !== '' && trimmed !== null && trimmed !== undefined;
                },
                message: window.i18n?.messages?.requiredField || 'This field is required'
            });
        }
        
        // Type-specific validations
        if (input.type === 'email') {
            field.validators.push({
                name: 'email',
                validate: (value) => {
                    if (!value || value.trim() === '') return true; // Optional fields can be empty
                    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    return emailRegex.test(value);
                },
                message: 'Please enter a valid email address'
            });
        }
        
        // Phone/tel validation
        if (input.type === 'tel' || 
            input.name?.toLowerCase().includes('phone') || 
            input.name?.toLowerCase().includes('tel') ||
            input.id?.toLowerCase().includes('phone') ||
            input.id?.toLowerCase().includes('tel')) {
            field.validators.push({
                name: 'phone',
                validate: (value) => {
                    if (!value || value.trim() === '') return true; // Optional fields can be empty
                    // Remove common phone formatting characters
                    const cleaned = value.replace(/[\s\-\(\)\+]/g, '');
                    // Check if it contains only digits (and optional + at start)
                    const phoneRegex = /^\+?\d{7,15}$/;
                    return phoneRegex.test(cleaned);
                },
                message: 'Please enter a valid phone number (7-15 digits, with optional country code)'
            });
        }
        
        if (input.type === 'url') {
            field.validators.push({
                name: 'url',
                validate: (value) => {
                    if (!value || value.trim() === '') return true;
                    try {
                        new URL(value);
                        return true;
                    } catch {
                        return false;
                    }
                },
                message: 'Please enter a valid URL'
            });
        }
        
        if (input.type === 'number') {
            const min = input.getAttribute('min');
            const max = input.getAttribute('max');
            
            if (min !== null) {
                field.validators.push({
                    name: 'min',
                    validate: (value) => {
                        if (!value || value === '') return true;
                        return parseFloat(value) >= parseFloat(min);
                    },
                    message: `Value must be at least ${min}`
                });
            }
            
            if (max !== null) {
                field.validators.push({
                    name: 'max',
                    validate: (value) => {
                        if (!value || value === '') return true;
                        return parseFloat(value) <= parseFloat(max);
                    },
                    message: `Value must be at most ${max}`
                });
            }
        }
        
        if (input.hasAttribute('minlength')) {
            const minLength = parseInt(input.getAttribute('minlength'));
            field.validators.push({
                name: 'minlength',
                validate: (value) => {
                    if (!value || value.trim() === '') return true;
                    return value.length >= minLength;
                },
                message: `Must be at least ${minLength} characters`
            });
        }
        
        if (input.hasAttribute('maxlength')) {
            const maxLength = parseInt(input.getAttribute('maxlength'));
            field.validators.push({
                name: 'maxlength',
                validate: (value) => {
                    if (!value || value.trim() === '') return true;
                    return value.length <= maxLength;
                },
                message: `Must be at most ${maxLength} characters`
            });
        }
        
        // Pattern validation
        if (input.hasAttribute('pattern')) {
            const pattern = new RegExp(input.getAttribute('pattern'));
            field.validators.push({
                name: 'pattern',
                validate: (value) => {
                    if (!value || value.trim() === '') return true;
                    return pattern.test(value);
                },
                message: input.getAttribute('title') || 'Please match the required format'
            });
        }
        
        // Date validations
        if (input.type === 'date') {
            // Check for date range validation (end date after start date, etc.)
            const startDateField = input.getAttribute('data-start-date-for');
            const endDateField = input.getAttribute('data-end-date-for');
            
            if (startDateField) {
                field.validators.push({
                    name: 'dateRange',
                    validate: (value) => {
                        if (!value) return true;
                        const startDateInput = this.form.querySelector(`[name="${startDateField}"], [id="${startDateField}"]`);
                        if (!startDateInput || !startDateInput.value) return true;
                        return new Date(value) >= new Date(startDateInput.value);
                    },
                    message: 'End date must be after start date'
                });
            }
        }
    }
    
    debouncedValidate(field, event) {
        const timer = this.debounceTimers.get(field.name);
        if (timer) {
            clearTimeout(timer);
        }
        
        const newTimer = setTimeout(() => {
            this.validateField(field, event);
        }, this.options.debounceDelay);
        
        this.debounceTimers.set(field.name, newTimer);
    }
    
    validateField(field, event) {
        const input = field.element;
        const value = input.type === 'checkbox' ? input.checked : input.value;
        
        field.errors = [];
        
        // Run all validators
        for (const validator of field.validators) {
            const isValid = validator.validate(value);
            if (!isValid) {
                field.errors.push(validator.message);
            }
        }
        
        // Check for custom validation
        const customValidation = input.getAttribute('data-validate');
        if (customValidation) {
            try {
                const validationFn = new Function('value', 'field', customValidation);
                const result = validationFn(value, field);
                if (result !== true && result !== undefined) {
                    field.errors.push(typeof result === 'string' ? result : 'Invalid value');
                }
            } catch (e) {
                console.warn('Custom validation error:', e);
            }
        }
        
        field.isValid = field.errors.length === 0;
        
        // Update UI
        this.updateFieldState(field);
        
        return field.isValid;
    }
    
    updateFieldState(field) {
        const input = field.element;
        
        // Remove all validation classes
        input.classList.remove('is-valid', 'is-invalid', 'field-required', 'field-optional');
        
        if (field.isValid === null) {
            // Initial state - no validation yet
            if (field.required) {
                input.classList.add('field-required');
            } else {
                input.classList.add('field-optional');
            }
            return;
        }
        
        if (field.isValid) {
            input.classList.add('is-valid');
            input.classList.remove('is-invalid');
            
            // Show success message
            if (this.options.showSuccessMessages && field.successContainer) {
                this.showSuccessMessage(field);
            } else {
                this.hideSuccessMessage(field);
            }
            
            // Hide error message
            this.hideErrorMessage(field);
        } else {
            input.classList.add('is-invalid');
            input.classList.remove('is-valid');
            
            // Show error message
            if (this.options.showErrorMessages && field.errorContainer) {
                this.showErrorMessage(field);
            }
            
            // Hide success message
            this.hideSuccessMessage(field);
        }
    }
    
    showErrorMessage(field) {
        if (!field.errorContainer) return;
        
        field.errorContainer.textContent = field.errors[0] || 'Invalid value';
        field.errorContainer.classList.remove('hidden');
        field.errorContainer.setAttribute('aria-hidden', 'false');
    }
    
    hideErrorMessage(field) {
        if (!field.errorContainer) return;
        
        field.errorContainer.classList.add('hidden');
        field.errorContainer.setAttribute('aria-hidden', 'true');
    }
    
    showSuccessMessage(field) {
        if (!field.successContainer) return;
        
        const successMessage = field.element.getAttribute('data-success-message') || 
                              'Looks good!';
        field.successContainer.textContent = successMessage;
        field.successContainer.classList.remove('hidden');
        field.successContainer.setAttribute('aria-hidden', 'false');
    }
    
    hideSuccessMessage(field) {
        if (!field.successContainer) return;
        
        field.successContainer.classList.add('hidden');
        field.successContainer.setAttribute('aria-hidden', 'true');
    }
    
    handleSubmit(event) {
        let isValid = true;
        
        // Validate all fields
        this.fields.forEach((field) => {
            const fieldValid = this.validateField(field);
            if (!fieldValid) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            event.preventDefault();
            event.stopPropagation();
            
            // Focus on first invalid field
            const firstInvalid = Array.from(this.fields.values()).find(f => !f.isValid);
            if (firstInvalid) {
                firstInvalid.element.focus();
                firstInvalid.element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            // Show form-level error message
            this.showFormError('Please fix the errors in the form before submitting.');
        }
        
        return isValid;
    }
    
    showFormError(message) {
        let formErrorContainer = this.form.querySelector('.form-error-message');
        
        if (!formErrorContainer) {
            formErrorContainer = document.createElement('div');
            formErrorContainer.className = 'form-error-message mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400';
            formErrorContainer.setAttribute('role', 'alert');
            this.form.insertBefore(formErrorContainer, this.form.firstChild);
        }
        
        formErrorContainer.textContent = message;
        formErrorContainer.classList.remove('hidden');
    }
    
    hideFormError() {
        const formErrorContainer = this.form.querySelector('.form-error-message');
        if (formErrorContainer) {
            formErrorContainer.classList.add('hidden');
        }
    }
    
    // Public API methods
    validate() {
        let isValid = true;
        this.fields.forEach((field) => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        return isValid;
    }
    
    reset() {
        this.fields.forEach((field) => {
            field.element.classList.remove('is-valid', 'is-invalid');
            field.isValid = null;
            this.hideErrorMessage(field);
            this.hideSuccessMessage(field);
            this.updateFieldState(field);
        });
        this.hideFormError();
    }
}

// Initialize validation on all forms when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-initialize forms with data-validate-form attribute
    document.querySelectorAll('form[data-validate-form]').forEach(form => {
        // Prevent duplicate initialization
        if (!form.dataset.validatorInitialized) {
            try {
                new FormValidator(form);
                form.dataset.validatorInitialized = 'true';
            } catch (e) {
                console.warn('Form validation initialization failed:', e);
            }
        }
    });
    
    // Initialize forms with novalidate attribute (for custom validation)
    // Only if they also have data-validate-form to avoid conflicts
    document.querySelectorAll('form[novalidate][data-validate-form]').forEach(form => {
        // Only initialize if not already initialized
        if (!form.dataset.validatorInitialized) {
            try {
                new FormValidator(form);
                form.dataset.validatorInitialized = 'true';
            } catch (e) {
                console.warn('Form validation initialization failed:', e);
            }
        }
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormValidator;
}

