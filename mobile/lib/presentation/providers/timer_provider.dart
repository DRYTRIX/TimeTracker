import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/timer.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Provider for time tracking repository
final timeTrackingRepositoryProvider = Provider<TimeTrackingRepository?>((ref) {
  final apiClientAsync = ref.watch(apiClientProvider);
  return apiClientAsync.when(
    data: (apiClient) => apiClient != null ? TimeTrackingRepository(apiClient) : null,
    loading: () => null,
    error: (_, __) => null,
  );
});

/// Timer state
class TimerState {
  final Timer? timer;
  final bool isLoading;
  final String? error;

  TimerState({
    this.timer,
    this.isLoading = false,
    this.error,
  });

  TimerState copyWith({
    Timer? timer,
    bool? isLoading,
    String? error,
    bool clearTimer = false,
    bool clearError = false,
  }) {
    return TimerState(
      timer: clearTimer ? null : (timer ?? this.timer),
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
    );
  }

  bool get isActive => timer != null;
  bool get isRunning => isActive;
  Timer? get activeTimer => timer;
}

/// Timer state notifier
class TimerNotifier extends StateNotifier<TimerState> {
  final TimeTrackingRepository? repository;

  TimerNotifier(this.repository) : super(TimerState()) {
    if (repository != null) {
      _loadTimerStatus();
      // Poll timer status every 5 seconds if active
      _startPolling();
    }
  }

  void _startPolling() {
    Future.delayed(const Duration(seconds: 5), () {
      if (state.isActive && repository != null) {
        _loadTimerStatus();
        _startPolling();
      }
    });
  }

  Future<void> _loadTimerStatus() async {
    if (repository == null) return;

    try {
      state = state.copyWith(isLoading: true, clearError: true);
      final timer = await repository!.getTimerStatus();
      state = state.copyWith(timer: timer, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> startTimer({
    required int projectId,
    int? taskId,
    String? notes,
  }) async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }

    try {
      state = state.copyWith(isLoading: true, clearError: true);
      final timer = await repository!.startTimer(
        projectId: projectId,
        taskId: taskId,
        notes: notes,
      );
      state = state.copyWith(timer: timer, isLoading: false);
      // Start polling
      _startPolling();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> stopTimer() async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }

    try {
      state = state.copyWith(isLoading: true, clearError: true);
      await repository!.stopTimer();
      state = state.copyWith(clearTimer: true, isLoading: false, clearError: true);
    } on TimerAlreadyStoppedException catch (e) {
      state = state.copyWith(clearTimer: true, isLoading: false, error: e.message);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> refresh() async {
    await _loadTimerStatus();
  }

  /// Get elapsed time for active timer
  Duration getElapsedTime() {
    if (state.timer == null) {
      return Duration.zero;
    }
    return DateTime.now().difference(state.timer!.startTime);
  }

  Future<void> checkTimerStatus() async {
    await _loadTimerStatus();
  }
}

/// Timer provider
final timerProvider = StateNotifierProvider<TimerNotifier, TimerState>((ref) {
  final repository = ref.watch(timeTrackingRepositoryProvider);
  return TimerNotifier(repository);
});
