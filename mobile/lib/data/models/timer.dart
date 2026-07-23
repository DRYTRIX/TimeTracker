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
  final DateTime? pausedAt;
  final int breakSeconds;

  const Timer({
    required this.id,
    this.userId = 0,
    this.projectId,
    this.taskId,
    required this.startTime,
    this.notes,
    this.pausedAt,
    this.breakSeconds = 0,
  });

  bool get isPaused => pausedAt != null;

  factory Timer.fromJson(Map<String, dynamic> json) {
    final startRaw = json['start_time'];
    final start = startRaw is DateTime
        ? startRaw
        : DateTime.tryParse(startRaw?.toString() ?? '') ?? DateTime.now();
    final pausedRaw = json['paused_at'];
    DateTime? pausedAt;
    if (pausedRaw != null) {
      pausedAt = pausedRaw is DateTime
          ? pausedRaw
          : DateTime.tryParse(pausedRaw.toString());
    }
    return Timer(
      id: (json['id'] as num).toInt(),
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      projectId: (json['project_id'] as num?)?.toInt(),
      taskId: (json['task_id'] as num?)?.toInt(),
      startTime: start,
      notes: json['notes']?.toString(),
      pausedAt: pausedAt,
      breakSeconds: (json['break_seconds'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'project_id': projectId,
        'task_id': taskId,
        'start_time': startTime.toIso8601String(),
        'notes': notes,
        'paused_at': pausedAt?.toIso8601String(),
        'break_seconds': breakSeconds,
      };

  /// Worked time excluding breaks; freezes at [pausedAt] when paused.
  Duration get elapsed {
    final endRef = pausedAt ?? DateTime.now();
    final raw = endRef.difference(startTime).inSeconds - breakSeconds;
    return Duration(seconds: raw < 0 ? 0 : raw);
  }

  String get formattedElapsed {
    final d = elapsed;
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    final s = d.inSeconds.remainder(60);
    return '${h.toString().padLeft(2, '0')}:'
        '${m.toString().padLeft(2, '0')}:'
        '${s.toString().padLeft(2, '0')}';
  }
}
