import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import 'belgium_report_screen.dart';
import 'calendar_screen.dart';
import 'clients_screen.dart';
import 'crm_hub_screen.dart';
import 'issues_screen.dart';
import 'kanban_screen.dart';
import 'mileage_screen.dart';
import 'per_diem_screen.dart';

class MoreHubScreen extends ConsumerStatefulWidget {
  const MoreHubScreen({super.key});

  @override
  ConsumerState<MoreHubScreen> createState() => _MoreHubScreenState();
}

class _MoreHubScreenState extends ConsumerState<MoreHubScreen> {
  Set<String>? _enabledModules;
  bool _loadingModules = true;

  @override
  void initState() {
    super.initState();
    _loadModules();
  }

  Future<void> _loadModules() async {
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) {
        setState(() => _loadingModules = false);
        return;
      }
      List<dynamic> modules = const [];
      try {
        final me = await api.getUsersMe();
        modules = (me['enabled_modules'] as List?) ?? const [];
      } catch (_) {
        final info = await api.getInfo();
        modules = (info['enabled_modules'] as List?) ?? const [];
      }
      if (!mounted) return;
      setState(() {
        _enabledModules = modules.map((e) => e.toString()).toSet();
        _loadingModules = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _enabledModules = null; // unknown → show all
        _loadingModules = false;
      });
    }
  }

  bool _isEnabled(String? moduleId) {
    if (moduleId == null) return true;
    final mods = _enabledModules;
    if (mods == null) return true;
    return mods.contains(moduleId);
  }

  void _open(BuildContext context, Widget screen) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) {
    final items = <_MoreItem>[
      const _MoreItem('Clients', Icons.people_outline, ClientsScreen(), null),
      const _MoreItem('Calendar', Icons.calendar_month_outlined, CalendarScreen(), 'calendar'),
      const _MoreItem('Kanban', Icons.view_kanban_outlined, KanbanScreen(), 'kanban'),
      const _MoreItem('CRM', Icons.handshake_outlined, CrmHubScreen(), 'deals'),
      const _MoreItem('Mileage', Icons.directions_car_outlined, MileageScreen(), 'mileage'),
      const _MoreItem('Per diem', Icons.restaurant_outlined, PerDiemScreen(), 'per_diem'),
      const _MoreItem('Issues', Icons.bug_report_outlined, IssuesScreen(), 'issues'),
      const _MoreItem(
        'Belgium compliance report',
        Icons.flag_outlined,
        BelgiumReportScreen(),
        null,
      ),
    ].where((i) => _isEnabled(i.moduleId)).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: _loadingModules
          ? const Center(child: CircularProgressIndicator())
          : ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
              itemBuilder: (context, index) {
                final item = items[index];
                return Card(
                  child: ListTile(
                    leading: Icon(item.icon),
                    title: Text(item.label),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _open(context, item.screen),
                  ),
                );
              },
            ),
    );
  }
}

class _MoreItem {
  const _MoreItem(this.label, this.icon, this.screen, this.moduleId);
  final String label;
  final IconData icon;
  final Widget screen;
  final String? moduleId;
}
