class TimeEntry {
  final int id;
  final int userId;
  final int? projectId;
  final DateTime? startTime;
  final DateTime? endTime;
  final int? durationSeconds;
  final String source;
  final bool billable;
  final bool paid;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  TimeEntry({
    required this.id,
    required this.userId,
    this.projectId,
    this.startTime,
    this.endTime,
    this.durationSeconds,
    required this.source,
    required this.billable,
    required this.paid,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TimeEntry.fromJson(Map<String, dynamic> json) {
    return TimeEntry(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      projectId: json['project_id'] as int?,
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

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'project_id': projectId,
      'start_time': startTime?.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'duration_seconds': durationSeconds,
      'source': source,
      'billable': billable,
      'paid': paid,
      'notes': notes,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
