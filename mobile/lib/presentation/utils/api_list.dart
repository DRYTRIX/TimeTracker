import 'package:dio/dio.dart';

/// Extract a list of maps from a typical API envelope.
List<Map<String, dynamic>> extractList(
  Map<String, dynamic> data,
  List<String> keys,
) {
  for (final key in keys) {
    final raw = data[key];
    if (raw is List) {
      return raw
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
  }
  return const [];
}

bool isModuleDisabled(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      final err = (data['error'] ?? data['message'] ?? '').toString().toLowerCase();
      if (err.contains('module_disabled') || err.contains('module disabled')) {
        return true;
      }
    }
    final msg = error.message?.toLowerCase() ?? '';
    if (msg.contains('module_disabled')) return true;
  }
  return error.toString().toLowerCase().contains('module_disabled');
}

String moduleDisabledMessage([String feature = 'This module']) {
  return '$feature is not enabled on this server.';
}
