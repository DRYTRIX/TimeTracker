import 'package:dio/dio.dart';
import 'dart:typed_data';
import 'package:timetracker_mobile/utils/ssl/ssl_utils.dart';

/// HTTP client for TimeTracker `/api/v1` (Bearer token after login).
class ApiClient {
  ApiClient({
    required String baseUrl,
    Set<String>? trustedInsecureHosts,
  })  : _trusted = trustedInsecureHosts ?? {},
        _dio = Dio() {
    var normalized = baseUrl.trim();
    if (!normalized.endsWith('/')) {
      normalized = '$normalized/';
    }
    _baseUrl = normalized;
    _dio.options = BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
      validateStatus: (_) => true,
    );
    configureDioTrustedHosts(_dio, _trusted);
  }

  final Dio _dio;
  final Set<String> _trusted;
  late final String _baseUrl;

  String get baseUrl => _baseUrl;

  Future<void> setAuthToken(String token) async {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  Future<Response<dynamic>> validateTokenRaw() {
    return _dio.get<dynamic>('/api/v1/timer/status');
  }

  Future<Map<String, dynamic>> getUsersMe() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/users/me');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    final me = await getUsersMe();
    final u = me['user'];
    if (u is Map<String, dynamic>) return u;
    if (u is Map) return Map<String, dynamic>.from(u);
    return {};
  }

  Future<Map<String, dynamic>> getTimerStatus() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/timer/status');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> startTimer({
    required int projectId,
    int? taskId,
    String? notes,
    int? templateId,
  }) async {
    final body = <String, dynamic>{
      'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (notes != null) 'notes': notes,
      if (templateId != null) 'template_id': templateId,
    };
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/timer/start', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> stopTimer() async {
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/timer/stop');
    final code = res.statusCode ?? 0;
    if (code >= 200 && code < 300) {
      return Map<String, dynamic>.from(res.data ?? {});
    }
    throw DioException(
      requestOptions: res.requestOptions,
      response: res,
      type: DioExceptionType.badResponse,
    );
  }

  Future<Map<String, dynamic>> getTimeEntries({
    int? projectId,
    String? startDate,
    String? endDate,
    bool? billable,
    int? page,
    int? perPage,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/time-entries',
      queryParameters: <String, dynamic>{
        if (projectId != null) 'project_id': projectId,
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
        if (billable != null) 'billable': billable.toString(),
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTimeEntry(int entryId) async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/time-entries/$entryId');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> createTimeEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
    String? idempotencyKey,
  }) async {
    final body = <String, dynamic>{
      'project_id': projectId,
      'start_time': startTime,
      if (taskId != null) 'task_id': taskId,
      if (endTime != null) 'end_time': endTime,
      if (notes != null) 'notes': notes,
      if (tags != null) 'tags': tags,
      if (billable != null) 'billable': billable,
    };
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-entries',
      data: body,
      options: idempotencyKey != null && idempotencyKey.isNotEmpty
          ? Options(headers: {'Idempotency-Key': idempotencyKey})
          : null,
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> updateTimeEntry(
    int entryId, {
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
    String? ifUpdatedAt,
  }) async {
    final body = <String, dynamic>{
      if (projectId != null) 'project_id': projectId,
      if (taskId != null) 'task_id': taskId,
      if (startTime != null) 'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (notes != null) 'notes': notes,
      if (tags != null) 'tags': tags,
      if (billable != null) 'billable': billable,
      if (ifUpdatedAt != null) 'if_updated_at': ifUpdatedAt,
    };
    final res = await _dio.patch<Map<String, dynamic>>('/api/v1/time-entries/$entryId', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<void> deleteTimeEntry(int entryId) async {
    final res = await _dio.delete<Map<String, dynamic>>('/api/v1/time-entries/$entryId');
    _throwIfError(res);
  }

  Future<Map<String, dynamic>> getProjects({
    String? status,
    int? clientId,
    int? page,
    int? perPage,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/projects',
      queryParameters: <String, dynamic>{
        if (status != null) 'status': status,
        if (clientId != null) 'client_id': clientId,
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getProject(int projectId) async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/projects/$projectId');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTasks({
    int? projectId,
    String? status,
    int? page,
    int? perPage,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/tasks',
      queryParameters: <String, dynamic>{
        if (projectId != null) 'project_id': projectId,
        if (status != null) 'status': status,
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTask(int taskId) async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/tasks/$taskId');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getClients({
    String? status,
    int? page,
    int? perPage,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/clients',
      queryParameters: <String, dynamic>{
        if (status != null) 'status': status,
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getInvoices({
    int? page,
    int? perPage,
    String? status,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/invoices',
      queryParameters: <String, dynamic>{
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
        if (status != null) 'status': status,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getInvoice(int invoiceId) async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/invoices/$invoiceId');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> createInvoiceFromTimeEntries({
    required int projectId,
    required List<int> timeEntryIds,
    String? issueDate,
    String? dueDate,
  }) async {
    final body = <String, dynamic>{
      'project_id': projectId,
      'time_entry_ids': timeEntryIds,
      if (issueDate != null) 'issue_date': issueDate,
      if (dueDate != null) 'due_date': dueDate,
    };
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/invoices/from-time-entries', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> generateInvoiceFromTime(
    int invoiceId, {
    required List<int> timeEntryIds,
    bool replaceExisting = true,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/invoices/$invoiceId/generate-from-time',
      data: {'time_entry_ids': timeEntryIds, 'replace_existing': replaceExisting},
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> setInvoiceItems(int invoiceId, List<Map<String, dynamic>> items) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/v1/invoices/$invoiceId/items',
      data: {'items': items},
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<List<int>> downloadInvoicePdf(int invoiceId) async {
    final res = await _dio.get<List<int>>(
      '/api/v1/invoices/$invoiceId/pdf',
      options: Options(responseType: ResponseType.bytes),
    );
    _throwIfError(res);
    final dynamic data = res.data;
    if (data is List<int>) return data;
    if (data is Uint8List) return data.toList();
    return <int>[];
  }

  Future<Map<String, dynamic>> getPayments({int? invoiceId, int? page, int? perPage}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/payments',
      queryParameters: <String, dynamic>{
        if (invoiceId != null) 'invoice_id': invoiceId,
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getReportSummary({
    String? startDate,
    String? endDate,
    int? projectId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/reports/summary',
      queryParameters: <String, dynamic>{
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
        if (projectId != null) 'project_id': projectId,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getExpenses({
    int? page,
    int? perPage,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/expenses',
      queryParameters: <String, dynamic>{
        if (page != null) 'page': page,
        if (perPage != null) 'per_page': perPage,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> createExpense(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/expenses', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> createInvoice(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/invoices', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> updateInvoice(int invoiceId, Map<String, dynamic> body) async {
    final res = await _dio.patch<Map<String, dynamic>>('/api/v1/invoices/$invoiceId', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTimesheetPeriods({
    String? startDate,
    String? endDate,
    String? status,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/timesheet-periods',
      queryParameters: <String, dynamic>{
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
        if (status != null) 'status': status,
      },
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getCapacityReport({
    required String startDate,
    required String endDate,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/reports/capacity',
      queryParameters: {'start_date': startDate, 'end_date': endDate},
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getLeaveTypes() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/time-off/leave-types');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTimeOffRequests() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/time-off/requests');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> getTimeOffBalances() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/time-off/balances');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<void> submitTimesheetPeriod(int periodId) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/timesheet-periods/$periodId/submit');
    _throwIfError(res);
  }

  Future<void> approveTimesheetPeriod(int periodId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/timesheet-periods/$periodId/approve',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<void> rejectTimesheetPeriod(int periodId, {String? reason}) async {
    final r = (reason ?? 'Rejected').trim();
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/timesheet-periods/$periodId/reject',
      data: {'reason': r.isEmpty ? 'Rejected' : r},
    );
    _throwIfError(res);
  }

  Future<void> deleteTimesheetPeriod(int periodId) async {
    final res = await _dio.delete<Map<String, dynamic>>('/api/v1/timesheet-periods/$periodId');
    _throwIfError(res);
  }

  Future<Map<String, dynamic>> createTimeOffRequest({
    required int leaveTypeId,
    required String startDate,
    required String endDate,
    double? requestedHours,
    String? comment,
  }) async {
    final body = <String, dynamic>{
      'leave_type_id': leaveTypeId,
      'start_date': startDate,
      'end_date': endDate,
      if (requestedHours != null) 'requested_hours': requestedHours,
      if (comment != null && comment.isNotEmpty) 'comment': comment,
    };
    final res = await _dio.post<Map<String, dynamic>>('/api/v1/time-off/requests', data: body);
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<void> approveTimeOffRequest(int requestId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-off/requests/$requestId/approve',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<void> rejectTimeOffRequest(int requestId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-off/requests/$requestId/reject',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<void> deleteTimeOffRequest(int requestId) async {
    final res = await _dio.delete<Map<String, dynamic>>('/api/v1/time-off/requests/$requestId');
    _throwIfError(res);
  }

  Future<Map<String, dynamic>> getTimeEntryApprovals() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/time-entry-approvals');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<void> approveTimeEntryApproval(int approvalId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-entry-approvals/$approvalId/approve',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<void> rejectTimeEntryApproval(int approvalId, {required String reason}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-entry-approvals/$approvalId/reject',
      data: {'reason': reason},
    );
    _throwIfError(res);
  }

  Future<void> requestTimeEntryApproval(int entryId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/time-entries/$entryId/request-approval',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<Map<String, dynamic>> getInvoiceApprovals() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/invoice-approvals');
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<Map<String, dynamic>> requestInvoiceApproval(int invoiceId, List<int> approverIds) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/invoices/$invoiceId/request-approval',
      data: {'approver_ids': approverIds},
    );
    _throwIfError(res);
    return Map<String, dynamic>.from(res.data ?? {});
  }

  Future<void> approveInvoiceApproval(int approvalId, {String? comment}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/invoice-approvals/$approvalId/approve',
      data: {if (comment != null) 'comment': comment},
    );
    _throwIfError(res);
  }

  Future<void> rejectInvoiceApproval(int approvalId, {required String reason}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/invoice-approvals/$approvalId/reject',
      data: {'reason': reason},
    );
    _throwIfError(res);
  }

  Future<void> closeTimesheetPeriod(int periodId, {String? reason}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/timesheet-periods/$periodId/close',
      data: {if (reason != null) 'reason': reason},
    );
    _throwIfError(res);
  }

  Future<List<Map<String, dynamic>>> getUsers({int perPage = 100}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/users',
      queryParameters: {'per_page': perPage},
    );
    _throwIfError(res);
    return List<Map<String, dynamic>>.from(res.data?['users'] ?? const []);
  }

  void _throwIfError(Response<dynamic> res) {
    final code = res.statusCode ?? 0;
    if (code >= 200 && code < 300) return;
    final data = res.data;
    String msg = 'HTTP $code';
    if (data is Map) {
      final err = data['error'] ?? data['message'];
      if (err != null) msg = err.toString();
    }
    throw DioException(
      requestOptions: res.requestOptions,
      response: res,
      type: DioExceptionType.badResponse,
      message: msg,
    );
  }
}
