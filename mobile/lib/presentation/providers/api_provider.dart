import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/config/app_config.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/utils/auth/auth_service.dart';

/// Provider for API client (authenticated when token is present)
final apiClientProvider = FutureProvider<ApiClient?>((ref) async {
  final serverUrl = await AppConfig.getServerUrl();
  if (serverUrl == null || serverUrl.isEmpty) {
    return null;
  }
  final token = await AuthService.getToken();
  final trustedHosts = await AppConfig.getTrustedInsecureHosts();
  final client = ApiClient(baseUrl: serverUrl, trustedInsecureHosts: trustedHosts);
  if (token != null && token.isNotEmpty) {
    await client.setAuthToken(token);
  }
  return client;
});

/// Provider for API client (synchronous, requires server URL)
final apiClientSyncProvider = Provider.family<ApiClient, String>((ref, baseUrl) {
  return ApiClient(baseUrl: baseUrl);
});
