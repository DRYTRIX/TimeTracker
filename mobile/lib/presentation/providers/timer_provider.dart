import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/services/notification_service.dart';
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
  bool get isRunning => isActive && !(timer?.isPaused ?? false);
  bool get isPaused => timer?.isPaused ?? false;
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
      state = state.copyWith(timer: timer, isLoading: false, clearTimer: timer == null);
      await _syncNotificationWithState();
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
      await _showRunningNotification(timer);
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
      await _cancelRunningNotification();
    } on TimerAlreadyStoppedException catch (e) {
      state = state.copyWith(clearTimer: true, isLoading: false, error: e.message);
      await _cancelRunningNotification();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> pauseTimer() async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }
    try {
      state = state.copyWith(isLoading: true, clearError: true);
      final timer = await repository!.pauseTimer();
      state = state.copyWith(timer: timer, isLoading: false);
      await _cancelRunningNotification();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> resumeTimer() async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }
    try {
      state = state.copyWith(isLoading: true, clearError: true);
      final timer = await repository!.resumeTimer();
      state = state.copyWith(timer: timer, isLoading: false);
      await _showRunningNotification(timer);
      _startPolling();
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
    return state.timer!.elapsed;
  }

  Future<void> checkTimerStatus() async {
    await _loadTimerStatus();
  }

  /// Keep the persistent notification in sync after a status poll.
  Future<void> _syncNotificationWithState() async {
    try {
      final timer = state.timer;
      if (timer == null || timer.isPaused) {
        if (NotificationService.instance.isShowing) {
          await NotificationService.instance.cancelTimerNotification();
        }
        return;
      }

      if (!NotificationService.instance.isShowing) {
        await _showRunningNotification(timer);
      }
    } catch (_) {
      // Notification failures must not break timer status sync.
    }
  }

  Future<void> _showRunningNotification(Timer timer) async {
    try {
      final names = await _resolveNames(timer);
      await NotificationService.instance.showTimerNotification(
        taskName: names.taskName,
        projectName: names.projectName,
        startTime: timer.startTime,
        breakSeconds: timer.breakSeconds,
      );
    } catch (_) {
      // Notification failures must not break start/resume.
    }
  }

  Future<void> _cancelRunningNotification() async {
    try {
      await NotificationService.instance.cancelTimerNotification();
    } catch (_) {
      // Ignore cancel failures.
    }
  }

  Future<({String projectName, String taskName})> _resolveNames(
    Timer timer,
  ) async {
    var projectName = 'Project';
    var taskName = '';

    if (repository == null) {
      return (projectName: projectName, taskName: taskName);
    }

    try {
      if (timer.projectId != null) {
        final project = await repository!.getProject(timer.projectId!);
        projectName = project.name;
      }
    } catch (_) {
      // Keep fallback label if lookup fails (offline / missing project).
    }

    try {
      if (timer.taskId != null) {
        final task = await repository!.getTask(timer.taskId!);
        taskName = task.name;
      }
    } catch (_) {
      // Task name is optional.
    }

    return (projectName: projectName, taskName: taskName);
  }
}

/// Timer provider
final timerProvider = StateNotifierProvider<TimerNotifier, TimerState>((ref) {
  final repository = ref.watch(timeTrackingRepositoryProvider);
  return TimerNotifier(repository);
});
