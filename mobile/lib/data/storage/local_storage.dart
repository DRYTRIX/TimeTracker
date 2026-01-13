import 'package:hive_flutter/hive_flutter.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/data/models/timer.dart';

/// Local storage using Hive for offline support
class LocalStorage {
  static const String _timeEntriesBox = 'time_entries';
  static const String _timerBox = 'timer';
  static const String _syncQueueBox = 'sync_queue';

  static Future<void> init() async {
    await Hive.initFlutter();
    
    // Register adapters if needed (for now we'll use JSON strings)
    // In production, you'd want to create proper Hive adapters
  }

  // ==================== Time Entries ====================

  /// Save time entry locally
  static Future<void> saveTimeEntry(TimeEntry entry) async {
    final box = await Hive.openBox(_timeEntriesBox);
    await box.put(entry.id.toString(), entry.toJson());
  }

  /// Get time entry from local storage
  static Future<TimeEntry?> getTimeEntry(int entryId) async {
    final box = await Hive.openBox(_timeEntriesBox);
    final data = box.get(entryId.toString());
    if (data != null) {
      return TimeEntry.fromJson(Map<String, dynamic>.from(data));
    }
    return null;
  }

  /// Get all time entries from local storage
  static Future<List<TimeEntry>> getAllTimeEntries() async {
    final box = await Hive.openBox(_timeEntriesBox);
    final entries = <TimeEntry>[];
    for (var key in box.keys) {
      final data = box.get(key);
      if (data != null) {
        try {
          entries.add(TimeEntry.fromJson(Map<String, dynamic>.from(data)));
        } catch (e) {
          // Skip invalid entries
        }
      }
    }
    return entries;
  }

  /// Delete time entry from local storage
  static Future<void> deleteTimeEntry(int entryId) async {
    final box = await Hive.openBox(_timeEntriesBox);
    await box.delete(entryId.toString());
  }

  /// Clear all time entries
  static Future<void> clearTimeEntries() async {
    final box = await Hive.openBox(_timeEntriesBox);
    await box.clear();
  }

  // ==================== Timer ====================

  /// Save timer locally
  static Future<void> saveTimer(Timer timer) async {
    final box = await Hive.openBox(_timerBox);
    await box.put('active', timer.toJson());
  }

  /// Get timer from local storage
  static Future<Timer?> getTimer() async {
    final box = await Hive.openBox(_timerBox);
    final data = box.get('active');
    if (data != null) {
      return Timer.fromJson(Map<String, dynamic>.from(data));
    }
    return null;
  }

  /// Clear timer from local storage
  static Future<void> clearTimer() async {
    final box = await Hive.openBox(_timerBox);
    await box.delete('active');
  }

  // ==================== Sync Queue ====================

  /// Add operation to sync queue
  static Future<void> addToSyncQueue({
    required String operation,
    required Map<String, dynamic> data,
  }) async {
    final box = await Hive.openBox(_syncQueueBox);
    final id = DateTime.now().millisecondsSinceEpoch.toString();
    await box.put(id, {
      'id': id,
      'operation': operation,
      'data': data,
      'created_at': DateTime.now().toIso8601String(),
      'retry_count': 0,
    });
  }

  /// Get all pending sync operations
  static Future<List<Map<String, dynamic>>> getSyncQueue() async {
    final box = await Hive.openBox(_syncQueueBox);
    final operations = <Map<String, dynamic>>[];
    for (var key in box.keys) {
      final data = box.get(key);
      if (data != null) {
        operations.add(Map<String, dynamic>.from(data));
      }
    }
    // Sort by creation time
    operations.sort((a, b) {
      final aTime = DateTime.parse(a['created_at'] as String);
      final bTime = DateTime.parse(b['created_at'] as String);
      return aTime.compareTo(bTime);
    });
    return operations;
  }

  /// Remove operation from sync queue
  static Future<void> removeFromSyncQueue(String operationId) async {
    final box = await Hive.openBox(_syncQueueBox);
    await box.delete(operationId);
  }

  /// Update retry count for sync operation
  static Future<void> updateSyncQueueRetry(String operationId, int retryCount) async {
    final box = await Hive.openBox(_syncQueueBox);
    final data = box.get(operationId);
    if (data != null) {
      final operation = Map<String, dynamic>.from(data);
      operation['retry_count'] = retryCount;
      await box.put(operationId, operation);
    }
  }

  /// Clear sync queue
  static Future<void> clearSyncQueue() async {
    final box = await Hive.openBox(_syncQueueBox);
    await box.clear();
  }
}
