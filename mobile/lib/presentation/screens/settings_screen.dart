import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../../core/config/app_config.dart';
import '../../domain/usecases/sync_usecase.dart';
import '../providers/api_provider.dart';
import '../../utils/auth/auth_service.dart';
import '../../utils/network/server_info.dart';
import '../providers/theme_mode_provider.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'login_screen.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _isLoading = true;
  String? _serverUrl;
  int _syncInterval = 60;
  bool _autoSync = true;
  bool _hasToken = false;
  String _version = '—';
  String? _lastSyncError;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final serverUrl = await AppConfig.getServerUrl();
    final syncInterval = await AppConfig.getSyncInterval();
    final autoSync = await AppConfig.getAutoSync();
    final token = await AuthService.getToken();
    String version = '—';
    try {
      final info = await PackageInfo.fromPlatform();
      version = '${info.version}+${info.buildNumber}';
    } catch (_) {}

    if (mounted) {
      setState(() {
        _serverUrl = serverUrl;
        _syncInterval = syncInterval;
        _autoSync = autoSync;
        _hasToken = token != null && token.isNotEmpty;
        _version = version;
        _lastSyncError = SyncUseCase.lastError;
        _isLoading = false;
      });
    }
  }

  Future<void> _runManualSync() async {
    setState(() => _syncing = true);
    await SyncUseCase.shared.sync();
    if (mounted) {
      setState(() {
        _syncing = false;
        _lastSyncError = SyncUseCase.lastError;
      });
    }
  }

  void _showThemePicker() {
    final themeMode = ref.read(themeModeProvider);
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Theme'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _ThemeOption(
              label: 'System',
              value: 'system',
              current: themeMode,
              onTap: () => _selectTheme('system'),
            ),
            _ThemeOption(
              label: 'Light',
              value: 'light',
              current: themeMode,
              onTap: () => _selectTheme('light'),
            ),
            _ThemeOption(
              label: 'Dark',
              value: 'dark',
              current: themeMode,
              onTap: () => _selectTheme('dark'),
            ),
          ],
        ),
      ),
    );
  }

  void _selectTheme(String value) {
    ref.read(themeModeProvider.notifier).setMode(value);
  }

  /// Match login flow: optional scheme, trim trailing slashes for stored base URL.
  String _normalizeServerUrlForSettings(String input) {
    var t = input.trim();
    if (t.isEmpty) return t;
    final lower = t.toLowerCase();
    if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
      t = 'https://$t';
    }
    while (t.endsWith('/')) {
      t = t.substring(0, t.length - 1);
    }
    return t;
  }

  Future<void> _showEditServerUrlDialog() async {
    final controller = TextEditingController(text: _serverUrl ?? '');
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server URL'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.url,
          textInputAction: TextInputAction.done,
          decoration: const InputDecoration(
            labelText: 'Server URL',
            hintText: 'https://example.com',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == null) return;
    if (result.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Server URL cannot be empty')),
      );
      return;
    }

    final normalized = _normalizeServerUrlForSettings(result);
    final trustedHosts = await AppConfig.getTrustedInsecureHosts();
    final infoResult = await probeServerInfo(
      normalized,
      trustedInsecureHosts: trustedHosts,
    );
    if (!infoResult.ok) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(infoResult.message ?? 'Invalid TimeTracker server')),
      );
      return;
    }

    final token = await AuthService.getToken();
    if (token != null && token.isNotEmpty) {
      final probe = ApiClient(baseUrl: normalized, trustedInsecureHosts: trustedHosts);
      await probe.setAuthToken(token);
      final validation = await probe.validateTokenRaw();
      final status = validation.statusCode ?? 0;
      if (status != 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              status == 401
                  ? 'This server did not accept your saved token (401). Sign out, then sign in again on the new server.'
                  : 'Could not verify your token on this server (HTTP $status). Server URL was not changed.',
            ),
          ),
        );
        return;
      }
    }

    await AppConfig.setServerUrl(normalized);
    ref.invalidate(apiClientProvider);
    if (mounted) {
      setState(() => _serverUrl = normalized);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            infoResult.appVersion != null
                ? 'Server URL updated (app ${infoResult.appVersion})'
                : 'Server URL updated',
          ),
        ),
      );
    }
  }

  Future<void> _showEditApiTokenDialog() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('API Token'),
        content: TextField(
          controller: controller,
          obscureText: true,
          textInputAction: TextInputAction.done,
          decoration: const InputDecoration(
            labelText: 'API Token',
            hintText: 'Paste token here',
            helperText: 'Leave blank to clear',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == null) return;
    if (result.isEmpty) {
      await AuthService.deleteToken();
      ref.invalidate(apiClientProvider);
      if (mounted) {
        setState(() => _hasToken = false);
      }
      return;
    }

    await AuthService.storeToken(result);
    ref.invalidate(apiClientProvider);
    if (mounted) {
      setState(() => _hasToken = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('API token updated')),
      );
    }
  }

  Future<void> _showSyncIntervalDialog() async {
    final controller = TextEditingController(text: _syncInterval.toString());
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sync Interval'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          textInputAction: TextInputAction.done,
          decoration: const InputDecoration(
            labelText: 'Seconds',
            helperText: 'How often to sync when enabled',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == null) return;
    final parsed = int.tryParse(result);
    if (parsed == null || parsed <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid number of seconds')),
      );
      return;
    }

    await AppConfig.setSyncInterval(parsed);
    if (mounted) {
      setState(() => _syncInterval = parsed);
    }
  }

  void _showAboutDialog() {
    showAboutDialog(
      context: context,
      applicationName: 'TimeTracker',
      applicationVersion: _version,
      applicationIcon: const Icon(Icons.timer),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);
    final colorScheme = Theme.of(context).colorScheme;

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Settings')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          _sectionHeader('Account'),
          ListTile(
            leading: const Icon(Icons.dns),
            title: const Text('Server URL'),
            subtitle: Text(_serverUrl?.isNotEmpty == true ? _serverUrl! : 'Not configured'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _showEditServerUrlDialog,
          ),
          ListTile(
            leading: const Icon(Icons.key),
            title: const Text('API Token'),
            subtitle: Text(_hasToken ? 'Configured' : 'Not set'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _showEditApiTokenDialog,
          ),
          _sectionHeader('Sync'),
          SwitchListTile(
            secondary: const Icon(Icons.sync),
            title: const Text('Auto Sync'),
            subtitle: const Text('Automatically sync data when online'),
            value: _autoSync,
            onChanged: (value) async {
              await AppConfig.setAutoSync(value);
              if (value) {
                await SyncUseCase.shared.startPeriodicSync();
              } else {
                SyncUseCase.shared.stopPeriodicSync();
              }
              if (mounted) setState(() => _autoSync = value);
            },
          ),
          ListTile(
            leading: const Icon(Icons.schedule),
            title: const Text('Sync Interval'),
            subtitle: Text('$_syncInterval seconds'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _showSyncIntervalDialog,
          ),
          ListTile(
            leading: const Icon(Icons.sync_problem_outlined),
            title: const Text('Last sync error'),
            subtitle: Text(
              _lastSyncError == null || _lastSyncError!.isEmpty ? 'None' : _lastSyncError!,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          ListTile(
            leading: _syncing
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.cloud_upload_outlined),
            title: const Text('Sync now'),
            subtitle: const Text('Push queued changes and refresh from server'),
            onTap: _syncing ? null : _runManualSync,
          ),
          _sectionHeader('Appearance'),
          ListTile(
            leading: const Icon(Icons.palette),
            title: const Text('Theme'),
            subtitle: Text(themeMode == 'system' ? 'System' : themeMode == 'dark' ? 'Dark' : 'Light'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _showThemePicker,
          ),
          _sectionHeader('About'),
          ListTile(
            leading: const Icon(Icons.info),
            title: const Text('About'),
            subtitle: Text('Version $_version'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _showAboutDialog,
          ),
          ListTile(
            leading: Icon(Icons.logout, color: colorScheme.error),
            title: Text('Logout', style: TextStyle(color: colorScheme.error, fontWeight: FontWeight.w500)),
            onTap: () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Logout'),
                  content: const Text('Are you sure you want to logout?'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancel'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: Text('Logout', style: TextStyle(color: colorScheme.error)),
                    ),
                  ],
                ),
              );
              if (confirm == true && mounted) {
                SyncUseCase.shared.stopPeriodicSync();
                await AuthService.deleteToken();
                await AppConfig.clear();
                if (mounted) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                    (route) => false,
                  );
                }
              }
            },
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
      child: Text(
        title,
        style: theme.textTheme.titleSmall?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _ThemeOption extends StatelessWidget {
  final String label;
  final String value;
  final String current;
  final VoidCallback onTap;

  const _ThemeOption({
    required this.label,
    required this.value,
    required this.current,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = current == value;
    return ListTile(
      title: Text(label),
      trailing: isSelected ? Icon(Icons.check, color: Theme.of(context).colorScheme.primary) : null,
      onTap: () {
        onTap();
        Navigator.of(context).pop();
      },
    );
  }
}
