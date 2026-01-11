// Utility functions

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m ${secs}s`;
}

function formatDurationLong(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(date) {
  if (typeof date === 'string') {
    date = new Date(date);
  }
  return date.toLocaleDateString();
}

function formatDateTime(date) {
  if (typeof date === 'string') {
    date = new Date(date);
  }
  return date.toLocaleString();
}

function parseISODate(dateString) {
  return new Date(dateString);
}

function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatDuration,
    formatDurationLong,
    formatDate,
    formatDateTime,
    parseISODate,
    isValidUrl,
    debounce,
  };
}

if (typeof window !== 'undefined') {
  window.Helpers = {
    formatDuration,
    formatDurationLong,
    formatDate,
    formatDateTime,
    parseISODate,
    isValidUrl,
    debounce,
  };
}
