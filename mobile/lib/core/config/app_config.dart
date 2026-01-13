import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// App configuration and settings
class AppConfig {
  static const String serverUrlKey = 'server_url';
  static const String apiTokenKey = 'api_token';
  static const _storage = FlutterSecureStorage();

  /// Get server URL from storage (synchronous getter for splash screen)
  static String? get serverUrl {
    // This is a synchronous getter, but we can't access SharedPreferences synchronously
    // For now, return null and let the splash screen handle async loading
    return null;
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

  /// Clear all stored configuration
  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(serverUrlKey);
    await _storage.delete(key: apiTokenKey);
  }
}
