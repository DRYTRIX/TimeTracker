import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/data/models/task.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';

import 'start_timer_sheet.dart';

class TimerWidget extends ConsumerStatefulWidget {
  const TimerWidget({super.key});

  @override
  ConsumerState<TimerWidget> createState() => _TimerWidgetState();
}

class _TimerWidgetState extends ConsumerState<TimerWidget> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      if (ref.read(timerProvider).isActive) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
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

    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    final isActive = timerState.isActive && timerState.timer != null;
    final elapsedText = isActive ? timerState.timer!.formattedElapsed : '00:00:00';
    final projectName = project?.name ?? 'Unknown project';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(isActive ? Icons.timer : Icons.timer_outlined, color: cs.primary),
                const SizedBox(width: AppSpacing.sm),
                Text('Timer', style: theme.textTheme.titleLarge),
                const Spacer(),
                IconButton(
                  onPressed: timerState.isLoading ? null : () => ref.read(timerProvider.notifier).refresh(),
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Refresh',
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            AnimatedSwitcher(
              duration: AppDurations.normal,
              child: isActive
                  ? Column(
                      key: const ValueKey('active'),
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Text(
                          elapsedText,
                          style: theme.textTheme.displayMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                            color: cs.primary,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Wrap(
                          alignment: WrapAlignment.center,
                          spacing: AppSpacing.sm,
                          runSpacing: AppSpacing.xs,
                          children: [
                            Chip(
                              avatar: const Icon(Icons.folder_outlined, size: 18),
                              label: Text(projectName),
                            ),
                            if (task != null)
                              Chip(
                                avatar: const Icon(Icons.task_outlined, size: 18),
                                label: Text(task.name),
                              ),
                          ],
                        ),
                        if (timerState.timer!.notes != null && timerState.timer!.notes!.isNotEmpty) ...[
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            timerState.timer!.notes!,
                            style: theme.textTheme.bodyMedium?.copyWith(color: cs.onSurfaceVariant),
                            textAlign: TextAlign.center,
                          ),
                        ],
                        const SizedBox(height: AppSpacing.lg),
                        FilledButton.icon(
                          onPressed: timerState.isLoading ? null : () => ref.read(timerProvider.notifier).stopTimer(),
                          icon: const Icon(Icons.stop),
                          label: const Text('Stop'),
                          style: FilledButton.styleFrom(
                            backgroundColor: cs.error,
                            foregroundColor: cs.onError,
                          ),
                        ),
                      ],
                    )
                  : Column(
                      key: const ValueKey('inactive'),
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Text(
                          elapsedText,
                          style: theme.textTheme.displayMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                            color: cs.onSurfaceVariant,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          'Ready to track time?',
                          style: theme.textTheme.bodyMedium?.copyWith(color: cs.onSurfaceVariant),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: AppSpacing.lg),
                        FilledButton.icon(
                          onPressed: timerState.isLoading
                              ? null
                              : () => showStartTimerSheet(context),
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Start'),
                        ),
                      ],
                    ),
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
          ],
        ),
      ),
    );
  }
}
