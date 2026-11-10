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

/// After this many failed attempts, a queued op is marked `failed`.
const int maxSyncAttempts = 8;

String syncErrorMessage(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['error'] != null) return data['error'].toString();
    if (error.message != null && error.message!.isNotEmpty) return error.message!;
  }
  return error.toString();
}

/// Exponential backoff delay after [attempts] failures (1-based).
Duration syncBackoffForAttempt(int attempts) {
  final capped = attempts.clamp(1, maxSyncAttempts);
  final seconds = min(300, 1 << (capped - 1)); // 1,2,4,...,128, then cap 300
  return Duration(seconds: seconds);
}

Map<String, dynamic> normalizeQueueOp(Map<String, dynamic> op) {
  final next = Map<String, dynamic>.from(op);
  next['status'] = (next['status'] ?? 'pending').toString();
  next['attempts'] = (next['attempts'] as num?)?.toInt() ?? 0;
  next['lastError'] = next['lastError']?.toString() ?? '';
  next['id'] = next['id']?.toString() ??
      '${next['op']}-${next['createdAt'] ?? DateTime.now().millisecondsSinceEpoch}-${Random().nextInt(1 << 20)}';
  next['createdAt'] ??= DateTime.now().toUtc().toIso8601String();
  return next;
}

bool shouldSkipUntilNextAttempt(Map<String, dynamic> op, {DateTime? now}) {
  final status = (op['status'] ?? 'pending').toString();
  if (status == 'failed') return true;
  final raw = op['nextAttemptAt']?.toString();
  if (raw == null || raw.isEmpty) return false;
  final nextAt = DateTime.tryParse(raw);
  if (nextAt == null) return false;
  return nextAt.isAfter(now ?? DateTime.now().toUtc());
}

Map<String, dynamic> markOpAttemptFailure(Map<String, dynamic> op, Object error, {DateTime? now}) {
  final next = normalizeQueueOp(op);
  final attempts = ((next['attempts'] as num?)?.toInt() ?? 0) + 1;
  final failed = attempts >= maxSyncAttempts;
  final when = now ?? DateTime.now().toUtc();
  next['attempts'] = attempts;
  next['lastError'] = syncErrorMessage(error);
  next['status'] = failed ? 'failed' : 'pending';
  if (failed) {
    next.remove('nextAttemptAt');
  } else {
    next['nextAttemptAt'] = when.add(syncBackoffForAttempt(attempts)).toIso8601String();
  }
  return next;
}

Map<String, dynamic> resetOpForRetry(Map<String, dynamic> op) {
  final next = normalizeQueueOp(op);
  next['status'] = 'pending';
  next['attempts'] = 0;
  next['lastError'] = '';
  next.remove('nextAttemptAt');
  return next;
}

class SyncService {
  SyncService(this._api);

  final ApiClient? _api;

  static Future<void> _enqueue(Map<String, dynamic> op) async {
    final q = await LocalStorage.getSyncQueue();
    q.add(normalizeQueueOp(op));
    await LocalStorage.setSyncQueue(q);
  }

  static Future<void> queueCreateTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    await _enqueue({
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
  }

  /// Queue timer start (offline). Processed before manual entry creates when syncing.
  static Future<void> queueTimerStart({
    required int projectId,
    int? taskId,
    String? notes,
  }) async {
    await _enqueue({
      'op': 'timer_start',
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
      'start_time': DateTime.now().toUtc().toIso8601String(),
    });
  }

  /// Queue timer stop (offline). Server creates the time entry on sync.
  static Future<void> queueTimerStop({String? stopTime}) async {
    await _enqueue({
      'op': 'timer_stop',
      if (stopTime != null) 'stop_time': stopTime,
    });
  }

  static Future<void> queueDeleteTimeEntry(int entryId) async {
    await _enqueue({
      'op': 'delete_time_entry',
      'entry_id': entryId,
    });
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
    await _enqueue({
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
  }

  static Future<List<Map<String, dynamic>>> listFailed() async {
    final q = await LocalStorage.getSyncQueue();
    return q
        .map(normalizeQueueOp)
        .where((op) => (op['status'] ?? '') == 'failed')
        .toList();
  }

  static Future<bool> retry(String id) async {
    final q = await LocalStorage.getSyncQueue();
    var found = false;
    final next = <Map<String, dynamic>>[];
    for (final raw in q) {
      final op = normalizeQueueOp(raw);
      if (op['id']?.toString() == id) {
        found = true;
        next.add(resetOpForRetry(op));
      } else {
        next.add(op);
      }
    }
    if (!found) return false;
    await LocalStorage.setSyncQueue(next);
    return true;
  }

  static Future<bool> discard(String id) async {
    final q = await LocalStorage.getSyncQueue();
    final next = q.where((op) => normalizeQueueOp(op)['id']?.toString() != id).toList();
    if (next.length == q.length) return false;
    await LocalStorage.setSyncQueue(next);
    return true;
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
    final now = DateTime.now().toUtc();

    for (final raw in q) {
      final op = normalizeQueueOp(raw);
      final type = op['op']?.toString();
      final status = (op['status'] ?? 'pending').toString();

      if (status == 'failed') {
        remaining.add(op);
        continue;
      }

      if (shouldSkipUntilNextAttempt(op, now: now)) {
        remaining.add(op);
        continue;
      }

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
        remaining.add(markOpAttemptFailure(op, e, now: now));
      } catch (e, st) {
        developer.log(
          'Sync queue op failed (non-Dio): $type',
          name: 'SyncService',
          error: e,
          stackTrace: st,
        );
        remaining.add(markOpAttemptFailure(op, e, now: now));
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
