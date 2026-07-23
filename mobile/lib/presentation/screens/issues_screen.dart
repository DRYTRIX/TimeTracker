import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class IssuesScreen extends ConsumerStatefulWidget {
  const IssuesScreen({super.key});

  @override
  ConsumerState<IssuesScreen> createState() => _IssuesScreenState();
}

class _IssuesScreenState extends ConsumerState<IssuesScreen> {
  static const _statuses = ['open', 'in_progress', 'resolved', 'closed', 'cancelled'];
  static const _priorities = ['low', 'medium', 'high', 'urgent'];

  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) return const [];
    final res = await api.getIssues(perPage: 50);
    return extractList(res, const ['issues', 'items', 'data']);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _createOrEdit({Map<String, dynamic>? existing}) async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) return;

    List<Map<String, dynamic>> clients = const [];
    try {
      final clientsRes = await api.getClients(status: 'active', perPage: 100);
      clients = extractList(clientsRes, const ['clients', 'items', 'data']);
    } catch (_) {}

    final titleCtrl = TextEditingController(text: (existing?['title'] ?? '').toString());
    final descCtrl = TextEditingController(text: (existing?['description'] ?? '').toString());
    var status = (existing?['status'] ?? 'open').toString();
    if (!_statuses.contains(status)) status = 'open';
    var priority = (existing?['priority'] ?? 'medium').toString();
    if (!_priorities.contains(priority)) priority = 'medium';
    int? clientId = (existing?['client_id'] as num?)?.toInt();
    if (clientId == null && clients.isNotEmpty) {
      clientId = (clients.first['id'] as num?)?.toInt();
    }
    final isEdit = existing != null;
    final issueId = (existing?['id'] as num?)?.toInt();

    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: Text(isEdit ? 'Edit issue' : 'New issue'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: titleCtrl,
                    decoration: const InputDecoration(labelText: 'Title *'),
                    autofocus: true,
                  ),
                  if (!isEdit) ...[
                    const SizedBox(height: AppSpacing.sm),
                    DropdownButtonFormField<int>(
                      value: clientId,
                      decoration: const InputDecoration(labelText: 'Client *'),
                      items: clients
                          .map(
                            (c) => DropdownMenuItem<int>(
                              value: (c['id'] as num).toInt(),
                              child: Text((c['name'] ?? 'Client').toString()),
                            ),
                          )
                          .toList(),
                      onChanged: (v) => setDialogState(() => clientId = v),
                    ),
                  ],
                  TextField(
                    controller: descCtrl,
                    decoration: const InputDecoration(labelText: 'Description'),
                    maxLines: 3,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  DropdownButtonFormField<String>(
                    value: status,
                    decoration: const InputDecoration(labelText: 'Status'),
                    items: _statuses
                        .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) setDialogState(() => status = v);
                    },
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  DropdownButtonFormField<String>(
                    value: priority,
                    decoration: const InputDecoration(labelText: 'Priority'),
                    items: _priorities
                        .map((p) => DropdownMenuItem(value: p, child: Text(p)))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) setDialogState(() => priority = v);
                    },
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              FilledButton(
                onPressed: () {
                  if (titleCtrl.text.trim().isEmpty) return;
                  if (!isEdit && clientId == null) return;
                  Navigator.pop(ctx, true);
                },
                child: Text(isEdit ? 'Save' : 'Create'),
              ),
            ],
          ),
        ),
      );
      if (ok != true) return;
      if (isEdit && issueId != null) {
        await api.updateIssue(
          issueId,
          title: titleCtrl.text.trim(),
          description: descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
          status: status,
          priority: priority,
        );
      } else {
        await api.createIssue(
          title: titleCtrl.text.trim(),
          clientId: clientId!,
          description: descCtrl.text.trim().isEmpty ? null : descCtrl.text.trim(),
          status: status,
          priority: priority,
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(isEdit ? 'Issue updated' : 'Issue created')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      titleCtrl.dispose();
      descCtrl.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Issues')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _createOrEdit(),
        child: const Icon(Icons.add),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return EmptyState(
                icon: Icons.error_outline,
                title: 'Could not load issues',
                subtitle: snapshot.error.toString(),
              );
            }
            final items = snapshot.data ?? const [];
            if (items.isEmpty) {
              return const EmptyState(
                icon: Icons.bug_report_outlined,
                title: 'No issues',
                subtitle: 'Create an issue with the + button',
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
              itemBuilder: (context, i) {
                final issue = items[i];
                return Card(
                  child: ListTile(
                    title: Text((issue['title'] ?? 'Issue').toString()),
                    subtitle: Text(
                      '${issue['status'] ?? ''} · ${issue['priority'] ?? ''} · ${issue['client_name'] ?? ''}',
                    ),
                    onTap: () => _createOrEdit(existing: issue),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
