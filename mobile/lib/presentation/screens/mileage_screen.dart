import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class MileageScreen extends ConsumerStatefulWidget {
  const MileageScreen({super.key});

  @override
  ConsumerState<MileageScreen> createState() => _MileageScreenState();
}

class _MileageScreenState extends ConsumerState<MileageScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) return const [];
    final res = await api.getMileage(perPage: 50);
    return extractList(res, const ['mileage', 'entries', 'items', 'data']);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _create() async {
    final purposeCtrl = TextEditingController();
    final startCtrl = TextEditingController();
    final endCtrl = TextEditingController();
    final distanceCtrl = TextEditingController();
    final rateCtrl = TextEditingController(text: '0.4');
    DateTime tripDate = DateTime.now();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: const Text('New mileage'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Date: ${_ymd(tripDate)}'),
                    trailing: const Icon(Icons.calendar_today),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: ctx,
                        initialDate: tripDate,
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2100),
                      );
                      if (picked != null) setDialogState(() => tripDate = picked);
                    },
                  ),
                  TextField(
                    controller: purposeCtrl,
                    decoration: const InputDecoration(labelText: 'Purpose *'),
                  ),
                  TextField(
                    controller: startCtrl,
                    decoration: const InputDecoration(labelText: 'Start location *'),
                  ),
                  TextField(
                    controller: endCtrl,
                    decoration: const InputDecoration(labelText: 'End location *'),
                  ),
                  TextField(
                    controller: distanceCtrl,
                    decoration: const InputDecoration(labelText: 'Distance (km) *'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  ),
                  TextField(
                    controller: rateCtrl,
                    decoration: const InputDecoration(labelText: 'Rate per km *'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              FilledButton(
                onPressed: () {
                  if (purposeCtrl.text.trim().isEmpty ||
                      startCtrl.text.trim().isEmpty ||
                      endCtrl.text.trim().isEmpty ||
                      double.tryParse(distanceCtrl.text.trim()) == null ||
                      double.tryParse(rateCtrl.text.trim()) == null) {
                    return;
                  }
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
      await api.createMileage(
        tripDate: _ymd(tripDate),
        purpose: purposeCtrl.text.trim(),
        startLocation: startCtrl.text.trim(),
        endLocation: endCtrl.text.trim(),
        distanceKm: double.parse(distanceCtrl.text.trim()),
        ratePerKm: double.parse(rateCtrl.text.trim()),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Mileage created')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Create failed: $e')));
    } finally {
      purposeCtrl.dispose();
      startCtrl.dispose();
      endCtrl.dispose();
      distanceCtrl.dispose();
      rateCtrl.dispose();
    }
  }

  String _ymd(DateTime d) => d.toIso8601String().split('T')[0];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mileage')),
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
              final msg = isModuleDisabled(snapshot.error!)
                  ? moduleDisabledMessage('Mileage')
                  : snapshot.error.toString();
              return ListView(
                children: [
                  EmptyState(icon: Icons.error_outline, title: 'Unavailable', subtitle: msg),
                ],
              );
            }
            final items = snapshot.data ?? const [];
            if (items.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 80),
                  EmptyState(
                    icon: Icons.directions_car_outlined,
                    title: 'No mileage entries',
                    subtitle: 'Log a trip with the + button.',
                  ),
                ],
              );
            }
            return ListView.builder(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: items.length,
              itemBuilder: (context, index) {
                final m = items[index];
                final purpose = (m['purpose'] ?? 'Trip').toString();
                final date = (m['trip_date'] ?? m['date'] ?? '').toString();
                final distance = (m['distance_km'] ?? m['distance'] ?? '').toString();
                final from = (m['start_location'] ?? '').toString();
                final to = (m['end_location'] ?? '').toString();
                return Card(
                  margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: ListTile(
                    title: Text(purpose),
                    subtitle: Text([
                      if (date.isNotEmpty) date,
                      if (from.isNotEmpty || to.isNotEmpty) '$from → $to',
                    ].join('\n')),
                    isThreeLine: from.isNotEmpty || to.isNotEmpty,
                    trailing: Text('${distance} km'),
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
