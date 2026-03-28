import 'dart:convert';

import 'package:opentelemetry/api.dart' as otel_api;
import 'package:opentelemetry/sdk.dart' as otel_sdk;
import 'package:package_info_plus/package_info_plus.dart';

bool _mobileOtelInitialized = false;

/// OTLP endpoint and token from `--dart-define=OTEL_EXPORTER_OTLP_*` (CI parity with main app).
/// Values are embedded in release binaries—avoid for untrusted distribution.
Future<void> initMobileOpenTelemetry() async {
  const endpoint = String.fromEnvironment('OTEL_EXPORTER_OTLP_ENDPOINT');
  const token = String.fromEnvironment('OTEL_EXPORTER_OTLP_TOKEN');
  if (endpoint.isEmpty || token.isEmpty) {
    return;
  }

  var base = endpoint.trim();
  if (base.endsWith('/')) {
    base = base.substring(0, base.length - 1);
  }
  if (base.endsWith('/v1/logs')) {
    base = base.substring(0, base.length - '/v1/logs'.length);
  } else {
    final idx = base.lastIndexOf('/v1/logs');
    if (idx != -1) {
      base = base.substring(0, idx);
    }
  }

  final traceUri = Uri.parse('$base/v1/traces');
  final authHeader = buildOtlpAuthHeader(token);
  final info = await PackageInfo.fromPlatform();
  final resource = otel_sdk.Resource([
    otel_api.Attribute.fromString('service.name', 'timetracker-mobile'),
    otel_api.Attribute.fromString('service.version', info.version),
  ]);

  final exporter = otel_sdk.CollectorExporter(
    traceUri,
    headers: {'Authorization': authHeader},
  );

  final provider = otel_sdk.TracerProviderBase(
    resource: resource,
    processors: [
      otel_sdk.BatchSpanProcessor(exporter),
    ],
  );

  otel_api.registerGlobalTracerProvider(provider);
  _mobileOtelInitialized = true;
}

/// Matches [app.telemetry.service._build_otlp_auth_header] (Basic / instance:token).
String buildOtlpAuthHeader(String token) {
  final value = token.trim();
  if (value.toLowerCase().startsWith('basic ')) {
    return value;
  }
  if (value.contains(':')) {
    final encoded = base64Encode(utf8.encode(value));
    return 'Basic $encoded';
  }
  return 'Basic $value';
}

/// No-op if OpenTelemetry was not initialized.
otel_api.Tracer? get mobileTracerOrNull {
  if (!_mobileOtelInitialized) return null;
  return otel_api.globalTracerProvider.getTracer('timetracker.mobile');
}

Future<T> runMobileSpan<T>(
  String name,
  Future<T> Function() body, {
  Map<String, String> attributes = const {},
}) async {
  final tracer = mobileTracerOrNull;
  if (tracer == null) {
    return body();
  }
  final span = tracer.startSpan(name);
  for (final e in attributes.entries) {
    span.setAttribute(otel_api.Attribute.fromString(e.key, e.value));
  }
  try {
    return await body();
  } catch (e, st) {
    span.setStatus(otel_api.StatusCode.error, e.toString());
    span.recordException(e, stackTrace: st);
    rethrow;
  } finally {
    span.end();
  }
}
