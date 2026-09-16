import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/api_provider.dart';

class ExpenseDetailScreen extends ConsumerStatefulWidget {
  const ExpenseDetailScreen({super.key, required this.expenseId});

  final int expenseId;

  @override
  ConsumerState<ExpenseDetailScreen> createState() => _ExpenseDetailScreenState();
}

class _ExpenseDetailScreenState extends ConsumerState<ExpenseDetailScreen> {
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
    final res = await client.getExpense(widget.expenseId);
    final expense = res['expense'];
    if (expense is Map<String, dynamic>) return expense;
    if (expense is Map) return Map<String, dynamic>.from(expense);
    throw StateError('Expense not found');
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _edit(Map<String, dynamic> expense) async {
    final titleCtrl = TextEditingController(text: (expense['title'] ?? '').toString());
    final categoryCtrl = TextEditingController(text: (expense['category'] ?? '').toString());
    final amountCtrl = TextEditingController(text: (expense['amount'] ?? '').toString());
    var billable = expense['billable'] == true;
    var reimbursable = expense['reimbursable'] != false;

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Edit Expense'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Title')),
                TextField(controller: categoryCtrl, decoration: const InputDecoration(labelText: 'Category')),
                TextField(
                  controller: amountCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Amount'),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Billable'),
                  value: billable,
                  onChanged: (v) => setDialogState(() => billable = v),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Reimbursable'),
                  value: reimbursable,
                  onChanged: (v) => setDialogState(() => reimbursable = v),
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
    if (saved != true) return;

    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      final amount = double.tryParse(amountCtrl.text.trim());
      await client.updateExpense(widget.expenseId, {
        'title': titleCtrl.text.trim(),
        'category': categoryCtrl.text.trim(),
        if (amount != null) 'amount': amount,
        'billable': billable,
        'reimbursable': reimbursable,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Expense updated')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _approve() async {
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.approveExpense(widget.expenseId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Expense approved')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Approve failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _reject() async {
    final reasonCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reject Expense'),
        content: TextField(controller: reasonCtrl, decoration: const InputDecoration(labelText: 'Reason'), autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Reject')),
        ],
      ),
    );
    if (ok != true || reasonCtrl.text.trim().isEmpty) return;
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.rejectExpense(widget.expenseId, reason: reasonCtrl.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Expense rejected')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Reject failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Expense'),
        content: const Text('Delete this expense?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.deleteExpense(widget.expenseId);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Delete failed: $e')));
      setState(() => _saving = false);
    }
  }

  Future<void> _markReimbursed(Map<String, dynamic> expense) async {
    setState(() => _saving = true);
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.updateExpense(widget.expenseId, {'reimbursed': true, 'status': 'reimbursed'});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Marked reimbursed')));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Expense'),
        actions: [
          if (_saving)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
            ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Text('Error: ${snap.error}'));
          }
          final expense = snap.data!;
          final status = (expense['status'] ?? 'pending').toString();
          final title = (expense['title'] ?? 'Expense').toString();
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text('${expense['amount'] ?? '-'} · ${expense['category'] ?? ''}'),
              Text('Date: ${expense['expense_date'] ?? '-'}'),
              Text('Status: $status'),
              Text('Billable: ${expense['billable'] == true ? 'Yes' : 'No'}'),
              Text('Reimbursable: ${expense['reimbursable'] == true ? 'Yes' : 'No'}'),
              if (expense['project_name'] != null) Text('Project: ${expense['project_name']}'),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton(onPressed: _saving ? null : () => _edit(expense), child: const Text('Edit')),
                  if (status == 'pending') ...[
                    OutlinedButton(onPressed: _saving ? null : _approve, child: const Text('Approve')),
                    OutlinedButton(onPressed: _saving ? null : _reject, child: const Text('Reject')),
                  ],
                  if (status == 'approved' && expense['reimbursed'] != true)
                    OutlinedButton(onPressed: _saving ? null : () => _markReimbursed(expense), child: const Text('Mark reimbursed')),
                  TextButton(onPressed: _saving ? null : _delete, child: const Text('Delete')),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}
