import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import '../providers/attendance_provider.dart';

/// Workday clock-in/out controls shared between Home and Timer screens.
class WorkdayCard extends ConsumerWidget {
  const WorkdayCard({super.key});

  Future<void> _runAction(
    BuildContext context,
    WidgetRef ref,
    Future<bool> Function() action,
  ) async {
    final ok = await action();
    if (!context.mounted) return;
    final error = ref.read(attendanceProvider).error;
    if (!ok && error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error)),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen<AttendanceState>(attendanceProvider, (prev, next) {
      if (next.error != null && next.error != prev?.error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.error!)),
        );
      }
    });

    final attendanceState = ref.watch(attendanceProvider);
    final theme = Theme.of(context);
    final notifier = ref.read(attendanceProvider.notifier);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Workday', style: theme.textTheme.titleMedium),
            const SizedBox(height: AppSpacing.sm),
            Text(
              attendanceState.workActive ? 'At work' : 'Not clocked in',
              style: theme.textTheme.titleLarge?.copyWith(
                color: attendanceState.workActive
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurfaceVariant,
              ),
            ),
            if (attendanceState.breakActive)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.xs),
                child: Text(
                  'On break',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.tertiary,
                  ),
                ),
              ),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                if (!attendanceState.workActive)
                  FilledButton.icon(
                    onPressed: attendanceState.loading
                        ? null
                        : () => _runAction(context, ref, notifier.startWorkday),
                    icon: const Icon(Icons.login),
                    label: const Text('Start workday'),
                  )
                else ...[
                  FilledButton.icon(
                    onPressed: attendanceState.loading
                        ? null
                        : () => _runAction(context, ref, notifier.endWorkday),
                    icon: const Icon(Icons.logout),
                    label: const Text('End workday'),
                  ),
                  if (!attendanceState.breakActive)
                    OutlinedButton.icon(
                      onPressed: attendanceState.loading
                          ? null
                          : () => _runAction(context, ref, notifier.startBreak),
                      icon: const Icon(Icons.coffee),
                      label: const Text('Start break'),
                    )
                  else
                    OutlinedButton.icon(
                      onPressed: attendanceState.loading
                          ? null
                          : () => _runAction(context, ref, notifier.endBreak),
                      icon: const Icon(Icons.coffee_outlined),
                      label: const Text('End break'),
                    ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
