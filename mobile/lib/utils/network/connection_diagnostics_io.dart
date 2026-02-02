import 'dart:io';

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

bool _looksLikeHttpsToHttpHandshake(Object? err) {
  final s = err.toString().toLowerCase();
  return s.contains('wrong version number') ||
      s.contains('unknown protocol') ||
      s.contains('plaintext connection') ||
      s.contains('tlsv1 alert protocol version');
}

bool _looksLikeHostnameMismatch(Object? err) {
  final s = err.toString().toLowerCase();
  return s.contains('hostname') && (s.contains('not') || s.contains('mismatch'));
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

  bool isCertIssue = false;

  // --- DNS / socket level ---
  if (e.error is SocketException) {
    final se = e.error as SocketException;
    final msg = se.message.toLowerCase();
    final os = se.osError;
    final osMsg = (os?.message ?? '').toLowerCase();

    if (msg.contains('failed host lookup') || osMsg.contains('name or service not known')) {
      title = 'DNS lookup failed';
      summary =
          'The hostname "${host ?? '(unknown)'}" could not be resolved. The device cannot find an IP address for this DNS name.';
      checks
        ..clear()
        ..addAll([
          'Check spelling of the hostname.',
          'If this is an internal DNS name, connect the phone to the correct Wi‑Fi and/or VPN.',
          'If your DNS returns an IPv6 (AAAA) record, ensure IPv6 works end-to-end or remove AAAA.',
          'Try the server’s IP address to confirm whether this is DNS-specific.',
        ]);
    } else if (msg.contains('connection refused') || osMsg.contains('refused')) {
      title = 'Connection refused';
      summary =
          'The server is reachable, but nothing is listening on that port (or a firewall actively refused it).';
      checks
        ..clear()
        ..addAll([
          'Confirm the port is correct (common: 443 for HTTPS, 80 for HTTP).',
          'If you run behind NGINX, ensure the HTTPS listener is enabled.',
          'Check firewall rules and port-forwarding (if hosted behind a router).',
        ]);
    } else if (msg.contains('network is unreachable') || osMsg.contains('unreachable')) {
      title = 'Network unreachable';
      summary = 'The phone cannot reach the network required to connect to the server.';
      checks
        ..clear()
        ..addAll([
          'Check Wi‑Fi / mobile data connectivity.',
          'If the server is internal, connect to the correct Wi‑Fi and/or VPN.',
          'Disable VPN/proxy temporarily to test.',
        ]);
    } else {
      title = 'Network error';
      summary = 'A low-level network error occurred while connecting.';
      checks.add('If this happens only on one network, check proxies, VPNs, or restrictive firewalls.');
    }
  }

  // --- Timeouts ---
  if (e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.receiveTimeout ||
      e.type == DioExceptionType.sendTimeout) {
    title = 'Connection timed out';
    summary = 'The server did not respond in time.';
    checks
      ..clear()
      ..addAll([
        'Check the hostname and port.',
        'Ensure the server is reachable from this network (Wi‑Fi/VPN).',
        'If your DNS returns IPv6 (AAAA), ensure IPv6 works end-to-end or remove AAAA.',
        'If the server is behind a reverse proxy, verify it forwards to the app.',
      ]);
  }

  // --- TLS / certificate ---
  if (e.error is HandshakeException || e.error is TlsException || _looksLikeHostnameMismatch(e.error)) {
    isCertIssue = true;
    title = 'TLS / certificate problem';

    if (_looksLikeHttpsToHttpHandshake(e.error)) {
      summary =
          'The app tried HTTPS, but the server appears to be speaking HTTP on that port (TLS handshake failed).';
      checks
        ..clear()
        ..addAll([
          'If your server is HTTP-only, enter the URL starting with http://',
          'If your server should be HTTPS, ensure TLS is enabled on that port (often 443).',
          'If you use a reverse proxy (NGINX), verify HTTPS is configured correctly.',
        ]);
    } else {
      summary =
          'Android could not verify the server certificate for "${host ?? '(unknown)'}". This can happen with self-signed certs, expired certs, missing intermediate chain, or hostname mismatch.';
      checks
        ..clear()
        ..addAll([
          'Use a publicly trusted certificate for this exact hostname (recommended: Let’s Encrypt).',
          'Ensure the certificate includes the hostname in SAN (Subject Alternative Name).',
          'Ensure the full certificate chain (intermediate certs) is served.',
          'Check the phone’s date/time is correct.',
          'If a corporate proxy/VPN intercepts TLS, try disabling it to test.',
        ]);
    }
  }

  // --- HTTP response codes (server reachable) ---
  if (status != null) {
    title = 'Server responded with an error';
    summary = 'The server responded with HTTP $status.';
    checks.insert(0, 'Confirm you entered the base URL (e.g. https://your-domain), not a deep link.');
    if (status == 301 || status == 302 || status == 307 || status == 308) {
      checks.add('If the server redirects from HTTP to HTTPS, enter the final HTTPS URL directly.');
    }
    if (status == 404) {
      checks.add('Ensure the reverse proxy routes /api/v1/... to the TimeTracker app.');
    }
    if (status == 502 || status == 503 || status == 504) {
      checks.add('Reverse proxy is up but backend is down/misconfigured (NGINX ↔ app).');
    }
  }

  // --- Non-JSON / captive portal / proxy ---
  if (e.error is FormatException) {
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
    ..writeln('Error type: ${e.error?.runtimeType ?? '—'}')
    ..writeln('Error: ${e.error ?? '—'}');

  return ConnectionDiagnostics(
    title: title,
    summary: summary,
    checks: checks,
    technicalReport: report.toString(),
    host: host,
    isCertificateIssue: isCertIssue,
  );
}

