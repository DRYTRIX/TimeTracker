import 'package:flutter/foundation.dart';

/// Active timer row from `/api/v1/timer/status` (same fields as server time entry JSON).
@immutable
class Timer {
  final int id;
  final int userId;
  final int? projectId;
  final int? clientId;
  final int? taskId;
  final DateTime startTime;
  final String? notes;
  final DateTime? pausedAt;
  final int breakSeconds;
  /// Denormalized project name from API (`project` field).
  final String? project;
  /// Denormalized client name from API (`client` field).
  final String? client;

  const Timer({
    required this.id,
    this.userId = 0,
    this.projectId,
    this.clientId,
    this.taskId,
    required this.startTime,
    this.notes,
    this.pausedAt,
    this.breakSeconds = 0,
    this.project,
    this.client,
  });

  bool get isPaused => pausedAt != null;

  /// Display label: project name, else client name, else a fallback.
  String get displayLabel {
    if (project != null && project!.isNotEmpty) return project!;
    if (client != null && client!.isNotEmpty) return client!;
    if (projectId != null) return 'Project #$projectId';
    if (clientId != null) return 'Client #$clientId';
    return 'Timer';
  }

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
      clientId: (json['client_id'] as num?)?.toInt(),
      taskId: (json['task_id'] as num?)?.toInt(),
      startTime: start,
      notes: json['notes']?.toString(),
      pausedAt: pausedAt,
      breakSeconds: (json['break_seconds'] as num?)?.toInt() ?? 0,
      project: json['project']?.toString(),
      client: json['client']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'project_id': projectId,
        'client_id': clientId,
        'task_id': taskId,
        'start_time': startTime.toIso8601String(),
        'notes': notes,
        'paused_at': pausedAt?.toIso8601String(),
        'break_seconds': breakSeconds,
        'project': project,
        'client': client,
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
