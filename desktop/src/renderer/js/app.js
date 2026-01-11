// Main application logic
const { storeGet, storeSet, storeClear } = window.config || {};
const ApiClient = require('./api/client');
const StorageService = require('./storage/storage');

let apiClient = null;
let currentView = 'dashboard';
let timerInterval = null;
let isTimerRunning = false;

// Initialize app
async function initApp() {
  // Check if already logged in
  const serverUrl = await storeGet('server_url');
  const apiToken = await storeGet('api_token');
  
  if (serverUrl && apiToken) {
    // Initialize API client
    apiClient = new ApiClient(serverUrl);
    await apiClient.setAuthToken(apiToken);
    
    // Validate token
    const isValid = await apiClient.validateToken();
    if (isValid) {
      showMainScreen();
      loadDashboard();
    } else {
      showLoginScreen();
    }
  } else {
    showLoginScreen();
  }
  
  setupEventListeners();
}

function setupEventListeners() {
  // Login form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }
  
  // Navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const view = e.target.dataset.view;
      switchView(view);
    });
  });
  
  // Window controls
  const minimizeBtn = document.getElementById('minimize-btn');
  const maximizeBtn = document.getElementById('maximize-btn');
  const closeBtn = document.getElementById('close-btn');
  
  if (minimizeBtn) minimizeBtn.addEventListener('click', () => window.electronAPI?.minimizeWindow());
  if (maximizeBtn) maximizeBtn.addEventListener('click', () => window.electronAPI?.maximizeWindow());
  if (closeBtn) closeBtn.addEventListener('click', () => window.electronAPI?.closeWindow());
  
  // Timer controls
  const startTimerBtn = document.getElementById('start-timer-btn');
  const stopTimerBtn = document.getElementById('stop-timer-btn');
  
  if (startTimerBtn) startTimerBtn.addEventListener('click', handleStartTimer);
  if (stopTimerBtn) stopTimerBtn.addEventListener('click', handleStopTimer);
  
  // Logout
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
}

async function handleLogin(e) {
  e.preventDefault();
  
  const serverUrl = document.getElementById('server-url').value.trim();
  const apiToken = document.getElementById('api-token').value.trim();
  const errorDiv = document.getElementById('login-error');
  
  // Validate
  if (!serverUrl || !isValidUrl(serverUrl)) {
    showError('Please enter a valid server URL');
    return;
  }
  
  if (!apiToken || !apiToken.startsWith('tt_')) {
    showError('Please enter a valid API token (must start with tt_)');
    return;
  }
  
  // Store credentials
  await storeSet('server_url', serverUrl);
  await storeSet('api_token', apiToken);
  
  // Initialize API client
  apiClient = new ApiClient(serverUrl);
  await apiClient.setAuthToken(apiToken);
  
  // Validate token
  const isValid = await apiClient.validateToken();
  if (isValid) {
    showMainScreen();
    loadDashboard();
  } else {
    showError('Invalid API token. Please check your token.');
    await storeDelete('api_token');
  }
}

function showError(message) {
  const errorDiv = document.getElementById('login-error');
  if (errorDiv) {
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
  }
}

function showLoginScreen() {
  document.getElementById('loading-screen').classList.remove('active');
  document.getElementById('login-screen').classList.add('active');
  document.getElementById('main-screen').classList.remove('active');
}

function showMainScreen() {
  document.getElementById('loading-screen').classList.remove('active');
  document.getElementById('login-screen').classList.remove('active');
  document.getElementById('main-screen').classList.add('active');
}

function switchView(view) {
  // Update navigation
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`[data-view="${view}"]`).classList.add('active');
  
  // Update views
  document.querySelectorAll('.view').forEach(v => {
    v.classList.remove('active');
  });
  document.getElementById(`${view}-view`).classList.add('active');
  
  currentView = view;
  
  // Load view data
  if (view === 'dashboard') {
    loadDashboard();
  } else if (view === 'projects') {
    loadProjects();
  } else if (view === 'entries') {
    loadTimeEntries();
  }
}

async function loadDashboard() {
  if (!apiClient) return;
  
  try {
    // Get timer status
    const timerResponse = await apiClient.getTimerStatus();
    if (timerResponse.data.active) {
      isTimerRunning = true;
      updateTimerDisplay(timerResponse.data.timer);
      startTimerPolling();
    }
    
    // Get today's summary
    const today = new Date().toISOString().split('T')[0];
    const entriesResponse = await apiClient.getTimeEntries({ startDate: today, endDate: today });
    const totalSeconds = entriesResponse.data.time_entries?.reduce((sum, entry) => {
      return sum + (entry.duration_seconds || 0);
    }, 0) || 0;
    
    document.getElementById('today-summary').textContent = formatDuration(totalSeconds);
    
    // Load recent entries
    loadRecentEntries();
  } catch (error) {
    console.error('Error loading dashboard:', error);
  }
}

async function loadRecentEntries() {
  if (!apiClient) return;
  
  try {
    const response = await apiClient.getTimeEntries({ perPage: 5 });
    const entries = response.data.time_entries || [];
    const entriesList = document.getElementById('recent-entries');
    
    if (entries.length === 0) {
      entriesList.innerHTML = '<p class="empty-state">No recent entries</p>';
      return;
    }
    
    entriesList.innerHTML = entries.map(entry => `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${entry.project?.name || 'Unknown Project'}</h3>
          <p>${formatDateTime(entry.start_time)}</p>
        </div>
        <div class="entry-time">${formatDuration(entry.duration_seconds || 0)}</div>
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading recent entries:', error);
  }
}

async function loadProjects() {
  if (!apiClient) return;
  
  try {
    const response = await apiClient.getProjects({ status: 'active' });
    const projects = response.data.projects || [];
    const projectsList = document.getElementById('projects-list');
    
    if (projects.length === 0) {
      projectsList.innerHTML = '<p class="empty-state">No projects found</p>';
      return;
    }
    
    projectsList.innerHTML = projects.map(project => `
      <div class="project-card" onclick="selectProject(${project.id})">
        <h3>${project.name}</h3>
        <p>${project.client || 'No client'}</p>
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading projects:', error);
  }
}

async function loadTimeEntries() {
  if (!apiClient) return;
  
  try {
    const response = await apiClient.getTimeEntries({ perPage: 50 });
    const entries = response.data.time_entries || [];
    const entriesList = document.getElementById('entries-list');
    
    if (entries.length === 0) {
      entriesList.innerHTML = '<p class="empty-state">No time entries</p>';
      return;
    }
    
    entriesList.innerHTML = entries.map(entry => `
      <div class="entry-item">
        <div class="entry-info">
          <h3>${entry.project?.name || 'Unknown Project'}</h3>
          <p>${formatDateTime(entry.start_time)} - ${entry.end_time ? formatDateTime(entry.end_time) : 'Running'}</p>
        </div>
        <div class="entry-time">${formatDuration(entry.duration_seconds || 0)}</div>
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading time entries:', error);
  }
}

async function handleStartTimer() {
  if (!apiClient) return;
  
  // TODO: Show project selection dialog first
  // For now, just start without project (will fail, but shows flow)
  try {
    const response = await apiClient.startTimer({ projectId: 1 });
    if (response.data) {
      isTimerRunning = true;
      updateTimerDisplay(response.data.timer);
      startTimerPolling();
      document.getElementById('start-timer-btn').style.display = 'none';
      document.getElementById('stop-timer-btn').style.display = 'block';
    }
  } catch (error) {
    alert('Please select a project first');
  }
}

async function handleStopTimer() {
  if (!apiClient) return;
  
  try {
    await apiClient.stopTimer();
    isTimerRunning = false;
    stopTimerPolling();
    document.getElementById('timer-display').textContent = '00:00:00';
    document.getElementById('timer-project').textContent = 'No active timer';
    document.getElementById('start-timer-btn').style.display = 'block';
    document.getElementById('stop-timer-btn').style.display = 'none';
  } catch (error) {
    console.error('Error stopping timer:', error);
  }
}

function startTimerPolling() {
  if (timerInterval) clearInterval(timerInterval);
  
  timerInterval = setInterval(async () => {
    if (!apiClient || !isTimerRunning) return;
    
    try {
      const response = await apiClient.getTimerStatus();
      if (response.data.active) {
        updateTimerDisplay(response.data.timer);
      } else {
        isTimerRunning = false;
        stopTimerPolling();
      }
    } catch (error) {
      console.error('Error polling timer:', error);
    }
  }, 5000); // Poll every 5 seconds
}

function stopTimerPolling() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function updateTimerDisplay(timer) {
  if (!timer) return;
  
  const startTime = new Date(timer.start_time);
  const now = new Date();
  const seconds = Math.floor((now - startTime) / 1000);
  
  document.getElementById('timer-display').textContent = formatDurationLong(seconds);
  document.getElementById('timer-project').textContent = timer.project?.name || 'Unknown Project';
}

async function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    await storeClear();
    apiClient = null;
    isTimerRunning = false;
    stopTimerPolling();
    showLoginScreen();
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

// Use helper functions from helpers.js
const { formatDuration, formatDurationLong, formatDateTime, isValidUrl } = window.Helpers || {};
