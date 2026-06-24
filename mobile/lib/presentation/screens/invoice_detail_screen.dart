import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../providers/api_provider.dart';

class InvoiceDetailScreen extends ConsumerStatefulWidget {
  const InvoiceDetailScreen({super.key, required this.invoiceId});

  final int invoiceId;

  @override
  ConsumerState<InvoiceDetailScreen> createState() => _InvoiceDetailScreenState();
}

class _InvoiceDetailScreenState extends ConsumerState<InvoiceDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final client = await ref.read(apiClientProvider.future);
    if (client == null) throw StateError('Not authenticated');
    final res = await client.getInvoice(widget.invoiceId);
    final invoice = res['invoice'];
    if (invoice is Map<String, dynamic>) return invoice;
    if (invoice is Map) return Map<String, dynamic>.from(invoice);
    throw StateError('Invoice not found');
  }

  Future<void> _refresh() async {
    setState(() {
      _future = _load();
    });
    await _future;
  }

  Future<void> _updateStatus(String status, {double? amountPaid}) async {
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      final payload = <String, dynamic>{'status': status};
      if (amountPaid != null) payload['amount_paid'] = amountPaid;
      await client.updateInvoice(widget.invoiceId, payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Status updated to $status')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _sharePdf() async {
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      final bytes = await client.downloadInvoicePdf(widget.invoiceId);
      final dir = await getTemporaryDirectory();
      final invoice = await _future;
      final number = (invoice['invoice_number'] ?? widget.invoiceId).toString();
      final file = File('${dir.path}/$number.pdf');
      await file.writeAsBytes(Uint8List.fromList(bytes));
      await Share.shareXFiles([XFile(file.path)], text: 'Invoice $number');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('PDF export failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _editInvoice(Map<String, dynamic> invoice) async {
    final notesController = TextEditingController(text: (invoice['notes'] ?? '').toString());
    final termsController = TextEditingController(text: (invoice['terms'] ?? '').toString());
    final taxController = TextEditingController(text: (invoice['tax_rate'] ?? 0).toString());
    DateTime dueDate = DateTime.tryParse((invoice['due_date'] ?? '').toString()) ?? DateTime.now().add(const Duration(days: 30));

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Edit Invoice'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: notesController,
                  decoration: const InputDecoration(labelText: 'Notes'),
                  maxLines: 3,
                ),
                TextField(
                  controller: termsController,
                  decoration: const InputDecoration(labelText: 'Terms'),
                  maxLines: 2,
                ),
                TextField(
                  controller: taxController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Tax rate %'),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: Text('Due: ${dueDate.toIso8601String().split('T')[0]}')),
                    TextButton(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: ctx,
                          initialDate: dueDate,
                          firstDate: DateTime(2000),
                          lastDate: DateTime(2100),
                        );
                        if (picked != null) setDialogState(() => dueDate = picked);
                      },
                      child: const Text('Change'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (saved != true) return;

    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.updateInvoice(widget.invoiceId, {
        'notes': notesController.text.trim(),
        'terms': termsController.text.trim(),
        'tax_rate': double.tryParse(taxController.text.trim()) ?? 0,
        'due_date': dueDate.toIso8601String().split('T')[0],
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Invoice updated')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
    } finally {
      notesController.dispose();
      termsController.dispose();
      taxController.dispose();
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _editLineItems(List<Map<String, dynamic>> items) async {
    final rows = items
        .map(
          (item) => _LineItemRow(
            description: (item['description'] ?? '').toString(),
            quantity: (item['quantity'] as num?)?.toDouble() ?? 1,
            unitPrice: (item['unit_price'] as num?)?.toDouble() ?? 0,
          ),
        )
        .toList();
    if (rows.isEmpty) rows.add(_LineItemRow());

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Edit Line Items'),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                children: [
                  for (var i = 0; i < rows.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Column(
                        children: [
                          TextField(
                            decoration: const InputDecoration(labelText: 'Description'),
                            controller: rows[i].descriptionController,
                          ),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  decoration: const InputDecoration(labelText: 'Qty'),
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  controller: rows[i].quantityController,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  decoration: const InputDecoration(labelText: 'Unit price'),
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  controller: rows[i].unitPriceController,
                                ),
                              ),
                              IconButton(
                                onPressed: rows.length > 1
                                    ? () => setDialogState(() => rows.removeAt(i))
                                    : null,
                                icon: const Icon(Icons.delete_outline),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  TextButton.icon(
                    onPressed: () => setDialogState(() => rows.add(_LineItemRow())),
                    icon: const Icon(Icons.add),
                    label: const Text('Add line'),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    for (final row in rows) {
      row.dispose();
    }
    if (saved != true) return;

    final payload = rows
        .where((r) => r.descriptionController.text.trim().isNotEmpty)
        .map(
          (r) => {
            'description': r.descriptionController.text.trim(),
            'quantity': double.tryParse(r.quantityController.text.trim()) ?? 1,
            'unit_price': double.tryParse(r.unitPriceController.text.trim()) ?? 0,
          },
        )
        .toList();

    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.setInvoiceItems(widget.invoiceId, payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Line items updated')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _generateFromTime(Map<String, dynamic> invoice) async {
    final projectId = (invoice['project_id'] as num?)?.toInt();
    if (projectId == null) return;

    final client = await ref.read(apiClientProvider.future);
    if (client == null) return;

    DateTime start = DateTime.now().subtract(const Duration(days: 30));
    DateTime end = DateTime.now();
    final pickedRange = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      initialDateRange: DateTimeRange(start: start, end: end),
    );
    if (pickedRange == null) return;

    setState(() => _saving = true);
    try {
      final entriesRes = await client.getTimeEntries(
        projectId: projectId,
        startDate: pickedRange.start.toIso8601String().split('T')[0],
        endDate: pickedRange.end.toIso8601String().split('T')[0],
        billable: true,
        perPage: 200,
      );
      final entries = List<Map<String, dynamic>>.from(entriesRes['time_entries'] ?? const []);
      if (entries.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No billable entries in range')));
        return;
      }
      final ids = entries.map((e) => (e['id'] as num).toInt()).toList();
      await client.generateInvoiceFromTime(widget.invoiceId, timeEntryIds: ids);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Generated items from ${ids.length} time entries')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Generate failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _requestApproval(Map<String, dynamic> invoice) async {
    final client = await ref.read(apiClientProvider.future);
    if (client == null) return;
    List<Map<String, dynamic>> users = [];
    try {
      users = await client.getUsers();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not load users: $e')));
      return;
    }
    if (users.isEmpty) return;

    int? selectedApprover = (users.first['id'] as num?)?.toInt();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Request approval'),
          content: DropdownButtonFormField<int>(
            value: selectedApprover,
            decoration: const InputDecoration(labelText: 'Approver'),
            items: users
                .map(
                  (u) => DropdownMenuItem<int>(
                    value: (u['id'] as num).toInt(),
                    child: Text((u['display_name'] ?? u['username'] ?? u['id']).toString()),
                  ),
                )
                .toList(),
            onChanged: (v) => setDialogState(() => selectedApprover = v),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Request')),
          ],
        ),
      ),
    );
    if (confirmed != true || selectedApprover == null) return;

    setState(() => _saving = true);
    try {
      await client.requestInvoiceApproval(widget.invoiceId, [selectedApprover!]);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Approval requested')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Request failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Invoice'),
        actions: [
          if (_saving) const Padding(
            padding: EdgeInsets.all(16),
            child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return ListView(children: const [SizedBox(height: 120), Center(child: CircularProgressIndicator())]);
            }
            if (snapshot.hasError) {
              return ListView(
                children: [
                  const SizedBox(height: 80),
                  Center(child: Text('Error: ${snapshot.error}')),
                ],
              );
            }
            final invoice = snapshot.data ?? {};
            final items = List<Map<String, dynamic>>.from(invoice['items'] ?? const []);
            final payments = List<Map<String, dynamic>>.from(invoice['payments'] ?? const []);
            final status = (invoice['status'] ?? 'draft').toString();
            final total = (invoice['total_amount'] as num?)?.toDouble();
            final isDraft = status == 'draft';

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  (invoice['invoice_number'] ?? 'Invoice').toString(),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                Text((invoice['client_name'] ?? '').toString()),
                if (invoice['project_name'] != null) Text('Project: ${invoice['project_name']}'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    Chip(label: Text('Status: $status')),
                    if (total != null) Chip(label: Text('Total: ${total.toStringAsFixed(2)}')),
                  ],
                ),
                const SizedBox(height: 16),
                Text('Line items', style: Theme.of(context).textTheme.titleMedium),
                if (items.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Text('No line items yet'),
                  )
                else
                  ...items.map(
                    (item) => ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text((item['description'] ?? '').toString()),
                      subtitle: Text(
                        '${item['quantity']} × ${item['unit_price']} = ${item['total_amount']}',
                      ),
                    ),
                  ),
                if (payments.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text('Payments', style: Theme.of(context).textTheme.titleMedium),
                  ...payments.map(
                    (p) => ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text('${p['amount']} — ${p['status'] ?? ''}'),
                      subtitle: Text((p['payment_date'] ?? p['created_at'] ?? '').toString()),
                    ),
                  ),
                ],
                const SizedBox(height: 24),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: _sharePdf,
                      icon: const Icon(Icons.picture_as_pdf_outlined),
                      label: const Text('Share PDF'),
                    ),
                    if (isDraft) ...[
                      OutlinedButton.icon(
                        onPressed: () => _editInvoice(invoice),
                        icon: const Icon(Icons.edit_outlined),
                        label: const Text('Edit'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _editLineItems(items),
                        icon: const Icon(Icons.list_alt),
                        label: const Text('Line items'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _generateFromTime(invoice),
                        icon: const Icon(Icons.schedule),
                        label: const Text('From time'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _requestApproval(invoice),
                        icon: const Icon(Icons.how_to_reg_outlined),
                        label: const Text('Request approval'),
                      ),
                    ],
                    if (status != 'sent' && status != 'paid' && status != 'cancelled')
                      FilledButton(
                        onPressed: () => _updateStatus('sent'),
                        child: const Text('Mark sent'),
                      ),
                    if (total != null && total > 0 && status != 'paid' && status != 'cancelled')
                      FilledButton.tonal(
                        onPressed: () => _updateStatus('paid', amountPaid: total),
                        child: const Text('Mark paid'),
                      ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _LineItemRow {
  _LineItemRow({String description = '', double quantity = 1, double unitPrice = 0})
      : descriptionController = TextEditingController(text: description),
        quantityController = TextEditingController(text: quantity.toString()),
        unitPriceController = TextEditingController(text: unitPrice.toString());

  final TextEditingController descriptionController;
  final TextEditingController quantityController;
  final TextEditingController unitPriceController;

  void dispose() {
    descriptionController.dispose();
    quantityController.dispose();
    unitPriceController.dispose();
  }
}
