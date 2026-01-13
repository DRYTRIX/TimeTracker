import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/config/app_config.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';

/// Provider for API client
final apiClientProvider = FutureProvider<ApiClient?>((ref) async {
  final serverUrl = await AppConfig.getServerUrl();
  if (serverUrl == null || serverUrl.isEmpty) {
    return null;
  }
  return ApiClient(baseUrl: serverUrl);
});

/// Provider for API client (synchronous, requires server URL)
final apiClientSyncProvider = Provider.family<ApiClient, String>((ref, baseUrl) {
  return ApiClient(baseUrl: baseUrl);
});
