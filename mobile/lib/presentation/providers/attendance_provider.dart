import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

class AttendanceState {
  const AttendanceState({
    this.loading = false,
    this.workActive = false,
    this.breakActive = false,
    this.error,
    this.workPeriod,
    this.today,
  });

  final bool loading;
  final bool workActive;
  final bool breakActive;
  final String? error;
  final Map<String, dynamic>? workPeriod;
  final Map<String, dynamic>? today;

  AttendanceState copyWith({
    bool? loading,
    bool? workActive,
    bool? breakActive,
    String? error,
    Map<String, dynamic>? workPeriod,
    Map<String, dynamic>? today,
  }) {
    return AttendanceState(
      loading: loading ?? this.loading,
      workActive: workActive ?? this.workActive,
      breakActive: breakActive ?? this.breakActive,
      error: error,
      workPeriod: workPeriod ?? this.workPeriod,
      today: today ?? this.today,
    );
  }
}

class AttendanceNotifier extends StateNotifier<AttendanceState> {
  AttendanceNotifier(this.ref) : super(const AttendanceState());

  final Ref ref;

  Future<void> refresh() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(loading: false, error: 'Not authenticated');
        return;
      }
      final data = await client.getAttendanceStatus();
      state = AttendanceState(
        workActive: data['work_active'] == true,
        breakActive: data['break_active'] == true,
        workPeriod: data['work_period'] is Map
            ? Map<String, dynamic>.from(data['work_period'] as Map)
            : null,
        today: data['today'] is Map
            ? Map<String, dynamic>.from(data['today'] as Map)
            : null,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  Future<bool> startWorkday() async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(error: 'Not authenticated');
        return false;
      }
      await client.startWorkday();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> endWorkday() async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(error: 'Not authenticated');
        return false;
      }
      await client.endWorkday();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> startBreak() async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(error: 'Not authenticated');
        return false;
      }
      await client.startAttendanceBreak();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> endBreak() async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(error: 'Not authenticated');
        return false;
      }
      await client.endAttendanceBreak();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> loadHistory({int days = 30}) async {
    final client = await ref.read(apiClientProvider.future);
    if (client == null) return const [];
    final data = await client.getAttendanceHistory(days: days);
    final raw = data['records'] ?? data['history'] ?? data['days'] ?? data['items'] ?? const [];
    if (raw is! List) return const [];
    return raw
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<bool> requestCorrection({
    required int attendanceDayId,
    required String reason,
    String entityType = 'AddWorkPeriod',
    int entityId = 0,
    Map<String, dynamic>? correctedValues,
  }) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) {
        state = state.copyWith(error: 'Not authenticated');
        return false;
      }
      await client.requestAttendanceCorrection(
        attendanceDayId: attendanceDayId,
        entityType: entityType,
        entityId: entityId,
        reason: reason,
        correctedValues: correctedValues,
      );
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }
}

final attendanceProvider =
    StateNotifierProvider<AttendanceNotifier, AttendanceState>((ref) {
  return AttendanceNotifier(ref);
});
