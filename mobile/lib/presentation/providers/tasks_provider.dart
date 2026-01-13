import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/task.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Tasks state
class TasksState {
  final List<Task> tasks;
  final bool isLoading;
  final String? error;

  TasksState({
    this.tasks = const [],
    this.isLoading = false,
    this.error,
  });

  TasksState copyWith({
    List<Task>? tasks,
    bool? isLoading,
    String? error,
  }) {
    return TasksState(
      tasks: tasks ?? this.tasks,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Tasks notifier
class TasksNotifier extends StateNotifier<TasksState> {
  final TimeTrackingRepository? repository;

  TasksNotifier(this.repository) : super(TasksState());

  Future<void> loadTasks({int? projectId, String? status}) async {
    if (repository == null) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final tasks = await repository!.getTasks(
        projectId: projectId,
        status: status,
      );
      state = state.copyWith(tasks: tasks, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> refresh() async {
    await loadTasks();
  }
}

/// Tasks provider
final tasksProvider =
    StateNotifierProvider<TasksNotifier, TasksState>((ref) {
  final repository = ref.watch(timeTrackingRepositoryProvider);
  return TasksNotifier(repository);
});
