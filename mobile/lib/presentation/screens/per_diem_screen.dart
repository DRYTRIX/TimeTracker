import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class PerDiemScreen extends ConsumerStatefulWidget {
  const PerDiemScreen({super.key});

  @override
  ConsumerState<PerDiemScreen> createState() => _PerDiemScreenState();
}

class _PerDiemScreenState extends ConsumerState<PerDiemScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');
    final entriesRes = await api.getPerDiems(perPage: 50);
    return extractList(entriesRes, const ['per_diems', 'entries', 'items', 'data']);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _create() async {
    final purposeCtrl = TextEditingController();
    final countryCtrl = TextEditingController(text: 'BE');
    final fullRateCtrl = TextEditingController(text: '50');
    final halfRateCtrl = TextEditingController(text: '25');
    final notesCtrl = TextEditingController();
    DateTime start = DateTime.now();
    DateTime end = DateTime.now();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: const Text('New per diem'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: purposeCtrl,
                    decoration: const InputDecoration(labelText: 'Trip purpose *'),
                    autofocus: true,
                  ),
                  TextField(
                    controller: countryCtrl,
                    decoration: const InputDecoration(labelText: 'Country *'),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Start: ${start.toIso8601String().split('T')[0]}'),
                    trailing: const Icon(Icons.calendar_today),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: ctx,
                        initialDate: start,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                      );
                      if (picked != null) setDialogState(() => start = picked);
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('End: ${end.toIso8601String().split('T')[0]}'),
                    trailing: const Icon(Icons.calendar_today),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: ctx,
                        initialDate: end,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                      );
                      if (picked != null) setDialogState(() => end = picked);
                    },
                  ),
                  TextField(
                    controller: fullRateCtrl,
                    decoration: const InputDecoration(labelText: 'Full day rate *'),
                    keyboardType: TextInputType.number,
                  ),
                  TextField(
                    controller: halfRateCtrl,
                    decoration: const InputDecoration(labelText: 'Half day rate *'),
                    keyboardType: TextInputType.number,
                  ),
                  TextField(
                    controller: notesCtrl,
                    decoration: const InputDecoration(labelText: 'Notes'),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Create')),
            ],
          ),
        ),
      );
      if (ok != true) return;
      if (purposeCtrl.text.trim().isEmpty || countryCtrl.text.trim().isEmpty) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createPerDiem(
        tripPurpose: purposeCtrl.text.trim(),
        startDate: start.toIso8601String().split('T')[0],
        endDate: end.toIso8601String().split('T')[0],
        country: countryCtrl.text.trim(),
        fullDayRate: num.parse(fullRateCtrl.text.trim()),
        halfDayRate: num.parse(halfRateCtrl.text.trim()),
        notes: notesCtrl.text.trim().isEmpty ? null : notesCtrl.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Per diem created')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Create failed: $e')));
    } finally {
      purposeCtrl.dispose();
      countryCtrl.dispose();
      fullRateCtrl.dispose();
      halfRateCtrl.dispose();
      notesCtrl.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Per diem')),
      floatingActionButton: FloatingActionButton(
        onPressed: _create,
        child: const Icon(Icons.add),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return EmptyState(
                icon: Icons.error_outline,
                title: 'Could not load per diems',
                subtitle: snapshot.error.toString(),
              );
            }
            final items = snapshot.data ?? const [];
            if (items.isEmpty) {
              return const EmptyState(
                icon: Icons.restaurant_outlined,
                title: 'No per diem claims',
                subtitle: 'Create a claim with the + button',
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.sm),
              itemBuilder: (context, i) {
                final e = items[i];
                final id = (e['id'] as num?)?.toInt();
                return Card(
                  child: ListTile(
                    title: Text((e['trip_purpose'] ?? e['purpose'] ?? 'Per diem').toString()),
                    subtitle: Text(
                      '${e['start_date'] ?? ''} → ${e['end_date'] ?? ''} · ${e['country'] ?? ''}',
                    ),
                    trailing: id == null
                        ? null
                        : IconButton(
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () async {
                              final api = await ref.read(apiClientProvider.future);
                              if (api == null) return;
                              await api.deletePerDiem(id);
                              await _refresh();
                            },
                          ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
