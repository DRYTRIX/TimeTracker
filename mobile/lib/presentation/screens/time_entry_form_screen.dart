import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';
import 'package:timetracker_mobile/presentation/providers/projects_provider.dart';
import 'package:timetracker_mobile/presentation/providers/tasks_provider.dart';
import 'package:timetracker_mobile/presentation/providers/time_entries_provider.dart';
import 'package:timetracker_mobile/presentation/providers/time_entry_requirements_provider.dart';
import 'package:timetracker_mobile/presentation/providers/user_prefs_provider.dart';
import 'package:timetracker_mobile/utils/date_format_utils.dart';

class TimeEntryFormScreen extends ConsumerStatefulWidget {
  final int? entryId;

  const TimeEntryFormScreen({super.key, this.entryId});

  @override
  ConsumerState<TimeEntryFormScreen> createState() =>
      _TimeEntryFormScreenState();
}

class _TimeEntryFormScreenState extends ConsumerState<TimeEntryFormScreen> {
  final _formKey = GlobalKey<FormState>();
  int? _selectedClientId;
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
  List<Map<String, dynamic>> _clients = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
      _loadClients();
      if (widget.entryId != null) {
        _loadEntry();
      }
    });
  }

  Future<void> _loadClients() async {
    final api = ref.read(apiClientProvider).valueOrNull;
    if (api == null) return;
    try {
      final res = await api.getClients(status: 'active', perPage: 100);
      final list = (res['clients'] as List<dynamic>? ?? [])
          .whereType<Map>()
          .map((c) => Map<String, dynamic>.from(c))
          .toList();
      if (mounted) setState(() => _clients = list);
    } catch (_) {
      // Keep form usable without clients list
    }
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

      _selectedClientId = entry.clientId;
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
        final projects = ref.read(projectsProvider).projects;
        final match = projects.where((p) => p.id == _selectedProjectId);
        if (match.isNotEmpty && match.first.clientId != null) {
          _selectedClientId ??= match.first.clientId;
        }
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

  List<Project> _filteredProjects(List<Project> projects) {
    if (_selectedClientId == null) return projects;
    return projects
        .where((p) => p.clientId == null || p.clientId == _selectedClientId)
        .toList();
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
              clientId: _selectedProjectId == null ? _selectedClientId : null,
              taskId: _selectedTaskId,
              startTime: startDateTime.toIso8601String(),
              endTime: endDateTimeStr,
              notes: notes.isEmpty ? null : notes,
              tags: _tagsController.text.trim().isEmpty
                  ? null
                  : _tagsController.text.trim(),
              billable: _billable,
            );
      } else {
        await ref.read(timeEntriesProvider.notifier).createEntry(
              projectId: _selectedProjectId,
              clientId: _selectedProjectId == null ? _selectedClientId : null,
              taskId: _selectedTaskId,
              startTime: startDateTime.toIso8601String(),
              endTime: endDateTimeStr,
              notes: notes.isEmpty ? null : notes,
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
    final requirementsAsync = ref.watch(timeEntryRequirementsProvider);
    final filteredProjects = _filteredProjects(projectsState.projects);

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
              DropdownButtonFormField<int>(
                key: ValueKey('client_$_selectedClientId'),
                decoration: const InputDecoration(
                  labelText: 'Client (optional)',
                  prefixIcon: Icon(Icons.business),
                ),
                initialValue: _selectedClientId != null &&
                        _clients.any((c) => (c['id'] as num?)?.toInt() == _selectedClientId)
                    ? _selectedClientId
                    : null,
                items: [
                  const DropdownMenuItem<int>(
                    value: null,
                    child: Text('Any client'),
                  ),
                  ..._clients.map((c) {
                    final id = (c['id'] as num).toInt();
                    return DropdownMenuItem<int>(
                      value: id,
                      child: Text(c['name']?.toString() ?? 'Client #$id'),
                    );
                  }),
                ],
                onChanged: (value) {
                  setState(() {
                    _selectedClientId = value;
                    if (_selectedProjectId != null) {
                      final project = projectsState.projects
                          .where((p) => p.id == _selectedProjectId)
                          .toList();
                      final ok = project.isNotEmpty &&
                          (value == null ||
                              project.first.clientId == null ||
                              project.first.clientId == value);
                      if (!ok) {
                        _selectedProjectId = null;
                        _selectedTaskId = null;
                      }
                    }
                  });
                },
              ),
              const SizedBox(height: AppSpacing.md),
              // Project selection (optional when client is set)
              DropdownButtonFormField<int>(
                key: ValueKey('project_${_selectedClientId}_$_selectedProjectId'),
                decoration: InputDecoration(
                  labelText: _selectedClientId != null
                      ? 'Project (optional)'
                      : 'Project *',
                  prefixIcon: const Icon(Icons.folder),
                ),
                initialValue: _selectedProjectId != null &&
                        filteredProjects.any((p) => p.id == _selectedProjectId)
                    ? _selectedProjectId
                    : null,
                items: [
                  const DropdownMenuItem<int>(
                    value: null,
                    child: Text('No project'),
                  ),
                  ...filteredProjects.map((p) => DropdownMenuItem(
                        value: p.id,
                        child: Text(p.name),
                      )),
                ],
                onChanged: (value) {
                  setState(() {
                    _selectedProjectId = value;
                    _selectedTaskId = null;
                    if (value != null) {
                      final match =
                          projectsState.projects.where((p) => p.id == value);
                      if (match.isNotEmpty && match.first.clientId != null) {
                        _selectedClientId = match.first.clientId;
                      }
                    }
                  });
                  if (value != null) {
                    _loadTasks(value);
                  }
                },
                validator: (value) {
                  if (value == null && _selectedClientId == null) {
                    return 'Select a client or project';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              // Task selection
              if (_selectedProjectId != null)
                DropdownButtonFormField<int>(
                  decoration: InputDecoration(
                    labelText: requirementsAsync.valueOrNull?.requireTask == true
                        ? 'Task *'
                        : 'Task (Optional)',
                    prefixIcon: const Icon(Icons.task),
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
              // Start date/time (display uses user's format; API still gets ISO)
              ListTile(
                title: const Text('Start Date & Time *'),
                subtitle: Text(
                  formatDateTime(
                    DateTime(
                      _startDate.year,
                      _startDate.month,
                      _startDate.day,
                      _startTime.hour,
                      _startTime.minute,
                    ),
                    ref.read(userPrefsProvider).valueOrNull?.dateFormatKey,
                    ref.read(userPrefsProvider).valueOrNull?.timeFormatKey,
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
                      ? formatDateTime(
                          DateTime(
                            _endDate!.year,
                            _endDate!.month,
                            _endDate!.day,
                            _endTime!.hour,
                            _endTime!.minute,
                          ),
                          ref.read(userPrefsProvider).valueOrNull?.dateFormatKey,
                          ref.read(userPrefsProvider).valueOrNull?.timeFormatKey,
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
                decoration: InputDecoration(
                  labelText: requirementsAsync.valueOrNull?.requireDescription == true
                      ? 'Notes *'
                      : 'Notes',
                  prefixIcon: const Icon(Icons.note),
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
