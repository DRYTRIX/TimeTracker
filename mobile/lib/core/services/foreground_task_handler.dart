import 'package:flutter_foreground_task/flutter_foreground_task.dart';

/// Top-level entry point for the Android foreground service isolate.
@pragma('vm:entry-point')
void timerForegroundStartCallback() {
  FlutterForegroundTask.setTaskHandler(TimerForegroundTaskHandler());
}

/// Updates the persistent timer notification every second while the
/// foreground service is running, and periodically nudges the main isolate
/// to poll server idle status (Issue #722).
class TimerForegroundTaskHandler extends TaskHandler {
  static const String keyStartTimeMillis = 'timer_start_time_millis';
  static const String keyBreakSeconds = 'timer_break_seconds';
  static const String keyProjectName = 'timer_project_name';
  static const String keyTaskName = 'timer_task_name';
  static const Duration idleNudgeInterval = Duration(seconds: 30);

  DateTime? _lastIdleNudge;

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    await _updateNotification();
    _nudgeIdleCheck(timestamp);
  }

  @override
  void onRepeatEvent(DateTime timestamp) {
    _updateNotification();
    _nudgeIdleCheck(timestamp);
  }

  void _nudgeIdleCheck(DateTime timestamp) {
    final last = _lastIdleNudge;
    if (last != null && timestamp.difference(last) < idleNudgeInterval) {
      return;
    }
    _lastIdleNudge = timestamp;
    try {
      FlutterForegroundTask.sendDataToMain({'type': 'idle_check'});
    } catch (_) {
      // Main isolate may be gone; server check_idle_timers is the safety net.
    }
  }

  @override
  Future<void> onDestroy(DateTime timestamp) async {}

  @override
  void onReceiveData(Object data) {
    // Allow the main isolate to push updated break seconds / labels.
    if (data is Map) {
      final breakSeconds = data['breakSeconds'];
      if (breakSeconds is int) {
        FlutterForegroundTask.saveData(
          key: keyBreakSeconds,
          value: breakSeconds,
        );
      }
      final projectName = data['projectName'];
      if (projectName is String) {
        FlutterForegroundTask.saveData(
          key: keyProjectName,
          value: projectName,
        );
      }
      final taskName = data['taskName'];
      if (taskName is String) {
        FlutterForegroundTask.saveData(
          key: keyTaskName,
          value: taskName,
        );
      }
      final startTimeMillis = data['startTimeMillis'];
      if (startTimeMillis is int) {
        FlutterForegroundTask.saveData(
          key: keyStartTimeMillis,
          value: startTimeMillis,
        );
      }
      _updateNotification();
    }
  }

  Future<void> _updateNotification() async {
    final startMillis =
        await FlutterForegroundTask.getData<int>(key: keyStartTimeMillis);
    final breakSeconds =
        await FlutterForegroundTask.getData<int>(key: keyBreakSeconds) ?? 0;
    final projectName =
        await FlutterForegroundTask.getData<String>(key: keyProjectName) ??
            'Timer';
    final taskName =
        await FlutterForegroundTask.getData<String>(key: keyTaskName) ?? '';

    if (startMillis == null) {
      return;
    }

    final startTime = DateTime.fromMillisecondsSinceEpoch(startMillis);
    final rawSeconds =
        DateTime.now().difference(startTime).inSeconds - breakSeconds;
    final elapsed = Duration(seconds: rawSeconds < 0 ? 0 : rawSeconds);

    final title = _buildTitle(
      projectName: projectName,
      taskName: taskName,
    );
    final text = 'Running ${_formatElapsed(elapsed)}';

    FlutterForegroundTask.updateService(
      notificationTitle: title,
      notificationText: text,
    );
  }

  static String _buildTitle({
    required String projectName,
    required String taskName,
  }) {
    if (taskName.isNotEmpty) {
      return '$projectName · $taskName';
    }
    return projectName.isNotEmpty ? projectName : 'Timer running';
  }

  static String _formatElapsed(Duration d) {
    final h = d.inHours;
    final m = d.inMinutes.remainder(60);
    final s = d.inSeconds.remainder(60);
    if (h > 0) {
      return '${h}h ${m.toString().padLeft(2, '0')}m ${s.toString().padLeft(2, '0')}s';
    }
    if (m > 0) {
      return '${m}m ${s.toString().padLeft(2, '0')}s';
    }
    return '${s}s';
  }
}
