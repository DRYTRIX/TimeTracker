import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/domain/repositories/time_tracking_repository.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Projects state
class ProjectsState {
  final List<Project> projects;
  final bool isLoading;
  final String? error;

  ProjectsState({
    this.projects = const [],
    this.isLoading = false,
    this.error,
  });

  ProjectsState copyWith({
    List<Project>? projects,
    bool? isLoading,
    String? error,
  }) {
    return ProjectsState(
      projects: projects ?? this.projects,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Projects notifier
class ProjectsNotifier extends StateNotifier<ProjectsState> {
  final TimeTrackingRepository? repository;

  ProjectsNotifier(this.repository) : super(ProjectsState()) {
    if (repository != null) {
      loadProjects();
    }
  }

  Future<void> loadProjects({String? status}) async {
    if (repository == null) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final projects = await repository!.getProjects(status: status ?? 'active');
      state = state.copyWith(projects: projects, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> refresh() async {
    await loadProjects();
  }
}

/// Projects provider
final projectsProvider =
    StateNotifierProvider<ProjectsNotifier, ProjectsState>((ref) {
  final repository = ref.watch(timeTrackingRepositoryProvider);
  return ProjectsNotifier(repository);
});
