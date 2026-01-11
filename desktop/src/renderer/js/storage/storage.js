// Storage utilities for local database
// Uses IndexedDB via Dexie for offline storage

const Dexie = require('dexie');

class TimeTrackerDB extends Dexie {
  constructor() {
    super('TimeTrackerDB');
    
    this.version(1).stores({
      timeEntries: 'id, startTime, projectId, userId',
      projects: 'id, name, status',
      tasks: 'id, projectId, status',
      syncQueue: '++id, type, action, data, timestamp',
    });
  }
}

const db = new TimeTrackerDB();

// Storage service
const StorageService = {
  // Time Entries
  async saveTimeEntry(entry) {
    return await db.timeEntries.put(entry);
  },
  
  async getTimeEntries(filters = {}) {
    let collection = db.timeEntries.toCollection();
    
    if (filters.startDate) {
      collection = collection.filter(entry => entry.startTime >= filters.startDate);
    }
    if (filters.endDate) {
      collection = collection.filter(entry => entry.startTime <= filters.endDate);
    }
    if (filters.projectId) {
      collection = collection.filter(entry => entry.projectId === filters.projectId);
    }
    
    return await collection.toArray();
  },
  
  async deleteTimeEntry(id) {
    return await db.timeEntries.delete(id);
  },
  
  // Projects
  async saveProject(project) {
    return await db.projects.put(project);
  },
  
  async getProjects(filters = {}) {
    let collection = db.projects.toCollection();
    
    if (filters.status) {
      collection = collection.filter(project => project.status === filters.status);
    }
    
    return await collection.toArray();
  },
  
  async deleteProject(id) {
    return await db.projects.delete(id);
  },
  
  // Tasks
  async saveTask(task) {
    return await db.tasks.put(task);
  },
  
  async getTasks(filters = {}) {
    let collection = db.tasks.toCollection();
    
    if (filters.projectId) {
      collection = collection.filter(task => task.projectId === filters.projectId);
    }
    if (filters.status) {
      collection = collection.filter(task => task.status === filters.status);
    }
    
    return await collection.toArray();
  },
  
  // Sync Queue
  async addToSyncQueue(type, action, data) {
    return await db.syncQueue.add({
      type, // 'time_entry', 'project', etc.
      action, // 'create', 'update', 'delete'
      data,
      timestamp: new Date(),
    });
  },
  
  async getSyncQueue() {
    return await db.syncQueue.toArray();
  },
  
  async removeFromSyncQueue(id) {
    return await db.syncQueue.delete(id);
  },
  
  async clearSyncQueue() {
    return await db.syncQueue.clear();
  },
  
  // Clear all data
  async clearAll() {
    await db.timeEntries.clear();
    await db.projects.clear();
    await db.tasks.clear();
    await db.syncQueue.clear();
  },
};

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StorageService;
}

if (typeof window !== 'undefined') {
  window.StorageService = StorageService;
}
