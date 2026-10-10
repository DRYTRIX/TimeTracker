import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timetracker_mobile/core/services/notification_service.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';

/// Server-authoritative idle handling for the mobile app (Issue #722).
///
/// The app NEVER decides on its own whether the timer is idle and never stops
/// it locally: the server sweep arms an idle check and this app renders the
/// "Still working?" prompt when the status poll (nudged by the Android
/// foreground task) or an FCM ``idle_timeout`` data message reports
/// ``idle_notified``. Answers go through the idempotent
/// ``POST /api/v1/timer/idle-response`` endpoint carrying the check token, so
/// the first device to answer wins and stale answers are ignored.
///
/// While the app is in the foreground it heartbeats every 60 seconds (which
/// keeps the server from arming a check); once backgrounded the heartbeats
/// stop and the server takes over.
class IdleDetectionService with WidgetsBindingObserver {
  IdleDetectionService._();

  static final IdleDetectionService instance = IdleDetectionService._();

  static const String prefsIdleTimeoutKey = 'idle_timeout_minutes';
  static const String prefsUnansweredActionKey = 'idle_unanswered_action';
  static const int defaultIdleTimeoutMinutes = 30;
  static const Duration heartbeatInterval = Duration(seconds: 60);
  static const Duration checkInterval = Duration(seconds: 30);
  static const Duration gracePeriod = Duration(minutes: 5);

  TimeTrackingRepository? _repository;
  Timer? _heartbeatTimer;
  Timer? _checkTimer;
  Timer? _graceTimer;
  int _idleTimeoutMinutes = defaultIdleTimeoutMinutes;
  String _unansweredAction = 'review';
  bool _promptShown = false;
  bool _started = false;
  bool _timerActive = false;
  bool _inForeground = true;
  bool _taskDataCallbackRegistered = false;
  bool _needsReview = false;

  /// The server's idle check token (idle_notified_at) for the shown prompt.
  String? _idleNotifiedAt;

  bool get isRunning => _started;

  /// True while the grace window of a shown "Still working?" prompt is open.
  bool get isPromptActive => _promptShown;

  Future<void> start(TimeTrackingRepository? repository) async {
    _repository = repository;
    if (_started) return;
    _started = true;
    WidgetsBinding.instance.addObserver(this);
    final prefs = await SharedPreferences.getInstance();
    _idleTimeoutMinutes =
        prefs.getInt(prefsIdleTimeoutKey) ?? defaultIdleTimeoutMinutes;
    final storedAction = prefs.getString(prefsUnansweredActionKey);
    _unansweredAction =
        storedAction == 'auto_stop' ? 'auto_stop' : 'review';
    _heartbeatTimer =
        Timer.periodic(heartbeatInterval, (_) => _sendHeartbeat());
    _checkTimer = Timer.periodic(checkInterval, (_) => _tick());
    NotificationService.instance.onIdleAction = respondToIdlePrompt;
    NotificationService.instance.onIdlePush = _onIdlePushFromServer;
    _registerForegroundTaskCallback();

    // The app may have been cold-started by an idle prompt action tap.
    final pending = NotificationService.instance.consumePendingIdleAction();
    if (pending != null) {
      await respondToIdlePrompt(pending);
    }
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
    NotificationService.instance.onIdlePush = null;
    NotificationService.instance.onIdlePromptOpened = null;
  }

  void setRepository(TimeTrackingRepository? repository) {
    _repository = repository;
  }

  Future<void> updateFromTimerStatus({
    required bool active,
    int? idleTimeoutMinutes,
    bool idleNotified = false,
    String? idleNotifiedAt,
    String? idleUnansweredAction,
    bool needsReview = false,
  }) async {
    _timerActive = active;
    if (idleTimeoutMinutes != null && idleTimeoutMinutes >= 1) {
      _idleTimeoutMinutes = idleTimeoutMinutes.clamp(1, 480);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(prefsIdleTimeoutKey, _idleTimeoutMinutes);
    }
    if (idleUnansweredAction != null) {
      _unansweredAction =
          idleUnansweredAction == 'auto_stop' ? 'auto_stop' : 'review';
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(prefsUnansweredActionKey, _unansweredAction);
    }
    if (!active) {
      _cancelGrace();
      await NotificationService.instance.cancelIdlePrompt();
      return;
    }
    _needsReview = needsReview;
    if (!idleNotified && _promptShown) {
      // The check was resolved elsewhere (another device answered or the
      // server acted) — dismiss the local prompt.
      _cancelGrace();
      await NotificationService.instance.cancelIdlePrompt();
      return;
    }
    if (idleNotified && !_promptShown && !needsReview) {
      // Server-armed idle check: render it with its token (Issue #722).
      // The needs_review guard prevents the old re-prompt loop: a flagged
      // timer stays idle_notified server-side until reviewed.
      _idleNotifiedAt = idleNotifiedAt;
      await _showPrompt();
    }
  }

  /// External activity hint (pointer/timer events). The server decides
  /// idleness via heartbeats, so this no longer drives local state.
  void markActive() {}

  /// Server FCM idle_timeout wake-up (Issue #722): render the armed check.
  void _onIdlePushFromServer(Map<String, dynamic> data) {
    if (!_timerActive || _promptShown || _needsReview) return;
    final action = (data['idle_unanswered_action'] as String?)?.trim().toLowerCase();
    if (action == 'auto_stop' || action == 'review') {
      _unansweredAction = action!;
    }
    _idleNotifiedAt = data['idle_notified_at'] as String?;
    unawaited(_showPrompt());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _inForeground = true;
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

    final answer =
        action == IdlePromptAction.stillWorking ? 'yes' : 'stop';
    final token = _idleNotifiedAt;
    _promptShown = false;
    _idleNotifiedAt = null;
    try {
      // The server decides: "yes" resets the idle window, "stop" stops the
      // timer now. already_resolved means another device answered first.
      await _repository?.idleResponse(answer, notifiedAt: token);
    } catch (e) {
      debugPrint('IdleDetectionService idle response failed: $e');
    }
  }

  /// Grace expired unanswered: the SERVER sweep resolves the check (flags in
  /// review mode, stops credited in auto_stop mode) — never act locally.
  Future<void> _onGraceExpired() async {
    await NotificationService.instance.cancelIdlePrompt();
    _promptShown = false;
    if (_unansweredAction != 'auto_stop') {
      await NotificationService.instance.showNeedsReviewNotification();
    }
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
    // The server decides when the timer is idle — poll for armed checks
    // both foreground and background (Issue #722).
    await _pollServerIdleStatus();
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
        idleNotifiedAt: status.idleNotifiedAt,
        idleUnansweredAction: status.idleUnansweredAction,
        needsReview: status.needsReview,
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
      autoStop: _unansweredAction == 'auto_stop',
    );
    _graceTimer?.cancel();
    _graceTimer = Timer(gracePeriod, () {
      unawaited(_onGraceExpired());
    });
  }

  void _cancelGrace() {
    _graceTimer?.cancel();
    _graceTimer = null;
    _promptShown = false;
    _idleNotifiedAt = null;
  }
}
