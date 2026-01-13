import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';

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
                    timerState.timer!.project?.name ?? 'Unknown Project',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (timerState.timer!.task != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      timerState.timer!.task!.name,
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
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
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
                          color: Colors.grey,
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
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  timerState.error!,
                  style: TextStyle(color: Colors.red.shade700),
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

    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final projectsState = ref.watch(projectsProvider);
    final tasksState = ref.watch(tasksProvider);

    return AlertDialog(
      title: const Text('Start Timer'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Project selection
            DropdownButtonFormField<int>(
              decoration: const InputDecoration(
                labelText: 'Project',
                prefixIcon: Icon(Icons.folder),
              ),
              value: _selectedProjectId,
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
                decoration: const InputDecoration(
                  labelText: 'Task (Optional)',
                  prefixIcon: Icon(Icons.task),
                ),
                value: _selectedTaskId,
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
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _handleStart,
          child: const Text('Start'),
        ),
      ],
    );
  }
}
