import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../../core/config/app_config.dart';
import '../../utils/auth/auth_service.dart';
import '../providers/theme_mode_provider.dart';
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
  String _version = '—';

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final serverUrl = await AppConfig.getServerUrl();
    final syncInterval = await AppConfig.getSyncInterval();
    final autoSync = await AppConfig.getAutoSync();
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
        _version = version;
        _isLoading = false;
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
            onTap: () {
              // TODO: Edit server URL
            },
          ),
          ListTile(
            leading: const Icon(Icons.key),
            title: const Text('API Token'),
            subtitle: const Text('••••••••'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Edit API token
            },
          ),
          _sectionHeader('Sync'),
          SwitchListTile(
            secondary: const Icon(Icons.sync),
            title: const Text('Auto Sync'),
            subtitle: const Text('Automatically sync data when online'),
            value: _autoSync,
            onChanged: (value) async {
              await AppConfig.setAutoSync(value);
              if (mounted) setState(() => _autoSync = value);
            },
          ),
          ListTile(
            leading: const Icon(Icons.schedule),
            title: const Text('Sync Interval'),
            subtitle: Text('$_syncInterval seconds'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Edit sync interval
            },
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
            onTap: () {
              // TODO: Show about dialog
            },
          ),
          _sectionHeader('Account'),
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
