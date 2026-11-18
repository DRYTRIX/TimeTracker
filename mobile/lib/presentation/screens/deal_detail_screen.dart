import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';

class DealDetailScreen extends ConsumerStatefulWidget {
  const DealDetailScreen({super.key, required this.dealId, this.initialName});

  final int dealId;
  final String? initialName;

  @override
  ConsumerState<DealDetailScreen> createState() => _DealDetailScreenState();
}

class _DealDetailScreenState extends ConsumerState<DealDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _saving = false;

  static const _stages = ['lead', 'qualified', 'proposal', 'negotiation', 'won', 'lost'];

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');
    final res = await api.getDeal(widget.dealId);
    if (res['deal'] is Map) {
      return Map<String, dynamic>.from(res['deal'] as Map);
    }
    return Map<String, dynamic>.from(res);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _edit() async {
    final deal = await _future;
    final nameCtrl = TextEditingController(text: (deal['name'] ?? '').toString());
    final valueCtrl = TextEditingController(
      text: deal['value'] != null ? deal['value'].toString() : '',
    );
    var stage = (deal['stage'] ?? deal['status'] ?? 'lead').toString();
    if (!_stages.contains(stage)) stage = _stages.first;

    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setLocal) => AlertDialog(
            title: const Text('Edit deal'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Name'),
                  ),
                  TextField(
                    controller: valueCtrl,
                    decoration: const InputDecoration(labelText: 'Value'),
                    keyboardType: TextInputType.number,
                  ),
                  DropdownButtonFormField<String>(
                    value: stage,
                    decoration: const InputDecoration(labelText: 'Stage'),
                    items: _stages
                        .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) setLocal(() => stage = v);
                    },
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
            ],
          ),
        ),
      );
      if (ok != true) return;
      setState(() => _saving = true);
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      final valueText = valueCtrl.text.trim();
      await api.updateDeal(
        widget.dealId,
        name: nameCtrl.text.trim().isEmpty ? null : nameCtrl.text.trim(),
        value: valueText.isEmpty ? null : num.tryParse(valueText),
        stage: stage,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Deal updated')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      nameCtrl.dispose();
      valueCtrl.dispose();
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.initialName ?? 'Deal'),
        actions: [
          IconButton(
            tooltip: 'Edit',
            onPressed: _saving ? null : _edit,
            icon: const Icon(Icons.edit_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return ListView(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Text('Failed to load: ${snapshot.error}'),
                  ),
                ],
              );
            }
            final d = snapshot.data!;
            final name = (d['name'] ?? widget.initialName ?? 'Deal').toString();
            return ListView(
              padding: const EdgeInsets.all(AppSpacing.md),
              children: [
                Card(
                  child: ListTile(
                    title: Text(name, style: Theme.of(context).textTheme.titleLarge),
                    subtitle: Text(
                      [
                        if ((d['stage'] ?? d['status']) != null) '${d['stage'] ?? d['status']}',
                        if (d['value'] != null) 'Value: ${d['value']}',
                        if (d['client_name'] != null) d['client_name'].toString(),
                      ].join(' · '),
                    ),
                  ),
                ),
                if (d['description'] != null && d['description'].toString().isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.md),
                  Text('Description', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: AppSpacing.sm),
                  Text(d['description'].toString()),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}
