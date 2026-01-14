import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/models/timer.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/data/models/task.dart';
import 'package:timetracker_mobile/data/storage/local_storage.dart';
import 'package:timetracker_mobile/data/storage/sync_service.dart';

/// Repository for time tracking operations
class TimeTrackingRepository {
  final ApiClient? apiClient;
  final Connectivity _connectivity = Connectivity();
  SyncService? _syncService;

  TimeTrackingRepository(this.apiClient) {
    _syncService = SyncService(apiClient);
  }

  Future<bool> _isOnline() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }

  // ==================== Timer Operations ====================

  /// Get current timer status
  Future<Timer?> getTimerStatus() async {
    if (apiClient == null) {
      // Return cached timer if offline
      return await LocalStorage.getTimer();
    }

    try {
      final isOnline = await _isOnline();
      if (!isOnline) {
        return await LocalStorage.getTimer();
      }

      final response = await apiClient!.getTimerStatus();
      if (response['active'] == true && response['timer'] != null) {
        final timer = Timer.fromJson(response['timer'] as Map<String, dynamic>);
        await LocalStorage.saveTimer(timer);
        return timer;
      }
      await LocalStorage.clearTimer();
      return null;
    } catch (e) {
      // Return cached timer on error
      return await LocalStorage.getTimer();
    }
  }

  /// Start a timer
  Future<Timer> startTimer({
    required int projectId,
    int? taskId,
    String? notes,
    int? templateId,
  }) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }

    try {
      final isOnline = await _isOnline();
      if (!isOnline) {
        // Queue for sync
        await SyncService.queueCreateTimeEntry(
          projectId: projectId,
          taskId: taskId,
          startTime: DateTime.now().toIso8601String(),
          notes: notes,
        );
        // Create a local timer representation
        final timer = Timer(
          id: DateTime.now().millisecondsSinceEpoch,
          userId: 0, // Will be set by server
          projectId: projectId,
          taskId: taskId,
          startTime: DateTime.now(),
          notes: notes,
        );
        await LocalStorage.saveTimer(timer);
        return timer;
      }

      final response = await apiClient!.startTimer(
        projectId: projectId,
        taskId: taskId,
        notes: notes,
        templateId: templateId,
      );
      final timer = Timer.fromJson(response['timer'] as Map<String, dynamic>);
      await LocalStorage.saveTimer(timer);
      return timer;
    } catch (e) {
      throw Exception('Failed to start timer: $e');
    }
  }

  /// Stop the active timer
  Future<TimeEntry> stopTimer() async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.stopTimer();
      return TimeEntry.fromJson(response['time_entry'] as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to stop timer: $e');
    }
  }

  // ==================== Time Entry Operations ====================

  /// Get time entries with filters
  Future<List<TimeEntry>> getTimeEntries({
    int? projectId,
    String? startDate,
    String? endDate,
    bool? billable,
    int? page,
    int? perPage,
  }) async {
    if (apiClient == null) {
      // Return cached entries if offline
      final entries = await LocalStorage.getAllTimeEntries();
      // Apply basic filtering
      var filtered = entries;
      if (projectId != null) {
        filtered = filtered.where((e) => e.projectId == projectId).toList();
      }
      return filtered;
    }

    try {
      final isOnline = await _isOnline();
      if (!isOnline) {
        // Return cached entries
        final entries = await LocalStorage.getAllTimeEntries();
        var filtered = entries;
        if (projectId != null) {
          filtered = filtered.where((e) => e.projectId == projectId).toList();
        }
        return filtered;
      }

      final response = await apiClient!.getTimeEntries(
        projectId: projectId,
        startDate: startDate,
        endDate: endDate,
        billable: billable,
        page: page,
        perPage: perPage,
      );
      final entries = response['time_entries'] as List<dynamic>? ?? [];
      final timeEntries = entries
          .map((e) => TimeEntry.fromJson(e as Map<String, dynamic>))
          .toList();
      
      // Cache entries
      for (final entry in timeEntries) {
        await LocalStorage.saveTimeEntry(entry);
      }
      
      return timeEntries;
    } catch (e) {
      // Return cached entries on error
      final entries = await LocalStorage.getAllTimeEntries();
      var filtered = entries;
      if (projectId != null) {
        filtered = filtered.where((e) => e.projectId == projectId).toList();
      }
      return filtered;
    }
  }

  /// Get a specific time entry
  Future<TimeEntry> getTimeEntry(int entryId) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.getTimeEntry(entryId);
      return TimeEntry.fromJson(response['time_entry'] as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to get time entry: $e');
    }
  }

  /// Create a manual time entry
  Future<TimeEntry> createTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }

    try {
      final isOnline = await _isOnline();
      if (!isOnline) {
        // Queue for sync
        await SyncService.queueCreateTimeEntry(
          projectId: projectId,
          taskId: taskId,
          startTime: startTime,
          endTime: endTime,
          notes: notes,
          tags: tags,
          billable: billable,
        );
        // Create a local entry representation
        final entry = TimeEntry(
          id: DateTime.now().millisecondsSinceEpoch,
          userId: 0,
          projectId: projectId,
          taskId: taskId,
          startTime: DateTime.parse(startTime),
          endTime: endTime != null ? DateTime.parse(endTime) : null,
          notes: notes,
          tags: tags,
          billable: billable ?? true,
          paid: false,
          source: 'manual',
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
        );
        await LocalStorage.saveTimeEntry(entry);
        return entry;
      }

      final response = await apiClient!.createTimeEntry(
        projectId: projectId,
        taskId: taskId,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        tags: tags,
        billable: billable,
      );
      final entry = TimeEntry.fromJson(response['time_entry'] as Map<String, dynamic>);
      await LocalStorage.saveTimeEntry(entry);
      return entry;
    } catch (e) {
      throw Exception('Failed to create time entry: $e');
    }
  }

  /// Update a time entry
  Future<TimeEntry> updateTimeEntry(
    int entryId, {
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.updateTimeEntry(
        entryId,
        projectId: projectId,
        taskId: taskId,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        tags: tags,
        billable: billable,
      );
      return TimeEntry.fromJson(response['time_entry'] as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to update time entry: $e');
    }
  }

  /// Delete a time entry
  Future<void> deleteTimeEntry(int entryId) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }

    try {
      final isOnline = await _isOnline();
      if (!isOnline) {
        // Queue for sync
        await SyncService.queueDeleteTimeEntry(entryId);
        // Remove from local storage
        await LocalStorage.deleteTimeEntry(entryId);
        return;
      }

      await apiClient!.deleteTimeEntry(entryId);
      await LocalStorage.deleteTimeEntry(entryId);
    } catch (e) {
      throw Exception('Failed to delete time entry: $e');
    }
  }

  /// Sync pending operations
  Future<void> syncPending() async {
    await _syncService?.syncAll();
  }

  // ==================== Project Operations ====================

  /// Get projects
  Future<List<Project>> getProjects({
    String? status,
    int? clientId,
    int? page,
    int? perPage,
  }) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.getProjects(
        status: status,
        clientId: clientId,
        page: page,
        perPage: perPage,
      );
      final projects = response['projects'] as List<dynamic>? ?? [];
      return projects
          .map((p) => Project.fromJson(p as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw Exception('Failed to get projects: $e');
    }
  }

  /// Get a specific project
  Future<Project> getProject(int projectId) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.getProject(projectId);
      return Project.fromJson(response['project'] as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to get project: $e');
    }
  }

  // ==================== Task Operations ====================

  /// Get tasks
  Future<List<Task>> getTasks({
    int? projectId,
    String? status,
    int? page,
    int? perPage,
  }) async {
    try {
      final response = await apiClient.getTasks(
        projectId: projectId,
        status: status,
        page: page,
        perPage: perPage,
      );
      final tasks = response['tasks'] as List<dynamic>? ?? [];
      return tasks
          .map((t) => Task.fromJson(t as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw Exception('Failed to get tasks: $e');
    }
  }

  /// Get a specific task
  Future<Task> getTask(int taskId) async {
    if (apiClient == null) {
      throw Exception('Not connected to server');
    }
    try {
      final response = await apiClient!.getTask(taskId);
      return Task.fromJson(response['task'] as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to get task: $e');
    }
  }
}
