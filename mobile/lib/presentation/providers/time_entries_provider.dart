import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';
import 'package:timetracker_mobile/presentation/providers/timer_provider.dart';

/// Time entries filter state
class TimeEntriesFilter {
  final int? projectId;
  final String? startDate;
  final String? endDate;
  final bool? billable;
  final int page;
  final int perPage;

  TimeEntriesFilter({
    this.projectId,
    this.startDate,
    this.endDate,
    this.billable,
    this.page = 1,
    this.perPage = 50,
  });

  TimeEntriesFilter copyWith({
    int? projectId,
    String? startDate,
    String? endDate,
    bool? billable,
    int? page,
    int? perPage,
  }) {
    return TimeEntriesFilter(
      projectId: projectId ?? this.projectId,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      billable: billable ?? this.billable,
      page: page ?? this.page,
      perPage: perPage ?? this.perPage,
    );
  }
}

/// Time entries state
class TimeEntriesState {
  final List<TimeEntry> entries;
  final bool isLoading;
  final String? error;
  final TimeEntriesFilter filter;

  TimeEntriesState({
    this.entries = const [],
    this.isLoading = false,
    this.error,
    TimeEntriesFilter? filter,
  }) : filter = filter ?? TimeEntriesFilter();

  TimeEntriesState copyWith({
    List<TimeEntry>? entries,
    bool? isLoading,
    String? error,
    TimeEntriesFilter? filter,
  }) {
    return TimeEntriesState(
      entries: entries ?? this.entries,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      filter: filter ?? this.filter,
    );
  }
}

/// Time entries notifier
class TimeEntriesNotifier extends StateNotifier<TimeEntriesState> {
  final TimeTrackingRepository? repository;

  TimeEntriesNotifier(this.repository) : super(TimeEntriesState()) {
    if (repository != null) {
      loadEntries();
    }
  }

  Future<void> loadEntries({TimeEntriesFilter? filter}) async {
    if (repository == null) return;

    final currentFilter = filter ?? state.filter;
    state = state.copyWith(isLoading: true, error: null, filter: currentFilter);

    try {
      final entries = await repository!.getTimeEntries(
        projectId: currentFilter.projectId,
        startDate: currentFilter.startDate,
        endDate: currentFilter.endDate,
        billable: currentFilter.billable,
        page: currentFilter.page,
        perPage: currentFilter.perPage,
      );
      state = state.copyWith(entries: entries, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> refresh() async {
    await loadEntries();
  }

  Future<void> loadTimeEntries({
    String? startDate,
    String? endDate,
  }) async {
    await loadEntries(
      filter: state.filter.copyWith(
        startDate: startDate,
        endDate: endDate,
      ),
    );
  }

  Future<void> setFilter(TimeEntriesFilter filter) async {
    await loadEntries(filter: filter);
  }

  Future<void> createEntry({
    required int projectId,
    int? taskId,
    required String startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }

    try {
      state = state.copyWith(isLoading: true, error: null);
      await repository!.createTimeEntry(
        projectId: projectId,
        taskId: taskId,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        tags: tags,
        billable: billable,
      );
      await loadEntries();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> updateEntry(
    int entryId, {
    int? projectId,
    int? taskId,
    String? startTime,
    String? endTime,
    String? notes,
    String? tags,
    bool? billable,
  }) async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }

    try {
      state = state.copyWith(isLoading: true, error: null);
      await repository!.updateTimeEntry(
        entryId,
        projectId: projectId,
        taskId: taskId,
        startTime: startTime,
        endTime: endTime,
        notes: notes,
        tags: tags,
        billable: billable,
      );
      await loadEntries();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> deleteEntry(int entryId) async {
    if (repository == null) {
      state = state.copyWith(error: 'Not connected to server');
      return;
    }

    try {
      state = state.copyWith(isLoading: true, error: null);
      await repository!.deleteTimeEntry(entryId);
      await loadEntries();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

/// Time entries provider
final timeEntriesProvider =
    StateNotifierProvider<TimeEntriesNotifier, TimeEntriesState>((ref) {
  final repository = ref.watch(timeTrackingRepositoryProvider);
  return TimeEntriesNotifier(repository);
});
