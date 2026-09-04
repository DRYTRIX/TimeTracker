import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:intl/intl.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:timetracker_mobile/core/constants/app_constants.dart';
import 'package:timetracker_mobile/core/services/foreground_task_handler.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';

enum IdlePromptAction { stillWorking, stop }

/// Top-level FCM background handler (must be a top-level or static function).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Background isolate — show a local idle prompt when the server wakes us.
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp();
    }
  } catch (_) {
    // Firebase not configured for this build.
    return;
  }
  final kind = message.data['kind'] ?? message.data['type'];
  if (kind != 'idle_timeout') return;

  final plugin = FlutterLocalNotificationsPlugin();
  const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
  const iosSettings = DarwinInitializationSettings();
  await plugin.initialize(
    const InitializationSettings(android: androidSettings, iOS: iosSettings),
  );
  await plugin.show(
    AppConstants.notificationIdleReminder,
    message.notification?.title ?? message.data['title'] ?? 'Still working?',
    message.notification?.body ??
        message.data['message'] ??
        'Your timer has been idle. Confirm you are still working or it will stop automatically.',
    const NotificationDetails(
      android: AndroidNotificationDetails(
        AppConstants.idleReminderChannelId,
        AppConstants.idleReminderChannelName,
        channelDescription: AppConstants.idleReminderChannelDescription,
        importance: Importance.high,
        priority: Priority.high,
        category: AndroidNotificationCategory.alarm,
      ),
      iOS: DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        interruptionLevel: InterruptionLevel.timeSensitive,
      ),
    ),
    payload: 'idle_prompt',
  );
}

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
  bool _firebaseReady = false;
  StreamSubscription<RemoteMessage>? _onMessageSub;
  StreamSubscription<RemoteMessage>? _onOpenedSub;
  StreamSubscription<String>? _tokenRefreshSub;

  /// Callback when the user taps Yes/No on the idle prompt notification.
  void Function(IdlePromptAction action)? onIdleAction;

  /// Called when an FCM idle_timeout data message arrives (foreground/background open).
  void Function(Map<String, dynamic> data)? onIdlePush;

  bool get isShowing => _isShowing;
  bool get firebaseReady => _firebaseReady;

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
      await _initFirebaseMessaging();
    } catch (e, st) {
      debugPrint('NotificationService.initialize failed: $e\n$st');
    }

    _initialized = true;
  }

  Future<void> _initFirebaseMessaging() async {
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp();
      }

      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      _onMessageSub?.cancel();
      _onMessageSub = FirebaseMessaging.onMessage.listen(_handleRemoteMessage);

      _onOpenedSub?.cancel();
      _onOpenedSub =
          FirebaseMessaging.onMessageOpenedApp.listen(_handleRemoteMessage);

      // Cold-start from a notification tap.
      final initial = await messaging.getInitialMessage();
      if (initial != null) {
        _handleRemoteMessage(initial);
      }

      _firebaseReady = true;
      debugPrint('NotificationService: Firebase Messaging ready');
    } catch (e) {
      // Expected when google-services.json / GoogleService-Info.plist is absent.
      _firebaseReady = false;
      debugPrint('NotificationService: Firebase Messaging unavailable: $e');
    }
  }

  void _handleRemoteMessage(RemoteMessage message) {
    final kind = message.data['kind'] ?? message.data['type'];
    if (kind == 'idle_timeout') {
      onIdlePush?.call(Map<String, dynamic>.from(message.data));
      // Also surface a local notification if one was not already shown.
      unawaited(
        showIdlePrompt(graceMinutes: 5),
      );
    }
  }

  /// Obtain the FCM token and POST it to the TimeTracker server.
  ///
  /// No-ops when Firebase is not configured. Safe to call after every login.
  Future<void> registerDeviceToken(ApiClient apiClient) async {
    if (!_initialized) {
      await initialize();
    }
    if (!_firebaseReady) return;

    try {
      final messaging = FirebaseMessaging.instance;
      final token = await messaging.getToken();
      if (token == null || token.isEmpty) return;

      final platform = Platform.isIOS ? 'ios' : 'android';
      await apiClient.registerDevicePush(
        deviceToken: token,
        platform: platform,
      );

      _tokenRefreshSub?.cancel();
      _tokenRefreshSub = messaging.onTokenRefresh.listen((newToken) async {
        try {
          await apiClient.registerDevicePush(
            deviceToken: newToken,
            platform: platform,
          );
        } catch (e) {
          debugPrint('FCM token refresh register failed: $e');
        }
      });
    } catch (e) {
      debugPrint('NotificationService.registerDeviceToken failed: $e');
    }
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
  ///
  /// Failures are swallowed so a plugin/R8 regression cannot blank the Timer
  /// screen (see GitHub issue #731).
  Future<void> showIdlePrompt({int graceMinutes = 5}) async {
    try {
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
    } catch (e, st) {
      debugPrint('NotificationService.showIdlePrompt failed: $e\n$st');
    }
  }

  /// Cancel the idle prompt if one is showing.
  ///
  /// No-ops when nothing is showing (avoids a redundant plugin cancel that can
  /// throw under R8 full mode — GitHub issue #731). Failures are swallowed.
  Future<void> cancelIdlePrompt() async {
    if (!_idlePromptShowing) {
      return;
    }
    try {
      await _localNotifications.cancel(AppConstants.notificationIdleReminder);
    } catch (e, st) {
      debugPrint('NotificationService.cancelIdlePrompt failed: $e\n$st');
    } finally {
      _idlePromptShowing = false;
    }
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
