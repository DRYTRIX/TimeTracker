import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';
import 'package:timetracker_mobile/presentation/providers/time_entries_provider.dart';

class TimeEntryFormScreen extends ConsumerStatefulWidget {
  final int? entryId;

  const TimeEntryFormScreen({super.key, this.entryId});

  @override
  ConsumerState<TimeEntryFormScreen> createState() =>
      _TimeEntryFormScreenState();
}

class _TimeEntryFormScreenState extends ConsumerState<TimeEntryFormScreen> {
  final _formKey = GlobalKey<FormState>();
  int? _selectedProjectId;
  int? _selectedTaskId;
  DateTime _startDate = DateTime.now();
  TimeOfDay _startTime = TimeOfDay.now();
  DateTime? _endDate;
  TimeOfDay? _endTime;
  final _notesController = TextEditingController();
  final _tagsController = TextEditingController();
  bool _billable = true;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
      if (widget.entryId != null) {
        _loadEntry();
      }
    });
  }

  Future<void> _loadEntry() async {
    setState(() {
      _isLoading = true;
    });

    try {
      var entries = ref.read(timeEntriesProvider).entries;
      if (entries.isEmpty) {
        await ref.read(timeEntriesProvider.notifier).loadEntries();
        entries = ref.read(timeEntriesProvider).entries;
      }

      final entry = entries.firstWhere(
        (e) => e.id == widget.entryId,
        orElse: () => throw StateError('Entry not found'),
      );

      final startTime = entry.startTime ?? DateTime.now();
      final endTime = entry.endTime;

      _selectedProjectId = entry.projectId;
      _selectedTaskId = entry.taskId;
      _startDate = DateTime(startTime.year, startTime.month, startTime.day);
      _startTime = TimeOfDay(hour: startTime.hour, minute: startTime.minute);
      if (endTime != null) {
        _endDate = DateTime(endTime.year, endTime.month, endTime.day);
        _endTime = TimeOfDay(hour: endTime.hour, minute: endTime.minute);
      } else {
        _endDate = null;
        _endTime = null;
      }
      _notesController.text = entry.notes ?? '';
      _tagsController.text = entry.tags ?? '';
      _billable = entry.billable;

      if (_selectedProjectId != null) {
        await _loadTasks(_selectedProjectId!);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to load time entry')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _notesController.dispose();
    _tagsController.dispose();
    super.dispose();
  }

  Future<void> _loadTasks(int projectId) async {
    await ref.read(tasksProvider.notifier).loadTasks(projectId: projectId);
  }

  Future<void> _selectDateTime(
    BuildContext context, {
    required bool isStart,
  }) async {
    final date = await showDatePicker(
      context: context,
      initialDate: isStart ? _startDate : (_endDate ?? DateTime.now()),
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );

    if (date == null) return;

    final time = await showTimePicker(
      context: context,
      initialTime: isStart ? _startTime : (_endTime ?? TimeOfDay.now()),
    );

    if (time == null) return;

    setState(() {
      if (isStart) {
        _startDate = date;
        _startTime = time;
      } else {
        _endDate = date;
        _endTime = time;
      }
    });
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedProjectId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a project')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final startDateTime = DateTime(
        _startDate.year,
        _startDate.month,
        _startDate.day,
        _startTime.hour,
        _startTime.minute,
      );

      String? endDateTimeStr;
      if (_endDate != null && _endTime != null) {
        final endDateTime = DateTime(
          _endDate!.year,
          _endDate!.month,
          _endDate!.day,
          _endTime!.hour,
          _endTime!.minute,
        );
        endDateTimeStr = endDateTime.toIso8601String();
      }

      if (widget.entryId != null) {
        await ref.read(timeEntriesProvider.notifier).updateEntry(
              widget.entryId!,
              projectId: _selectedProjectId,
              taskId: _selectedTaskId,
              startTime: startDateTime.toIso8601String(),
              endTime: endDateTimeStr,
              notes: _notesController.text.trim().isEmpty
                  ? null
                  : _notesController.text.trim(),
              tags: _tagsController.text.trim().isEmpty
                  ? null
                  : _tagsController.text.trim(),
              billable: _billable,
            );
      } else {
        await ref.read(timeEntriesProvider.notifier).createEntry(
              projectId: _selectedProjectId!,
              taskId: _selectedTaskId,
              startTime: startDateTime.toIso8601String(),
              endTime: endDateTimeStr,
              notes: _notesController.text.trim().isEmpty
                  ? null
                  : _notesController.text.trim(),
              tags: _tagsController.text.trim().isEmpty
                  ? null
                  : _tagsController.text.trim(),
              billable: _billable,
            );
      }

      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final projectsState = ref.watch(projectsProvider);
    final tasksState = ref.watch(tasksProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.entryId != null ? 'Edit Entry' : 'New Entry'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Project selection
              DropdownButtonFormField<int>(
                decoration: const InputDecoration(
                  labelText: 'Project *',
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
                    _selectedTaskId = null;
                  });
                  if (value != null) {
                    _loadTasks(value);
                  }
                },
                validator: (value) {
                  if (value == null) {
                    return 'Please select a project';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              // Task selection
              if (_selectedProjectId != null)
                DropdownButtonFormField<int>(
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
              const SizedBox(height: AppSpacing.md),
              // Start date/time
              ListTile(
                title: const Text('Start Date & Time *'),
                subtitle: Text(
                  DateFormat('yyyy-MM-dd HH:mm').format(
                    DateTime(
                      _startDate.year,
                      _startDate.month,
                      _startDate.day,
                      _startTime.hour,
                      _startTime.minute,
                    ),
                  ),
                ),
                trailing: const Icon(Icons.calendar_today),
                onTap: () => _selectDateTime(context, isStart: true),
              ),
              const SizedBox(height: AppSpacing.md),
              // End date/time
              ListTile(
                title: const Text('End Date & Time (Optional)'),
                subtitle: Text(
                  _endDate != null && _endTime != null
                      ? DateFormat('yyyy-MM-dd HH:mm').format(
                          DateTime(
                            _endDate!.year,
                            _endDate!.month,
                            _endDate!.day,
                            _endTime!.hour,
                            _endTime!.minute,
                          ),
                        )
                      : 'Not set',
                ),
                trailing: const Icon(Icons.calendar_today),
                onTap: () => _selectDateTime(context, isStart: false),
              ),
              const SizedBox(height: AppSpacing.md),
              // Notes
              TextFormField(
                controller: _notesController,
                decoration: const InputDecoration(
                  labelText: 'Notes',
                  prefixIcon: Icon(Icons.note),
                ),
                maxLines: 3,
              ),
              const SizedBox(height: AppSpacing.md),
              // Tags
              TextFormField(
                controller: _tagsController,
                decoration: const InputDecoration(
                  labelText: 'Tags (comma-separated)',
                  prefixIcon: Icon(Icons.tag),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              // Billable checkbox
              CheckboxListTile(
                title: const Text('Billable'),
                value: _billable,
                onChanged: (value) {
                  setState(() {
                    _billable = value ?? true;
                  });
                },
              ),
              const SizedBox(height: AppSpacing.lg),
              // Submit button
              ElevatedButton(
                onPressed: _isLoading ? null : _handleSubmit,
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(widget.entryId != null ? 'Update Entry' : 'Create Entry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
