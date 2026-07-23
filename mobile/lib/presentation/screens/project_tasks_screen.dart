import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class ProjectTasksScreen extends ConsumerStatefulWidget {
  const ProjectTasksScreen({
    super.key,
    required this.projectId,
    required this.projectName,
  });

  final int projectId;
  final String projectName;

  @override
  ConsumerState<ProjectTasksScreen> createState() => _ProjectTasksScreenState();
}

class _ProjectTasksScreenState extends ConsumerState<ProjectTasksScreen> {
  static const _statuses = ['todo', 'in_progress', 'done'];
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
    final res = await api.getTasks(projectId: widget.projectId, perPage: 100);
    return extractList(res, const ['tasks', 'items', 'data']);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _createOrEdit({Map<String, dynamic>? existing}) async {
    final nameCtrl = TextEditingController(text: (existing?['name'] ?? '').toString());
    var status = (existing?['status'] ?? 'todo').toString();
    if (!_statuses.contains(status)) status = 'todo';
    var priority = (existing?['priority'] ?? 'medium').toString();
    if (!_priorities.contains(priority)) priority = 'medium';
    final isEdit = existing != null;
    final taskId = (existing?['id'] as num?)?.toInt();

    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: Text(isEdit ? 'Edit task' : 'New task'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Name *'),
                    autofocus: true,
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
                  if (nameCtrl.text.trim().isEmpty) return;
                  Navigator.pop(ctx, true);
                },
                child: Text(isEdit ? 'Save' : 'Create'),
              ),
            ],
          ),
        ),
      );
      if (ok != true) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      if (isEdit && taskId != null) {
        await api.updateTask(
          taskId,
          name: nameCtrl.text.trim(),
          status: status,
          priority: priority,
        );
      } else {
        await api.createTask(
          projectId: widget.projectId,
          name: nameCtrl.text.trim(),
          status: status,
          priority: priority,
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(isEdit ? 'Task updated' : 'Task created')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      nameCtrl.dispose();
    }
  }

  Future<void> _deleteTask(int taskId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete task?'),
        content: const Text('This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.deleteTask(taskId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Task deleted')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Delete failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.projectName)),
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
              return ListView(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Text('Failed to load tasks: ${snapshot.error}'),
                  ),
                ],
              );
            }
            final tasks = snapshot.data ?? const [];
            if (tasks.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  EmptyState(
                    icon: Icons.checklist,
                    title: 'No tasks',
                    subtitle: 'Create a task for this project.',
                  ),
                ],
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: tasks.length,
              itemBuilder: (context, index) {
                final task = tasks[index];
                final id = (task['id'] as num?)?.toInt();
                final name = (task['name'] ?? 'Task').toString();
                final status = (task['status'] ?? '').toString();
                final priority = (task['priority'] ?? '').toString();
                final tile = Card(
                  margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: ListTile(
                    title: Text(name),
                    subtitle: Text([
                      if (status.isNotEmpty) status,
                      if (priority.isNotEmpty) priority,
                    ].join(' · ')),
                    trailing: id == null
                        ? null
                        : PopupMenuButton<String>(
                            onSelected: (v) {
                              if (v == 'edit') _createOrEdit(existing: task);
                              if (v == 'delete') _deleteTask(id);
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(value: 'edit', child: Text('Edit')),
                              PopupMenuItem(value: 'delete', child: Text('Delete')),
                            ],
                          ),
                    onTap: () => _createOrEdit(existing: task),
                  ),
                );
                if (id == null) return tile;
                return Dismissible(
                  key: ValueKey('task-$id'),
                  direction: DismissDirection.endToStart,
                  confirmDismiss: (_) async {
                    await _deleteTask(id);
                    return false;
                  },
                  background: Container(
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: AppSpacing.md),
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Icon(Icons.delete, color: Theme.of(context).colorScheme.onErrorContainer),
                  ),
                  child: tile,
                );
              },
            );
          },
        ),
      ),
    );
  }
}
