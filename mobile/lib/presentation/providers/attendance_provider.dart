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
      final client = ref.read(apiClientProvider);
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
      await ref.read(apiClientProvider).startWorkday();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> endWorkday() async {
    try {
      await ref.read(apiClientProvider).endWorkday();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> startBreak() async {
    try {
      await ref.read(apiClientProvider).startAttendanceBreak();
      await refresh();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> endBreak() async {
    try {
      await ref.read(apiClientProvider).endAttendanceBreak();
      await refresh();
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
