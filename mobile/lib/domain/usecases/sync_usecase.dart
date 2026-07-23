import 'dart:async';
import 'dart:developer' as developer;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:timetracker_mobile/core/config/app_config.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/storage/sync_service.dart';
import 'package:timetracker_mobile/utils/auth/auth_service.dart';

class SyncUseCase {
  final Connectivity _connectivity = Connectivity();
  Timer? _syncTimer;

  /// Shared instance so login/home can start periodic sync once.
  static final SyncUseCase shared = SyncUseCase();

  /// Last sync error message for UI or support (cleared on successful sync start).
  static String? lastError;

  SyncUseCase();

  // Start periodic sync if auto-sync is enabled
  Future<void> startPeriodicSync() async {
    final autoSync = await AppConfig.getAutoSync();
    if (!autoSync) {
      stopPeriodicSync();
      return;
    }

    _syncTimer?.cancel();
    final intervalSeconds = await AppConfig.getSyncInterval();
    _syncTimer = Timer.periodic(Duration(seconds: intervalSeconds), (timer) async {
      if (await _isOnline()) {
        await sync();
      }
    });
  }

  // Stop periodic sync
  void stopPeriodicSync() {
    _syncTimer?.cancel();
    _syncTimer = null;
  }

  // Check if device is online
  Future<bool> _isOnline() async {
    final connectivityResult = await _connectivity.checkConnectivity();
    return connectivityResult != ConnectivityResult.none;
  }

  // Full sync: process queue and sync from server
  Future<bool> sync() async {
    lastError = null;
    try {
      final serverUrl = await AppConfig.getServerUrl();
      final token = await AuthService.getToken();

      if (serverUrl == null || serverUrl.isEmpty || token == null || token.isEmpty) {
        lastError = 'Missing server URL or auth token';
        developer.log(
          'Sync skipped: $lastError',
          name: 'SyncUseCase',
        );
        return false;
      }

      final trustedHosts = await AppConfig.getTrustedInsecureHosts();
      final apiClient = ApiClient(baseUrl: serverUrl, trustedInsecureHosts: trustedHosts);
      await apiClient.setAuthToken(token);

      final syncService = SyncService(apiClient);
      await syncService.syncAll();

      return true;
    } catch (e, st) {
      lastError = e.toString();
      developer.log(
        'Sync failed: $e',
        name: 'SyncUseCase',
        error: e,
        stackTrace: st,
      );
      return false;
    }
  }

  // Sync when connection is restored
  Future<void> onConnectionRestored() async {
    if (await _isOnline()) {
      await sync();
    }
  }
}
