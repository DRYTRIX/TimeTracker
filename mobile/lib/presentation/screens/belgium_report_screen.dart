import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class BelgiumReportScreen extends ConsumerStatefulWidget {
  const BelgiumReportScreen({super.key});

  @override
  ConsumerState<BelgiumReportScreen> createState() => _BelgiumReportScreenState();
}

class _BelgiumReportScreenState extends ConsumerState<BelgiumReportScreen> {
  late DateTime _start;
  late DateTime _end;
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _start = DateTime(now.year, now.month, 1);
    _end = DateTime(now.year, now.month + 1, 0);
    _future = _load();
  }

  String _ymd(DateTime d) => d.toIso8601String().split('T')[0];

  Future<List<Map<String, dynamic>>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');
    final res = await api.getBelgiumAttendanceReport(
      startDate: _ymd(_start),
      endDate: _ymd(_end),
    );
    return extractList(res, const [
      'rows',
      'records',
      'report',
      'items',
      'data',
      'attendance',
    ]);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _pickStart() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _start,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() {
      _start = picked;
      if (_end.isBefore(_start)) _end = _start;
      _future = _load();
    });
  }

  Future<void> _pickEnd() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _end,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() {
      _end = picked.isBefore(_start) ? _start : picked;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Belgium compliance')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _pickStart,
                    child: Text('From ${_ymd(_start)}'),
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _pickEnd,
                    child: Text('To ${_ymd(_end)}'),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: FutureBuilder<List<Map<String, dynamic>>>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  if (snapshot.hasError) {
                    final err = snapshot.error!;
                    final msg = isModuleDisabled(err)
                        ? moduleDisabledMessage('Belgium compliance report')
                        : err.toString().toLowerCase().contains('permission')
                            ? 'You do not have permission to view this report.'
                            : err.toString();
                    return ListView(
                      children: [
                        EmptyState(
                          icon: Icons.lock_outline,
                          title: 'Unavailable',
                          subtitle: msg,
                        ),
                      ],
                    );
                  }
                  final rows = snapshot.data ?? const [];
                  if (rows.isEmpty) {
                    return ListView(
                      children: const [
                        SizedBox(height: 80),
                        EmptyState(
                          icon: Icons.flag_outlined,
                          title: 'No rows',
                          subtitle: 'No attendance data for this date range.',
                        ),
                      ],
                    );
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    itemCount: rows.length,
                    itemBuilder: (context, index) {
                      final row = rows[index];
                      final title = (row['user_name'] ??
                              row['username'] ??
                              row['employee'] ??
                              row['date'] ??
                              'Row ${index + 1}')
                          .toString();
                      final subtitle = [
                        if ((row['date'] ?? '').toString().isNotEmpty) row['date'],
                        if ((row['status'] ?? '').toString().isNotEmpty) row['status'],
                        if ((row['hours'] ?? row['total_hours'] ?? '').toString().isNotEmpty)
                          '${row['hours'] ?? row['total_hours']}h',
                        if ((row['compliance'] ?? row['compliant'] ?? '').toString().isNotEmpty)
                          'compliance: ${row['compliance'] ?? row['compliant']}',
                      ].map((e) => e.toString()).join(' · ');
                      return Card(
                        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: ListTile(
                          title: Text(title),
                          subtitle: subtitle.isEmpty ? null : Text(subtitle),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
