import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  static const _storage = FlutterSecureStorage();
  static const String _keyApiToken = 'api_token';
  
  // Store API token securely
  static Future<void> storeToken(String token) async {
    await _storage.write(key: _keyApiToken, value: token);
  }
  
  // Retrieve API token
  static Future<String?> getToken() async {
    return await _storage.read(key: _keyApiToken);
  }
  
  // Delete API token (logout)
  static Future<void> deleteToken() async {
    await _storage.delete(key: _keyApiToken);
  }
  
  // Check if token exists
  static Future<bool> hasToken() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }
}
