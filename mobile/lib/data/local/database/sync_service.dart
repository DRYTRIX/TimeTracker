import 'dart:convert';

import '../database/hive_service.dart';
import '../../api/api_client.dart';
import '../../models/time_entry.dart';
import '../../models/project.dart';

class SyncQueueItem {
  final String id;
  final String type; // 'time_entry', 'project', 'task'
  final String action; // 'create', 'update', 'delete'
  final Map<String, dynamic> data;
  final DateTime timestamp;

  SyncQueueItem({
    required this.id,
    required this.type,
    required this.action,
    required this.data,
    required this.timestamp,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'action': action,
      'data': data,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  factory SyncQueueItem.fromJson(Map<String, dynamic> json) {
    return SyncQueueItem(
      id: json['id'],
      type: json['type'],
      action: json['action'],
      data: json['data'],
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}

class SyncService {
  final ApiClient apiClient;

  SyncService(this.apiClient);

  // Add item to sync queue
  Future<void> addToQueue({
    required String type,
    required String action,
    required Map<String, dynamic> data,
  }) async {
    final item = SyncQueueItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      type: type,
      action: action,
      data: data,
      timestamp: DateTime.now(),
    );

    await HiveService.syncQueueBox.put(item.id, item.toJson());
  }

  // Process sync queue
  Future<void> processQueue() async {
    final queueBox = HiveService.syncQueueBox;
    final queueItems = queueBox.values.toList();

    for (final itemData in queueItems) {
      final item = SyncQueueItem.fromJson(Map<String, dynamic>.from(itemData));
      
      try {
        await _processSyncItem(item);
        await queueBox.delete(item.id);
      } catch (e) {
        // Log error but continue with other items
        print('Error syncing item ${item.id}: $e');
      }
    }
  }

  Future<void> _processSyncItem(SyncQueueItem item) async {
    switch (item.type) {
      case 'time_entry':
        await _syncTimeEntry(item);
        break;
      case 'project':
        await _syncProject(item);
        break;
      case 'task':
        await _syncTask(item);
        break;
    }
  }

  Future<void> _syncTimeEntry(SyncQueueItem item) async {
    final d = item.data;
    switch (item.action) {
      case 'create':
        await apiClient.createTimeEntry(
          projectId: d['project_id'] as int,
          startTime: d['start_time'] as String,
          taskId: d['task_id'] as int?,
          endTime: d['end_time'] as String?,
          notes: d['notes'] as String?,
          tags: d['tags'] as String?,
          billable: d['billable'] as bool?,
        );
        break;
      case 'update':
        await apiClient.updateTimeEntry(
          d['id'] as int,
          projectId: d['project_id'] as int?,
          taskId: d['task_id'] as int?,
          startTime: d['start_time'] as String?,
          endTime: d['end_time'] as String?,
          notes: d['notes'] as String?,
          tags: d['tags'] as String?,
          billable: d['billable'] as bool?,
        );
        break;
      case 'delete':
        await apiClient.deleteTimeEntry(d['id'] as int);
        break;
    }
  }

  Future<void> _syncProject(SyncQueueItem item) async {
    // Similar implementation for projects
    // This is a placeholder as project sync may not be needed
  }

  Future<void> _syncTask(SyncQueueItem item) async {
    // Similar implementation for tasks
    // This is a placeholder as task sync may not be needed
  }

  // Sync local data with server
  Future<void> syncFromServer() async {
    try {
      // Sync projects
      final projectsData = await apiClient.getProjects(status: 'active');
      final projectsList = projectsData['projects'] as List?;
      if (projectsList != null) {
        for (final json in projectsList) {
          final project = Project.fromJson(Map<String, dynamic>.from(json as Map));
          await HiveService.projectsBox.put(project.id, project.toJson());
        }
      }

      // Sync time entries (recent ones)
      final now = DateTime.now();
      final startDate = now.subtract(const Duration(days: 30));
      final entriesData = await apiClient.getTimeEntries(
        startDate: startDate.toIso8601String().split('T')[0],
        endDate: now.toIso8601String().split('T')[0],
      );
      final entriesList = entriesData['time_entries'] as List?;
      if (entriesList != null) {
        for (final json in entriesList) {
          final entry = TimeEntry.fromJson(Map<String, dynamic>.from(json as Map));
          await HiveService.timeEntriesBox.put(entry.id, entry.toJson());
        }
      }
    } catch (e) {
      print('Error syncing from server: $e');
      rethrow;
    }
  }

  // Get cached data (stored as JSON in Hive)
  List<Project> getCachedProjects() {
    try {
      return HiveService.projectsBox.values
          .map((value) {
            // Handle both Map and JSON string
            if (value is Map) {
              return Project.fromJson(Map<String, dynamic>.from(value));
            } else if (value is String) {
              return Project.fromJson(
                  Map<String, dynamic>.from(jsonDecode(value) as Map));
            }
            throw Exception('Invalid project data format');
          })
          .toList();
    } catch (e) {
      return [];
    }
  }

  List<TimeEntry> getCachedTimeEntries({
    DateTime? startDate,
    DateTime? endDate,
    int? projectId,
  }) {
    try {
      var entries = HiveService.timeEntriesBox.values
          .map((value) {
            // Handle both Map and JSON string
            if (value is Map) {
              return TimeEntry.fromJson(Map<String, dynamic>.from(value));
            } else if (value is String) {
              return TimeEntry.fromJson(
                  Map<String, dynamic>.from(jsonDecode(value) as Map));
            }
            throw Exception('Invalid time entry data format');
          })
          .toList();

      if (startDate != null) {
        entries = entries
            .where((e) =>
                e.startTime != null && e.startTime!.isAfter(startDate))
            .toList();
      }
      if (endDate != null) {
        entries = entries
            .where((e) =>
                e.startTime != null && e.startTime!.isBefore(endDate))
            .toList();
      }
      if (projectId != null) {
        entries =
            entries.where((e) => e.projectId == projectId).toList();
      }

      return entries;
    } catch (e) {
      return [];
    }
  }
}
