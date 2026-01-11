const axios = require('axios');
const { storeGet, storeSet } = require('../../../../shared/config');

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    
    this.setupInterceptors();
  }
  
  setupInterceptors() {
    // Add auth token to requests
    this.client.interceptors.request.use(async (config) => {
      const token = await storeGet('api_token');
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      return config;
    });
    
    // Handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          // Could trigger re-auth flow here
        }
        return Promise.reject(error);
      }
    );
  }
  
  async setAuthToken(token) {
    await storeSet('api_token', token);
  }
  
  async validateToken() {
    try {
      const response = await this.client.get('/api/v1/info');
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }
  
  // Timer endpoints
  async getTimerStatus() {
    return await this.client.get('/api/v1/timer/status');
  }
  
  async startTimer({ projectId, taskId, notes }) {
    return await this.client.post('/api/v1/timer/start', {
      project_id: projectId,
      task_id: taskId,
      notes: notes,
    });
  }
  
  async stopTimer() {
    return await this.client.post('/api/v1/timer/stop');
  }
  
  // Time entries endpoints
  async getTimeEntries({ projectId, startDate, endDate, billable, page, perPage }) {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (billable !== undefined) params.billable = billable;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    
    return await this.client.get('/api/v1/time-entries', { params });
  }
  
  async createTimeEntry(data) {
    return await this.client.post('/api/v1/time-entries', data);
  }
  
  async updateTimeEntry(id, data) {
    return await this.client.put(`/api/v1/time-entries/${id}`, data);
  }
  
  async deleteTimeEntry(id) {
    return await this.client.delete(`/api/v1/time-entries/${id}`);
  }
  
  // Projects endpoints
  async getProjects({ status, clientId, page, perPage }) {
    const params = {};
    if (status) params.status = status;
    if (clientId) params.client_id = clientId;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    
    return await this.client.get('/api/v1/projects', { params });
  }
  
  async getProject(id) {
    return await this.client.get(`/api/v1/projects/${id}`);
  }
  
  // Tasks endpoints
  async getTasks({ projectId, status, page, perPage }) {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (status) params.status = status;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    
    return await this.client.get('/api/v1/tasks', { params });
  }
  
  async getTask(id) {
    return await this.client.get(`/api/v1/tasks/${id}`);
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ApiClient;
}
