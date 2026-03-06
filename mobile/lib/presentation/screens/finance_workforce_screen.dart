import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/api_provider.dart';
import '../providers/finance_workforce_providers.dart';

class FinanceWorkforceScreen extends ConsumerStatefulWidget {
  const FinanceWorkforceScreen({super.key});

  @override
  ConsumerState<FinanceWorkforceScreen> createState() => _FinanceWorkforceScreenState();
}

class _FinanceWorkforceScreenState extends ConsumerState<FinanceWorkforceScreen> {
  static const int _pageSize = 8;
  late Future<_FinanceWorkforceData> _future;
  final TextEditingController _invoiceFilterController = TextEditingController();
  final TextEditingController _expenseFilterController = TextEditingController();
  final TextEditingController _timeOffFilterController = TextEditingController();
  bool _canApprove = false;
  String _invoiceFilter = '';
  String _expenseFilter = '';
  String _timeOffFilter = '';
  int _invoicePage = 1;
  int _expensePage = 1;
  int _invoiceTotalPagesState = 1;
  int _expenseTotalPagesState = 1;
  int _invoiceVisible = _pageSize;
  int _expenseVisible = _pageSize;
  int _timeOffVisible = _pageSize;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _invoiceFilterController.dispose();
    _expenseFilterController.dispose();
    _timeOffFilterController.dispose();
    super.dispose();
  }

  Future<_FinanceWorkforceData> _load() async {
    final client = await ref.read(apiClientProvider.future);
    if (client == null) {
      return const _FinanceWorkforceData.empty();
    }

    final invoicesRes = await client.getInvoices(page: _invoicePage, perPage: 20);
    final expensesRes = await client.getExpenses(page: _expensePage, perPage: 20);
    final projectsRes = await client.getProjects(status: 'active', perPage: 100);
    final clientsRes = await client.getClients(status: 'active', perPage: 100);

    final now = DateTime.now();
    final start = DateTime(now.year, now.month, now.day - now.weekday + 1);
    final end = start.add(const Duration(days: 6));

    final capacityRes = await client.getCapacityReport(
      startDate: start.toIso8601String().split('T')[0],
      endDate: end.toIso8601String().split('T')[0],
    );

    final periodsRes = await client.getTimesheetPeriods(
      startDate: start.toIso8601String().split('T')[0],
      endDate: end.toIso8601String().split('T')[0],
    );
    final leaveTypesRes = await client.getLeaveTypes();
    final timeOffReqRes = await client.getTimeOffRequests();
    final balancesRes = await client.getTimeOffBalances();
    final meRes = await client.getUsersMe();
    final user = meRes['user'] is Map<String, dynamic> ? meRes['user'] as Map<String, dynamic> : <String, dynamic>{};
    final role = (user['role'] ?? '').toString().toLowerCase();
    final roleCanApprove = role == 'admin' || role == 'owner' || role == 'manager' || role == 'approver';
    if (mounted) {
      _canApprove = (user['is_admin'] == true) || roleCanApprove;
    }

    final invoiceTotalPages = ((invoicesRes['pagination'] ?? const {})['pages'] as num?)?.toInt() ?? 1;
    final expenseTotalPages = ((expensesRes['pagination'] ?? const {})['pages'] as num?)?.toInt() ?? 1;
    if (mounted) {
      _invoiceTotalPagesState = invoiceTotalPages;
      _expenseTotalPagesState = expenseTotalPages;
    }

    return _FinanceWorkforceData(
      invoices: List<Map<String, dynamic>>.from(invoicesRes['invoices'] ?? const []),
      expenses: List<Map<String, dynamic>>.from(expensesRes['expenses'] ?? const []),
      capacity: List<Map<String, dynamic>>.from(capacityRes['capacity'] ?? const []),
      periods: List<Map<String, dynamic>>.from(periodsRes['timesheet_periods'] ?? const []),
      projects: List<Map<String, dynamic>>.from(projectsRes['projects'] ?? const []),
      clients: List<Map<String, dynamic>>.from(clientsRes['clients'] ?? const []),
      leaveTypes: List<Map<String, dynamic>>.from(leaveTypesRes['leave_types'] ?? const []),
      timeOffRequests: List<Map<String, dynamic>>.from(timeOffReqRes['time_off_requests'] ?? const []),
      balances: List<Map<String, dynamic>>.from(balancesRes['balances'] ?? const []),
      invoicePage: ((invoicesRes['pagination'] ?? const {})['page'] as num?)?.toInt() ?? _invoicePage,
      invoiceTotalPages: invoiceTotalPages,
      expensePage: ((expensesRes['pagination'] ?? const {})['page'] as num?)?.toInt() ?? _expensePage,
      expenseTotalPages: expenseTotalPages,
    );
  }

  Future<void> _refresh() async {
    ref.invalidate(timesheetPeriodsProvider);
    ref.invalidate(capacityReportProvider);
    ref.invalidate(timeOffRequestsProvider);
    ref.invalidate(leaveBalancesProvider);
    ref.invalidate(leaveTypesProvider);
    ref.invalidate(financeInvoicesProvider);
    ref.invalidate(financeExpensesProvider);
    ref.invalidate(financeProjectsProvider);
    ref.invalidate(financeClientsProvider);
    ref.invalidate(userCanApproveProvider);
    setState(() {
      _invoiceVisible = _pageSize;
      _expenseVisible = _pageSize;
      _timeOffVisible = _pageSize;
      _future = _load();
    });
    await _future;
  }

  Future<void> _changeInvoicePage(int delta) async {
    final next = _invoicePage + delta;
    if (next < 1 || next > _invoiceTotalPagesState) return;
    setState(() {
      _invoicePage = next;
      _invoiceVisible = _pageSize;
      _future = _load();
    });
    await _future;
  }

  Future<void> _changeExpensePage(int delta) async {
    final next = _expensePage + delta;
    if (next < 1 || next > _expenseTotalPagesState) return;
    setState(() {
      _expensePage = next;
      _expenseVisible = _pageSize;
      _future = _load();
    });
    await _future;
  }

  Future<void> _submitPeriod(int periodId) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.submitTimesheetPeriod(periodId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Timesheet period submitted')),
      );
      ref.invalidate(timesheetPeriodsProvider);
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to submit period: $e')),
      );
    }
  }

  Future<void> _reviewPeriod({
    required int periodId,
    required bool approve,
  }) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      if (approve) {
        await client.approveTimesheetPeriod(periodId);
      } else {
        await client.rejectTimesheetPeriod(periodId);
      }
      if (!mounted) return;
      ref.invalidate(timesheetPeriodsProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(approve ? 'Period approved' : 'Period rejected')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to review period: $e')),
      );
    }
  }

  Future<void> _createExpense({
    required String title,
    required String category,
    required String amount,
    required String expenseDate,
  }) async {
    final parsedAmount = double.tryParse(amount);
    if (parsedAmount == null || parsedAmount <= 0) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid amount')),
      );
      return;
    }

    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.createExpense({
        'title': title.trim(),
        'category': category.trim(),
        'amount': parsedAmount,
        'expense_date': expenseDate,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Expense created')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to create expense: $e')),
      );
    }
  }

  Future<void> _openCreateExpenseDialog() async {
    final titleController = TextEditingController();
    final categoryController = TextEditingController(text: 'travel');
    final amountController = TextEditingController();
    DateTime selectedDate = DateTime.now();

    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: const Text('Create Expense'),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: titleController,
                        decoration: const InputDecoration(labelText: 'Title *'),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: categoryController,
                        decoration: const InputDecoration(labelText: 'Category *'),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: amountController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Amount *'),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Date: ${selectedDate.toIso8601String().split('T')[0]}',
                            ),
                          ),
                          TextButton(
                            onPressed: () async {
                              final picked = await showDatePicker(
                                context: dialogContext,
                                initialDate: selectedDate,
                                firstDate: DateTime(2000),
                                lastDate: DateTime(2100),
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  selectedDate = picked;
                                });
                              }
                            },
                            child: const Text('Change'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(dialogContext),
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: () async {
                      if (titleController.text.trim().isEmpty ||
                          categoryController.text.trim().isEmpty ||
                          amountController.text.trim().isEmpty) {
                        return;
                      }
                      Navigator.pop(dialogContext);
                      await _createExpense(
                        title: titleController.text,
                        category: categoryController.text,
                        amount: amountController.text,
                        expenseDate: selectedDate.toIso8601String().split('T')[0],
                      );
                    },
                    child: const Text('Create'),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      titleController.dispose();
      categoryController.dispose();
      amountController.dispose();
    }
  }

  Future<void> _createInvoice({
    required int projectId,
    required int clientId,
    required String clientName,
    required String dueDate,
  }) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.createInvoice({
        'project_id': projectId,
        'client_id': clientId,
        'client_name': clientName,
        'due_date': dueDate,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invoice created')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to create invoice: $e')),
      );
    }
  }

  Future<void> _openCreateInvoiceDialog(_FinanceWorkforceData data) async {
    if (data.projects.isEmpty || data.clients.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Projects and clients are required to create invoices')),
      );
      return;
    }

    int selectedProjectId = (data.projects.first['id'] as num).toInt();
    int selectedClientId = (data.clients.first['id'] as num).toInt();
    DateTime dueDate = DateTime.now().add(const Duration(days: 14));

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Create Invoice'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    DropdownButtonFormField<int>(
                      value: selectedProjectId,
                      decoration: const InputDecoration(labelText: 'Project *'),
                      items: data.projects
                          .map(
                            (p) => DropdownMenuItem<int>(
                              value: (p['id'] as num).toInt(),
                              child: Text((p['name'] ?? 'Project').toString()),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() {
                            selectedProjectId = value;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<int>(
                      value: selectedClientId,
                      decoration: const InputDecoration(labelText: 'Client *'),
                      items: data.clients
                          .map(
                            (c) => DropdownMenuItem<int>(
                              value: (c['id'] as num).toInt(),
                              child: Text((c['name'] ?? 'Client').toString()),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() {
                            selectedClientId = value;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: Text('Due: ${dueDate.toIso8601String().split('T')[0]}'),
                        ),
                        TextButton(
                          onPressed: () async {
                            final picked = await showDatePicker(
                              context: dialogContext,
                              initialDate: dueDate,
                              firstDate: DateTime(2000),
                              lastDate: DateTime(2100),
                            );
                            if (picked != null) {
                              setDialogState(() {
                                dueDate = picked;
                              });
                            }
                          },
                          child: const Text('Change'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final client = data.clients.firstWhere(
                      (c) => (c['id'] as num).toInt() == selectedClientId,
                      orElse: () => <String, dynamic>{},
                    );
                    final clientName = (client['name'] ?? '').toString().trim();
                    if (clientName.isEmpty) return;
                    Navigator.pop(dialogContext);
                    await _createInvoice(
                      projectId: selectedProjectId,
                      clientId: selectedClientId,
                      clientName: clientName,
                      dueDate: dueDate.toIso8601String().split('T')[0],
                    );
                  },
                  child: const Text('Create'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _createTimeOffRequest({
    required int leaveTypeId,
    required String startDate,
    required String endDate,
    String? requestedHours,
    String? comment,
  }) async {
    final parsedHours = (requestedHours != null && requestedHours.trim().isNotEmpty)
        ? double.tryParse(requestedHours.trim())
        : null;
    if (requestedHours != null && requestedHours.trim().isNotEmpty && parsedHours == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('requested_hours must be numeric')),
      );
      return;
    }

    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      await client.createTimeOffRequest(
        leaveTypeId: leaveTypeId,
        startDate: startDate,
        endDate: endDate,
        requestedHours: parsedHours,
        comment: comment,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Time-off request created')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to create time-off request: $e')),
      );
    }
  }

  Future<void> _updateInvoiceStatus({
    required int invoiceId,
    String? status,
    double? amountPaid,
  }) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      final payload = <String, dynamic>{};
      if (status != null) payload['status'] = status;
      if (amountPaid != null) payload['amount_paid'] = amountPaid;
      await client.updateInvoice(invoiceId, payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invoice updated')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update invoice: $e')),
      );
    }
  }

  Future<void> _reviewTimeOffRequest({
    required int requestId,
    required bool approve,
  }) async {
    try {
      final client = await ref.read(apiClientProvider.future);
      if (client == null) return;
      if (approve) {
        await client.approveTimeOffRequest(requestId);
      } else {
        await client.rejectTimeOffRequest(requestId);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(approve ? 'Request approved' : 'Request rejected')),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Review failed: $e')),
      );
    }
  }

  Future<void> _openCreateTimeOffDialog(_FinanceWorkforceData data) async {
    if (data.leaveTypes.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No leave types available')),
      );
      return;
    }

    int selectedLeaveTypeId = (data.leaveTypes.first['id'] as num).toInt();
    DateTime startDate = DateTime.now();
    DateTime endDate = DateTime.now();
    final hoursController = TextEditingController();
    final commentController = TextEditingController();

    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: const Text('Create Time-Off Request'),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DropdownButtonFormField<int>(
                        value: selectedLeaveTypeId,
                        decoration: const InputDecoration(labelText: 'Leave type *'),
                        items: data.leaveTypes
                            .map(
                              (lt) => DropdownMenuItem<int>(
                                value: (lt['id'] as num).toInt(),
                                child: Text((lt['name'] ?? 'Leave Type').toString()),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          if (value != null) {
                            setDialogState(() {
                              selectedLeaveTypeId = value;
                            });
                          }
                        },
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(child: Text('Start: ${startDate.toIso8601String().split('T')[0]}')),
                          TextButton(
                            onPressed: () async {
                              final picked = await showDatePicker(
                                context: dialogContext,
                                initialDate: startDate,
                                firstDate: DateTime(2000),
                                lastDate: DateTime(2100),
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  startDate = picked;
                                  if (endDate.isBefore(startDate)) endDate = startDate;
                                });
                              }
                            },
                            child: const Text('Change'),
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          Expanded(child: Text('End: ${endDate.toIso8601String().split('T')[0]}')),
                          TextButton(
                            onPressed: () async {
                              final picked = await showDatePicker(
                                context: dialogContext,
                                initialDate: endDate,
                                firstDate: DateTime(2000),
                                lastDate: DateTime(2100),
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  endDate = picked;
                                });
                              }
                            },
                            child: const Text('Change'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: hoursController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Requested hours (optional)'),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: commentController,
                        decoration: const InputDecoration(labelText: 'Comment (optional)'),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(dialogContext),
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: () async {
                      Navigator.pop(dialogContext);
                      await _createTimeOffRequest(
                        leaveTypeId: selectedLeaveTypeId,
                        startDate: startDate.toIso8601String().split('T')[0],
                        endDate: endDate.toIso8601String().split('T')[0],
                        requestedHours: hoursController.text,
                        comment: commentController.text,
                      );
                    },
                    child: const Text('Create'),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      hoursController.dispose();
      commentController.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Finance & Workforce'),
        actions: [
          IconButton(
            onPressed: _openCreateExpenseDialog,
            icon: const Icon(Icons.add_card_outlined),
            tooltip: 'Create expense',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<_FinanceWorkforceData>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return ListView(
                children: [
                  const SizedBox(height: 60),
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text('Failed to load finance/workforce data: ${snapshot.error}'),
                    ),
                  ),
                ],
              );
            }

            final data = snapshot.data ?? const _FinanceWorkforceData.empty();
            final filteredInvoices = data.invoices.where((invoice) {
              if (_invoiceFilter.isEmpty) return true;
              final text = '${invoice['invoice_number'] ?? ''} ${invoice['client_name'] ?? ''} ${invoice['status'] ?? ''}'
                  .toLowerCase();
              return text.contains(_invoiceFilter);
            }).toList();
            final filteredExpenses = data.expenses.where((expense) {
              if (_expenseFilter.isEmpty) return true;
              final text = '${expense['title'] ?? ''} ${expense['category'] ?? ''} ${expense['expense_date'] ?? ''}'
                  .toLowerCase();
              return text.contains(_expenseFilter);
            }).toList();
            final filteredTimeOffRequests = data.timeOffRequests.where((req) {
              if (_timeOffFilter.isEmpty) return true;
              final text = '${req['leave_type_name'] ?? ''} ${req['status'] ?? ''} ${req['start_date'] ?? ''} ${req['end_date'] ?? ''}'
                  .toLowerCase();
              return text.contains(_timeOffFilter);
            }).toList();

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _SectionCard(
                  title: 'Invoices',
                  subtitle: 'Latest invoices from the server',
                  child: Column(
                    children: [
                      Row(
                        children: [
                          OutlinedButton(
                            onPressed: data.invoicePage > 1 ? () => _changeInvoicePage(-1) : null,
                            child: const Text('Prev'),
                          ),
                          const SizedBox(width: 8),
                          Text('Page ${data.invoicePage}/${data.invoiceTotalPages}'),
                          const SizedBox(width: 8),
                          OutlinedButton(
                            onPressed: data.invoicePage < data.invoiceTotalPages ? () => _changeInvoicePage(1) : null,
                            child: const Text('Next'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (filteredInvoices.isEmpty)
                        const _EmptyText('No invoices found')
                      else
                        Column(
                          children: filteredInvoices.take(_invoiceVisible).map((invoice) {
                            final invoiceIdRaw = invoice['id'];
                            final invoiceId = invoiceIdRaw is num ? invoiceIdRaw.toInt() : null;
                            final number = (invoice['invoice_number'] ?? invoice['id'] ?? 'N/A').toString();
                            final status = (invoice['status'] ?? 'unknown').toString();
                            final total = (invoice['total_amount'] ?? invoice['total'] ?? '-').toString();
                            final totalAmount = (invoice['total_amount'] ?? invoice['total']);
                            final totalPaid = totalAmount is num ? totalAmount.toDouble() : double.tryParse(totalAmount.toString());
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text('Invoice $number'),
                              subtitle: Text('Status: $status'),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(total),
                                  if (invoiceId != null)
                                    PopupMenuButton<String>(
                                      onSelected: (value) async {
                                        if (value == 'sent') {
                                          await _updateInvoiceStatus(invoiceId: invoiceId, status: 'sent');
                                        } else if (value == 'cancelled') {
                                          await _updateInvoiceStatus(invoiceId: invoiceId, status: 'cancelled');
                                        } else if (value == 'paid' && totalPaid != null && totalPaid > 0) {
                                          await _updateInvoiceStatus(invoiceId: invoiceId, amountPaid: totalPaid);
                                        }
                                      },
                                      itemBuilder: (context) => [
                                        const PopupMenuItem(value: 'sent', child: Text('Mark Sent')),
                                        if (totalPaid != null && totalPaid > 0)
                                          const PopupMenuItem(value: 'paid', child: Text('Mark Paid')),
                                        const PopupMenuItem(value: 'cancelled', child: Text('Cancel')),
                                      ],
                                    ),
                                ],
                              ),
                            );
                          }).toList(),
                        ),
                    ],
                  ),
                ),
                if (filteredInvoices.length > _invoiceVisible)
                  _LoadMoreButton(
                    onPressed: () {
                      setState(() {
                        _invoiceVisible += _pageSize;
                      });
                    },
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: _invoiceFilterController,
                  decoration: const InputDecoration(
                    labelText: 'Filter invoices',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                  ),
                  onChanged: (value) {
                    setState(() {
                      _invoiceFilter = value.trim().toLowerCase();
                      _invoiceVisible = _pageSize;
                    });
                  },
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _openCreateInvoiceDialog(data),
                        icon: const Icon(Icons.receipt_long_outlined),
                        label: const Text('New Invoice'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _openCreateTimeOffDialog(data),
                        icon: const Icon(Icons.event_available_outlined),
                        label: const Text('New Time-Off'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Expenses',
                  subtitle: 'Latest expense entries',
                  child: Column(
                    children: [
                      Row(
                        children: [
                          OutlinedButton(
                            onPressed: data.expensePage > 1 ? () => _changeExpensePage(-1) : null,
                            child: const Text('Prev'),
                          ),
                          const SizedBox(width: 8),
                          Text('Page ${data.expensePage}/${data.expenseTotalPages}'),
                          const SizedBox(width: 8),
                          OutlinedButton(
                            onPressed: data.expensePage < data.expenseTotalPages ? () => _changeExpensePage(1) : null,
                            child: const Text('Next'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (filteredExpenses.isEmpty)
                        const _EmptyText('No expenses found')
                      else
                        Column(
                          children: filteredExpenses.take(_expenseVisible).map((expense) {
                            final category = (expense['category'] ?? 'General').toString();
                            final amount = (expense['amount'] ?? '-').toString();
                            final date = (expense['expense_date'] ?? expense['date'] ?? '').toString();
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text(category),
                              subtitle: Text(date),
                              trailing: Text(amount),
                            );
                          }).toList(),
                        ),
                    ],
                  ),
                ),
                if (filteredExpenses.length > _expenseVisible)
                  _LoadMoreButton(
                    onPressed: () {
                      setState(() {
                        _expenseVisible += _pageSize;
                      });
                    },
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: _expenseFilterController,
                  decoration: const InputDecoration(
                    labelText: 'Filter expenses',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                  ),
                  onChanged: (value) {
                    setState(() {
                      _expenseFilter = value.trim().toLowerCase();
                      _expenseVisible = _pageSize;
                    });
                  },
                ),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Time-Off Requests',
                  subtitle: 'Recent requests',
                  child: filteredTimeOffRequests.isEmpty
                      ? const _EmptyText('No time-off requests')
                      : Column(
                          children: filteredTimeOffRequests.take(_timeOffVisible).map((req) {
                            final reqIdRaw = req['id'];
                            final requestId = reqIdRaw is num ? reqIdRaw.toInt() : null;
                            final status = (req['status'] ?? '').toString();
                            final start = (req['start_date'] ?? '').toString();
                            final end = (req['end_date'] ?? '').toString();
                            final leaveType = (req['leave_type_name'] ?? 'Leave').toString();
                            final isSubmitted = status.toLowerCase() == 'submitted';
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text(leaveType),
                              subtitle: Text('$start to $end'),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(status),
                                  if (isSubmitted && requestId != null && _canApprove)
                                    PopupMenuButton<String>(
                                      onSelected: (value) async {
                                        if (value == 'approve') {
                                          await _reviewTimeOffRequest(requestId: requestId, approve: true);
                                        } else if (value == 'reject') {
                                          await _reviewTimeOffRequest(requestId: requestId, approve: false);
                                        }
                                      },
                                      itemBuilder: (context) => const [
                                        PopupMenuItem(value: 'approve', child: Text('Approve')),
                                        PopupMenuItem(value: 'reject', child: Text('Reject')),
                                      ],
                                    ),
                                ],
                              ),
                            );
                          }).toList(),
                        ),
                ),
                if (filteredTimeOffRequests.length > _timeOffVisible)
                  _LoadMoreButton(
                    onPressed: () {
                      setState(() {
                        _timeOffVisible += _pageSize;
                      });
                    },
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: _timeOffFilterController,
                  decoration: const InputDecoration(
                    labelText: 'Filter time-off requests',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                  ),
                  onChanged: (value) {
                    setState(() {
                      _timeOffFilter = value.trim().toLowerCase();
                      _timeOffVisible = _pageSize;
                    });
                  },
                ),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Leave Balances',
                  subtitle: 'Current user balances',
                  child: data.balances.isEmpty
                      ? const _EmptyText('No leave balances')
                      : Column(
                          children: data.balances.take(8).map((bal) {
                            final leaveType = (bal['leave_type_name'] ?? 'Leave').toString();
                            final remaining = (bal['remaining_hours'] ?? bal['balance_hours'] ?? 0).toString();
                            final approved = (bal['approved_hours'] ?? 0).toString();
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text(leaveType),
                              subtitle: Text('Approved: $approved h'),
                              trailing: Text('$remaining h'),
                            );
                          }).toList(),
                        ),
                ),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Timesheet Periods',
                  subtitle: 'Current period workflow status',
                  child: data.periods.isEmpty
                      ? const _EmptyText('No periods available')
                      : Column(
                          children: data.periods.take(8).map((period) {
                            final start = (period['period_start'] ?? '').toString();
                            final end = (period['period_end'] ?? '').toString();
                            final status = (period['status'] ?? '').toString();
                            final periodId = period['id'] as int?;
                            final canSubmit = status.toLowerCase() == 'draft' && periodId != null;
                            final canReview = _canApprove && status.toLowerCase() == 'submitted' && periodId != null;
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text('$start - $end'),
                              subtitle: Text('Status: $status'),
                              trailing: canSubmit
                                  ? TextButton(
                                      onPressed: () => _submitPeriod(periodId),
                                      child: const Text('Submit'),
                                    )
                                  : (canReview
                                      ? PopupMenuButton<String>(
                                          onSelected: (value) async {
                                            if (value == 'approve') {
                                              await _reviewPeriod(periodId: periodId, approve: true);
                                            } else if (value == 'reject') {
                                              await _reviewPeriod(periodId: periodId, approve: false);
                                            }
                                          },
                                          itemBuilder: (context) => const [
                                            PopupMenuItem(value: 'approve', child: Text('Approve')),
                                            PopupMenuItem(value: 'reject', child: Text('Reject')),
                                          ],
                                        )
                                      : null),
                            );
                          }).toList(),
                        ),
                ),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Capacity',
                  subtitle: 'Expected vs allocated hours',
                  child: data.capacity.isEmpty
                      ? const _EmptyText('No capacity data')
                      : Column(
                          children: data.capacity.take(8).map((row) {
                            final user = (row['username'] ?? 'user').toString();
                            final expected = (row['expected_hours'] ?? 0).toString();
                            final allocated = (row['allocated_hours'] ?? 0).toString();
                            final util = (row['utilization_pct'] ?? 0).toString();
                            return ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              title: Text(user),
                              subtitle: Text('Expected: $expected | Allocated: $allocated'),
                              trailing: Text('$util%'),
                            );
                          }).toList(),
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

class _SectionCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final Widget child;

  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 2),
            Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            child,
          ],
        ),
      ),
    );
  }
}

class _EmptyText extends StatelessWidget {
  final String text;
  const _EmptyText(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
    );
  }
}

class _LoadMoreButton extends StatelessWidget {
  final VoidCallback onPressed;
  const _LoadMoreButton({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: TextButton.icon(
        onPressed: onPressed,
        icon: const Icon(Icons.expand_more),
        label: const Text('Load more'),
      ),
    );
  }
}

class _FinanceWorkforceData {
  final List<Map<String, dynamic>> invoices;
  final List<Map<String, dynamic>> expenses;
  final List<Map<String, dynamic>> capacity;
  final List<Map<String, dynamic>> periods;
  final List<Map<String, dynamic>> projects;
  final List<Map<String, dynamic>> clients;
  final List<Map<String, dynamic>> leaveTypes;
  final List<Map<String, dynamic>> timeOffRequests;
  final List<Map<String, dynamic>> balances;
  final int invoicePage;
  final int invoiceTotalPages;
  final int expensePage;
  final int expenseTotalPages;

  const _FinanceWorkforceData({
    required this.invoices,
    required this.expenses,
    required this.capacity,
    required this.periods,
    required this.projects,
    required this.clients,
    required this.leaveTypes,
    required this.timeOffRequests,
    required this.balances,
    required this.invoicePage,
    required this.invoiceTotalPages,
    required this.expensePage,
    required this.expenseTotalPages,
  });

  const _FinanceWorkforceData.empty()
      : invoices = const [],
        expenses = const [],
        capacity = const [],
        periods = const [],
        projects = const [],
        clients = const [],
        leaveTypes = const [],
        timeOffRequests = const [],
        balances = const [],
        invoicePage = 1,
        invoiceTotalPages = 1,
        expensePage = 1,
        expenseTotalPages = 1;
}
