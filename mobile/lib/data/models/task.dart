class Task {
  final int id;
  final int projectId;
  final String name;
  final String status;
  final String? priority;
  final int? createdBy;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const Task({
    required this.id,
    required this.projectId,
    required this.name,
    this.status = 'todo',
    this.priority,
    this.createdBy,
    this.createdAt,
    this.updatedAt,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: (json['id'] as num).toInt(),
      projectId: (json['project_id'] as num?)?.toInt() ?? 0,
      name: (json['name'] ?? '').toString(),
      status: (json['status'] ?? 'todo').toString(),
      priority: json['priority']?.toString(),
      createdBy: (json['created_by'] as num?)?.toInt(),
      createdAt: _parseDt(json['created_at']),
      updatedAt: _parseDt(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'project_id': projectId,
        'name': name,
        'status': status,
        'priority': priority,
        'created_by': createdBy,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };

  static DateTime? _parseDt(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}
