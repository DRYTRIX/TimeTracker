import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class CrmHubScreen extends ConsumerStatefulWidget {
  const CrmHubScreen({super.key});

  @override
  ConsumerState<CrmHubScreen> createState() => _CrmHubScreenState();
}

class _CrmHubScreenState extends ConsumerState<CrmHubScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  late Future<_CrmData> _future;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _future = _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<_CrmData> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');

    List<Map<String, dynamic>> deals = const [];
    List<Map<String, dynamic>> leads = const [];
    List<Map<String, dynamic>> quotes = const [];
    String? dealsError;
    String? leadsError;
    String? quotesError;

    try {
      final res = await api.getDeals(perPage: 50);
      deals = extractList(res, const ['deals', 'items', 'data']);
    } catch (e) {
      dealsError = isModuleDisabled(e)
          ? moduleDisabledMessage('CRM deals')
          : e.toString();
    }
    try {
      final res = await api.getLeads(perPage: 50);
      leads = extractList(res, const ['leads', 'items', 'data']);
    } catch (e) {
      leadsError = isModuleDisabled(e)
          ? moduleDisabledMessage('CRM leads')
          : e.toString();
    }
    try {
      final res = await api.getQuotes(perPage: 50);
      quotes = extractList(res, const ['quotes', 'items', 'data']);
    } catch (e) {
      quotesError = isModuleDisabled(e)
          ? moduleDisabledMessage('CRM quotes')
          : e.toString();
    }

    return _CrmData(
      deals: deals,
      leads: leads,
      quotes: quotes,
      dealsError: dealsError,
      leadsError: leadsError,
      quotesError: quotesError,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _createDeal() async {
    final nameCtrl = TextEditingController();
    final valueCtrl = TextEditingController();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('New deal'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'Name *'),
                autofocus: true,
              ),
              TextField(
                controller: valueCtrl,
                decoration: const InputDecoration(labelText: 'Value'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: () {
                if (nameCtrl.text.trim().isEmpty) return;
                Navigator.pop(ctx, true);
              },
              child: const Text('Create'),
            ),
          ],
        ),
      );
      if (ok != true) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createDeal(
        name: nameCtrl.text.trim(),
        value: double.tryParse(valueCtrl.text.trim()),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Deal created')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      final msg = isModuleDisabled(e) ? moduleDisabledMessage('CRM') : 'Create failed: $e';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    } finally {
      nameCtrl.dispose();
      valueCtrl.dispose();
    }
  }

  Future<void> _createLead() async {
    final firstCtrl = TextEditingController();
    final lastCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final companyCtrl = TextEditingController();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('New lead'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: firstCtrl,
                decoration: const InputDecoration(labelText: 'First name *'),
                autofocus: true,
              ),
              TextField(
                controller: lastCtrl,
                decoration: const InputDecoration(labelText: 'Last name *'),
              ),
              TextField(
                controller: emailCtrl,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: companyCtrl,
                decoration: const InputDecoration(labelText: 'Company'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: () {
                if (firstCtrl.text.trim().isEmpty || lastCtrl.text.trim().isEmpty) return;
                Navigator.pop(ctx, true);
              },
              child: const Text('Create'),
            ),
          ],
        ),
      );
      if (ok != true) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createLead(
        firstName: firstCtrl.text.trim(),
        lastName: lastCtrl.text.trim(),
        email: emailCtrl.text.trim().isEmpty ? null : emailCtrl.text.trim(),
        companyName: companyCtrl.text.trim().isEmpty ? null : companyCtrl.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Lead created')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      final msg = isModuleDisabled(e) ? moduleDisabledMessage('CRM') : 'Create failed: $e';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    } finally {
      firstCtrl.dispose();
      lastCtrl.dispose();
      emailCtrl.dispose();
      companyCtrl.dispose();
    }
  }

  Widget _listBody({
    required List<Map<String, dynamic>> items,
    required String? error,
    required String emptyTitle,
    required String Function(Map<String, dynamic>) titleOf,
    required String Function(Map<String, dynamic>) subtitleOf,
    VoidCallback? onCreate,
  }) {
    if (error != null) {
      return ListView(
        children: [
          EmptyState(
            icon: Icons.block,
            title: 'Unavailable',
            subtitle: error,
          ),
        ],
      );
    }
    if (items.isEmpty) {
      return ListView(
        children: [
          EmptyState(
            icon: Icons.inbox_outlined,
            title: emptyTitle,
            action: onCreate == null
                ? null
                : FilledButton(onPressed: onCreate, child: const Text('Create')),
          ),
        ],
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return Card(
          margin: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: ListTile(
            title: Text(titleOf(item)),
            subtitle: Text(subtitleOf(item)),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('CRM'),
        bottom: TabBar(
          controller: _tabs,
          tabs: const [
            Tab(text: 'Deals'),
            Tab(text: 'Leads'),
            Tab(text: 'Quotes'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'New deal',
            onPressed: _createDeal,
            icon: const Icon(Icons.handshake_outlined),
          ),
          IconButton(
            tooltip: 'New lead',
            onPressed: _createLead,
            icon: const Icon(Icons.person_add_alt_1),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<_CrmData>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              final msg = isModuleDisabled(snapshot.error!)
                  ? moduleDisabledMessage('CRM')
                  : snapshot.error.toString();
              return ListView(
                children: [
                  EmptyState(icon: Icons.error_outline, title: 'Failed to load', subtitle: msg),
                ],
              );
            }
            final data = snapshot.data!;
            return TabBarView(
              controller: _tabs,
              children: [
                _listBody(
                  items: data.deals,
                  error: data.dealsError,
                  emptyTitle: 'No deals',
                  titleOf: (d) => (d['name'] ?? 'Deal').toString(),
                  subtitleOf: (d) =>
                      '${d['stage'] ?? d['status'] ?? ''} · ${d['value'] ?? ''}'.trim(),
                  onCreate: _createDeal,
                ),
                _listBody(
                  items: data.leads,
                  error: data.leadsError,
                  emptyTitle: 'No leads',
                  titleOf: (d) => (d['name'] ?? 'Lead').toString(),
                  subtitleOf: (d) =>
                      '${d['company'] ?? ''} · ${d['email'] ?? d['status'] ?? ''}'.trim(),
                  onCreate: _createLead,
                ),
                _listBody(
                  items: data.quotes,
                  error: data.quotesError,
                  emptyTitle: 'No quotes',
                  titleOf: (d) => (d['title'] ?? d['name'] ?? d['quote_number'] ?? 'Quote').toString(),
                  subtitleOf: (d) =>
                      '${d['status'] ?? ''} · ${d['total'] ?? d['amount'] ?? ''}'.trim(),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CrmData {
  const _CrmData({
    required this.deals,
    required this.leads,
    required this.quotes,
    this.dealsError,
    this.leadsError,
    this.quotesError,
  });

  final List<Map<String, dynamic>> deals;
  final List<Map<String, dynamic>> leads;
  final List<Map<String, dynamic>> quotes;
  final String? dealsError;
  final String? leadsError;
  final String? quotesError;
}
