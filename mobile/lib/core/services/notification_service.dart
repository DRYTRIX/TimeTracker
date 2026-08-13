import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:intl/intl.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:timetracker_mobile/core/constants/app_constants.dart';
import 'package:timetracker_mobile/core/services/foreground_task_handler.dart';

enum IdlePromptAction { stillWorking, stop }

/// Persistent "timer running" notification for Android (foreground service)
/// and iOS (local notification with start time).
class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;
  bool _isShowing = false;
  bool _idlePromptShowing = false;

  /// Callback when the user taps Yes/No on the idle prompt notification.
  void Function(IdlePromptAction action)? onIdleAction;

  bool get isShowing => _isShowing;

  /// Call once at app startup (before [runApp]).
  Future<void> initialize() async {
    if (_initialized) return;

    try {
      // Required for TaskHandler ↔ UI communication on Android.
      FlutterForegroundTask.initCommunicationPort();

      if (Platform.isAndroid) {
        await _initAndroidForegroundTask();
      }

      await _initLocalNotifications();
      await _requestPermissions();
    } catch (e, st) {
      debugPrint('NotificationService.initialize failed: $e\n$st');
    }

    _initialized = true;
  }

  Future<void> _initAndroidForegroundTask() async {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: AppConstants.timerNotificationChannelId,
        channelName: AppConstants.timerNotificationChannelName,
        channelDescription: AppConstants.timerNotificationChannelDescription,
        channelImportance: NotificationChannelImportance.HIGH,
        priority: NotificationPriority.HIGH,
        onlyAlertOnce: true,
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        // iOS uses flutter_local_notifications instead.
        showNotification: false,
        playSound: false,
      ),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.repeat(1000),
        autoRunOnBoot: false,
        autoRunOnMyPackageReplaced: false,
        allowWakeLock: true,
        allowWifiLock: false,
      ),
    );
  }

  Future<void> _initLocalNotifications() async {
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: false,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(
      settings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Ensure the Android channel exists for any local-notification fallback.
    final androidPlugin =
        _localNotifications.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(
      const AndroidNotificationChannel(
        AppConstants.timerNotificationChannelId,
        AppConstants.timerNotificationChannelName,
        description: AppConstants.timerNotificationChannelDescription,
        importance: Importance.high,
      ),
    );
    await androidPlugin?.createNotificationChannel(
      const AndroidNotificationChannel(
        AppConstants.idleReminderChannelId,
        AppConstants.idleReminderChannelName,
        description: AppConstants.idleReminderChannelDescription,
        importance: Importance.high,
      ),
    );
  }

  Future<void> _requestPermissions() async {
    if (Platform.isAndroid) {
      final notificationPermission =
          await FlutterForegroundTask.checkNotificationPermission();
      if (notificationPermission != NotificationPermission.granted) {
        await FlutterForegroundTask.requestNotificationPermission();
      }
      // Android 13+ POST_NOTIFICATIONS via permission_handler as a fallback.
      if (await Permission.notification.isDenied) {
        await Permission.notification.request();
      }
    } else if (Platform.isIOS) {
      await _localNotifications
          .resolvePlatformSpecificImplementation<
              IOSFlutterLocalNotificationsPlugin>()
          ?.requestPermissions(alert: true, badge: true, sound: false);
    }
  }

  void _onNotificationTapped(NotificationResponse response) {
    debugPrint(
      'Notification tapped: payload=${response.payload} action=${response.actionId}',
    );
    final actionId = response.actionId;
    if (actionId == 'idle_yes') {
      onIdleAction?.call(IdlePromptAction.stillWorking);
      return;
    }
    if (actionId == 'idle_no') {
      onIdleAction?.call(IdlePromptAction.stop);
      return;
    }
    if (response.payload == 'idle_prompt') {
      // Body tap = still working
      onIdleAction?.call(IdlePromptAction.stillWorking);
    }
  }

  /// Show (or refresh) the persistent timer notification.
  Future<void> showTimerNotification({
    required String taskName,
    required String projectName,
    required DateTime startTime,
    int breakSeconds = 0,
  }) async {
    if (!_initialized) {
      await initialize();
    }

    final title = _buildTitle(projectName: projectName, taskName: taskName);

    if (Platform.isAndroid) {
      await _showAndroidForegroundNotification(
        title: title,
        projectName: projectName,
        taskName: taskName,
        startTime: startTime,
        breakSeconds: breakSeconds,
      );
    } else if (Platform.isIOS) {
      await _showIosLocalNotification(
        title: title,
        startTime: startTime,
        projectName: projectName,
        taskName: taskName,
      );
    }

    _isShowing = true;
  }

  Future<void> _showAndroidForegroundNotification({
    required String title,
    required String projectName,
    required String taskName,
    required DateTime startTime,
    required int breakSeconds,
  }) async {
    await FlutterForegroundTask.saveData(
      key: TimerForegroundTaskHandler.keyStartTimeMillis,
      value: startTime.millisecondsSinceEpoch,
    );
    await FlutterForegroundTask.saveData(
      key: TimerForegroundTaskHandler.keyBreakSeconds,
      value: breakSeconds,
    );
    await FlutterForegroundTask.saveData(
      key: TimerForegroundTaskHandler.keyProjectName,
      value: projectName,
    );
    await FlutterForegroundTask.saveData(
      key: TimerForegroundTaskHandler.keyTaskName,
      value: taskName,
    );

    final elapsed = _elapsed(startTime, breakSeconds);
    final text = 'Running ${_formatElapsed(elapsed)}';

    if (await FlutterForegroundTask.isRunningService) {
      await FlutterForegroundTask.updateService(
        notificationTitle: title,
        notificationText: text,
      );
      FlutterForegroundTask.sendDataToTask({
        'startTimeMillis': startTime.millisecondsSinceEpoch,
        'breakSeconds': breakSeconds,
        'projectName': projectName,
        'taskName': taskName,
      });
    } else {
      await FlutterForegroundTask.startService(
        serviceId: AppConstants.notificationTimerRunning,
        notificationTitle: title,
        notificationText: text,
        notificationInitialRoute: AppConstants.routeHome,
        callback: timerForegroundStartCallback,
      );
    }
  }

  Future<void> _showIosLocalNotification({
    required String title,
    required DateTime startTime,
    required String projectName,
    required String taskName,
  }) async {
    final since = DateFormat.Hm().format(startTime.toLocal());
    final label = taskName.isNotEmpty
        ? '$taskName · $projectName'
        : projectName;
    final body = 'Running since $since — $label';

    const details = NotificationDetails(
      iOS: DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: false,
        presentSound: false,
        interruptionLevel: InterruptionLevel.passive,
      ),
      android: AndroidNotificationDetails(
        AppConstants.timerNotificationChannelId,
        AppConstants.timerNotificationChannelName,
        channelDescription: AppConstants.timerNotificationChannelDescription,
        importance: Importance.high,
        priority: Priority.high,
        ongoing: true,
        autoCancel: false,
        onlyAlertOnce: true,
      ),
    );

    await _localNotifications.show(
      AppConstants.notificationTimerRunning,
      title,
      body,
      details,
      payload: 'timer_running',
    );
  }

  /// "Still working?" idle prompt with Yes / No actions.
  Future<void> showIdlePrompt({int graceMinutes = 5}) async {
    if (!_initialized) {
      await initialize();
    }

    const title = 'Still working?';
    final body =
        'Your timer will stop in $graceMinutes minutes if you do not answer.';

    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        AppConstants.idleReminderChannelId,
        AppConstants.idleReminderChannelName,
        channelDescription: AppConstants.idleReminderChannelDescription,
        importance: Importance.high,
        priority: Priority.high,
        category: AndroidNotificationCategory.alarm,
        ongoing: true,
        autoCancel: false,
        actions: const <AndroidNotificationAction>[
          AndroidNotificationAction(
            'idle_yes',
            'Yes, still working',
            showsUserInterface: true,
          ),
          AndroidNotificationAction(
            'idle_no',
            'No, stop timer',
            showsUserInterface: true,
          ),
        ],
      ),
      iOS: const DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        interruptionLevel: InterruptionLevel.timeSensitive,
        categoryIdentifier: 'idle_prompt',
      ),
    );

    await _localNotifications.show(
      AppConstants.notificationIdleReminder,
      title,
      body,
      details,
      payload: 'idle_prompt',
    );
    _idlePromptShowing = true;
  }

  Future<void> cancelIdlePrompt() async {
    if (!_idlePromptShowing) {
      await _localNotifications.cancel(AppConstants.notificationIdleReminder);
      return;
    }
    await _localNotifications.cancel(AppConstants.notificationIdleReminder);
    _idlePromptShowing = false;
  }

  /// Update elapsed text (mainly used on platforms that do not tick via FGS).
  Future<void> updateTimerNotification(Duration elapsed) async {
    if (!_isShowing) return;
    // Android FGS handler updates itself every second.
    if (Platform.isAndroid) return;
  }

  /// Stop the foreground service / cancel the local notification.
  Future<void> cancelTimerNotification() async {
    if (Platform.isAndroid) {
      if (await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.stopService();
      }
      await FlutterForegroundTask.clearAllData();
    }

    await _localNotifications.cancel(AppConstants.notificationTimerRunning);
    _isShowing = false;
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

  static Duration _elapsed(DateTime startTime, int breakSeconds) {
    final raw = DateTime.now().difference(startTime).inSeconds - breakSeconds;
    return Duration(seconds: raw < 0 ? 0 : raw);
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
