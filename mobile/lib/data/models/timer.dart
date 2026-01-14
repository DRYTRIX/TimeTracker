class Timer {
  final int id;
  final int userId;
  final int projectId;
  final int? taskId;
  final DateTime startTime;
  final String? notes;
  final int? templateId;

  Timer({
    required this.id,
    required this.userId,
    required this.projectId,
    this.taskId,
    required this.startTime,
    this.notes,
    this.templateId,
  });

  factory Timer.fromJson(Map<String, dynamic> json) {
    return Timer(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      projectId: json['project_id'] as int,
      taskId: json['task_id'] as int?,
      startTime: DateTime.parse(json['start_time'] as String),
      notes: json['notes'] as String?,
      templateId: json['template_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'project_id': projectId,
      'task_id': taskId,
      'start_time': startTime.toIso8601String(),
      'notes': notes,
      'template_id': templateId,
    };
  }

  /// Get formatted elapsed time as HH:MM:SS
  String get formattedElapsed {
    final elapsed = DateTime.now().difference(startTime);
    final hours = elapsed.inHours;
    final minutes = elapsed.inMinutes.remainder(60);
    final seconds = elapsed.inSeconds.remainder(60);
    return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }
}
