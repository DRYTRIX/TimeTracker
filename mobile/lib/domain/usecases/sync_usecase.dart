import 'dart:async';
import '../../core/config/app_config.dart';
import '../../data/api/api_client.dart';
import '../../data/local/database/sync_service.dart';
import '../../utils/auth/auth_service.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

class SyncUseCase {
  final Connectivity _connectivity = Connectivity();
  Timer? _syncTimer;

  SyncUseCase();

  // Start periodic sync if auto-sync is enabled
  Future<void> startPeriodicSync() async {
    final autoSync = await AppConfig.getAutoSync();
    if (!autoSync) return;

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
    try {
      final serverUrl = await AppConfig.getServerUrl();
      final token = await AuthService.getToken();

      if (serverUrl == null || serverUrl.isEmpty || token == null || token.isEmpty) {
        return false;
      }

      final apiClient = ApiClient(baseUrl: serverUrl);
      await apiClient.setAuthToken(token);

      final syncService = SyncService(apiClient);

      await syncService.processQueue();
      await syncService.syncFromServer();

      return true;
    } catch (_) {
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
