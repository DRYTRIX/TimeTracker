import 'dart:developer' as developer;
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/data/storage/local_storage.dart';

/// RFC 4122-style random key (server allows up to 128 chars).
String newSyncIdempotencyKey() {
  final r = Random.secure();
  final raw = List<int>.generate(16, (_) => r.nextInt(256));
  raw[6] = (raw[6] & 0x0f) | 0x40;
  raw[8] = (raw[8] & 0x3f) | 0x80;
  final hex = raw.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20, 32)}';
}

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
      'idempotency_key': newSyncIdempotencyKey(),
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

  /// Queue timer start (offline). Processed before manual entry creates when syncing.
  static Future<void> queueTimerStart({
    required int projectId,
    int? taskId,
    String? notes,
  }) async {
    final q = await LocalStorage.getSyncQueue();
    q.add({
      'op': 'timer_start',
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
      'start_time': DateTime.now().toUtc().toIso8601String(),
    });
    await LocalStorage.setSyncQueue(q);
  }

  /// Queue timer stop (offline). Server creates the time entry on sync.
  static Future<void> queueTimerStop({String? stopTime}) async {
    final q = await LocalStorage.getSyncQueue();
    q.add({
      'op': 'timer_stop',
      if (stopTime != null) 'stop_time': stopTime,
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

  /// Queue a PATCH for when offline; sends [if_updated_at] for optimistic locking (409 drops op).
  static Future<void> queueUpdateTimeEntry({
    required int entryId,
    String? ifUpdatedAt,
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    final q = await LocalStorage.getSyncQueue();
    q.add({
      'op': 'update_time_entry',
      'entry_id': entryId,
      if (ifUpdatedAt != null) 'if_updated_at': ifUpdatedAt,
      if (projectId != null) 'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (startTime != null) 'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (notes != null) 'notes': notes,
      if (tags != null) 'tags': tags,
      if (billable != null) 'billable': billable,
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
          final idem = op['idempotency_key']?.toString();
          await api.createTimeEntry(
            projectId: (op['project_id'] as num).toInt(),
            taskId: (op['task_id'] as num?)?.toInt(),
            startTime: op['start_time'].toString(),
            endTime: op['end_time']?.toString(),
            notes: op['notes']?.toString(),
            tags: op['tags']?.toString(),
            billable: op['billable'] as bool?,
            idempotencyKey: idem != null && idem.isNotEmpty ? idem : null,
          );
        } else if (type == 'delete_time_entry') {
          await api.deleteTimeEntry((op['entry_id'] as num).toInt());
        } else if (type == 'update_time_entry') {
          final eid = (op['entry_id'] as num).toInt();
          await api.updateTimeEntry(
            eid,
            projectId: (op['project_id'] as num?)?.toInt(),
            taskId: (op['task_id'] as num?)?.toInt(),
            startTime: op['start_time']?.toString(),
            endTime: op['end_time']?.toString(),
            notes: op['notes']?.toString(),
            tags: op['tags']?.toString(),
            billable: op['billable'] as bool?,
            ifUpdatedAt: op['if_updated_at']?.toString(),
          );
        } else if (type == 'timer_start') {
          await api.startTimer(
            projectId: (op['project_id'] as num).toInt(),
            taskId: (op['task_id'] as num?)?.toInt(),
            notes: op['notes']?.toString(),
          );
        } else if (type == 'timer_stop') {
          final rawStop = op['stop_time']?.toString();
          await api.stopTimer(
            stopTime: rawStop != null ? DateTime.tryParse(rawStop) : null,
          );
        } else {
          remaining.add(op);
        }
      } on DioException catch (e) {
        if (type == 'update_time_entry' && e.response?.statusCode == 409) {
          continue;
        }
        remaining.add(op);
      } catch (e, st) {
        developer.log(
          'Sync queue op failed (non-Dio): $type',
          name: 'SyncService',
          error: e,
          stackTrace: st,
        );
        remaining.add(op);
      }
    }

    await LocalStorage.setSyncQueue(remaining);
  }

  Future<void> syncFromServer() async {
    final api = _api;
    if (api == null) return;

    var page = 1;
    const perPage = 100;

    while (true) {
      final res = await api.getTimeEntries(page: page, perPage: perPage);
      final raw = res['time_entries'] as List<dynamic>? ?? [];
      for (final e in raw) {
        if (e is Map) {
          final entry = TimeEntry.fromJson(Map<String, dynamic>.from(e));
          await LocalStorage.saveTimeEntry(entry);
        }
      }

      final pag = res['pagination'];
      var hasNext = false;
      if (pag is Map) {
        final hn = pag['has_next'];
        if (hn is bool) {
          hasNext = hn;
        }
      }
      if (!hasNext) break;
      page += 1;
    }
  }
}
