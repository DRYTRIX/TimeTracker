import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:timetracker_mobile/core/config/app_config.dart';
import 'package:timetracker_mobile/core/constants/app_constants.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/utils/network/connection_diagnostics.dart';
import 'package:timetracker_mobile/utils/ssl/certificate_error.dart';
import 'package:timetracker_mobile/utils/ssl/ssl_utils.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverUrlController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _storage = const FlutterSecureStorage();
  bool _isLoading = false;
  String? _error;
  ConnectionDiagnostics? _connectionDiag;

  @override
  void initState() {
    super.initState();
    _loadSavedCredentials();
  }

  Future<void> _loadSavedCredentials() async {
    final serverUrl = await AppConfig.getServerUrl();
    if (serverUrl != null) {
      _serverUrlController.text = serverUrl;
    }
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// True if host is likely local/emulator (self-signed cert is common).
  static bool _isLikelyLocalOrEmulator(String host) {
    final h = host.toLowerCase();
    if (h == '10.0.2.2' || h == 'localhost' || h == '127.0.0.1') return true;
    if (h.startsWith('192.168.') || h.startsWith('10.') || h.startsWith('172.')) return true;
    return false;
  }

  /// Normalize server URL: add https:// if no scheme, then ensure valid base.
  static String _normalizeServerUrl(String input) {
    final trimmed = input.trim();
    if (trimmed.isEmpty) return trimmed;
    if (trimmed.toLowerCase().startsWith('https://') ||
        trimmed.toLowerCase().startsWith('http://')) {
      return trimmed;
    }
    return 'https://$trimmed';
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _connectionDiag = null;
    });

    try {
      final rawUrl = _serverUrlController.text.trim();
      final serverUrl = _normalizeServerUrl(rawUrl);
      final username = _usernameController.text.trim();
      final password = _passwordController.text;

      final baseUrl = serverUrl.endsWith('/') ? serverUrl : '$serverUrl/';
      final trustedHosts = await AppConfig.getTrustedInsecureHosts();
      final dio = Dio(BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {'Content-Type': 'application/json'},
      ));
      configureDioTrustedHosts(dio, trustedHosts);

      final response = await dio.post<Map<String, dynamic>>(
        '/api/v1/auth/login',
        data: {'username': username, 'password': password},
      );

      final token = response.data?['token'] as String?;
      if (token == null || token.isEmpty) {
        setState(() {
          _error = 'Invalid username or password';
          _isLoading = false;
        });
        return;
      }

      final apiClient = ApiClient(baseUrl: serverUrl, trustedInsecureHosts: trustedHosts);
      await apiClient.setAuthToken(token);
      final validationResponse = await apiClient.validateTokenRaw();
      final status = validationResponse.statusCode;
      if (status != 200) {
        setState(() {
          if (status == 401) {
            _error =
                'Login succeeded, but the server rejected the session (401 Unauthorized). Check that the Server URL points to the correct TimeTracker instance.';
          } else {
            _error =
                'Login succeeded, but the server returned HTTP ${status ?? '—'} while validating the connection.';
          }
          _isLoading = false;
        });
        return;
      }

      // Only persist configuration after we know the connection works.
      await AppConfig.setServerUrl(serverUrl);
      await _storage.write(key: 'api_token', value: token);

      if (mounted) {
        Navigator.of(context).pushReplacementNamed(AppConstants.routeHome);
      }
    } on DioException catch (e) {
      final host = e.requestOptions.uri.host;
      final isConnectionFailure = e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.unknown;
      final isCertError = isCertificateError(e);
      final phase = e.requestOptions.path.contains('/api/v1/auth/login')
          ? 'login'
          : (e.requestOptions.path.contains('/api/v1/timer/status') ? 'token validation' : 'request');
      final diag = diagnoseDioFailure(
        e,
        attemptedBaseUrl: _normalizeServerUrl(_serverUrlController.text.trim()),
        phase: phase,
      );
      final showTrustOption = (diag.host?.isNotEmpty == true) &&
          (diag.isCertificateIssue || isCertError || (isConnectionFailure && _isLikelyLocalOrEmulator(host)));

      if (showTrustOption && mounted) {
        final trust = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (context) => AlertDialog(
            title: Text(diag.isCertificateIssue || isCertError ? 'Certificate not trusted' : 'Connection failed'),
            content: Text(
              (diag.isCertificateIssue || isCertError)
                  ? 'Android could not verify the TLS certificate for "$host". '
                    'If you trust this server, you can allow it for this host and retry.\n\n'
                    'Recommended: Use a valid certificate (e.g. Let’s Encrypt) for production.'
                  : 'Cannot reach "$host".\n\n'
                    'If the server uses a self-signed certificate (common on local IPs), tap "Trust and retry". '
                    'Otherwise check the URL and port (e.g. https://your-server.com or https://10.0.2.2:8443).',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text((diag.isCertificateIssue || isCertError) ? 'Yes, trust' : 'Trust and retry'),
              ),
            ],
          ),
        );
        if (trust == true && mounted) {
          await AppConfig.addTrustedInsecureHost(host);
          await _handleLogin();
          return;
        }
      } else if (isCertError && mounted && host.isEmpty) {
        setState(() {
          _error = 'Certificate error. Check the server URL and try again.';
          _isLoading = false;
        });
        return;
      }

      final statusCode = e.response?.statusCode;
      final message = e.response?.data is Map ? (e.response!.data as Map)['error'] as String? : null;
      final errMsg = (statusCode == 401)
          ? (message ?? 'Invalid username or password')
          : (message ?? diag.summary);

      if (mounted) {
        setState(() {
          _error = errMsg;
          _connectionDiag = diag;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Connection failed. Check the URL and your network, then try again.';
          _connectionDiag = null;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _showDiagnostics(ConnectionDiagnostics diag) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) {
        final theme = Theme.of(context);
        final maxHeight = MediaQuery.of(context).size.height * 0.9;
        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: maxHeight),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
            child: Column(
              mainAxisSize: MainAxisSize.max,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(diag.title, style: theme.textTheme.titleLarge),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                      tooltip: 'Close',
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(diag.summary),
                if (diag.checks.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text('What to check', style: theme.textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ...diag.checks.map(
                    (c) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('• '),
                          Expanded(child: Text(c)),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                Text('Technical details', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SingleChildScrollView(
                      child: SelectableText(
                        diag.technicalReport,
                        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: diag.technicalReport));
                    if (!context.mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Diagnostics copied to clipboard')),
                    );
                  },
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy diagnostics'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    width: 88,
                    height: 88,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primary,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.4),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Image.asset(
                        'assets/icon/app_icon.png',
                        fit: BoxFit.contain,
                        semanticLabel: 'TimeTracker logo',
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'TimeTracker',
                    style: Theme.of(context).textTheme.headlineLarge,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Connect to your server',
                    style: Theme.of(context).textTheme.bodyLarge,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  TextFormField(
                    controller: _serverUrlController,
                    decoration: const InputDecoration(
                      labelText: 'Server URL',
                      hintText: 'your-server.com or https://your-server.com',
                      prefixIcon: Icon(Icons.link),
                      helperText: 'Self-signed certificates may require Trust.',
                    ),
                    keyboardType: TextInputType.url,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter server URL';
                      }
                      final trimmed = value.trim();
                      if (trimmed.contains('://')) {
                        final uri = Uri.tryParse(trimmed);
                        if (uri == null ||
                            !uri.hasScheme ||
                            uri.host.isEmpty ||
                            (!uri.scheme.toLowerCase().startsWith('http'))) {
                          return 'Enter a valid URL (e.g. https://your-server.com)';
                        }
                      } else {
                        final withScheme = Uri.tryParse('https://$trimmed');
                        if (withScheme == null || withScheme.host.isEmpty) {
                          return 'Enter a valid server address (e.g. your-server.com or https://...)';
                        }
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _usernameController,
                    decoration: const InputDecoration(
                      labelText: 'Username',
                      hintText: 'Your web login username',
                      prefixIcon: Icon(Icons.person),
                    ),
                    textCapitalization: TextCapitalization.none,
                    autocorrect: false,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter username';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _passwordController,
                    decoration: const InputDecoration(
                      labelText: 'Password',
                      hintText: 'Your web login password',
                      prefixIcon: Icon(Icons.lock),
                    ),
                    obscureText: true,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter password';
                      }
                      return null;
                    },
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Theme.of(context).colorScheme.error),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            _error!,
                            style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
                          ),
                          if (_connectionDiag != null) ...[
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              alignment: WrapAlignment.end,
                              children: [
                                TextButton.icon(
                                  onPressed: () => _showDiagnostics(_connectionDiag!),
                                  icon: const Icon(Icons.info_outline),
                                  label: const Text('Details'),
                                ),
                                TextButton.icon(
                                  onPressed: () async {
                                    final diag = _connectionDiag!;
                                    await Clipboard.setData(ClipboardData(text: diag.technicalReport));
                                    if (!mounted) return;
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Diagnostics copied to clipboard')),
                                    );
                                  },
                                  icon: const Icon(Icons.copy),
                                  label: const Text('Copy'),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _handleLogin,
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Login'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
