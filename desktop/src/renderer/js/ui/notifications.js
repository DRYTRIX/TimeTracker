/**
 * UI notifications: error and success toasts.
 * Used by app.js for non-login feedback.
 */
function showError(message) {
  let errorDiv = document.getElementById('error-notification');
  if (!errorDiv) {
    errorDiv = document.createElement('div');
    errorDiv.id = 'error-notification';
    errorDiv.className = 'notification notification-error';
    errorDiv.setAttribute('role', 'alert');
    errorDiv.setAttribute('aria-live', 'assertive');
    document.body.appendChild(errorDiv);
  }
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 5000);
}

function showSuccess(message) {
  let successDiv = document.getElementById('success-notification');
  if (!successDiv) {
    successDiv = document.createElement('div');
    successDiv.id = 'success-notification';
    successDiv.className = 'notification notification-success';
    successDiv.setAttribute('role', 'status');
    successDiv.setAttribute('aria-live', 'polite');
    document.body.appendChild(successDiv);
  }
  successDiv.textContent = message;
  successDiv.style.display = 'block';
  setTimeout(() => {
    successDiv.style.display = 'none';
  }, 3000);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { showError, showSuccess };
}
