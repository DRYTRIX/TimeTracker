import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key});

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = DateTime.now();
  List<Map<String, dynamic>> _events = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForMonth(_focusedDay));
  }

  String _ymd(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  DateTime? _parseDay(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final dt = DateTime.tryParse(raw);
    if (dt == null) return null;
    return DateTime(dt.year, dt.month, dt.day);
  }

  Future<void> _loadForMonth(DateTime month) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) throw StateError('Not authenticated');
      final start = DateTime(month.year, month.month, 1);
      final end = DateTime(month.year, month.month + 1, 0);
      final res = await api.getCalendarEvents(
        startDate: _ymd(start),
        endDate: _ymd(end),
      );
      final events = extractList(res, const ['events', 'calendar_events', 'items', 'data']);
      if (!mounted) return;
      setState(() {
        _events = events;
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

  List<Map<String, dynamic>> _eventsForDay(DateTime day) {
    final key = DateTime(day.year, day.month, day.day);
    return _events.where((e) {
      final start = _parseDay(
        (e['start_time'] ?? e['start'] ?? e['start_date'] ?? e['date'])?.toString(),
      );
      if (start == null) return false;
      return isSameDay(start, key);
    }).toList();
  }

  Future<void> _createEvent() async {
    final titleCtrl = TextEditingController();
    DateTime start = DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day, 9);
    DateTime end = start.add(const Duration(hours: 1));
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: const Text('New event'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: titleCtrl,
                    decoration: const InputDecoration(labelText: 'Title *'),
                    autofocus: true,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Start: ${start.toIso8601String().substring(0, 16)}'),
                    trailing: const Icon(Icons.edit_calendar),
                    onTap: () async {
                      final date = await showDatePicker(
                        context: ctx,
                        initialDate: start,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                      );
                      if (date == null) return;
                      if (!ctx.mounted) return;
                      final time = await showTimePicker(
                        context: ctx,
                        initialTime: TimeOfDay.fromDateTime(start),
                      );
                      setDialogState(() {
                        start = DateTime(
                          date.year,
                          date.month,
                          date.day,
                          time?.hour ?? start.hour,
                          time?.minute ?? start.minute,
                        );
                        if (!end.isAfter(start)) {
                          end = start.add(const Duration(hours: 1));
                        }
                      });
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('End: ${end.toIso8601String().substring(0, 16)}'),
                    trailing: const Icon(Icons.edit_calendar),
                    onTap: () async {
                      final date = await showDatePicker(
                        context: ctx,
                        initialDate: end,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                      );
                      if (date == null) return;
                      if (!ctx.mounted) return;
                      final time = await showTimePicker(
                        context: ctx,
                        initialTime: TimeOfDay.fromDateTime(end),
                      );
                      setDialogState(() {
                        end = DateTime(
                          date.year,
                          date.month,
                          date.day,
                          time?.hour ?? end.hour,
                          time?.minute ?? end.minute,
                        );
                      });
                    },
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              FilledButton(
                onPressed: () {
                  if (titleCtrl.text.trim().isEmpty) return;
                  Navigator.pop(ctx, true);
                },
                child: const Text('Create'),
              ),
            ],
          ),
        ),
      );
      if (ok != true) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createCalendarEvent(
        title: titleCtrl.text.trim(),
        startTime: start.toIso8601String(),
        endTime: end.toIso8601String(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Event created')));
      await _loadForMonth(_focusedDay);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Create failed: $e')));
    } finally {
      titleCtrl.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    final dayEvents = _eventsForDay(_selectedDay);
    return Scaffold(
      appBar: AppBar(title: const Text('Calendar')),
      floatingActionButton: FloatingActionButton(
        onPressed: _createEvent,
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          TableCalendar<Map<String, dynamic>>(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2100, 12, 31),
            focusedDay: _focusedDay,
            selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
            eventLoader: _eventsForDay,
            calendarFormat: CalendarFormat.month,
            onDaySelected: (selected, focused) {
              setState(() {
                _selectedDay = selected;
                _focusedDay = focused;
              });
            },
            onPageChanged: (focused) {
              _focusedDay = focused;
              _loadForMonth(focused);
            },
          ),
          const Divider(height: 1),
          Expanded(
            child: dayEvents.isEmpty
                ? const EmptyState(
                    icon: Icons.event_busy,
                    title: 'No events',
                    subtitle: 'Tap + to create an event for this day.',
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    itemCount: dayEvents.length,
                    itemBuilder: (context, index) {
                      final e = dayEvents[index];
                      final title = (e['title'] ?? 'Event').toString();
                      final start = (e['start'] ?? e['start_date'] ?? '').toString();
                      final end = (e['end'] ?? e['end_date'] ?? '').toString();
                      return Card(
                        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: ListTile(
                          leading: const Icon(Icons.event),
                          title: Text(title),
                          subtitle: Text([
                            if (start.isNotEmpty) start,
                            if (end.isNotEmpty) end,
                          ].join(' → ')),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
