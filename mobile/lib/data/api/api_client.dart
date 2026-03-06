import 'package:dio/dio.dart';

import 'package:timetracker_mobile/utils/ssl/ssl_utils.dart';

class ApiClient {
  final String baseUrl;
  late final Dio _dio;

  ApiClient({
    required String baseUrl,
    Set<String> trustedInsecureHosts = const {},
  }) : baseUrl = baseUrl.endsWith('/') ? baseUrl : '$baseUrl/' {
    _dio = Dio(BaseOptions(
      baseUrl: this.baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    ));
    configureDioTrustedHosts(_dio, trustedInsecureHosts);
  }

  /// Set authentication token
  Future<void> setAuthToken(String token) async {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// Validate token by making a test API call.
  ///
  /// This returns the raw response (with status codes preserved) so callers can
  /// distinguish "unauthorized" from network failures.
  Future<Response<dynamic>> validateTokenRaw() async {
    return _dio.get(
      '/api/v1/timer/status',
      options: Options(validateStatus: (_) => true),
    );
  }

  /// Get current authenticated user (includes resolved date_format, time_format, timezone).
  Future<Map<String, dynamic>> getCurrentUser() async {
    final response = await _dio.get('/api/v1/users/me');
    final data = response.data as Map<String, dynamic>;
    return data['user'] as Map<String, dynamic>;
  }

  /// Get full /api/v1/users/me response (user + time_entry_requirements).
  Future<Map<String, dynamic>> getUsersMe() async {
    final response = await _dio.get('/api/v1/users/me');
    return response.data as Map<String, dynamic>;
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

  /// Get clients
  Future<Map<String, dynamic>> getClients({
    String? status,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;
    final response = await _dio.get('/api/v1/clients', queryParameters: queryParams);
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

  // ==================== Freelancer Cashflow Parity ====================

  Future<Map<String, dynamic>> getInvoices({
    String? status,
    int? clientId,
    int? projectId,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (clientId != null) queryParams['client_id'] = clientId;
    if (projectId != null) queryParams['project_id'] = projectId;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;
    final response = await _dio.get('/api/v1/invoices', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getInvoice(int invoiceId) async {
    final response = await _dio.get('/api/v1/invoices/$invoiceId');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createInvoice(Map<String, dynamic> data) async {
    final response = await _dio.post('/api/v1/invoices', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateInvoice(int invoiceId, Map<String, dynamic> data) async {
    final response = await _dio.put('/api/v1/invoices/$invoiceId', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getExpenses({
    int? projectId,
    String? category,
    String? startDate,
    String? endDate,
    int? page,
    int? perPage,
  }) async {
    final queryParams = <String, dynamic>{};
    if (projectId != null) queryParams['project_id'] = projectId;
    if (category != null) queryParams['category'] = category;
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    if (page != null) queryParams['page'] = page;
    if (perPage != null) queryParams['per_page'] = perPage;
    final response = await _dio.get('/api/v1/expenses', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createExpense(Map<String, dynamic> data) async {
    final response = await _dio.post('/api/v1/expenses', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getCapacityReport({required String startDate, required String endDate}) async {
    final response = await _dio.get(
      '/api/v1/reports/capacity',
      queryParameters: {
        'start_date': startDate,
        'end_date': endDate,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getTimesheetPeriods({String? status, String? startDate, String? endDate}) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    final response = await _dio.get('/api/v1/timesheet-periods', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submitTimesheetPeriod(int periodId) async {
    final response = await _dio.post('/api/v1/timesheet-periods/$periodId/submit');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> approveTimesheetPeriod(int periodId, {String? comment}) async {
    final data = <String, dynamic>{};
    if (comment != null && comment.trim().isNotEmpty) data['comment'] = comment.trim();
    final response = await _dio.post('/api/v1/timesheet-periods/$periodId/approve', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rejectTimesheetPeriod(int periodId, {String? reason}) async {
    final data = <String, dynamic>{};
    if (reason != null && reason.trim().isNotEmpty) data['reason'] = reason.trim();
    final response = await _dio.post('/api/v1/timesheet-periods/$periodId/reject', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getLeaveTypes() async {
    final response = await _dio.get('/api/v1/time-off/leave-types');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getTimeOffRequests({
    String? status,
    String? startDate,
    String? endDate,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    final response = await _dio.get('/api/v1/time-off/requests', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createTimeOffRequest({
    required int leaveTypeId,
    required String startDate,
    required String endDate,
    double? requestedHours,
    String? comment,
    bool submit = true,
  }) async {
    final data = <String, dynamic>{
      'leave_type_id': leaveTypeId,
      'start_date': startDate,
      'end_date': endDate,
      'submit': submit,
    };
    if (requestedHours != null) data['requested_hours'] = requestedHours;
    if (comment != null && comment.trim().isNotEmpty) data['comment'] = comment.trim();
    final response = await _dio.post('/api/v1/time-off/requests', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getTimeOffBalances({int? userId}) async {
    final queryParams = <String, dynamic>{};
    if (userId != null) queryParams['user_id'] = userId;
    final response = await _dio.get('/api/v1/time-off/balances', queryParameters: queryParams);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> approveTimeOffRequest(int requestId, {String? comment}) async {
    final data = <String, dynamic>{};
    if (comment != null && comment.trim().isNotEmpty) data['comment'] = comment.trim();
    final response = await _dio.post('/api/v1/time-off/requests/$requestId/approve', data: data);
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> rejectTimeOffRequest(int requestId, {String? comment}) async {
    final data = <String, dynamic>{};
    if (comment != null && comment.trim().isNotEmpty) data['comment'] = comment.trim();
    final response = await _dio.post('/api/v1/time-off/requests/$requestId/reject', data: data);
    return response.data as Map<String, dynamic>;
  }
}
