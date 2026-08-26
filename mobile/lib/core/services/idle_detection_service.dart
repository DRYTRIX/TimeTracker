import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timetracker_mobile/core/services/notification_service.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';

/// Client-side idle detection for the mobile app.
///
/// While a timer is active and the app is in the foreground, sends a heartbeat
/// every 60 seconds. Tracks last resume / interaction time; after
/// [idleTimeoutMinutes] of no activity shows a "Still working?" notification
/// with a 5-minute grace window, then auto-stops the timer.
///
/// When the app is backgrounded, polls the server for ``idle_notified`` (nudged
/// by the Android foreground task) so the local notification still fires.
/// When the app is killed, the server-side `check_idle_timers` job is the
/// safety net (requires heartbeats to have been flowing while the app was open).
class IdleDetectionService with WidgetsBindingObserver {
  IdleDetectionService._();

  static final IdleDetectionService instance = IdleDetectionService._();

  static const String prefsIdleTimeoutKey = 'idle_timeout_minutes';
  static const int defaultIdleTimeoutMinutes = 30;
  static const Duration heartbeatInterval = Duration(seconds: 60);
  static const Duration checkInterval = Duration(seconds: 30);
  static const Duration gracePeriod = Duration(minutes: 5);

  TimeTrackingRepository? _repository;
  Timer? _heartbeatTimer;
  Timer? _checkTimer;
  Timer? _graceTimer;
  DateTime _lastActivity = DateTime.now();
  int _idleTimeoutMinutes = defaultIdleTimeoutMinutes;
  bool _promptShown = false;
  bool _started = false;
  bool _timerActive = false;
  bool _inForeground = true;
  bool _taskDataCallbackRegistered = false;
  DateTime? _idleStopAt;

  bool get isRunning => _started;

  Future<void> start(TimeTrackingRepository? repository) async {
    _repository = repository;
    if (_started) return;
    _started = true;
    WidgetsBinding.instance.addObserver(this);
    final prefs = await SharedPreferences.getInstance();
    _idleTimeoutMinutes =
        prefs.getInt(prefsIdleTimeoutKey) ?? defaultIdleTimeoutMinutes;
    _lastActivity = DateTime.now();
    _heartbeatTimer =
        Timer.periodic(heartbeatInterval, (_) => _sendHeartbeat());
    _checkTimer = Timer.periodic(checkInterval, (_) => _tick());
    NotificationService.instance.onIdleAction = respondToIdlePrompt;
    _registerForegroundTaskCallback();
  }

  void stop() {
    if (!_started) return;
    _started = false;
    WidgetsBinding.instance.removeObserver(this);
    _unregisterForegroundTaskCallback();
    _heartbeatTimer?.cancel();
    _checkTimer?.cancel();
    _graceTimer?.cancel();
    _heartbeatTimer = null;
    _checkTimer = null;
    _graceTimer = null;
    _promptShown = false;
    NotificationService.instance.onIdleAction = null;
  }

  void setRepository(TimeTrackingRepository? repository) {
    _repository = repository;
  }

  Future<void> updateFromTimerStatus({
    required bool active,
    int? idleTimeoutMinutes,
    bool idleNotified = false,
  }) async {
    _timerActive = active;
    if (idleTimeoutMinutes != null && idleTimeoutMinutes >= 1) {
      _idleTimeoutMinutes = idleTimeoutMinutes.clamp(1, 480);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(prefsIdleTimeoutKey, _idleTimeoutMinutes);
    }
    if (!active) {
      _cancelGrace();
      await NotificationService.instance.cancelIdlePrompt();
      return;
    }
    if (idleNotified && !_promptShown) {
      // Server already waited idle_timeout; credit that window (Issue #722).
      _idleStopAt = _creditedStopAt(_lastActivity);
      await _showPrompt();
    }
  }

  void markActive() {
    if (_promptShown) return;
    _lastActivity = DateTime.now();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _inForeground = true;
      markActive();
      _sendHeartbeat();
    } else if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached) {
      _inForeground = false;
    }
  }

  Future<void> respondToIdlePrompt(IdlePromptAction action) async {
    _graceTimer?.cancel();
    _graceTimer = null;
    await NotificationService.instance.cancelIdlePrompt();

    if (action == IdlePromptAction.stillWorking) {
      _promptShown = false;
      _idleStopAt = null;
      _lastActivity = DateTime.now();
      await _sendHeartbeatForced();
      return;
    }

    final stopAt = _idleStopAt ?? _creditedStopAt(_lastActivity);
    _promptShown = false;
    _idleStopAt = null;
    try {
      await _repository?.stopTimer(stopTime: stopAt);
    } catch (e) {
      debugPrint('IdleDetectionService stop failed: $e');
    }
    _timerActive = false;
  }

  /// last_active + idle_timeout, capped at now (Issue #722 — not 0 min).
  DateTime _creditedStopAt(DateTime lastActive) {
    final credited =
        lastActive.add(Duration(minutes: _idleTimeoutMinutes));
    final now = DateTime.now();
    return credited.isAfter(now) ? now : credited;
  }

  void _registerForegroundTaskCallback() {
    if (_taskDataCallbackRegistered) return;
    try {
      FlutterForegroundTask.addTaskDataCallback(_onForegroundTaskData);
      _taskDataCallbackRegistered = true;
    } catch (e) {
      debugPrint('IdleDetectionService FGS callback register failed: $e');
    }
  }

  void _unregisterForegroundTaskCallback() {
    if (!_taskDataCallbackRegistered) return;
    try {
      FlutterForegroundTask.removeTaskDataCallback(_onForegroundTaskData);
    } catch (e) {
      debugPrint('IdleDetectionService FGS callback unregister failed: $e');
    }
    _taskDataCallbackRegistered = false;
  }

  void _onForegroundTaskData(Object data) {
    if (data is Map && data['type'] == 'idle_check') {
      // Keep idle detection alive while the Android FGS is running (#722).
      unawaited(_pollServerIdleStatus());
    }
  }

  Future<void> _sendHeartbeat() async {
    if (!_timerActive || _repository == null || _promptShown || !_inForeground) {
      return;
    }
    await _sendHeartbeatForced();
  }

  Future<void> _sendHeartbeatForced() async {
    if (_repository == null) return;
    try {
      await _repository!.sendHeartbeat();
    } catch (e) {
      debugPrint('IdleDetectionService heartbeat failed: $e');
    }
  }

  Future<void> _tick() async {
    if (!_timerActive || _repository == null) return;
    if (_promptShown) return;

    // When backgrounded, rely on server idle_notified (heartbeats stop).
    if (!_inForeground) {
      await _pollServerIdleStatus();
      return;
    }

    final idleFor = DateTime.now().difference(_lastActivity);
    final threshold = Duration(minutes: _idleTimeoutMinutes);
    if (idleFor >= threshold) {
      _idleStopAt = _creditedStopAt(_lastActivity);
      await _showPrompt();
    }
  }

  Future<void> _pollServerIdleStatus() async {
    if (!_timerActive || _repository == null || _promptShown) return;
    try {
      final status = await _repository!.getTimerStatusDetailed();
      final timer = status.timer;
      final active = timer != null && !timer.isPaused;
      await updateFromTimerStatus(
        active: active,
        idleTimeoutMinutes: status.idleTimeoutMinutes,
        idleNotified: status.idleNotified,
      );
    } catch (e) {
      debugPrint('IdleDetectionService background poll failed: $e');
    }
  }

  Future<void> _showPrompt() async {
    if (_promptShown) return;
    _promptShown = true;
    await NotificationService.instance.showIdlePrompt(
      graceMinutes: gracePeriod.inMinutes,
    );
    _graceTimer?.cancel();
    _graceTimer = Timer(gracePeriod, () {
      respondToIdlePrompt(IdlePromptAction.stop);
    });
  }

  void _cancelGrace() {
    _graceTimer?.cancel();
    _graceTimer = null;
    _promptShown = false;
    _idleStopAt = null;
  }
}
