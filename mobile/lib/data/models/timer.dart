import 'package:flutter/foundation.dart';

/// Active timer row from `/api/v1/timer/status` (same fields as server time entry JSON).
@immutable
class Timer {
  final int id;
  final int userId;
  final int? projectId;
  final int? taskId;
  final DateTime startTime;
  final String? notes;

  const Timer({
    required this.id,
    this.userId = 0,
    this.projectId,
    this.taskId,
    required this.startTime,
    this.notes,
  });

  factory Timer.fromJson(Map<String, dynamic> json) {
    final startRaw = json['start_time'];
    final start = startRaw is DateTime
        ? startRaw
        : DateTime.tryParse(startRaw?.toString() ?? '') ?? DateTime.now();
    return Timer(
      id: (json['id'] as num).toInt(),
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      projectId: (json['project_id'] as num?)?.toInt(),
      taskId: (json['task_id'] as num?)?.toInt(),
      startTime: start,
      notes: json['notes']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'project_id': projectId,
        'task_id': taskId,
        'start_time': startTime.toIso8601String(),
        'notes': notes,
      };

  String get formattedElapsed {
    final d = DateTime.now().difference(startTime);
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    final s = d.inSeconds.remainder(60);
    return '${h.toString().padLeft(2, '0')}:'
        '${m.toString().padLeft(2, '0')}:'
        '${s.toString().padLeft(2, '0')}';
  }
}
