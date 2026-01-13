import 'dart:async';
import '../../core/config/app_config.dart';
import '../../data/api/api_client.dart';
import '../../data/local/database/sync_service.dart';
import '../../utils/auth/auth_service.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

class SyncUseCase {
  final SyncService _syncService;
  final Connectivity _connectivity = Connectivity();
  Timer? _syncTimer;

  SyncUseCase(this._syncService);

  // Start periodic sync if auto-sync is enabled
  void startPeriodicSync() {
    if (!AppConfig.autoSync) return;

    _syncTimer?.cancel();
    final interval = Duration(seconds: AppConfig.syncInterval);
    
    _syncTimer = Timer.periodic(interval, (timer) async {
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
      // Ensure we have API client
      final serverUrl = AppConfig.serverUrl;
      final token = await AuthService.getToken();

      if (serverUrl == null || token == null) {
        return false;
      }

      final apiClient = ApiClient(baseUrl: serverUrl);
      await apiClient.setAuthToken(token);

      final syncService = SyncService(apiClient);

      // Process sync queue (offline operations)
      await syncService.processQueue();

      // Sync from server (get latest data)
      await syncService.syncFromServer();

      return true;
    } catch (e) {
      print('Sync error: $e');
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
