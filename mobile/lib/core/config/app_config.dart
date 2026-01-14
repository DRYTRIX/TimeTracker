import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// App configuration and settings
class AppConfig {
  static const String serverUrlKey = 'server_url';
  static const String apiTokenKey = 'api_token';
  static const String syncIntervalKey = 'sync_interval';
  static const String autoSyncKey = 'auto_sync';
  static const String themeModeKey = 'theme_mode';
  static const _storage = FlutterSecureStorage();

  /// Get server URL from storage (synchronous getter for splash screen)
  static String? get serverUrl {
    // This is a synchronous getter, but we can't access SharedPreferences synchronously
    // For now, return null and let the splash screen handle async loading
    return null;
  }

  /// Get sync interval (synchronous getter)
  static int get syncInterval {
    // This is a synchronous getter, but we can't access SharedPreferences synchronously
    // For now, return default value
    return 60;
  }

  /// Get auto sync setting (synchronous getter)
  static bool get autoSync {
    // This is a synchronous getter, but we can't access SharedPreferences synchronously
    // For now, return default value
    return true;
  }

  /// Get theme mode (synchronous getter)
  static String get themeMode {
    // This is a synchronous getter, but we can't access SharedPreferences synchronously
    // For now, return default value
    return 'system';
  }

  /// Check if token exists (synchronous getter for splash screen)
  static bool get hasToken {
    // This is a synchronous getter, but we can't access secure storage synchronously
    // For now, return false and let the splash screen handle async loading
    return false;
  }

  /// Get server URL from storage
  static Future<String?> getServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(serverUrlKey);
  }

  /// Save server URL to storage
  static Future<void> setServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(serverUrlKey, url);
  }

  /// Clear server URL from storage
  static Future<void> clearServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(serverUrlKey);
  }

  /// Set auto sync setting
  static Future<void> setAutoSync(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(autoSyncKey, value);
  }

  /// Clear all stored configuration
  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(serverUrlKey);
    await prefs.remove(syncIntervalKey);
    await prefs.remove(autoSyncKey);
    await prefs.remove(themeModeKey);
    await _storage.delete(key: apiTokenKey);
  }

  /// Clear all stored configuration (alias for clear)
  static Future<void> clearAll() async {
    await clear();
  }
}
