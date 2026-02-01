import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/config/app_config.dart';

/// Notifier that holds the current theme mode string ('system', 'light', 'dark')
/// and loads the saved value on startup.
class ThemeModeNotifier extends StateNotifier<String> {
  ThemeModeNotifier() : super('system') {
    _load();
  }

  void _load() {
    AppConfig.getThemeMode().then((value) {
      state = value;
    });
  }

  Future<void> setMode(String value) async {
    await AppConfig.setThemeMode(value);
    state = value;
  }
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, String>((ref) => ThemeModeNotifier());

/// Maps stored string to Flutter's ThemeMode.
ThemeMode themeModeFromString(String value) {
  switch (value) {
    case 'light':
      return ThemeMode.light;
    case 'dark':
      return ThemeMode.dark;
    default:
      return ThemeMode.system;
  }
}
