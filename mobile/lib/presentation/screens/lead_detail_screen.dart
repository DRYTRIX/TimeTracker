import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';

class LeadDetailScreen extends ConsumerStatefulWidget {
  const LeadDetailScreen({super.key, required this.leadId, this.initialName});

  final int leadId;
  final String? initialName;

  @override
  ConsumerState<LeadDetailScreen> createState() => _LeadDetailScreenState();
}

class _LeadDetailScreenState extends ConsumerState<LeadDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _busy = false;

  static const _statuses = ['new', 'contacted', 'qualified', 'converted', 'lost'];

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');
    final res = await api.getLead(widget.leadId);
    if (res['lead'] is Map) {
      return Map<String, dynamic>.from(res['lead'] as Map);
    }
    return Map<String, dynamic>.from(res);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  String _displayName(Map<String, dynamic> lead) {
    final full = (lead['full_name'] ?? '').toString().trim();
    if (full.isNotEmpty) return full;
    final parts = [lead['first_name'], lead['last_name']]
        .where((v) => v != null && v.toString().trim().isNotEmpty)
        .map((v) => v.toString())
        .join(' ')
        .trim();
    if (parts.isNotEmpty) return parts;
    return widget.initialName ?? 'Lead';
  }

  Future<void> _edit() async {
    final lead = await _future;
    final firstCtrl = TextEditingController(text: (lead['first_name'] ?? '').toString());
    final lastCtrl = TextEditingController(text: (lead['last_name'] ?? '').toString());
    final emailCtrl = TextEditingController(text: (lead['email'] ?? '').toString());
    final companyCtrl = TextEditingController(text: (lead['company_name'] ?? '').toString());
    var status = (lead['status'] ?? 'new').toString();
    if (!_statuses.contains(status)) status = _statuses.first;

    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setLocal) => AlertDialog(
            title: const Text('Edit lead'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: firstCtrl,
                    decoration: const InputDecoration(labelText: 'First name'),
                  ),
                  TextField(
                    controller: lastCtrl,
                    decoration: const InputDecoration(labelText: 'Last name'),
                  ),
                  TextField(
                    controller: emailCtrl,
                    decoration: const InputDecoration(labelText: 'Email'),
                  ),
                  TextField(
                    controller: companyCtrl,
                    decoration: const InputDecoration(labelText: 'Company'),
                  ),
                  DropdownButtonFormField<String>(
                    value: status,
                    decoration: const InputDecoration(labelText: 'Status'),
                    items: _statuses
                        .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) setLocal(() => status = v);
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
      setState(() => _busy = true);
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.updateLead(
        widget.leadId,
        firstName: firstCtrl.text.trim(),
        lastName: lastCtrl.text.trim(),
        email: emailCtrl.text.trim().isEmpty ? null : emailCtrl.text.trim(),
        companyName: companyCtrl.text.trim().isEmpty ? null : companyCtrl.text.trim(),
        status: status,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Lead updated')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      firstCtrl.dispose();
      lastCtrl.dispose();
      emailCtrl.dispose();
      companyCtrl.dispose();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _convert({required bool toDeal}) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(toDeal ? 'Convert to deal' : 'Convert to client'),
        content: Text(
          toDeal
              ? 'Create a deal from this lead?'
              : 'Create a client from this lead?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Convert')),
        ],
      ),
    );
    if (confirm != true) return;
    setState(() => _busy = true);
    try {
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      if (toDeal) {
        await api.convertLeadToDeal(widget.leadId);
      } else {
        await api.convertLeadToClient(widget.leadId);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(toDeal ? 'Converted to deal' : 'Converted to client')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.initialName ?? 'Lead'),
        actions: [
          IconButton(
            tooltip: 'Edit',
            onPressed: _busy ? null : _edit,
            icon: const Icon(Icons.edit_outlined),
          ),
          PopupMenuButton<String>(
            enabled: !_busy,
            onSelected: (v) {
              if (v == 'client') _convert(toDeal: false);
              if (v == 'deal') _convert(toDeal: true);
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'client', child: Text('Convert to client')),
              PopupMenuItem(value: 'deal', child: Text('Convert to deal')),
            ],
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
            final lead = snapshot.data!;
            final name = _displayName(lead);
            return ListView(
              padding: const EdgeInsets.all(AppSpacing.md),
              children: [
                Card(
                  child: ListTile(
                    title: Text(name, style: Theme.of(context).textTheme.titleLarge),
                    subtitle: Text(
                      [
                        if (lead['status'] != null) lead['status'].toString(),
                        if (lead['email'] != null) lead['email'].toString(),
                        if (lead['company_name'] != null) lead['company_name'].toString(),
                      ].join(' · '),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
