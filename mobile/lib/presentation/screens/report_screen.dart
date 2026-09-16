import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/api_provider.dart';

class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  DateTime _start = DateTime.now().subtract(const Duration(days: 30));
  DateTime _end = DateTime.now();
  int? _projectId;
  List<Map<String, dynamic>> _projects = const [];
  Map<String, dynamic>? _summary;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) throw StateError('Not authenticated');
      final projectsRes = await client.getProjects();
      final projects = List<Map<String, dynamic>>.from(
        (projectsRes['projects'] ?? projectsRes['items'] ?? const []) as List,
      );
      setState(() => _projects = projects);
      await _loadSummary();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _fmt(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _loadSummary() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) throw StateError('Not authenticated');
      final summary = await client.getReportSummary(
        startDate: _fmt(_start),
        endDate: _fmt(_end),
        projectId: _projectId,
      );
      setState(() => _summary = summary['summary'] is Map
          ? Map<String, dynamic>.from(summary['summary'] as Map)
          : Map<String, dynamic>.from(summary));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickDate({required bool isStart}) async {
    final initial = isStart ? _start : _end;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _start = picked;
      } else {
        _end = picked;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final hours = _summary?['total_hours'] ?? _summary?['hours'] ?? '-';
    final billable = _summary?['billable_hours'] ?? '-';
    final revenue = _summary?['revenue'] ?? _summary?['estimated_revenue'] ?? '-';

    return Scaffold(
      appBar: AppBar(title: const Text('Reports')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(isStart: true),
                  child: Text('From ${_fmt(_start)}'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(isStart: false),
                  child: Text('To ${_fmt(_end)}'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int?>(
            value: _projectId,
            decoration: const InputDecoration(labelText: 'Project', border: OutlineInputBorder()),
            items: [
              const DropdownMenuItem<int?>(value: null, child: Text('All projects')),
              ..._projects.map((p) {
                final id = (p['id'] as num?)?.toInt();
                return DropdownMenuItem<int?>(
                  value: id,
                  child: Text((p['name'] ?? 'Project $id').toString()),
                );
              }),
            ],
            onChanged: (v) => setState(() => _projectId = v),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _loading ? null : _loadSummary, child: const Text('Run report')),
          const SizedBox(height: 16),
          if (_loading) const Center(child: CircularProgressIndicator()),
          if (_error != null) Text('Error: $_error', style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (!_loading && _summary != null) ...[
            Card(
              child: ListTile(
                title: const Text('Total hours'),
                trailing: Text('$hours'),
              ),
            ),
            Card(
              child: ListTile(
                title: const Text('Billable hours'),
                trailing: Text('$billable'),
              ),
            ),
            Card(
              child: ListTile(
                title: const Text('Revenue est.'),
                trailing: Text('$revenue'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
