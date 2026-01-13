/// Core configuration for TimeTracker Mobile App
/// 
/// This file handles server URL configuration and other app-wide settings.
/// The server URL can be:
/// 1. Set via environment variable: TIMETRACKER_SERVER_URL
/// 2. Configured in the app settings
/// 3. Defaults to empty string (must be configured by user)

import 'package:shared_preferences/shared_preferences.dart';

class AppConfig {
  static const String _serverUrlKey = 'server_url';
  static const String _apiTokenKey = 'api_token';
  
  /// Get server URL from preferences or environment
  static Future<String?> getServerUrl() async {
    // First check environment variable
    const envUrl = String.fromEnvironment('TIMETRACKER_SERVER_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }
    
    // Then check shared preferences
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_serverUrlKey);
  }
  
  /// Set server URL in preferences
  static Future<bool> setServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    return await prefs.setString(_serverUrlKey, url);
  }
  
  /// Get API token from preferences
  static Future<String?> getApiToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_apiTokenKey);
  }
  
  /// Set API token in preferences
  static Future<bool> setApiToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    return await prefs.setString(_apiTokenKey, token);
  }
  
  /// Clear all stored configuration
  static Future<bool> clearConfig() async {
    final prefs = await SharedPreferences.getInstance();
    return await prefs.remove(_serverUrlKey) && 
           await prefs.remove(_apiTokenKey);
  }
  
  /// Validate server URL format
  static bool isValidServerUrl(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.hasScheme && 
             (uri.scheme == 'http' || uri.scheme == 'https') &&
             uri.hasAuthority;
    } catch (e) {
      return false;
    }
  }
  
  /// Get default server URL (can be overridden)
  static String? getDefaultServerUrl() {
    // Can be set at compile time via --dart-define
    const defaultUrl = String.fromEnvironment('DEFAULT_SERVER_URL');
    return defaultUrl.isEmpty ? null : defaultUrl;
  }
}
