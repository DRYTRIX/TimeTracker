class Project {
  final int id;
  final String name;
  final int? clientId;
  final String? client;
  final String status;
  final bool billable;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final DateTime? lastUsedAt;

  const Project({
    required this.id,
    required this.name,
    this.clientId,
    this.client,
    this.status = 'active',
    this.billable = true,
    this.createdAt,
    this.updatedAt,
    this.lastUsedAt,
  });

  factory Project.fromJson(Map<String, dynamic> json) {
    final clientField = json['client'];
    String? clientName;
    int? nestedClientId;
    if (clientField is Map) {
      clientName = clientField['name']?.toString();
      nestedClientId = (clientField['id'] as num?)?.toInt();
    } else if (clientField != null) {
      clientName = clientField.toString();
    }
    return Project(
      id: (json['id'] as num).toInt(),
      name: (json['name'] ?? '').toString(),
      clientId: (json['client_id'] as num?)?.toInt() ?? nestedClientId,
      client: clientName,
      status: (json['status'] ?? 'active').toString(),
      billable: json['billable'] == true,
      createdAt: _parseDt(json['created_at']),
      updatedAt: _parseDt(json['updated_at']),
      lastUsedAt: _parseDt(json['last_used_at']),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'client_id': clientId,
        'client': client,
        'status': status,
        'billable': billable,
        'created_at': createdAt?.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
        'last_used_at': lastUsedAt?.toIso8601String(),
      };

  static DateTime? _parseDt(dynamic v) {
    if (v == null) return null;
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString());
  }
}
