import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import 'package:timetracker_mobile/presentation/providers/time_entries_provider.dart';
import 'package:timetracker_mobile/presentation/providers/user_prefs_provider.dart';
import 'package:timetracker_mobile/presentation/screens/time_entry_form_screen.dart';
import 'package:timetracker_mobile/presentation/widgets/empty_state.dart';
import 'package:timetracker_mobile/presentation/widgets/error_view.dart';
import 'package:timetracker_mobile/presentation/widgets/time_entry_card.dart';
import 'package:timetracker_mobile/utils/date_format_utils.dart';

class TimeEntriesScreen extends ConsumerStatefulWidget {
  const TimeEntriesScreen({super.key});

  @override
  ConsumerState<TimeEntriesScreen> createState() => _TimeEntriesScreenState();
}

class _TimeEntriesScreenState extends ConsumerState<TimeEntriesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(timeEntriesProvider.notifier).loadEntries();
    });
  }

  @override
  Widget build(BuildContext context) {
    final entriesState = ref.watch(timeEntriesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Time Entries'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
            tooltip: 'Filter',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(timeEntriesProvider.notifier).refresh(),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(timeEntriesProvider.notifier).refresh(),
        child: _buildBody(entriesState),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddEntryDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody(TimeEntriesState state) {
    if (state.isLoading && state.entries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.entries.isEmpty) {
      return ErrorView(
        title: 'Error loading entries',
        message: state.error,
        onRetry: () => ref.read(timeEntriesProvider.notifier).refresh(),
      );
    }

    if (state.entries.isEmpty) {
      return const EmptyState(
        icon: Icons.history,
        title: 'No time entries',
        subtitle: 'Start tracking time or add a manual entry',
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: state.entries.length,
      itemBuilder: (context, index) {
        final entry = state.entries[index];
        return TimeEntryCard(
          entry: entry,
          onEdit: () => _showEditEntryDialog(entry.id),
          onDelete: () => _showDeleteConfirmation(entry.id),
        );
      },
    );
  }

  void _showAddEntryDialog() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const TimeEntryFormScreen(),
      ),
    );
  }

  void _showEditEntryDialog(int entryId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => TimeEntryFormScreen(entryId: entryId),
      ),
    );
  }

  void _showDeleteConfirmation(int entryId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Entry'),
        content: const Text('Are you sure you want to delete this time entry?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              ref.read(timeEntriesProvider.notifier).deleteEntry(entryId);
              Navigator.of(context).pop();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
              foregroundColor: Theme.of(context).colorScheme.onError,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _showFilterDialog() {
    final currentFilter = ref.read(timeEntriesProvider).filter;
    final prefs = ref.read(userPrefsProvider).valueOrNull;
    final dateFormatKey = prefs?.dateFormat;
    DateTime? startDate;
    DateTime? endDate;

    if (currentFilter.startDate != null) {
      startDate = DateTime.parse(currentFilter.startDate!);
    }
    if (currentFilter.endDate != null) {
      endDate = DateTime.parse(currentFilter.endDate!);
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Entries'),
        content: StatefulBuilder(
          builder: (context, setState) {
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  title: const Text('Start Date'),
                  subtitle: Text(
                    startDate != null
                        ? formatDate(startDate, dateFormatKey)
                        : 'No date selected',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: startDate ?? DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) {
                      setState(() {
                        startDate = date;
                      });
                    }
                  },
                ),
                ListTile(
                  title: const Text('End Date'),
                  subtitle: Text(
                    endDate != null
                        ? formatDate(endDate, dateFormatKey)
                        : 'No date selected',
                  ),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: endDate ?? DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) {
                      setState(() {
                        endDate = date;
                      });
                    }
                  },
                ),
              ],
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () {
              // Clear filters
              ref.read(timeEntriesProvider.notifier).setFilter(
                    TimeEntriesFilter(),
                  );
              Navigator.of(context).pop();
            },
            child: const Text('Clear'),
          ),
          ElevatedButton(
            onPressed: () {
              ref.read(timeEntriesProvider.notifier).setFilter(
                    currentFilter.copyWith(
                      startDate: startDate != null
                          ? DateFormat('yyyy-MM-dd').format(startDate!)
                          : null,
                      endDate: endDate != null
                          ? DateFormat('yyyy-MM-dd').format(endDate!)
                          : null,
                    ),
                  );
              Navigator.of(context).pop();
            },
            child: const Text('Apply'),
          ),
        ],
      ),
    );
  }
}
