// Main application logic
const { storeGet, storeSet, storeDelete, storeClear } = window.config || {};
const ApiClient = require('./api/client');
const StorageService = require('./storage/storage');

let apiClient = null;
let currentView = 'dashboard';
let timerInterval = null;
let isTimerRunning = false;
let connectionCheckInterval = null;

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
  startConnectionCheck();
  setupTrayListeners();
}

function setupTrayListeners() {
  // Listen for tray timer actions
  if (window.electronAPI && window.electronAPI.onTrayAction) {
    window.electronAPI.onTrayAction((action) => {
      if (action === 'start-timer' && !isTimerRunning) {
        // Tray wants to start timer - show the start dialog
        handleStartTimer();
      } else if (action === 'stop-timer' && isTimerRunning) {
        // Tray wants to stop timer
        handleStopTimer();
      }
    });
  }
}

function startConnectionCheck() {
  // Check connection every 30 seconds
  connectionCheckInterval = setInterval(async () => {
    await checkConnection();
  }, 30000);
  
  // Initial check
  checkConnection();
}

async function checkConnection() {
  if (!apiClient) {
    updateConnectionStatus('disconnected');
    return;
  }
  
  try {
    const isValid = await apiClient.validateToken();
    updateConnectionStatus(isValid ? 'connected' : 'error');
  } catch (error) {
    updateConnectionStatus('error');
  }
}

function updateConnectionStatus(status) {
  const statusEl = document.getElementById('connection-status');
  if (!statusEl) return;
  
  statusEl.className = 'connection-status connection-' + status;
  switch (status) {
    case 'connected':
      statusEl.textContent = '●';
      statusEl.title = 'Connected';
      break;
    case 'error':
      statusEl.textContent = '●';
      statusEl.title = 'Connection error';
      break;
    case 'disconnected':
      statusEl.textContent = '○';
      statusEl.title = 'Disconnected';
      break;
  }
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
  
  // Settings
  const saveSettingsBtn = document.getElementById('save-settings-btn');
  const testConnectionBtn = document.getElementById('test-connection-btn');
  const autoSyncInput = document.getElementById('auto-sync');
  if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', handleSaveSettings);
  if (testConnectionBtn) testConnectionBtn.addEventListener('click', handleTestConnection);
  if (autoSyncInput) {
    autoSyncInput.addEventListener('change', () => updateSyncIntervalState());
  }
  
  // Time entries
  const addEntryBtn = document.getElementById('add-entry-btn');
  const filterEntriesBtn = document.getElementById('filter-entries-btn');
  const applyFilterBtn = document.getElementById('apply-filter-btn');
  const clearFilterBtn = document.getElementById('clear-filter-btn');
  
  if (addEntryBtn) addEntryBtn.addEventListener('click', () => showTimeEntryForm());
  if (filterEntriesBtn) filterEntriesBtn.addEventListener('click', toggleFilters);
  if (applyFilterBtn) applyFilterBtn.addEventListener('click', applyFilters);
  if (clearFilterBtn) clearFilterBtn.addEventListener('click', clearFilters);
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
      updateConnectionStatus('connected');
      showMainScreen();
      loadDashboard();
    } else {
      updateConnectionStatus('error');
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
    loadProjectsForFilter();
  } else if (view === 'settings') {
    loadSettings();
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

function selectProject(projectId) {
  currentFilters = {
    ...currentFilters,
    projectId: projectId || null,
  };
  switchView('entries');
}

let currentFilters = {
  startDate: null,
  endDate: null,
  projectId: null,
};

async function loadTimeEntries() {
  if (!apiClient) return;
  
  try {
    const params = { perPage: 50 };
    if (currentFilters.startDate) params.startDate = currentFilters.startDate;
    if (currentFilters.endDate) params.endDate = currentFilters.endDate;
    if (currentFilters.projectId) params.projectId = currentFilters.projectId;
    
    const response = await apiClient.getTimeEntries(params);
    const entries = response.data.time_entries || [];
    const entriesList = document.getElementById('entries-list');
    
    if (entries.length === 0) {
      entriesList.innerHTML = '<p class="empty-state">No time entries</p>';
      return;
    }
    
    entriesList.innerHTML = entries.map(entry => `
      <div class="entry-item" data-entry-id="${entry.id}">
        <div class="entry-info">
          <h3>${entry.project?.name || 'Unknown Project'}</h3>
          ${entry.task ? `<p class="entry-task">${entry.task.name}</p>` : ''}
          <p class="entry-time-range">
            ${formatDateTime(entry.start_time)} - ${entry.end_time ? formatDateTime(entry.end_time) : 'Running'}
          </p>
          ${entry.notes ? `<p class="entry-notes">${entry.notes}</p>` : ''}
          ${entry.tags ? `<p class="entry-tags">Tags: ${entry.tags}</p>` : ''}
          ${entry.billable ? '<span class="badge badge-success">Billable</span>' : ''}
        </div>
        <div class="entry-actions">
          <div class="entry-time">${formatDuration(entry.duration_seconds || 0)}</div>
          <button class="btn btn-sm btn-secondary" onclick="editTimeEntry(${entry.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteTimeEntry(${entry.id})">Delete</button>
        </div>
      </div>
    `).join('');
  } catch (error) {
    console.error('Error loading time entries:', error);
    showError('Failed to load time entries: ' + (error.response?.data?.error || error.message));
  }
}

function editTimeEntry(entryId) {
  showTimeEntryForm(entryId);
}

async function deleteTimeEntry(entryId) {
  if (!confirm('Are you sure you want to delete this time entry?')) {
    return;
  }
  
  if (!apiClient) return;
  
  try {
    await apiClient.deleteTimeEntry(entryId);
    loadTimeEntries();
    showSuccess('Time entry deleted successfully');
  } catch (error) {
    showError('Failed to delete time entry: ' + (error.response?.data?.error || error.message));
  }
}

async function handleStartTimer() {
  if (!apiClient) return;
  
  // Show project selection dialog
  const result = await showStartTimerDialog();
  if (!result) return; // User cancelled
  
  try {
    const response = await apiClient.startTimer({
      projectId: result.projectId,
      taskId: result.taskId,
      notes: result.notes,
    });
    if (response.data && response.data.timer) {
      isTimerRunning = true;
      updateTimerDisplay(response.data.timer);
      startTimerPolling();
      document.getElementById('start-timer-btn').style.display = 'none';
      document.getElementById('stop-timer-btn').style.display = 'block';
    }
  } catch (error) {
    showError('Failed to start timer: ' + (error.response?.data?.error || error.message));
  }
}

async function showStartTimerDialog() {
  return new Promise(async (resolve) => {
    // Load projects
    let projects = [];
    try {
      const projectsResponse = await apiClient.getProjects({ status: 'active' });
      projects = projectsResponse.data.projects || [];
    } catch (error) {
      showError('Failed to load projects');
      resolve(null);
      return;
    }
    
    if (projects.length === 0) {
      showError('No active projects found');
      resolve(null);
      return;
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>Start Timer</h3>
          <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="timer-project-select">Project *</label>
            <select id="timer-project-select" class="form-control" required>
              <option value="">Select a project...</option>
              ${projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
            </select>
          </div>
          <div class="form-group">
            <label for="timer-task-select">Task (Optional)</label>
            <select id="timer-task-select" class="form-control">
              <option value="">No task</option>
            </select>
          </div>
          <div class="form-group">
            <label for="timer-notes-input">Notes (Optional)</label>
            <textarea id="timer-notes-input" class="form-control" rows="3" placeholder="What are you working on?"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
          <button class="btn btn-primary" id="start-timer-confirm">Start</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    const projectSelect = modal.querySelector('#timer-project-select');
    const taskSelect = modal.querySelector('#timer-task-select');
    const notesInput = modal.querySelector('#timer-notes-input');
    const confirmBtn = modal.querySelector('#start-timer-confirm');
    
    // Load tasks when project changes
    projectSelect.addEventListener('change', async (e) => {
      const projectId = parseInt(e.target.value);
      if (!projectId) {
        taskSelect.innerHTML = '<option value="">No task</option>';
        return;
      }
      
      try {
        const tasksResponse = await apiClient.getTasks({ projectId: projectId });
        const tasks = tasksResponse.data.tasks || [];
        taskSelect.innerHTML = '<option value="">No task</option>' +
          tasks.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
      } catch (error) {
        console.error('Failed to load tasks:', error);
      }
    });
    
    // Handle confirm
    confirmBtn.addEventListener('click', () => {
      const projectId = parseInt(projectSelect.value);
      if (!projectId) {
        showError('Please select a project');
        return;
      }
      
      const taskId = taskSelect.value ? parseInt(taskSelect.value) : null;
      const notes = notesInput.value.trim() || null;
      
      modal.remove();
      resolve({ projectId, taskId, notes });
    });
    
    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
        resolve(null);
      }
    });
  });
}

async function handleStopTimer() {
  if (!apiClient) return;
  
  try {
    await apiClient.stopTimer();
    isTimerRunning = false;
    stopTimerPolling();
    document.getElementById('timer-display').textContent = '00:00:00';
    document.getElementById('timer-project').textContent = 'No active timer';
    document.getElementById('timer-task').style.display = 'none';
    document.getElementById('timer-notes').style.display = 'none';
    document.getElementById('start-timer-btn').style.display = 'block';
    document.getElementById('stop-timer-btn').style.display = 'none';
    // Notify tray
    updateTimerDisplay(null);
    // Refresh entries list
    loadTimeEntries();
    loadRecentEntries();
  } catch (error) {
    console.error('Error stopping timer:', error);
    showError('Failed to stop timer: ' + (error.response?.data?.error || error.message));
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
  if (!timer) {
    // Notify tray that timer is stopped
    if (window.electronAPI && window.electronAPI.sendTimerStatus) {
      window.electronAPI.sendTimerStatus({ active: false });
    }
    return;
  }
  
  const startTime = new Date(timer.start_time);
  const now = new Date();
  const seconds = Math.floor((now - startTime) / 1000);
  
  document.getElementById('timer-display').textContent = formatDurationLong(seconds);
  document.getElementById('timer-project').textContent = timer.project?.name || 'Unknown Project';
  
  // Show task if available
  const taskEl = document.getElementById('timer-task');
  if (timer.task) {
    taskEl.textContent = timer.task.name;
    taskEl.style.display = 'block';
  } else {
    taskEl.style.display = 'none';
  }
  
  // Show notes if available
  const notesEl = document.getElementById('timer-notes');
  if (timer.notes) {
    notesEl.textContent = timer.notes;
    notesEl.style.display = 'block';
  } else {
    notesEl.style.display = 'none';
  }
  
  // Notify tray that timer is running
  if (window.electronAPI && window.electronAPI.sendTimerStatus) {
    window.electronAPI.sendTimerStatus({ active: true, timer: timer });
  }
}

async function loadSettings() {
  // Load current settings
  const serverUrl = await storeGet('server_url') || '';
  const apiToken = await storeGet('api_token') || '';
  const autoSync = await storeGet('auto_sync');
  const syncInterval = await storeGet('sync_interval');
  
  const serverUrlInput = document.getElementById('settings-server-url');
  const apiTokenInput = document.getElementById('settings-api-token');
  const autoSyncInput = document.getElementById('auto-sync');
  const syncIntervalInput = document.getElementById('sync-interval');
  
  if (serverUrlInput) {
    serverUrlInput.value = serverUrl;
  }
  if (apiTokenInput) {
    // Only show if token exists, otherwise leave empty
    apiTokenInput.value = apiToken ? '••••••••' : '';
    apiTokenInput.dataset.hasToken = apiToken ? 'true' : 'false';
  }
  if (autoSyncInput) {
    autoSyncInput.checked = autoSync !== null ? Boolean(autoSync) : true;
  }
  if (syncIntervalInput) {
    syncIntervalInput.value = (syncInterval || 60).toString();
  }
  updateSyncIntervalState();
}

function updateSyncIntervalState() {
  const autoSyncInput = document.getElementById('auto-sync');
  const syncIntervalInput = document.getElementById('sync-interval');
  if (!autoSyncInput || !syncIntervalInput) return;
  syncIntervalInput.disabled = !autoSyncInput.checked;
}

async function handleSaveSettings() {
  const serverUrlInput = document.getElementById('settings-server-url');
  const apiTokenInput = document.getElementById('settings-api-token');
  const autoSyncInput = document.getElementById('auto-sync');
  const syncIntervalInput = document.getElementById('sync-interval');
  const messageDiv = document.getElementById('settings-message');
  
  if (!serverUrlInput || !apiTokenInput || !autoSyncInput || !syncIntervalInput) return;
  
  const serverUrl = serverUrlInput.value.trim();
  const apiToken = apiTokenInput.value.trim();
  const autoSync = autoSyncInput.checked;
  const syncInterval = parseInt(syncIntervalInput.value, 10);
  
  // Validate server URL
  if (!serverUrl || !isValidUrl(serverUrl)) {
    showSettingsMessage('Please enter a valid server URL', 'error');
    return;
  }
  
  // Check if API token was changed (if it's not the masked value)
  const hasExistingToken = apiTokenInput.dataset.hasToken === 'true';
  let finalApiToken = apiToken;
  
  // If token input shows masked value and user didn't change it, keep existing token
  if (hasExistingToken && apiToken === '••••••••') {
    finalApiToken = await storeGet('api_token');
  } else if (!apiToken || !apiToken.startsWith('tt_')) {
    showSettingsMessage('Please enter a valid API token (must start with tt_)', 'error');
    return;
  }

  if (Number.isNaN(syncInterval) || syncInterval < 10) {
    showSettingsMessage('Sync interval must be at least 10 seconds', 'error');
    return;
  }
  
  // Save settings
  try {
    await storeSet('server_url', serverUrl);
    await storeSet('api_token', finalApiToken);
    await storeSet('auto_sync', autoSync);
    await storeSet('sync_interval', syncInterval);
    
    // Reinitialize API client with new settings
    apiClient = new ApiClient(serverUrl);
    await apiClient.setAuthToken(finalApiToken);
    
    // Validate connection
    const isValid = await apiClient.validateToken();
    if (isValid) {
      updateConnectionStatus('connected');
      showSettingsMessage('Settings saved successfully!', 'success');
      // Update token input to show masked value
      apiTokenInput.value = '••••••••';
      apiTokenInput.dataset.hasToken = 'true';
    } else {
      updateConnectionStatus('error');
      showSettingsMessage('Settings saved, but connection test failed. Please check your API token.', 'warning');
    }
  } catch (error) {
    console.error('Error saving settings:', error);
    showSettingsMessage('Error saving settings: ' + error.message, 'error');
  }
}

async function handleTestConnection() {
  const serverUrlInput = document.getElementById('settings-server-url');
  const apiTokenInput = document.getElementById('settings-api-token');
  const messageDiv = document.getElementById('settings-message');
  
  if (!serverUrlInput || !apiTokenInput) return;
  
  const serverUrl = serverUrlInput.value.trim();
  let apiToken = apiTokenInput.value.trim();
  
  // Validate server URL
  if (!serverUrl || !isValidUrl(serverUrl)) {
    showSettingsMessage('Please enter a valid server URL', 'error');
    return;
  }
  
  // Get actual token if masked
  const hasExistingToken = apiTokenInput.dataset.hasToken === 'true';
  if (hasExistingToken && apiToken === '••••••••') {
    apiToken = await storeGet('api_token');
  }
  
  if (!apiToken || !apiToken.startsWith('tt_')) {
    showSettingsMessage('Please enter a valid API token (must start with tt_)', 'error');
    return;
  }
  
  // Test connection
  try {
    showSettingsMessage('Testing connection...', 'info');
    const testClient = new ApiClient(serverUrl);
    await testClient.setAuthToken(apiToken);
    const isValid = await testClient.validateToken();
    
    if (isValid) {
      updateConnectionStatus('connected');
      showSettingsMessage('Connection successful!', 'success');
    } else {
      updateConnectionStatus('error');
      showSettingsMessage('Connection failed. Please check your server URL and API token.', 'error');
    }
  } catch (error) {
    console.error('Error testing connection:', error);
    showSettingsMessage('Connection error: ' + error.message, 'error');
  }
}

function showSettingsMessage(message, type = 'info') {
  const messageDiv = document.getElementById('settings-message');
  if (!messageDiv) return;
  
  messageDiv.textContent = message;
  messageDiv.className = `message message-${type}`;
  messageDiv.style.display = 'block';
  
  // Auto-hide after 5 seconds for success/info messages
  if (type === 'success' || type === 'info') {
    setTimeout(() => {
      messageDiv.style.display = 'none';
    }, 5000);
  }
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

// Filter functions
function toggleFilters() {
  const filtersEl = document.getElementById('entries-filters');
  if (filtersEl) {
    filtersEl.style.display = filtersEl.style.display === 'none' ? 'block' : 'none';
  }
}

async function applyFilters() {
  const startDate = document.getElementById('filter-start-date')?.value || null;
  const endDate = document.getElementById('filter-end-date')?.value || null;
  const projectId = document.getElementById('filter-project')?.value 
    ? parseInt(document.getElementById('filter-project').value) 
    : null;
  
  currentFilters = { startDate, endDate, projectId };
  await loadTimeEntries();
}

function clearFilters() {
  currentFilters = { startDate: null, endDate: null, projectId: null };
  document.getElementById('filter-start-date').value = '';
  document.getElementById('filter-end-date').value = '';
  document.getElementById('filter-project').value = '';
  loadTimeEntries();
}

// Load projects for filter dropdown
async function loadProjectsForFilter() {
  if (!apiClient) return;
  
  try {
    const response = await apiClient.getProjects({ status: 'active' });
    const projects = response.data.projects || [];
    const select = document.getElementById('filter-project');
    if (select) {
      select.innerHTML = '<option value="">All Projects</option>' +
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
      if (currentFilters.projectId) {
        select.value = String(currentFilters.projectId);
      }
    }
  } catch (error) {
    console.error('Error loading projects for filter:', error);
  }
}

// Time entry form
async function showTimeEntryForm(entryId = null) {
  // Load projects
  let projects = [];
  try {
    const projectsResponse = await apiClient.getProjects({ status: 'active' });
    projects = projectsResponse.data.projects || [];
  } catch (error) {
    showError('Failed to load projects');
    return;
  }
  
  // Load entry if editing
  let entry = null;
  if (entryId) {
    try {
      const entryResponse = await apiClient.getTimeEntry(entryId);
      entry = entryResponse.data.time_entry;
    } catch (error) {
      showError('Failed to load time entry');
      return;
    }
  }
  
  // Load tasks if project is selected
  let tasks = [];
  const projectId = entry ? entry.project_id : null;
  if (projectId) {
    try {
      const tasksResponse = await apiClient.getTasks({ projectId: projectId });
      tasks = tasksResponse.data.tasks || [];
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  }
  
  // Create modal
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  const startDate = entry 
    ? new Date(entry.start_time).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0];
  const startTime = entry
    ? new Date(entry.start_time).toTimeString().slice(0, 5)
    : new Date().toTimeString().slice(0, 5);
  const endDate = entry && entry.end_time
    ? new Date(entry.end_time).toISOString().split('T')[0]
    : '';
  const endTime = entry && entry.end_time
    ? new Date(entry.end_time).toTimeString().slice(0, 5)
    : '';
  
  modal.innerHTML = `
    <div class="modal-content" style="max-width: 600px;">
      <div class="modal-header">
        <h3>${entryId ? 'Edit' : 'Add'} Time Entry</h3>
        <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label for="entry-project-select">Project *</label>
          <select id="entry-project-select" class="form-control" required>
            <option value="">Select a project...</option>
            ${projects.map(p => `<option value="${p.id}" ${entry && entry.project_id === p.id ? 'selected' : ''}>${p.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label for="entry-task-select">Task (Optional)</label>
          <select id="entry-task-select" class="form-control">
            <option value="">No task</option>
            ${tasks.map(t => `<option value="${t.id}" ${entry && entry.task_id === t.id ? 'selected' : ''}>${t.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="entry-start-date">Start Date *</label>
            <input type="date" id="entry-start-date" class="form-control" value="${startDate}" required>
          </div>
          <div class="form-group">
            <label for="entry-start-time">Start Time *</label>
            <input type="time" id="entry-start-time" class="form-control" value="${startTime}" required>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="entry-end-date">End Date (Optional)</label>
            <input type="date" id="entry-end-date" class="form-control" value="${endDate}">
          </div>
          <div class="form-group">
            <label for="entry-end-time">End Time (Optional)</label>
            <input type="time" id="entry-end-time" class="form-control" value="${endTime}">
          </div>
        </div>
        <div class="form-group">
          <label for="entry-notes">Notes</label>
          <textarea id="entry-notes" class="form-control" rows="3">${entry?.notes || ''}</textarea>
        </div>
        <div class="form-group">
          <label for="entry-tags">Tags (comma-separated)</label>
          <input type="text" id="entry-tags" class="form-control" value="${entry?.tags || ''}">
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" id="entry-billable" ${entry ? (entry.billable ? 'checked' : '') : 'checked'}>
            Billable
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
        <button class="btn btn-primary" id="save-entry-btn">${entryId ? 'Update' : 'Create'}</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  const projectSelect = modal.querySelector('#entry-project-select');
  const taskSelect = modal.querySelector('#entry-task-select');
  const saveBtn = modal.querySelector('#save-entry-btn');
  
  // Load tasks when project changes
  projectSelect.addEventListener('change', async (e) => {
    const projectId = parseInt(e.target.value);
    if (!projectId) {
      taskSelect.innerHTML = '<option value="">No task</option>';
      return;
    }
    
    try {
      const tasksResponse = await apiClient.getTasks({ projectId: projectId });
      const tasks = tasksResponse.data.tasks || [];
      taskSelect.innerHTML = '<option value="">No task</option>' +
        tasks.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  });
  
  // Handle save
  saveBtn.addEventListener('click', async () => {
    const projectId = parseInt(projectSelect.value);
    if (!projectId) {
      showError('Please select a project');
      return;
    }
    
    const taskId = taskSelect.value ? parseInt(taskSelect.value) : null;
    const startDate = document.getElementById('entry-start-date').value;
    const startTime = document.getElementById('entry-start-time').value;
    const endDate = document.getElementById('entry-end-date').value;
    const endTime = document.getElementById('entry-end-time').value;
    const notes = document.getElementById('entry-notes').value.trim() || null;
    const tags = document.getElementById('entry-tags').value.trim() || null;
    const billable = document.getElementById('entry-billable').checked;
    
    const startDateTime = new Date(`${startDate}T${startTime}`).toISOString();
    const endDateTime = (endDate && endTime) 
      ? new Date(`${endDate}T${endTime}`).toISOString()
      : null;
    
    try {
      if (entryId) {
        await apiClient.updateTimeEntry(entryId, {
          project_id: projectId,
          task_id: taskId,
          start_time: startDateTime,
          end_time: endDateTime,
          notes: notes,
          tags: tags,
          billable: billable,
        });
        showSuccess('Time entry updated successfully');
      } else {
        await apiClient.createTimeEntry({
          project_id: projectId,
          task_id: taskId,
          start_time: startDateTime,
          end_time: endDateTime,
          notes: notes,
          tags: tags,
          billable: billable,
        });
        showSuccess('Time entry created successfully');
      }
      
      modal.remove();
      loadTimeEntries();
    } catch (error) {
      showError('Failed to save time entry: ' + (error.response?.data?.error || error.message));
    }
  });
  
  // Close on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

function showError(message) {
  // Create or update error notification
  let errorDiv = document.getElementById('error-notification');
  if (!errorDiv) {
    errorDiv = document.createElement('div');
    errorDiv.id = 'error-notification';
    errorDiv.className = 'notification notification-error';
    document.body.appendChild(errorDiv);
  }
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 5000);
}

function showSuccess(message) {
  // Create or update success notification
  let successDiv = document.getElementById('success-notification');
  if (!successDiv) {
    successDiv = document.createElement('div');
    successDiv.id = 'success-notification';
    successDiv.className = 'notification notification-success';
    document.body.appendChild(successDiv);
  }
  successDiv.textContent = message;
  successDiv.style.display = 'block';
  setTimeout(() => {
    successDiv.style.display = 'none';
  }, 3000);
}
