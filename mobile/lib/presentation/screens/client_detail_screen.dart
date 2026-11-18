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
    List<Map<String, dynamic>> notes = const [];
    try {
      final notesRes = await api.getClientNotes(widget.clientId);
      notes = extractList(notesRes, const ['notes', 'client_notes', 'items', 'data']);
    } catch (_) {
      // Notes endpoint may be unavailable when CRM notes module is off.
      notes = const [];
    }
    return _ClientDetailData(client: client, contacts: contacts, notes: notes);
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _addContact() async {
    final firstCtrl = TextEditingController();
    final lastCtrl = TextEditingController();
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
                if (firstCtrl.text.trim().isEmpty || lastCtrl.text.trim().isEmpty) return;
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
        firstName: firstCtrl.text.trim(),
        lastName: lastCtrl.text.trim(),
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
      firstCtrl.dispose();
      lastCtrl.dispose();
      emailCtrl.dispose();
      phoneCtrl.dispose();
      roleCtrl.dispose();
    }
  }

  Future<void> _addNote() async {
    final contentCtrl = TextEditingController();
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Add note'),
          content: TextField(
            controller: contentCtrl,
            decoration: const InputDecoration(labelText: 'Note *'),
            maxLines: 4,
            autofocus: true,
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      );
      if (ok != true) return;
      final content = contentCtrl.text.trim();
      if (content.isEmpty) return;
      final api = await ref.read(apiClientProvider.future);
      if (api == null) return;
      await api.createClientNote(widget.clientId, content: content);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Note added')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    } finally {
      contentCtrl.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.clientName ?? 'Client'),
        actions: [
          IconButton(
            tooltip: 'Add note',
            onPressed: _addNote,
            icon: const Icon(Icons.note_add_outlined),
          ),
        ],
      ),
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
                    final full = (contact['full_name'] ?? '').toString().trim();
                    final parts = [
                      contact['first_name'],
                      contact['last_name'],
                    ].where((v) => v != null && v.toString().trim().isNotEmpty);
                    final cName = full.isNotEmpty
                        ? full
                        : (parts.map((v) => v.toString()).join(' ').trim().isNotEmpty
                            ? parts.map((v) => v.toString()).join(' ').trim()
                            : 'Contact');
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
                const SizedBox(height: AppSpacing.md),
                Text('Notes', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: AppSpacing.sm),
                if (data.notes.isEmpty)
                  const EmptyState(
                    icon: Icons.notes_outlined,
                    title: 'No notes',
                    subtitle: 'Add a client note.',
                  )
                else
                  ...data.notes.map((note) {
                    final content = (note['content'] ?? note['body'] ?? note['note'] ?? '').toString();
                    return Card(
                      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: ListTile(title: Text(content)),
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
  const _ClientDetailData({
    required this.client,
    required this.contacts,
    this.notes = const [],
  });
  final Map<String, dynamic> client;
  final List<Map<String, dynamic>> contacts;
  final List<Map<String, dynamic>> notes;
}
