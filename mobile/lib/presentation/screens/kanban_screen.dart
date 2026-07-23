import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class KanbanScreen extends ConsumerStatefulWidget {
  const KanbanScreen({super.key});

  @override
  ConsumerState<KanbanScreen> createState() => _KanbanScreenState();
}

class _KanbanScreenState extends ConsumerState<KanbanScreen> {
  List<Map<String, dynamic>> _projects = const [];
  List<Map<String, dynamic>> _columns = const [];
  List<Map<String, dynamic>> _tasks = const [];
  int? _projectId;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
  }

  Future<void> _bootstrap() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) throw StateError('Not authenticated');
      final projectsRes = await api.getProjects(status: 'active', perPage: 100);
      final projects = extractList(projectsRes, const ['projects', 'items', 'data']);
      final firstId = projects.isNotEmpty ? (projects.first['id'] as num?)?.toInt() : null;
      if (!mounted) return;
      setState(() {
        _projects = projects;
        _projectId = firstId;
      });
      await _loadBoard();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _loadBoard() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) throw StateError('Not authenticated');
      final columnsRes = await api.getKanbanColumns(projectId: _projectId);
      var columns = extractList(columnsRes, const ['columns', 'kanban_columns', 'items', 'data']);
      if (columns.isEmpty) {
        columns = const [
          {'name': 'todo', 'status': 'todo'},
          {'name': 'in_progress', 'status': 'in_progress'},
          {'name': 'done', 'status': 'done'},
        ];
      }
      final tasksRes = await api.getTasks(projectId: _projectId, perPage: 200);
      final tasks = extractList(tasksRes, const ['tasks', 'items', 'data']);
      if (!mounted) return;
      setState(() {
        _columns = columns;
        _tasks = tasks;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _columnKey(Map<String, dynamic> col) {
    return (col['status'] ?? col['key'] ?? col['name'] ?? '').toString().toLowerCase().trim();
  }

  List<Map<String, dynamic>> _tasksForColumn(Map<String, dynamic> col) {
    final key = _columnKey(col);
    final name = (col['name'] ?? '').toString().toLowerCase().trim();
    return _tasks.where((t) {
      final status = (t['status'] ?? '').toString().toLowerCase().trim();
      if (status.isEmpty) return false;
      return status == key ||
          status == name ||
          status.replaceAll(' ', '_') == key.replaceAll(' ', '_') ||
          status.replaceAll('_', ' ') == name.replaceAll('_', ' ');
    }).toList();
  }

  Future<void> _changeStatus(Map<String, dynamic> task, String status) async {
    final id = (task['id'] as num?)?.toInt();
    if (id == null) return;
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.updateTask(id, status: status);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Moved to $status')));
      await _loadBoard();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Kanban')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: DropdownButtonFormField<int>(
              value: _projectId,
              decoration: const InputDecoration(
                labelText: 'Project',
                border: OutlineInputBorder(),
              ),
              items: _projects
                  .map(
                    (p) => DropdownMenuItem<int>(
                      value: (p['id'] as num).toInt(),
                      child: Text((p['name'] ?? 'Project').toString()),
                    ),
                  )
                  .toList(),
              onChanged: (value) async {
                setState(() => _projectId = value);
                await _loadBoard();
              },
            ),
          ),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          Expanded(
            child: _projects.isEmpty
                ? const EmptyState(
                    icon: Icons.view_kanban_outlined,
                    title: 'No projects',
                    subtitle: 'Create a project to use the kanban board.',
                  )
                : RefreshIndicator(
                    onRefresh: _loadBoard,
                    child: ListView.builder(
                      padding: const EdgeInsets.fromLTRB(
                        AppSpacing.md,
                        0,
                        AppSpacing.md,
                        AppSpacing.md,
                      ),
                      itemCount: _columns.length,
                      itemBuilder: (context, index) {
                        final col = _columns[index];
                        final title = (col['name'] ?? col['status'] ?? 'Column').toString();
                        final tasks = _tasksForColumn(col);
                        final statusOptions = _columns
                            .map(_columnKey)
                            .where((s) => s.isNotEmpty)
                            .toSet()
                            .toList();
                        return Card(
                          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                          child: ExpansionTile(
                            initiallyExpanded: true,
                            title: Text('$title (${tasks.length})'),
                            children: tasks.isEmpty
                                ? [
                                    const Padding(
                                      padding: EdgeInsets.all(AppSpacing.md),
                                      child: Text('No tasks'),
                                    ),
                                  ]
                                : tasks.map((task) {
                                    final name = (task['name'] ?? 'Task').toString();
                                    final status = (task['status'] ?? '').toString();
                                    return ListTile(
                                      title: Text(name),
                                      subtitle: Text(status),
                                      trailing: PopupMenuButton<String>(
                                        onSelected: (v) => _changeStatus(task, v),
                                        itemBuilder: (_) => statusOptions
                                            .map(
                                              (s) => PopupMenuItem(
                                                value: s,
                                                child: Text('Move to $s'),
                                              ),
                                            )
                                            .toList(),
                                      ),
                                    );
                                  }).toList(),
                          ),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
