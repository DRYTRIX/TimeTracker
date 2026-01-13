import 'package:dio/dio.dart';

class ApiClient {
  final String baseUrl;
  late final Dio _dio;
  String? _authToken;

  ApiClient({required this.baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    ));
  }

  /// Set authentication token
  Future<void> setAuthToken(String token) async {
    _authToken = token;
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// Validate token by making a test API call
  Future<bool> validateToken() async {
    try {
      final response = await _dio.get('/api/v1/timer/status');
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // ==================== Timer Operations ====================

  /// Get timer status
  Future<Map<String, dynamic>> getTimerStatus() async {
    final response = await _dio.get('/api/v1/timer/status');
    return response.data as Map<String, dynamic>;
  }

  /// Start timer
  Future<Map<String, dynamic>> startTimer({
    required int projectId,
    int? taskId,
    String? notes,
    int? templateId,
  }) async {
    final response = await _dio.post('/api/v1/timer/start', data: {
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (notes != null) 'notes': notes,
      if (templateId != null) 'template_id': templateId,
    });
    return response.data as Map<String, dynamic>;
  }

  /// Stop timer
  Future<Map<String, dynamic>> stopTimer() async {
    final response = await _dio.post('/api/v1/timer/stop');
    return response.data as Map<String, dynamic>;
  }

  // ==================== Time Entry Operations ====================

  /// Get time entries
  Future<Map<String, dynamic>> getTimeEntries({
    int? projectId,
    String? startDate,
    String? endDate,
    bool? billable,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (projectId != null) queryParams['project_id'] = projectId;
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    if (billable != null) queryParams['billable'] = billable;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;

    final response = await _dio.get('/api/v1/time-entries', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  /// Get a specific time entry
  Future<Map<String, dynamic>> getTimeEntry(int entryId) async {
    final response = await _dio.get('/api/v1/time-entries/$entryId');
    return response.data as Map<String, dynamic>;
  }

  /// Create time entry
  Future<Map<String, dynamic>> createTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    final response = await _dio.post('/api/v1/time-entries', data: {
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (notes != null) 'notes': notes,
      if (tags != null) 'tags': tags,
      if (billable != null) 'billable': billable,
    });
    return response.data as Map<String, dynamic>;
  }

  /// Update time entry
  Future<Map<String, dynamic>> updateTimeEntry(
    int entryId, {
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    final data = <String, dynamic>{};
    if (projectId != null) data['project_id'] = projectId;
    if (taskId != null) data['task_id'] = taskId;
    if (startTime != null) data['start_time'] = startTime;
    if (endTime != null) data['end_time'] = endTime;
    if (notes != null) data['notes'] = notes;
    if (tags != null) data['tags'] = tags;
    if (billable != null) data['billable'] = billable;

    final response = await _dio.put('/api/v1/time-entries/$entryId', data: data);
    return response.data as Map<String, dynamic>;
  }

  /// Delete time entry
  Future<void> deleteTimeEntry(int entryId) async {
    await _dio.delete('/api/v1/time-entries/$entryId');
  }

  // ==================== Project Operations ====================

  /// Get projects
  Future<Map<String, dynamic>> getProjects({
    String? status,
    int? clientId,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (clientId != null) queryParams['client_id'] = clientId;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;

    final response = await _dio.get('/api/v1/projects', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  /// Get a specific project
  Future<Map<String, dynamic>> getProject(int projectId) async {
    final response = await _dio.get('/api/v1/projects/$projectId');
    return response.data as Map<String, dynamic>;
  }

  // ==================== Task Operations ====================

  /// Get tasks
  Future<Map<String, dynamic>> getTasks({
    int? projectId,
    String? status,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (projectId != null) queryParams['project_id'] = projectId;
    if (status != null) queryParams['status'] = status;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;

    final response = await _dio.get('/api/v1/tasks', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  /// Get a specific task
  Future<Map<String, dynamic>> getTask(int taskId) async {
    final response = await _dio.get('/api/v1/tasks/$taskId');
    return response.data as Map<String, dynamic>;
  }
}
