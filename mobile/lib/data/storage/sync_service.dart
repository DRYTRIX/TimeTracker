import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/data/storage/local_storage.dart';

class SyncService {
  SyncService(this._api);

  final ApiClient? _api;

  static Future<void> queueCreateTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    final q = await LocalStorage.getSyncQueue();
    q.add({
      'op': 'create_time_entry',
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (notes != null) 'notes': notes,
      if (tags != null) 'tags': tags,
      if (billable != null) 'billable': billable,
    });
    await LocalStorage.setSyncQueue(q);
  }

  static Future<void> queueDeleteTimeEntry(int entryId) async {
    final q = await LocalStorage.getSyncQueue();
    q.add({
      'op': 'delete_time_entry',
      'entry_id': entryId,
    });
    await LocalStorage.setSyncQueue(q);
  }

  Future<void> syncAll() async {
    await processQueue();
    await syncFromServer();
  }

  Future<void> processQueue() async {
    final api = _api;
    if (api == null) return;

    final q = await LocalStorage.getSyncQueue();
    final remaining = <Map<String, dynamic>>[];

    for (final op in q) {
      final type = op['op']?.toString();
      try {
        if (type == 'create_time_entry') {
          await api.createTimeEntry(
            projectId: (op['project_id'] as num).toInt(),
            taskId: (op['task_id'] as num?)?.toInt(),
            startTime: op['start_time'].toString(),
            endTime: op['end_time']?.toString(),
            notes: op['notes']?.toString(),
            tags: op['tags']?.toString(),
            billable: op['billable'] as bool?,
          );
        } else if (type == 'delete_time_entry') {
          await api.deleteTimeEntry((op['entry_id'] as num).toInt());
        } else {
          remaining.add(op);
        }
      } catch (_) {
        remaining.add(op);
      }
    }

    await LocalStorage.setSyncQueue(remaining);
  }

  Future<void> syncFromServer() async {
    final api = _api;
    if (api == null) return;
    try {
      final res = await api.getTimeEntries(perPage: 200);
      final raw = res['time_entries'] as List<dynamic>? ?? [];
      for (final e in raw) {
        if (e is Map) {
          final entry = TimeEntry.fromJson(Map<String, dynamic>.from(e));
          await LocalStorage.saveTimeEntry(entry);
        }
      }
    } catch (_) {}
  }
}
