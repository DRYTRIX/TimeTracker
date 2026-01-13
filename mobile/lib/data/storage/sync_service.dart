import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/storage/local_storage.dart';

/// Service for syncing offline data with server
class SyncService {
  final ApiClient? apiClient;
  final Connectivity _connectivity = Connectivity();
  bool _isSyncing = false;

  SyncService(this.apiClient);

  /// Check if device is online
  Future<bool> isOnline() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }

  /// Sync all pending operations
  Future<void> syncAll() async {
    if (_isSyncing || apiClient == null) return;

    final isOnline = await this.isOnline();
    if (!isOnline) return;

    _isSyncing = true;

    try {
      final queue = await LocalStorage.getSyncQueue();
      
      for (final operation in queue) {
        try {
          // Retry logic with exponential backoff
          int retryCount = operation['retry_count'] as int? ?? 0;
          bool success = false;
          int attempts = 0;
          const maxAttempts = 3;
          
          while (!success && attempts < maxAttempts) {
            try {
              await _processOperation(operation);
              success = true;
              await LocalStorage.removeFromSyncQueue(operation['id'] as String);
            } catch (e) {
              attempts++;
              if (attempts < maxAttempts) {
                // Exponential backoff: wait 1s, 2s, 4s
                await Future.delayed(Duration(seconds: 1 << (attempts - 1)));
              } else {
                // Final failure - update retry count
                retryCount++;
                await LocalStorage.updateSyncQueueRetry(
                  operation['id'] as String,
                  retryCount,
                );
                
                // Remove if retried too many times (5 total retries across sync attempts)
                if (retryCount >= 5) {
                  await LocalStorage.removeFromSyncQueue(operation['id'] as String);
                }
                rethrow;
              }
            }
          }
        } catch (e) {
          // Operation failed after all retries - will be retried on next sync
          print('Failed to sync operation ${operation['id']}: $e');
        }
      }
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _processOperation(Map<String, dynamic> operation) async {
    final opType = operation['operation'] as String;
    final data = operation['data'] as Map<String, dynamic>;

    switch (opType) {
      case 'create_time_entry':
        await apiClient!.createTimeEntry(
          projectId: data['project_id'] as int,
          taskId: data['task_id'] as int?,
          startTime: data['start_time'] as String,
          endTime: data['end_time'] as String?,
          notes: data['notes'] as String?,
          tags: data['tags'] as String?,
          billable: data['billable'] as bool?,
        );
        break;
      case 'update_time_entry':
        await apiClient!.updateTimeEntry(
          data['entry_id'] as int,
          projectId: data['project_id'] as int?,
          taskId: data['task_id'] as int?,
          startTime: data['start_time'] as String?,
          endTime: data['end_time'] as String?,
          notes: data['notes'] as String?,
          tags: data['tags'] as String?,
          billable: data['billable'] as bool?,
        );
        break;
      case 'delete_time_entry':
        await apiClient!.deleteTimeEntry(data['entry_id'] as int);
        break;
      case 'start_timer':
        await apiClient!.startTimer(
          projectId: data['project_id'] as int,
          taskId: data['task_id'] as int?,
          notes: data['notes'] as String?,
        );
        break;
      case 'stop_timer':
        await apiClient!.stopTimer();
        break;
    }
  }

  /// Add create time entry to sync queue
  static Future<void> queueCreateTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    await LocalStorage.addToSyncQueue(
      operation: 'create_time_entry',
      data: {
        'project_id': projectId,
        'task_id': taskId,
        'start_time': startTime,
        'end_time': endTime,
        'notes': notes,
        'tags': tags,
        'billable': billable,
      },
    );
  }

  /// Add update time entry to sync queue
  static Future<void> queueUpdateTimeEntry({
    required int entryId,
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    await LocalStorage.addToSyncQueue(
      operation: 'update_time_entry',
      data: {
        'entry_id': entryId,
        'project_id': projectId,
        'task_id': taskId,
        'start_time': startTime,
        'end_time': endTime,
        'notes': notes,
        'tags': tags,
        'billable': billable,
      },
    );
  }

  /// Add delete time entry to sync queue
  static Future<void> queueDeleteTimeEntry(int entryId) async {
    await LocalStorage.addToSyncQueue(
      operation: 'delete_time_entry',
      data: {'entry_id': entryId},
    );
  }
}
