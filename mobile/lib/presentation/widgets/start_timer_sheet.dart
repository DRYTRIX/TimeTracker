import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/data/models/task.dart' as task_model;
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';
import 'package:timetracker_mobile/presentation/providers/time_entry_requirements_provider.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';
import 'package:timetracker_mobile/presentation/widgets/searchable_picker_field.dart';

Future<void> showStartTimerSheet(
  BuildContext context, {
  int? initialProjectId,
  int? initialClientId,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => StartTimerSheet(
      initialProjectId: initialProjectId,
      initialClientId: initialClientId,
    ),
  );
}

class _ClientItem {
  final int id;
  final String name;

  const _ClientItem({required this.id, required this.name});
}

class StartTimerSheet extends ConsumerStatefulWidget {
  final int? initialProjectId;
  final int? initialClientId;

  const StartTimerSheet({
    super.key,
    this.initialProjectId,
    this.initialClientId,
  });

  @override
  ConsumerState<StartTimerSheet> createState() => _StartTimerSheetState();
}

class _StartTimerSheetState extends ConsumerState<StartTimerSheet> {
  final _notesController = TextEditingController();

  _ClientItem? _selectedClient;
  Project? _selectedProject;
  task_model.Task? _selectedTask;
  List<_ClientItem> _clients = [];
  bool _clientsLoading = false;
  String? _clientsError;
  bool _creating = false;

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
      _loadClients();
      _tryApplyInitialProject(ref.read(projectsProvider).projects);
    });
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadClients() async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null) return;
    setState(() {
      _clientsLoading = true;
      _clientsError = null;
    });
    try {
      final res = await api.getClients(status: 'active', perPage: 100);
      final list = (res['clients'] as List<dynamic>? ?? [])
          .whereType<Map>()
          .map((c) => _ClientItem(
                id: ((c['id'] as num?) ?? 0).toInt(),
                name: c['name']?.toString() ?? '',
              ))
          .toList();
      if (!mounted) return;
      setState(() {
        _clients = list;
        _clientsLoading = false;
        if (_selectedClient == null && widget.initialClientId != null) {
          final match = list.where((c) => c.id == widget.initialClientId);
          if (match.isNotEmpty) _selectedClient = match.first;
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _clientsLoading = false;
          _clientsError = e.toString();
        });
      }
    }
  }

  void _tryApplyInitialProject(List<Project> projects) {
    if (_selectedProject != null) return;
    final initialId = widget.initialProjectId;
    if (initialId == null) return;

    final match = projects.where((p) => p.id == initialId).toList();
    if (match.isEmpty) return;

    _applyProject(match.first);
  }

  void _applyProject(Project project) {
    _selectedProject = project;
    _selectedTask = null;
    if (project.clientId != null && _selectedClient == null) {
      final clientMatch =
          _clients.where((c) => c.id == project.clientId).toList();
      _selectedClient = clientMatch.isNotEmpty
          ? clientMatch.first
          : _ClientItem(id: project.clientId!, name: project.client ?? '');
    }
    ref.read(tasksProvider.notifier).loadTasks(projectId: project.id);
  }

  void _selectClient(_ClientItem? client) {
    setState(() {
      _selectedClient = client;
      // Changing the client invalidates project and task selections.
      _selectedProject = null;
      _selectedTask = null;
    });
  }

  void _selectProject(Project? project) {
    setState(() {
      _selectedProject = project;
      _selectedTask = null;
    });
    if (project != null) {
      ref.read(tasksProvider.notifier).loadTasks(projectId: project.id);
    }
  }

  void _selectTask(task_model.Task? task) {
    setState(() => _selectedTask = task);
  }

  List<Project> _clientProjects(List<Project> projects) {
    if (_selectedClient == null) return projects;
    return projects.where((p) => p.clientId == _selectedClient!.id).toList();
  }

  // The v1 create endpoints wrap the payload: {"message": ..., "<key>": {...}}.
  Map<String, dynamic> _unwrap(Map<String, dynamic> res, String key) {
    final nested = res[key];
    if (nested is Map) return Map<String, dynamic>.from(nested);
    return res;
  }

  Future<PickerItem<_ClientItem>?> _createClient(String name) async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null || _creating) return null;
    setState(() => _creating = true);
    try {
      final created = _unwrap(await api.createClient(name: name), 'client');
      final item = _ClientItem(
        id: ((created['id'] as num?) ?? 0).toInt(),
        name: created['name']?.toString() ?? name,
      );
      if (!mounted) return null;
      setState(() {
        _clients = [..._clients, item];
        _selectedClient = item;
        _selectedProject = null;
        _selectedTask = null;
        _creating = false;
      });
      return PickerItem(value: item, title: item.name);
    } catch (e) {
      if (mounted) {
        setState(() => _creating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not create client: $e')),
        );
      }
      return null;
    }
  }

  Future<PickerItem<Project>?> _createProject(String name) async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null || _creating || _selectedClient == null) return null;
    setState(() => _creating = true);
    try {
      final created =
          _unwrap(await api.createProject(name: name, clientId: _selectedClient!.id), 'project');
      final project = Project.fromJson(created);
      if (!mounted) return null;
      setState(() {
        _selectedProject = project;
        _selectedTask = null;
        _creating = false;
      });
      ref.read(projectsProvider.notifier).refresh();
      ref.read(tasksProvider.notifier).loadTasks(projectId: project.id);
      return PickerItem(value: project, title: project.name, subtitle: _selectedClient!.name);
    } catch (e) {
      if (mounted) {
        setState(() => _creating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not create project: $e')),
        );
      }
      return null;
    }
  }

  Future<PickerItem<task_model.Task>?> _createTask(String name) async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null || _creating || _selectedProject == null) return null;
    setState(() => _creating = true);
    try {
      final created = _unwrap(
        await api.createTask(projectId: _selectedProject!.id, name: name),
        'task',
      );
      final task = task_model.Task.fromJson(created);
      if (!mounted) return null;
      setState(() {
        _selectedTask = task;
        _creating = false;
      });
      ref.read(tasksProvider.notifier).loadTasks(projectId: _selectedProject!.id);
      return PickerItem(value: task, title: task.name);
    } catch (e) {
      if (mounted) {
        setState(() => _creating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not create task: $e')),
        );
      }
      return null;
    }
  }

  Future<void> _handleStart() async {
    if (_selectedProject == null && _selectedClient == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a client or project')),
      );
      return;
    }

    final requirements = await ref.read(timeEntryRequirementsProvider.future);
    if (_selectedProject != null &&
        requirements.requireTask &&
        _selectedTask == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('A task must be selected when logging time for a project')),
      );
      return;
    }
    final notes = _notesController.text.trim();
    if (requirements.requireDescription) {
      if (notes.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('A description is required when logging time')),
        );
        return;
      }
      if (notes.length < requirements.descriptionMinLength) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Description must be at least ${requirements.descriptionMinLength} characters',
            ),
          ),
        );
        return;
      }
    }

    await ref.read(timerProvider.notifier).startTimer(
          projectId: _selectedProject?.id,
          clientId: _selectedProject == null ? _selectedClient?.id : null,
          taskId: _selectedTask?.id,
          notes: notes.isEmpty ? null : notes,
        );

    if (!mounted) return;
    final timerState = ref.read(timerProvider);
    if (timerState.error != null) {
      // Keep sheet open and show error
      setState(() {});
      return;
    }
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    // Listen within build so initial project selection applies as soon as
    // projects finish loading.
    ref.listen<ProjectsState>(projectsProvider, (previous, next) {
      if (!mounted) return;
      _tryApplyInitialProject(next.projects);
    });

    final apiClientAsync = ref.watch(apiClientProvider);
    final projectsState = ref.watch(projectsProvider);
    final tasksState = ref.watch(tasksProvider);
    final timerState = ref.watch(timerProvider);
    final requirementsAsync = ref.watch(timeEntryRequirementsProvider);

    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    final isApiReady = apiClientAsync.when(
      data: (client) => client != null,
      loading: () => false,
      error: (_, __) => false,
    );
    final isApiLoading = apiClientAsync.isLoading;

    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final maxHeight = MediaQuery.of(context).size.height * 0.9;

    final canStart =
        isApiReady && !isApiLoading && !timerState.isLoading && !_creating;
    final clientProjects = _clientProjects(projectsState.projects);

    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: maxHeight),
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.md,
          right: AppSpacing.md,
          top: AppSpacing.sm,
          bottom: math.max(AppSpacing.md, bottomInset),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Text('Start timer', style: theme.textTheme.titleLarge),
                  const Spacer(),
                  IconButton(
                    onPressed: (timerState.isLoading || isApiLoading) ? null : () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                    tooltip: 'Close',
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              if (isApiLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (!isApiReady)
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: cs.errorContainer,
                    borderRadius: AppRadii.brMd,
                  ),
                  child: Text(
                    'Not connected to server. Check settings and try again.',
                    style: TextStyle(color: cs.onErrorContainer),
                  ),
                ),
              const SizedBox(height: AppSpacing.md),
              SearchablePickerField<_ClientItem>(
                label: 'Client (optional)',
                icon: Icons.business_outlined,
                searchHint: 'Search clients',
                emptyText: 'No clients found',
                isLoading: _clientsLoading,
                error: _clientsError,
                onRetry: _loadClients,
                enabled: isApiReady && !_clientsLoading && !_creating,
                items: _clients
                    .map((c) => PickerItem(value: c, title: c.name))
                    .toList(),
                selected: _selectedClient == null
                    ? null
                    : PickerItem(value: _selectedClient!, title: _selectedClient!.name),
                onSelected: (item) => _selectClient(item.value),
                onClear: () => _selectClient(null),
                onCreate: _createClient,
              ),
              const SizedBox(height: AppSpacing.md),
              SearchablePickerField<Project>(
                key: ValueKey('projects_${_selectedClient?.id}'),
                label: _selectedClient == null
                    ? 'Project (select a client first)'
                    : 'Project (optional for this client)',
                icon: Icons.folder_outlined,
                searchHint: 'Search projects',
                emptyText: _selectedClient == null
                    ? 'Select a client first'
                    : 'No projects for this client',
                enabled: _selectedClient != null && !_creating,
                isLoading: projectsState.isLoading,
                error: projectsState.error,
                onRetry: () => ref.read(projectsProvider.notifier).loadProjects(),
                items: clientProjects
                    .map((p) => PickerItem(
                          value: p,
                          title: p.name,
                          subtitle: p.client,
                        ))
                    .toList(),
                selected: _selectedProject == null
                    ? null
                    : PickerItem(
                        value: _selectedProject!,
                        title: _selectedProject!.name,
                        subtitle: _selectedProject!.client,
                      ),
                onSelected: (item) => _selectProject(item.value),
                onClear: () => _selectProject(null),
                onCreate: _selectedClient == null ? null : _createProject,
              ),
              const SizedBox(height: AppSpacing.md),
              SearchablePickerField<task_model.Task>(
                key: ValueKey('tasks_${_selectedProject?.id}'),
                label: requirementsAsync.valueOrNull?.requireTask == true
                    ? 'Task *'
                    : 'Task (optional)',
                icon: Icons.task_outlined,
                searchHint: 'Search tasks',
                emptyText: _selectedProject == null
                    ? 'Select a project first'
                    : 'No tasks for this project',
                enabled: _selectedProject != null && !_creating,
                isLoading: tasksState.isLoading,
                error: tasksState.error,
                onRetry: _selectedProject == null
                    ? null
                    : () => ref
                        .read(tasksProvider.notifier)
                        .loadTasks(projectId: _selectedProject!.id),
                items: tasksState.tasks
                    .map((t) => PickerItem(value: t, title: t.name))
                    .toList(),
                selected: _selectedTask == null
                    ? null
                    : PickerItem(value: _selectedTask!, title: _selectedTask!.name),
                onSelected: (item) => _selectTask(item.value),
                onClear: () => _selectTask(null),
                onCreate: _selectedProject == null ? null : _createTask,
              ),
              const SizedBox(height: AppSpacing.md),
              TextField(
                controller: _notesController,
                textInputAction: TextInputAction.done,
                decoration: InputDecoration(
                  labelText: requirementsAsync.valueOrNull?.requireDescription == true
                      ? 'Notes *'
                      : 'Notes (optional)',
                  prefixIcon: const Icon(Icons.note_outlined),
                ),
                maxLines: 3,
              ),
              if (timerState.error != null) ...[
                const SizedBox(height: AppSpacing.md),
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: cs.errorContainer,
                    borderRadius: AppRadii.brMd,
                  ),
                  child: Text(
                    timerState.error!,
                    style: TextStyle(color: cs.onErrorContainer),
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.lg),
              Row(
                children: [
                  Expanded(
                    child: TextButton(
                      onPressed: (timerState.isLoading || isApiLoading) ? null : () => Navigator.of(context).pop(),
                      child: const Text('Cancel'),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: canStart ? _handleStart : null,
                      icon: timerState.isLoading
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.play_arrow),
                      label: const Text('Start'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
