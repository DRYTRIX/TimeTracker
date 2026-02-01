import 'dart:io';

import 'package:dio/dio.dart';
import 'package:dio/io.dart';

/// Configures [dio] to trust HTTPS certificates for [trustedHosts] (e.g. self-signed).
/// Only has effect on platforms that use [IOHttpClientAdapter] (Android, iOS, macOS, etc.).
void configureDioTrustedHosts(Dio dio, Set<String> trustedHosts) {
  if (trustedHosts.isEmpty) return;
  final adapter = dio.httpClientAdapter;
  if (adapter is IOHttpClientAdapter) {
    adapter.createHttpClient = () {
      final client = HttpClient();
      client.badCertificateCallback = (_, host, __) => trustedHosts.contains(host);
      return client;
    };
  }
}
