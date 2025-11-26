/**
 * Kiosk Mode - Timer Integration
 */

let timerInterval = null;
let lastTimerUpdate = 0;
const TIMER_UPDATE_INTERVAL = 1000; // Update every second
const TIMER_API_INTERVAL = 5000; // Poll API every 5 seconds
let lastApiCheck = 0;

// Initialize timer display
document.addEventListener('DOMContentLoaded', function() {
    updateTimerDisplay();
    
    // Update timer display every second (client-side calculation)
    // Poll API less frequently to reduce server load
    timerInterval = setInterval(() => {
        const now = Date.now();
        
        // Update display every second
        if (now - lastTimerUpdate >= TIMER_UPDATE_INTERVAL) {
            updateTimerDisplay(true); // true = use client-side calculation
            lastTimerUpdate = now;
        }
        
        // Poll API every 5 seconds
        if (now - lastApiCheck >= TIMER_API_INTERVAL) {
            updateTimerDisplay(false); // false = fetch from API
            lastApiCheck = now;
        }
    }, TIMER_UPDATE_INTERVAL);
    
    // Handle timer form submission
    const timerForm = document.getElementById('timer-form');
    if (timerForm) {
        timerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            await startTimer();
        });
    }
});

// Cache timer data for client-side calculation
let cachedTimerData = null;

/**
 * Update timer display
 * @param {boolean} useCache - If true, use cached data and calculate client-side. If false, fetch from API.
 */
async function updateTimerDisplay(useCache = false) {
    try {
        let data = cachedTimerData;
        
        // Fetch from API if not using cache or cache is stale
        if (!useCache || !data) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            try {
                const response = await fetch('/api/kiosk/timer-status', {
                    credentials: 'same-origin',
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    // On error, try to use cached data if available
                    if (cachedTimerData) {
                        data = cachedTimerData;
                    } else {
                        return;
                    }
                } else {
                    data = await response.json();
                    cachedTimerData = data; // Cache the data
                }
            } catch (error) {
                clearTimeout(timeoutId);
                // Use cached data on network error
                if (cachedTimerData) {
                    data = cachedTimerData;
                } else {
                    return;
                }
            }
        }
        
        const timerDisplay = document.getElementById('kiosk-timer-display');
        if (!timerDisplay || !data) return;

        if (data.active && data.timer) {
            // Calculate elapsed time
            const startTime = new Date(data.timer.start_time);
            const now = new Date();
            const elapsed = Math.floor((now - startTime) / 1000);
            
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            const seconds = elapsed % 60;
            
            const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            
            timerDisplay.innerHTML = `
                <i class="fas fa-clock"></i>
                <span id="timer-time" class="font-mono">${timeString}</span>
                <span class="text-sm font-normal text-text-muted-light dark:text-text-muted-dark">${data.timer.project_name || ''}</span>
            `;
            
            // Update timer controls section
            const timerControls = document.getElementById('timer-controls');
            if (timerControls) {
                timerControls.innerHTML = `
                    <div class="bg-background-light dark:bg-gray-700 rounded-xl p-10 mb-6 text-center border-2 border-border-light dark:border-border-dark">
                        <p class="font-semibold text-xl mb-4 text-text-light dark:text-text-dark">Active Timer</p>
                        <p class="text-5xl font-bold text-primary mb-4 font-mono" id="timer-display">${timeString}</p>
                        <p class="text-xl text-text-light dark:text-text-dark mb-2 font-medium">${data.timer.project_name || ''}</p>
                        ${data.timer.task_name ? `<p class="text-text-muted-light dark:text-text-muted-dark">${data.timer.task_name}</p>` : ''}
                    </div>
                    <button onclick="stopTimer()" class="btn btn-danger w-full py-4 text-lg font-semibold rounded-lg">
                        <i class="fas fa-stop mr-2"></i>
                        Stop Timer
                    </button>
                `;
            }
        } else {
            cachedTimerData = null; // Clear cache when timer stops
            timerDisplay.innerHTML = `
                <i class="fas fa-clock text-text-muted-light dark:text-text-muted-dark"></i>
                <span class="text-text-muted-light dark:text-text-muted-dark font-medium">No active timer</span>
            `;
            
            // Update timer controls section - show start timer form
            const timerControls = document.getElementById('timer-controls');
            if (timerControls) {
                // Only update if we're on the timer tab
                const timerTab = document.getElementById('tab-timer');
                if (timerTab && timerTab.style.display !== 'none') {
                    // Check if form already exists with projects loaded - don't recreate it
                    const existingForm = document.getElementById('timer-form');
                    const existingProjectSelect = document.getElementById('timer-project');
                    if (existingForm && existingProjectSelect && existingProjectSelect.options.length > 1) {
                        // Form already exists with projects loaded, don't recreate
                        return;
                    }
                    
                    // Fetch projects for the form
                    fetch('/api/kiosk/projects', {
                        credentials: 'same-origin'
                    }).then(res => {
                        if (!res.ok) {
                            // Try to parse error message
                            return res.json().then(err => {
                                throw new Error(err.error || 'Failed to fetch projects');
                            }).catch(() => {
                                throw new Error('Failed to fetch projects');
                            });
                        }
                        return res.json();
                    }).then(data => {
                        const projects = data.projects || [];
                        let projectOptions = '';
                        if (projects.length > 0) {
                            projectOptions = projects.map(p => 
                                `<option value="${p.id}">${p.name}</option>`
                            ).join('');
                        } else {
                            projectOptions = '<option value="" disabled>No projects available</option>';
                        }
                        
                        timerControls.innerHTML = `
                            <form id="timer-form" class="space-y-6">
                                <div>
                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Project <span class="text-red-500">*</span></label>
                                    <div class="relative">
                                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <i class="fas fa-project-diagram text-gray-400"></i>
                                        </div>
                                        <select id="timer-project" class="w-full pl-10 bg-gray-50 dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 text-lg text-gray-900 dark:text-white focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/20 transition-all appearance-none cursor-pointer" required>
                                            <option value="">Select project...</option>
                                            ${projectOptions}
                                        </select>
                                        ${projects.length === 0 ? '<p class="text-xs text-yellow-600 dark:text-yellow-400 mt-1.5 flex items-center gap-1"><i class="fas fa-exclamation-triangle"></i>No active projects found. Please create a project first.</p>' : ''}
                                        <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                            <i class="fas fa-chevron-down text-gray-400"></i>
                                        </div>
                                    </div>
                                </div>
                                
                                <div>
                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Task <span class="text-gray-500 dark:text-gray-400 font-normal">(Optional)</span></label>
                                    <div class="relative">
                                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <i class="fas fa-tasks text-gray-400"></i>
                                        </div>
                                        <select id="timer-task" class="w-full pl-10 bg-gray-50 dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 text-lg text-gray-900 dark:text-white focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/20 transition-all appearance-none cursor-pointer" disabled>
                                            <option value="">No task</option>
                                        </select>
                                        <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                            <i class="fas fa-chevron-down text-gray-400"></i>
                                        </div>
                                    </div>
                                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Tasks will load after selecting a project</p>
                                </div>
                                
                                <div>
                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Notes <span class="text-gray-500 dark:text-gray-400 font-normal">(Optional)</span></label>
                                    <textarea id="timer-notes" class="w-full bg-gray-50 dark:bg-gray-900 border-2 border-gray-300 dark:border-gray-600 rounded-xl px-4 py-3 text-gray-900 dark:text-white focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/20 transition-all resize-none" rows="4" placeholder="What are you working on?"></textarea>
                                </div>
                                
                                <button type="submit" class="w-full bg-primary hover:bg-primary/90 text-white font-semibold py-4 px-6 rounded-xl transition-colors shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 flex items-center justify-center gap-2">
                                    <i class="fas fa-play"></i>
                                    Start Timer
                                </button>
                            </form>
                        `;
                        
                        // Re-attach form handler
                        const newTimerForm = document.getElementById('timer-form');
                        if (newTimerForm) {
                            newTimerForm.addEventListener('submit', async function(e) {
                                e.preventDefault();
                                await startTimer();
                            });
                            
                            // Add project change handler to load tasks
                            const projectSelect = document.getElementById('timer-project');
                            const taskSelect = document.getElementById('timer-task');
                            
                            if (projectSelect && taskSelect) {
                                projectSelect.addEventListener('change', function() {
                                    const projectId = this.value;
                                    
                                    // Reset task select
                                    taskSelect.innerHTML = '<option value="">No task</option>';
                                    taskSelect.disabled = true;
                                    
                                    if (!projectId) {
                                        return;
                                    }
                                    
                                    // Fetch tasks for selected project
                                    fetch(`/api/tasks?project_id=${projectId}`, {
                                        credentials: 'same-origin'
                                    })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.tasks && data.tasks.length > 0) {
                                            taskSelect.disabled = false;
                                            data.tasks.forEach(task => {
                                                const option = document.createElement('option');
                                                option.value = task.id;
                                                option.textContent = task.name;
                                                taskSelect.appendChild(option);
                                            });
                                        } else {
                                            taskSelect.disabled = false;
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error loading tasks:', error);
                                        taskSelect.disabled = false;
                                    });
                                });
                            }
                        }
                    }).catch(err => {
                        // Throttle error logging - only log once per minute
                        const now = Date.now();
                        if (!window._lastProjectErrorTime || (now - window._lastProjectErrorTime) > 60000) {
                            console.error('Error fetching projects:', err);
                            window._lastProjectErrorTime = now;
                        }
                        // Only show error message if timer controls exist and we haven't shown an error recently
                        if (timerControls && (!window._lastProjectErrorShown || (now - window._lastProjectErrorShown) > 60000)) {
                            timerControls.innerHTML = '<div class="text-red-600 dark:text-red-400 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"><i class="fas fa-exclamation-triangle mr-2"></i>Error loading projects. Please refresh the page.</div>';
                            window._lastProjectErrorShown = now;
                        }
                    });
                }
            }
        }
    } catch (error) {
        console.error('Error updating timer display:', error);
    }
}

/**
 * Start timer
 */
async function startTimer() {
    const projectId = document.getElementById('timer-project')?.value;
    const taskId = document.getElementById('timer-task')?.value || null;
    const notes = document.getElementById('timer-notes')?.value || '';

    if (!projectId) {
        showError('Please select a project');
        return;
    }
    
    // Set loading state
    const submitBtn = document.getElementById('timer-submit-btn');
    const submitIcon = document.getElementById('timer-submit-icon');
    const submitText = document.getElementById('timer-submit-text');
    const submitSpinner = document.getElementById('timer-submit-spinner');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        if (submitIcon) submitIcon.classList.add('hidden');
        if (submitText) submitText.textContent = 'Starting...';
        if (submitSpinner) submitSpinner.classList.remove('hidden');
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const response = await fetch('/api/kiosk/start-timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                project_id: parseInt(projectId),
                task_id: taskId ? parseInt(taskId) : null,
                notes: notes
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start timer');
        }

        const data = await response.json();
        showSuccess(data.message || 'Timer started successfully');
        
        // Clear cache and update display immediately
        cachedTimerData = null;
        updateTimerDisplay(false); // Force API fetch
        
        // Switch to timer tab and update controls
        const timerTab = document.querySelector('.kiosk-tab[data-tab="timer"]');
        if (timerTab) {
            timerTab.click();
        }
        
        // Update timer controls after a brief delay
        setTimeout(() => {
            updateTimerDisplay(false);
        }, 500);
    } catch (error) {
        console.error('Start timer error:', error);
        showError(error.message || 'Failed to start timer');
    } finally {
        // Reset loading state
        if (submitBtn) {
            submitBtn.disabled = false;
            if (submitIcon) submitIcon.classList.remove('hidden');
            if (submitText) submitText.textContent = 'Start Timer';
            if (submitSpinner) submitSpinner.classList.add('hidden');
        }
    }
}

/**
 * Stop timer
 */
async function stopTimer() {
    // Use showConfirm if available, otherwise use native confirm
    let confirmed = false;
    if (window.showConfirm) {
        confirmed = await window.showConfirm('Stop the active timer?', {
            title: 'Stop Timer',
            confirmText: 'Stop',
            cancelText: 'Cancel',
            variant: 'warning'
        });
    } else {
        confirmed = confirm('Stop the active timer?');
    }
    
    if (!confirmed) {
        return;
    }
    
    // Set loading state
    const stopBtn = document.getElementById('timer-stop-btn');
    const stopIcon = document.getElementById('timer-stop-icon');
    const stopText = document.getElementById('timer-stop-text');
    const stopSpinner = document.getElementById('timer-stop-spinner');
    
    if (stopBtn) {
        stopBtn.disabled = true;
        if (stopIcon) stopIcon.classList.add('hidden');
        if (stopText) stopText.textContent = 'Stopping...';
        if (stopSpinner) stopSpinner.classList.remove('hidden');
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const response = await fetch('/api/kiosk/stop-timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || ''
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to stop timer');
        }

        const data = await response.json();
        showSuccess(data.message || 'Timer stopped successfully');
        
        // Clear cache and update display immediately
        cachedTimerData = null;
        updateTimerDisplay(false); // Force API fetch
        
        // Update timer controls after a brief delay
        setTimeout(() => {
            updateTimerDisplay(false);
        }, 500);
    } catch (error) {
        console.error('Stop timer error:', error);
        showError(error.message || 'Failed to stop timer');
    } finally {
        // Reset loading state
        if (stopBtn) {
            stopBtn.disabled = false;
            if (stopIcon) stopIcon.classList.remove('hidden');
            if (stopText) stopText.textContent = 'Stop Timer';
            if (stopSpinner) stopSpinner.classList.add('hidden');
        }
    }
}

/**
 * Show error message - use toast notifications if available
 */
function showError(message) {
    // Use toast notifications if available
    if (window.showToast) {
        window.showToast(message, 'error');
    } else {
        // Fallback to alert
        alert('Error: ' + message);
    }
}

/**
 * Show success message - use toast notifications if available
 */
function showSuccess(message) {
    // Use toast notifications if available
    if (window.showToast) {
        window.showToast(message, 'success');
    } else {
        // Fallback to alert
        alert('Success: ' + message);
    }
}

// Make stopTimer globally available
window.stopTimer = stopTimer;

