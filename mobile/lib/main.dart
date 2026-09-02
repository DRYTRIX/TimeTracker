import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/constants/app_constants.dart';
import 'package:timetracker_mobile/core/services/idle_detection_service.dart';
import 'package:timetracker_mobile/core/services/notification_service.dart';
import 'package:timetracker_mobile/core/telemetry/mobile_otel.dart';
import 'package:timetracker_mobile/core/theme/app_theme.dart';
import 'package:timetracker_mobile/data/storage/local_storage.dart';
import 'package:timetracker_mobile/presentation/providers/theme_mode_provider.dart';
import 'package:timetracker_mobile/presentation/screens/splash_screen.dart';
import 'package:timetracker_mobile/presentation/screens/login_screen.dart';
import 'package:timetracker_mobile/presentation/screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await LocalStorage.init();
  await initMobileOpenTelemetry();

  // Optional Firebase — degrade gracefully when google-services.json is absent.
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp();
    }
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
  } catch (_) {
    // Expected for builds without Firebase config.
  }

  await NotificationService.instance.initialize();
  runApp(
    const ProviderScope(
      child: TimeTrackerApp(),
    ),
  );
}

class TimeTrackerApp extends ConsumerWidget {
  const TimeTrackerApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeModeString = ref.watch(themeModeProvider);
    final themeMode = themeModeFromString(themeModeString);
    return MaterialApp(
      title: 'TimeTracker',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      initialRoute: AppConstants.routeSplash,
      routes: {
        AppConstants.routeSplash: (context) => const SplashScreen(),
        AppConstants.routeLogin: (context) => const LoginScreen(),
        AppConstants.routeHome: (context) => const HomeScreen(),
      },
      builder: (context, child) {
        return Listener(
          behavior: HitTestBehavior.translucent,
          onPointerDown: (_) => IdleDetectionService.instance.markActive(),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}
