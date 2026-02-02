import 'package:dio/dio.dart';

class ConnectionDiagnostics {
  final String title;
  final String summary;
  final List<String> checks;
  final String technicalReport;
  final String? host;
  final bool isCertificateIssue;

  const ConnectionDiagnostics({
    required this.title,
    required this.summary,
    required this.checks,
    required this.technicalReport,
    required this.host,
    required this.isCertificateIssue,
  });
}

ConnectionDiagnostics diagnoseDioFailure(
  DioException e, {
  required String attemptedBaseUrl,
  String? phase,
}) {
  final uri = e.requestOptions.uri;
  final host = uri.host.isNotEmpty ? uri.host : null;
  final status = e.response?.statusCode;
  final contentType = e.response?.headers.value('content-type');

  String title = 'Connection failed';
  String summary = 'Could not connect to the server. Check the server URL and your network.';
  final checks = <String>[
    'Verify the server URL (including https:// and port if not standard).',
    'Check that the server is reachable from this network (Wi‑Fi/VPN).',
  ];

  if (status != null) {
    title = 'Server responded with an error';
    summary = 'The server responded with HTTP $status.';
    checks.insert(0, 'Confirm you entered the base URL (e.g. https://your-domain), not a deep link.');
  } else if (e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.receiveTimeout ||
      e.type == DioExceptionType.sendTimeout) {
    title = 'Connection timed out';
    summary = 'The server did not respond in time.';
    checks.add('If the hostname has IPv6 (AAAA), ensure IPv6 works or remove AAAA.');
  } else if (e.error is FormatException) {
    title = 'Unexpected server response';
    summary =
        'The server returned data the app could not read (not JSON). This can happen behind captive portals or misrouted proxies.';
    checks.add('If you are on a guest Wi‑Fi, open a browser once to clear any captive portal.');
  }

  final report = StringBuffer()
    ..writeln('TimeTracker mobile connection diagnostics')
    ..writeln('Phase: ${phase ?? 'unknown'}')
    ..writeln('Attempted base URL: $attemptedBaseUrl')
    ..writeln('Request URL: $uri')
    ..writeln('Dio type: ${e.type}')
    ..writeln('HTTP status: ${status ?? '—'}')
    ..writeln('Content-Type: ${contentType ?? '—'}')
    ..writeln('Message: ${e.message ?? '—'}')
    ..writeln('Error: ${e.error ?? '—'}');

  return ConnectionDiagnostics(
    title: title,
    summary: summary,
    checks: checks,
    technicalReport: report.toString(),
    host: host,
    isCertificateIssue: false,
  );
}

