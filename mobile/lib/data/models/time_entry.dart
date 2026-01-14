class TimeEntry {
  final int id;
  final int userId;
  final int? projectId;
  final int? taskId;
  final DateTime? startTime;
  final DateTime? endTime;
  final int? durationSeconds;
  final String source;
  final bool billable;
  final bool paid;
  final String? notes;
  final String? tags;
  final DateTime createdAt;
  final DateTime updatedAt;

  TimeEntry({
    required this.id,
    required this.userId,
    this.projectId,
    this.taskId,
    this.startTime,
    this.endTime,
    this.durationSeconds,
    required this.source,
    required this.billable,
    required this.paid,
    this.notes,
    this.tags,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TimeEntry.fromJson(Map<String, dynamic> json) {
    return TimeEntry(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      projectId: json['project_id'] as int?,
      taskId: json['task_id'] as int?,
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'] as String)
          : null,
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'] as String)
          : null,
      durationSeconds: json['duration_seconds'] as int?,
      source: json['source'] as String,
      billable: json['billable'] as bool,
      paid: json['paid'] as bool,
      notes: json['notes'] as String?,
      tags: json['tags'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  String get formattedDuration {
    if (durationSeconds == null) return '0m';
    final hours = durationSeconds! ~/ 3600;
    final minutes = (durationSeconds! % 3600) ~/ 60;
    if (hours > 0 && minutes > 0) {
      return '${hours}h ${minutes}m';
    } else if (hours > 0) {
      return '${hours}h';
    } else {
      return '${minutes}m';
    }
  }

  String get formattedDateRange {
    if (startTime == null && endTime == null) {
      return 'No date';
    }
    if (startTime != null && endTime != null) {
      // Format both dates
      final start = '${startTime!.year}-${startTime!.month.toString().padLeft(2, '0')}-${startTime!.day.toString().padLeft(2, '0')}';
      final end = '${endTime!.year}-${endTime!.month.toString().padLeft(2, '0')}-${endTime!.day.toString().padLeft(2, '0')}';
      if (start == end) {
        return start;
      }
      return '$start - $end';
    }
    if (startTime != null) {
      return '${startTime!.year}-${startTime!.month.toString().padLeft(2, '0')}-${startTime!.day.toString().padLeft(2, '0')}';
    }
    if (endTime != null) {
      return '${endTime!.year}-${endTime!.month.toString().padLeft(2, '0')}-${endTime!.day.toString().padLeft(2, '0')}';
    }
    return 'No date';
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'project_id': projectId,
      'task_id': taskId,
      'start_time': startTime?.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'duration_seconds': durationSeconds,
      'source': source,
      'billable': billable,
      'paid': paid,
      'notes': notes,
      'tags': tags,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
