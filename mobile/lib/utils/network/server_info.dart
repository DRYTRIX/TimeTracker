import 'package:dio/dio.dart';
import 'package:timetracker_mobile/utils/ssl/ssl_utils.dart';

/// Result of probing `GET /api/v1/info` on a candidate server base URL.
class ServerInfoResult {
  const ServerInfoResult({
    required this.ok,
    this.code,
    this.message,
    this.appVersion,
    this.setupRequired = false,
  });

  final bool ok;
  final String? code;
  final String? message;
  final String? appVersion;
  final bool setupRequired;
}

bool isTimeTrackerInfoPayload(dynamic data) {
  if (data is! Map) return false;
  final apiVersion = data['api_version'];
  final endpoints = data['endpoints'];
  return apiVersion == 'v1' && endpoints is Map;
}

/// Unauthenticated check: reachable TimeTracker JSON at GET /api/v1/info.
Future<ServerInfoResult> probeServerInfo(
  String baseUrl, {
  Set<String>? trustedInsecureHosts,
  Duration timeout = const Duration(seconds: 15),
}) async {
  var normalized = baseUrl.trim();
  if (normalized.isEmpty) {
    return const ServerInfoResult(
      ok: false,
      code: 'NO_URL',
      message: 'Please enter a server URL.',
    );
  }
  final lower = normalized.toLowerCase();
  if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
    normalized = 'https://$normalized';
  }
  while (normalized.endsWith('/')) {
    normalized = normalized.substring(0, normalized.length - 1);
  }

  Uri parsed;
  try {
    parsed = Uri.parse(normalized);
  } catch (_) {
    return const ServerInfoResult(
      ok: false,
      code: 'BAD_URL',
      message: 'Server URL is not valid.',
    );
  }
  if (parsed.scheme != 'http' && parsed.scheme != 'https') {
    return const ServerInfoResult(
      ok: false,
      code: 'BAD_URL',
      message: 'Server URL must start with http:// or https://.',
    );
  }

  final dio = Dio(BaseOptions(
    baseUrl: '$normalized/',
    connectTimeout: timeout,
    receiveTimeout: timeout,
    headers: {'Accept': 'application/json'},
    validateStatus: (_) => true,
  ));
  configureDioTrustedHosts(dio, trustedInsecureHosts ?? {});

  try {
    final response = await dio.get<Map<String, dynamic>>('/api/v1/info');
    final status = response.statusCode ?? 0;
    if (status != 200) {
      return ServerInfoResult(
        ok: false,
        code: 'HTTP_$status',
        message: 'Server returned HTTP $status. Check the URL and port.',
      );
    }
    final data = response.data;
    if (!isTimeTrackerInfoPayload(data)) {
      return const ServerInfoResult(
        ok: false,
        code: 'NOT_TIMETRACKER',
        message:
            'This address did not return a TimeTracker API response. Check the URL (base URL only) and port.',
      );
    }
    final setupRequired = data?['setup_required'] == true;
    if (setupRequired) {
      return const ServerInfoResult(
        ok: false,
        code: 'SETUP_REQUIRED',
        setupRequired: true,
        message:
            'TimeTracker is not fully set up yet. Open this server URL in a browser, complete initial setup, then try again.',
      );
    }
    final appVersion = data?['app_version']?.toString();
    return ServerInfoResult(ok: true, appVersion: appVersion);
  } on DioException catch (e) {
    return ServerInfoResult(
      ok: false,
      code: 'NETWORK',
      message: e.message ?? 'Could not reach the server.',
    );
  } catch (e) {
    return ServerInfoResult(
      ok: false,
      code: 'NETWORK',
      message: e.toString(),
    );
  }
}
