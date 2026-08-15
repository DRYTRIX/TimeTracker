import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';
import 'package:timetracker_mobile/presentation/providers/time_entry_requirements_provider.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';

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
  final SearchController _projectSearchController = SearchController();

  int? _selectedClientId;
  String? _selectedClientName;
  int? _selectedProjectId;
  int? _selectedTaskId;
  List<Map<String, dynamic>> _clients = [];
  bool _clientsLoading = false;

  @override
  void initState() {
    super.initState();
    _selectedClientId = widget.initialClientId;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
      _loadClients();
      _tryApplyInitialProject(ref.read(projectsProvider).projects);
    });

    ref.listen<ProjectsState>(projectsProvider, (previous, next) {
      if (!mounted) return;
      _tryApplyInitialProject(next.projects);
    });
  }

  @override
  void dispose() {
    _notesController.dispose();
    _projectSearchController.dispose();
    super.dispose();
  }

  Future<void> _loadClients() async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null) return;
    setState(() => _clientsLoading = true);
    try {
      final res = await api.getClients(status: 'active', perPage: 100);
      final list = (res['clients'] as List<dynamic>? ?? [])
          .whereType<Map>()
          .map((c) => Map<String, dynamic>.from(c))
          .toList();
      if (!mounted) return;
      setState(() {
        _clients = list;
        _clientsLoading = false;
        if (_selectedClientId != null) {
          final match = list.where((c) => (c['id'] as num?)?.toInt() == _selectedClientId);
          if (match.isNotEmpty) {
            _selectedClientName = match.first['name']?.toString();
          }
        }
      });
    } catch (_) {
      if (mounted) setState(() => _clientsLoading = false);
    }
  }

  void _tryApplyInitialProject(List<Project> projects) {
    if (_selectedProjectId != null) return;
    final initialId = widget.initialProjectId;
    if (initialId == null) return;

    final match = projects.where((p) => p.id == initialId).toList();
    if (match.isEmpty) return;

    _selectProject(match.first);
  }

  Future<void> _selectClient(int? clientId, {String? name}) async {
    setState(() {
      _selectedClientId = clientId;
      _selectedClientName = name;
      _selectedProjectId = null;
      _selectedTaskId = null;
      _projectSearchController.text = '';
    });
  }

  Future<void> _selectProject(Project project) async {
    setState(() {
      _selectedProjectId = project.id;
      _selectedTaskId = null;
      _projectSearchController.text = project.name;
      if (project.clientId != null) {
        _selectedClientId = project.clientId;
        _selectedClientName = project.client;
      }
    });
    await ref.read(tasksProvider.notifier).loadTasks(projectId: project.id);
  }

  List<Project> _filteredProjects(List<Project> projects) {
    if (_selectedClientId == null) return projects;
    return projects
        .where((p) => p.clientId == null || p.clientId == _selectedClientId)
        .toList();
  }

  Future<void> _handleStart() async {
    if (_selectedProjectId == null && _selectedClientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a client or project')),
      );
      return;
    }

    final requirements = await ref.read(timeEntryRequirementsProvider.future);
    if (_selectedProjectId != null &&
        requirements.requireTask &&
        _selectedTaskId == null) {
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
          projectId: _selectedProjectId,
          clientId: _selectedProjectId == null ? _selectedClientId : null,
          taskId: _selectedTaskId,
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

    final canStart = isApiReady && !isApiLoading && !timerState.isLoading;
    final filteredProjects = _filteredProjects(projectsState.projects);

    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: maxHeight),
      child: Padding(
        padding: EdgeInsets.only(
          left: AppSpacing.md,
          right: AppSpacing.md,
          top: AppSpacing.sm,
          bottom: math.max(AppSpacing.md, bottomInset),
        ),
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
            DropdownButtonFormField<int>(
              key: ValueKey('client_$_selectedClientId'),
              decoration: const InputDecoration(
                labelText: 'Client (optional)',
                prefixIcon: Icon(Icons.business_outlined),
              ),
              initialValue: _selectedClientId,
              items: [
                const DropdownMenuItem<int>(value: null, child: Text('Any client')),
                ..._clients.map((c) {
                  final id = (c['id'] as num).toInt();
                  return DropdownMenuItem<int>(
                    value: id,
                    child: Text(c['name']?.toString() ?? 'Client #$id'),
                  );
                }),
              ],
              onChanged: _clientsLoading
                  ? null
                  : (value) {
                      String? name;
                      if (value != null) {
                        for (final c in _clients) {
                          if ((c['id'] as num?)?.toInt() == value) {
                            name = c['name']?.toString();
                            break;
                          }
                        }
                      }
                      _selectClient(value, name: name ?? _selectedClientName);
                    },
            ),
            const SizedBox(height: AppSpacing.md),
            SearchAnchor(
              searchController: _projectSearchController,
              viewHintText: 'Search projects',
              builder: (context, controller) {
                return SearchBar(
                  controller: controller,
                  onTap: controller.openView,
                  onChanged: (_) => controller.openView(),
                  leading: const Icon(Icons.folder_outlined),
                  hintText: _selectedClientId != null
                      ? 'Project (optional for this client)'
                      : 'Select project',
                  trailing: [
                    if (_selectedProjectId != null)
                      IconButton(
                        onPressed: () {
                          setState(() {
                            _selectedProjectId = null;
                            _selectedTaskId = null;
                            _projectSearchController.text = '';
                          });
                        },
                        icon: const Icon(Icons.clear),
                        tooltip: 'Clear project',
                      ),
                  ],
                );
              },
              suggestionsBuilder: (context, controller) {
                final query = controller.text.trim().toLowerCase();
                final projects = filteredProjects;
                final matches = query.isEmpty
                    ? projects
                    : projects.where((p) {
                        final client = (p.client ?? '').toLowerCase();
                        return p.name.toLowerCase().contains(query) || client.contains(query);
                      }).toList();

                if (projectsState.isLoading && projects.isEmpty) {
                  return const [ListTile(title: Text('Loading projects...'))];
                }

                if (projectsState.error != null && projects.isEmpty) {
                  return [
                    ListTile(
                      title: const Text('Could not load projects'),
                      subtitle: Text(projectsState.error!),
                      trailing: TextButton(
                        onPressed: () => ref.read(projectsProvider.notifier).loadProjects(),
                        child: const Text('Retry'),
                      ),
                    ),
                  ];
                }

                if (matches.isEmpty) {
                  return [
                    ListTile(
                      title: Text(
                        _selectedClientId != null
                            ? 'No projects for this client — start client-only'
                            : 'No matching projects',
                      ),
                    ),
                  ];
                }

                return matches.map((p) {
                  return ListTile(
                    leading: CircleAvatar(
                      child: Text(
                        (p.name.isNotEmpty ? p.name[0] : '?').toUpperCase(),
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                    title: Text(p.name),
                    subtitle: (p.client == null || p.client!.isEmpty) ? null : Text(p.client!),
                    onTap: () async {
                      controller.closeView(p.name);
                      await _selectProject(p);
                    },
                  );
                });
              },
            ),
            const SizedBox(height: AppSpacing.md),
            DropdownButtonFormField<int>(
              key: ValueKey('task_$_selectedTaskId'),
              decoration: InputDecoration(
                labelText: requirementsAsync.valueOrNull?.requireTask == true
                    ? 'Task *'
                    : 'Task (optional)',
                prefixIcon: const Icon(Icons.task_outlined),
              ),
              initialValue: _selectedTaskId,
              items: [
                const DropdownMenuItem<int>(value: null, child: Text('No task')),
                ...tasksState.tasks.map(
                  (t) => DropdownMenuItem<int>(value: t.id, child: Text(t.name)),
                ),
              ],
              onChanged: _selectedProjectId == null
                  ? null
                  : (value) {
                      setState(() {
                        _selectedTaskId = value;
                      });
                    },
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
    );
  }
}
