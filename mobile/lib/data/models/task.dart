class Task {
  final int id;
  final int projectId;
  final String name;
  final String status;
  final String? priority;
  final int createdBy;
  final DateTime createdAt;
  final DateTime updatedAt;

  Task({
    required this.id,
    required this.projectId,
    required this.name,
    required this.status,
    this.priority,
    required this.createdBy,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      name: json['name'] as String,
      status: json['status'] as String,
      priority: json['priority'] as String?,
      createdBy: json['created_by'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
