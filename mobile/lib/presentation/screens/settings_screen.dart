import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/config/app_config.dart';
import '../../core/constants/app_constants.dart';
import '../../utils/auth/auth_service.dart';
import '../screens/login_screen.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    final serverUrl = AppConfig.serverUrl ?? 'Not configured';
    final syncInterval = AppConfig.syncInterval;
    final autoSync = AppConfig.autoSync;
    final themeMode = AppConfig.themeMode;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // Server Configuration
          ListTile(
            leading: const Icon(Icons.dns),
            title: const Text('Server URL'),
            subtitle: Text(serverUrl),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Edit server URL
            },
          ),
          const Divider(),
          
          // API Token
          ListTile(
            leading: const Icon(Icons.key),
            title: const Text('API Token'),
            subtitle: const Text('••••••••'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Edit API token
            },
          ),
          const Divider(),
          
          // Sync Settings
          SwitchListTile(
            secondary: const Icon(Icons.sync),
            title: const Text('Auto Sync'),
            subtitle: const Text('Automatically sync data when online'),
            value: autoSync,
            onChanged: (value) async {
              await AppConfig.setAutoSync(value);
              setState(() {});
            },
          ),
          ListTile(
            leading: const Icon(Icons.schedule),
            title: const Text('Sync Interval'),
            subtitle: Text('$syncInterval seconds'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Edit sync interval
            },
          ),
          const Divider(),
          
          // Theme
          ListTile(
            leading: const Icon(Icons.palette),
            title: const Text('Theme'),
            subtitle: Text(themeMode == 'system' ? 'System' : themeMode == 'dark' ? 'Dark' : 'Light'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Select theme
            },
          ),
          const Divider(),
          
          // About
          ListTile(
            leading: const Icon(Icons.info),
            title: const Text('About'),
            subtitle: const Text('Version 1.0.0'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // TODO: Show about dialog
            },
          ),
          const Divider(),
          
          // Logout
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Logout', style: TextStyle(color: Colors.red)),
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
                      child: const Text('Logout', style: TextStyle(color: Colors.red)),
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
}
