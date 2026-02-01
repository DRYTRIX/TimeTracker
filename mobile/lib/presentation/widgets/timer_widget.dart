import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/data/models/task.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';

class TimerWidget extends ConsumerStatefulWidget {
  const TimerWidget({super.key});

  @override
  ConsumerState<TimerWidget> createState() => _TimerWidgetState();
}

class _TimerWidgetState extends ConsumerState<TimerWidget> {
  @override
  void initState() {
    super.initState();
    // Refresh timer every second when active
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startTimerUpdate();
    });
  }

  void _startTimerUpdate() {
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        final timerState = ref.read(timerProvider);
        if (timerState.isActive) {
          setState(() {});
          _startTimerUpdate();
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final timerState = ref.watch(timerProvider);
    final projectsState = ref.watch(projectsProvider);
    final tasksState = ref.watch(tasksProvider);

    // Find project and task by ID
    Project? project;
    Task? task;
    if (timerState.timer != null) {
      try {
        project = projectsState.projects.firstWhere(
          (p) => p.id == timerState.timer!.projectId,
        );
      } catch (e) {
        project = null;
      }
      if (timerState.timer!.taskId != null) {
        try {
          task = tasksState.tasks.firstWhere(
            (t) => t.id == timerState.timer!.taskId,
          );
        } catch (e) {
          task = null;
        }
      }
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            Text(
              'Active Timer',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 24),
            if (timerState.isActive && timerState.timer != null)
              Column(
                children: [
                  Text(
                    timerState.timer!.formattedElapsed,
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    project?.name ?? 'Unknown Project',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (task != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      task.name,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  if (timerState.timer!.notes != null &&
                      timerState.timer!.notes!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      timerState.timer!.notes!,
                      style: Theme.of(context).textTheme.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                  ],
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: timerState.isLoading
                        ? null
                        : () => ref.read(timerProvider.notifier).stopTimer(),
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Timer'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.error,
                      foregroundColor: Theme.of(context).colorScheme.onError,
                    ),
                  ),
                ],
              )
            else
              Column(
                children: [
                  Text(
                    '00:00:00',
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'No active timer',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: timerState.isLoading
                        ? null
                        : () => _showStartTimerDialog(context),
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Timer'),
                  ),
                ],
              ),
            if (timerState.error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  timerState.error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showStartTimerDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => const StartTimerDialog(),
    );
  }
}

class StartTimerDialog extends ConsumerStatefulWidget {
  const StartTimerDialog({super.key});

  @override
  ConsumerState<StartTimerDialog> createState() => _StartTimerDialogState();
}

class _StartTimerDialogState extends ConsumerState<StartTimerDialog> {
  int? _selectedProjectId;
  int? _selectedTaskId;
  final _notesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Load projects if not loaded
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
    });
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadTasks(int projectId) async {
    await ref.read(tasksProvider.notifier).loadTasks(projectId: projectId);
  }

  Future<void> _handleStart() async {
    if (_selectedProjectId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a project')),
      );
      return;
    }

    await ref.read(timerProvider.notifier).startTimer(
          projectId: _selectedProjectId!,
          taskId: _selectedTaskId,
          notes: _notesController.text.trim().isEmpty
              ? null
              : _notesController.text.trim(),
        );

    if (!mounted) return;
    final timerState = ref.read(timerProvider);
    if (timerState.error != null) {
      // Keep dialog open and show error; do not pop
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

    final isApiReady = apiClientAsync.when(
      data: (client) => client != null,
      loading: () => false,
      error: (_, __) => false,
    );
    final isApiLoading = apiClientAsync.isLoading;

    return AlertDialog(
      title: const Text('Start Timer'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (isApiLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24.0),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (!isApiReady) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Not connected to server. Check settings and try again.',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onErrorContainer,
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ] else ...[
            // Project selection
            DropdownButtonFormField<int>(
              key: ValueKey('project_$_selectedProjectId'),
              decoration: const InputDecoration(
                labelText: 'Project',
                prefixIcon: Icon(Icons.folder),
              ),
              initialValue: _selectedProjectId != null &&
                      projectsState.projects.any((p) => p.id == _selectedProjectId)
                  ? _selectedProjectId
                  : null,
              items: projectsState.projects
                  .map((p) => DropdownMenuItem(
                        value: p.id,
                        child: Text(p.name),
                      ))
                  .toList(),
              onChanged: (value) {
                setState(() {
                  _selectedProjectId = value;
                  _selectedTaskId = null; // Reset task when project changes
                });
                if (value != null) {
                  _loadTasks(value);
                }
              },
            ),
            const SizedBox(height: 16),
            // Task selection (optional)
            if (_selectedProjectId != null)
              DropdownButtonFormField<int>(
                key: ValueKey('task_$_selectedTaskId'),
                decoration: const InputDecoration(
                  labelText: 'Task (Optional)',
                  prefixIcon: Icon(Icons.task),
                ),
                initialValue: _selectedTaskId != null &&
                        tasksState.tasks.any((t) => t.id == _selectedTaskId)
                    ? _selectedTaskId
                    : null,
                items: [
                  const DropdownMenuItem<int>(
                    value: null,
                    child: Text('No task'),
                  ),
                  ...tasksState.tasks
                      .map((t) => DropdownMenuItem(
                            value: t.id,
                            child: Text(t.name),
                          ))
                      .toList(),
                ],
                onChanged: (value) {
                  setState(() {
                    _selectedTaskId = value;
                  });
                },
              ),
            const SizedBox(height: 16),
            // Notes
            TextField(
              controller: _notesController,
              decoration: const InputDecoration(
                labelText: 'Notes (Optional)',
                prefixIcon: Icon(Icons.note),
              ),
              maxLines: 3,
            ),
            if (timerState.error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  timerState.error!,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onErrorContainer,
                  ),
                ),
              ),
            ],
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: timerState.isLoading || isApiLoading
              ? null
              : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: (timerState.isLoading || isApiLoading || !isApiReady)
              ? null
              : _handleStart,
          child: timerState.isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Start'),
        ),
      ],
    );
  }
}
