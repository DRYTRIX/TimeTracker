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

  Future<void> _showHistory(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(attendanceProvider.notifier);
    List<Map<String, dynamic>> records = const [];
    try {
      records = await notifier.loadHistory();
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load history: $e')),
      );
      return;
    }
    if (!context.mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Attendance history', style: Theme.of(sheetContext).textTheme.titleLarge),
                const SizedBox(height: AppSpacing.sm),
                if (records.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
                    child: Text('No attendance records found.'),
                  )
                else
                  ConstrainedBox(
                    constraints: BoxConstraints(
                      maxHeight: MediaQuery.of(sheetContext).size.height * 0.55,
                    ),
                    child: ListView.builder(
                      shrinkWrap: true,
                      itemCount: records.length,
                      itemBuilder: (context, index) {
                        final record = records[index];
                        final date = (record['date'] ??
                                record['work_date'] ??
                                record['day'] ??
                                '')
                            .toString();
                        final status = (record['status'] ?? '').toString();
                        final hours = (record['total_hours'] ??
                                record['hours'] ??
                                record['worked_hours'] ??
                                '')
                            .toString();
                        final subtitle = [
                          if (status.isNotEmpty) status,
                          if (hours.isNotEmpty) '${hours}h',
                        ].join(' · ');
                        return ListTile(
                          title: Text(date.isEmpty ? 'Day' : date),
                          subtitle: subtitle.isEmpty ? null : Text(subtitle),
                          trailing: const Icon(Icons.edit_note_outlined),
                          onTap: () async {
                            Navigator.pop(sheetContext);
                            await _requestCorrection(context, ref, record);
                          },
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _requestCorrection(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> record,
  ) async {
    final idRaw = record['id'] ?? record['attendance_day_id'];
    final attendanceDayId = idRaw is num ? idRaw.toInt() : int.tryParse('$idRaw');
    if (attendanceDayId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Missing attendance day id')),
      );
      return;
    }

    final reasonController = TextEditingController();
    final dateStr = (record['work_date'] ?? record['date'] ?? '').toString();
    final now = DateTime.now();
    var start = DateTime(now.year, now.month, now.day, 9);
    var end = DateTime(now.year, now.month, now.day, 17);
    final parsedDate = DateTime.tryParse(dateStr);
    if (parsedDate != null) {
      start = DateTime(parsedDate.year, parsedDate.month, parsedDate.day, 9);
      end = DateTime(parsedDate.year, parsedDate.month, parsedDate.day, 17);
    }

    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) => AlertDialog(
              title: const Text('Request correction'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      dateStr.isEmpty ? 'Add a missed work period' : 'Add work period for $dateStr',
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('Start: ${start.toIso8601String().substring(0, 16)}'),
                      trailing: const Icon(Icons.schedule),
                      onTap: () async {
                        final time = await showTimePicker(
                          context: dialogContext,
                          initialTime: TimeOfDay.fromDateTime(start),
                        );
                        if (time == null) return;
                        setDialogState(() {
                          start = DateTime(start.year, start.month, start.day, time.hour, time.minute);
                        });
                      },
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('End: ${end.toIso8601String().substring(0, 16)}'),
                      trailing: const Icon(Icons.schedule),
                      onTap: () async {
                        final time = await showTimePicker(
                          context: dialogContext,
                          initialTime: TimeOfDay.fromDateTime(end),
                        );
                        if (time == null) return;
                        setDialogState(() {
                          end = DateTime(end.year, end.month, end.day, time.hour, time.minute);
                        });
                      },
                    ),
                    TextField(
                      controller: reasonController,
                      decoration: const InputDecoration(labelText: 'Reason *'),
                      maxLines: 3,
                      autofocus: true,
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext, false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    if (reasonController.text.trim().isEmpty) return;
                    Navigator.pop(dialogContext, true);
                  },
                  child: const Text('Submit'),
                ),
              ],
            ),
          );
        },
      );
      if (ok != true) return;
      final success = await ref.read(attendanceProvider.notifier).requestCorrection(
            attendanceDayId: attendanceDayId,
            reason: reasonController.text.trim(),
            entityType: 'AddWorkPeriod',
            entityId: 0,
            correctedValues: {
              'start_time': start.toIso8601String(),
              'end_time': end.toIso8601String(),
            },
          );
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            success ? 'Correction requested' : (ref.read(attendanceProvider).error ?? 'Request failed'),
          ),
        ),
      );
    } finally {
      reasonController.dispose();
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
            Row(
              children: [
                Expanded(
                  child: Text('Workday', style: theme.textTheme.titleMedium),
                ),
                TextButton(
                  onPressed: () => _showHistory(context, ref),
                  child: const Text('History'),
                ),
              ],
            ),
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
