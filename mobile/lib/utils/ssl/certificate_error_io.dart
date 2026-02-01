import 'dart:io';

import 'package:dio/dio.dart';

/// Detects SSL/certificate errors (native platforms with dart:io).
bool isCertificateError(DioException e) {
  if (e.type == DioExceptionType.connectionError && e.error != null) {
    final err = e.error!;
    if (err is HandshakeException || err is TlsException) return true;
    final errStr = err.toString().toLowerCase();
    if (errStr.contains('certificate') ||
        errStr.contains('handshake') ||
        errStr.contains('certificate_verify_failed') ||
        errStr.contains('ssl')) {
      return true;
    }
  }
  final msg = e.message?.toLowerCase() ?? '';
  if (msg.contains('certificate') ||
      msg.contains('handshake') ||
      msg.contains('certificate_verify_failed') ||
      msg.contains('ssl')) {
    return true;
  }
  return false;
}
