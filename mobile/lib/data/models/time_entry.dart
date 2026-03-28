class TimeEntry {
  final int id;
  final int userId;
  final int? projectId;
  final int? taskId;
  final DateTime? startTime;
  final DateTime? endTime;
  final int? durationSeconds;
  final String? notes;
  final String? tags;
  final String source;
  final bool billable;
  final bool paid;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const TimeEntry({
    required this.id,
    this.userId = 0,
    this.projectId,
    this.taskId,
    this.startTime,
    this.endTime,
    this.durationSeconds,
    this.notes,
    this.tags,
    this.source = 'manual',
    this.billable = true,
    this.paid = false,
    this.createdAt,
    this.updatedAt,
  });

  factory TimeEntry.fromJson(Map<String, dynamic> json) {
    return TimeEntry(
      id: (json['id'] as num).toInt(),
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      projectId: (json['project_id'] as num?)?.toInt(),
      taskId: (json['task_id'] as num?)?.toInt(),
      startTime: _parseDt(json['start_time']),
      endTime: _parseDt(json['end_time']),
      durationSeconds: (json['duration_seconds'] as num?)?.toInt(),
      notes: json['notes']?.toString(),
      tags: json['tags']?.toString(),
      source: (json['source'] ?? 'manual').toString(),
      billable: json['billable'] != false,
      paid: json['paid'] == true,
      createdAt: _parseDt(json['created_at']),
      updatedAt: _parseDt(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'project_id': projectId,
        'task_id': taskId,
        'start_time': startTime?.toIso8601String(),
        'end_time': endTime?.toIso8601String(),
        'duration_seconds': durationSeconds,
        'notes': notes,
        'tags': tags,
        'source': source,
        'billable': billable,
        'paid': paid,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };

  String get formattedDuration {
    final secs = durationSeconds;
    if (secs == null || secs <= 0) {
      if (startTime != null && endTime != null) {
        final d = endTime!.difference(startTime!);
        return _formatSeconds(d.inSeconds);
      }
      return '0m';
    }
    return _formatSeconds(secs);
  }

  static String _formatSeconds(int totalSeconds) {
    final h = totalSeconds ~/ 3600;
    final m = (totalSeconds % 3600) ~/ 60;
    if (h > 0) {
      return m > 0 ? '${h}h ${m}m' : '${h}h';
    }
    if (m > 0) return '${m}m';
    final s = totalSeconds % 60;
    return '${s}s';
  }

  static DateTime? _parseDt(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}
