class Project {
  final int id;
  final String name;
  final String? client;
  final String status;
  final bool billable;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const Project({
    required this.id,
    required this.name,
    this.client,
    this.status = 'active',
    this.billable = true,
    this.createdAt,
    this.updatedAt,
  });

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: (json['id'] as num).toInt(),
      name: (json['name'] ?? '').toString(),
      client: json['client']?.toString(),
      status: (json['status'] ?? 'active').toString(),
      billable: json['billable'] == true,
      createdAt: _parseDt(json['created_at']),
      updatedAt: _parseDt(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'client': client,
        'status': status,
        'billable': billable,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
      };

  static DateTime? _parseDt(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}
