import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';

import '../providers/api_provider.dart';
import '../utils/api_list.dart';
import '../widgets/empty_state.dart';

class ClientDetailScreen extends ConsumerStatefulWidget {
  const ClientDetailScreen({
    super.key,
    required this.clientId,
    this.clientName,
  });

  final int clientId;
  final String? clientName;

  @override
  ConsumerState<ClientDetailScreen> createState() => _ClientDetailScreenState();
}

class _ClientDetailScreenState extends ConsumerState<ClientDetailScreen> {
  late Future<_ClientDetailData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_ClientDetailData> _load() async {
    final api = await ref.read(apiClientProvider.future);
    if (api == null) throw StateError('Not authenticated');
    final clientRes = await api.getClient(widget.clientId);
    Map<String, dynamic> client = {};
    if (clientRes['client'] is Map) {
      client = Map<String, dynamic>.from(clientRes['client'] as Map);
    } else {
      client = Map<String, dynamic>.from(clientRes);
    }
    final contactsRes = await api.getContacts(widget.clientId);
    final contacts = extractList(contactsRes, const ['contacts', 'items', 'data']);
    return _ClientDetailData(client: client, contacts: contacts);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _addContact() async {
    final nameCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final roleCtrl = TextEditingController();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Add contact'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(labelText: 'Name *'),
                  autofocus: true,
                ),
                TextField(
                  controller: emailCtrl,
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                TextField(
                  controller: phoneCtrl,
                  decoration: const InputDecoration(labelText: 'Phone'),
                ),
                TextField(
                  controller: roleCtrl,
                  decoration: const InputDecoration(labelText: 'Role'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(
              onPressed: () {
                if (nameCtrl.text.trim().isEmpty) return;
                Navigator.pop(ctx, true);
              },
              child: const Text('Add'),
            ),
          ],
        ),
      );
      if (ok != true) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createContact(
        widget.clientId,
        name: nameCtrl.text.trim(),
        email: emailCtrl.text.trim().isEmpty ? null : emailCtrl.text.trim(),
        phone: phoneCtrl.text.trim().isEmpty ? null : phoneCtrl.text.trim(),
        role: roleCtrl.text.trim().isEmpty ? null : roleCtrl.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Contact added')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      nameCtrl.dispose();
      emailCtrl.dispose();
      phoneCtrl.dispose();
      roleCtrl.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.clientName ?? 'Client')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addContact,
        icon: const Icon(Icons.person_add),
        label: const Text('Add contact'),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<_ClientDetailData>(
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
            final data = snapshot.data!;
            final c = data.client;
            final name = (c['name'] ?? widget.clientName ?? 'Client').toString();
            final email = (c['email'] ?? '').toString();
            final phone = (c['phone'] ?? '').toString();
            final address = (c['address'] ?? '').toString();

            return ListView(
              padding: const EdgeInsets.all(AppSpacing.md),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(name, style: Theme.of(context).textTheme.titleLarge),
                        if (email.isNotEmpty) ...[
                          const SizedBox(height: AppSpacing.xs),
                          Text(email),
                        ],
                        if (phone.isNotEmpty) Text(phone),
                        if (address.isNotEmpty) Text(address),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                Text('Contacts', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: AppSpacing.sm),
                if (data.contacts.isEmpty)
                  const EmptyState(
                    icon: Icons.contact_mail_outlined,
                    title: 'No contacts',
                    subtitle: 'Add a contact for this client.',
                  )
                else
                  ...data.contacts.map((contact) {
                    final cName = (contact['name'] ?? 'Contact').toString();
                    final cEmail = (contact['email'] ?? '').toString();
                    final cRole = (contact['role'] ?? '').toString();
                    return Card(
                      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: ListTile(
                        title: Text(cName),
                        subtitle: Text([
                          if (cRole.isNotEmpty) cRole,
                          if (cEmail.isNotEmpty) cEmail,
                        ].join(' · ')),
                      ),
                    );
                  }),
                const SizedBox(height: 72),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ClientDetailData {
  const _ClientDetailData({required this.client, required this.contacts});
  final Map<String, dynamic> client;
  final List<Map<String, dynamic>> contacts;
}
