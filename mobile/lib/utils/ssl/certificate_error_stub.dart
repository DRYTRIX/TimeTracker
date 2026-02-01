import 'package:dio/dio.dart';

/// Stub: detect certificate errors by message only (e.g. on web where dart:io is unavailable).
bool isCertificateError(DioException e) {
  final msg = e.message?.toLowerCase() ?? '';
  final errStr = e.error?.toString().toLowerCase() ?? '';
  return msg.contains('certificate') ||
      msg.contains('handshake') ||
      msg.contains('certificate_verify_failed') ||
      msg.contains('ssl') ||
      errStr.contains('certificate') ||
      errStr.contains('handshake') ||
      errStr.contains('ssl');
}
