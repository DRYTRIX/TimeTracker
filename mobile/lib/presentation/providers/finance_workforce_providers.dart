import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Date range for capacity/periods (current week)
({String start, String end}) _weekRange() {
  final now = DateTime.now();
  final start = DateTime(now.year, now.month, now.day - now.weekday + 1);
  final end = start.add(const Duration(days: 6));
  return (start: start.toIso8601String().split('T')[0], end: end.toIso8601String().split('T')[0]);
}

final financeInvoicesProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, page) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'invoices': <Map<String, dynamic>>[], 'pagination': {'page': 1, 'pages': 1}};
  return client.getInvoices(page: page, perPage: 20);
});

final financeExpensesProvider = FutureProvider.family<Map<String, dynamic>, int>((ref, page) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'expenses': <Map<String, dynamic>>[], 'pagination': {'page': 1, 'pages': 1}};
  return client.getExpenses(page: page, perPage: 20);
});

final timesheetPeriodsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'timesheet_periods': <Map<String, dynamic>>[]};
  final range = _weekRange();
  return client.getTimesheetPeriods(startDate: range.start, endDate: range.end);
});

final capacityReportProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'capacity': <Map<String, dynamic>>[]};
  final range = _weekRange();
  return client.getCapacityReport(startDate: range.start, endDate: range.end);
});

final timeOffRequestsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'time_off_requests': <Map<String, dynamic>>[]};
  return client.getTimeOffRequests();
});

final leaveBalancesProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'balances': <Map<String, dynamic>>[]};
  return client.getTimeOffBalances();
});

final leaveTypesProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'leave_types': <Map<String, dynamic>>[]};
  return client.getLeaveTypes();
});

final financeProjectsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'projects': <Map<String, dynamic>>[]};
  return client.getProjects(status: 'active', perPage: 100);
});

final financeClientsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return {'clients': <Map<String, dynamic>>[]};
  return client.getClients(status: 'active', perPage: 100);
});

/// Whether the current user can approve timesheets / time-off
final userCanApproveProvider = FutureProvider<bool>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) return false;
  final me = await client.getUsersMe();
  final user = me['user'] is Map<String, dynamic> ? me['user'] as Map<String, dynamic> : <String, dynamic>{};
  final role = (user['role'] ?? '').toString().toLowerCase();
  return (user['is_admin'] == true) || (role == 'admin' || role == 'owner' || role == 'manager' || role == 'approver');
});
