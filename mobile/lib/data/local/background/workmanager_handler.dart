import 'package:workmanager/workmanager.dart';
import '../../api/api_client.dart';
import '../../models/time_entry.dart';
import '../../../core/config/app_config.dart';
import '../../../utils/auth/auth_service.dart';
import 'dart:convert';

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    try {
      switch (task) {
        case 'timerStatusUpdate':
          return await _updateTimerStatus();
        case 'syncData':
          return await _syncData();
        default:
          return Future.value(false);
      }
    } catch (e) {
      return Future.value(false);
    }
  });
}

Future<bool> _updateTimerStatus() async {
  try {
    final serverUrl = AppConfig.serverUrl;
    final token = await AuthService.getToken();

    if (serverUrl == null || token == null) {
      return false;
    }

    final apiClient = ApiClient(baseUrl: serverUrl);
    await apiClient.setAuthToken(token);

    final response = await apiClient.getTimerStatus();
    if (response.statusCode == 200 && response.data['active'] == true) {
      // Timer is still running, could update local notification
      return true;
    }
    return false;
  } catch (e) {
    return false;
  }
}

Future<bool> _syncData() async {
  try {
    final serverUrl = AppConfig.serverUrl;
    final token = await AuthService.getToken();

    if (serverUrl == null || token == null) {
      return false;
    }

    final apiClient = ApiClient(baseUrl: serverUrl);
    await apiClient.setAuthToken(token);

    // Sync time entries
    final now = DateTime.now();
    final startDate = now.subtract(const Duration(days: 7));
    await apiClient.getTimeEntries(
      startDate: startDate.toIso8601String().split('T')[0],
      endDate: now.toIso8601String().split('T')[0],
    );

    return true;
  } catch (e) {
    return false;
  }
}

class WorkManagerService {
  static Future<void> initialize() async {
    await Workmanager().initialize(callbackDispatcher, isInDebugMode: false);
  }

  static Future<void> startTimerStatusUpdates() async {
    await Workmanager().registerPeriodicTask(
      'timerStatusUpdate',
      'timerStatusUpdate',
      frequency: const Duration(minutes: 5),
      constraints: Constraints(
        networkType: NetworkType.connected,
      ),
    );
  }

  static Future<void> startDataSync() async {
    await Workmanager().registerPeriodicTask(
      'syncData',
      'syncData',
      frequency: const Duration(minutes: 15),
      constraints: Constraints(
        networkType: NetworkType.connected,
      ),
    );
  }

  static Future<void> cancelAll() async {
    await Workmanager().cancelAll();
  }
}
