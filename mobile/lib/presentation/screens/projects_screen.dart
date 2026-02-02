import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import '../../data/models/project.dart';
import '../providers/projects_provider.dart';
import '../providers/timer_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/error_view.dart';
import '../widgets/start_timer_sheet.dart';

class ProjectsScreen extends ConsumerStatefulWidget {
  const ProjectsScreen({super.key});

  @override
  ConsumerState<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends ConsumerState<ProjectsScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(projectsProvider.notifier).loadProjects();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Project> _filterProjects(List<Project> projects, String query) {
    if (query.isEmpty) return projects;
    return projects.where((project) {
      return project.name.toLowerCase().contains(query.toLowerCase()) ||
          (project.client ?? '').toLowerCase().contains(query.toLowerCase());
    }).toList();
  }

  Future<void> _startTimerForProject(Project project) async {
    final timerState = ref.read(timerProvider);
    if (timerState.isRunning) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please stop the current timer first'),
        ),
      );
      return;
    }
    await showStartTimerSheet(context, initialProjectId: project.id);
  }

  @override
  Widget build(BuildContext context) {
    final projectsState = ref.watch(projectsProvider);
    final filteredProjects = _filterProjects(projectsState.projects, _searchController.text);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Projects'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: SearchBar(
              controller: _searchController,
              leading: const Icon(Icons.search),
              hintText: 'Search projects',
              trailing: [
                if (_searchController.text.isNotEmpty)
                  IconButton(
                    onPressed: () {
                      setState(() {
                        _searchController.clear();
                      });
                    },
                    icon: const Icon(Icons.clear),
                    tooltip: 'Clear search',
                  ),
              ],
              onChanged: (_) => setState(() {}),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.read(projectsProvider.notifier).refresh(),
              child: projectsState.isLoading && projectsState.projects.isEmpty
                  ? const Center(child: CircularProgressIndicator())
                  : projectsState.error != null && projectsState.projects.isEmpty
                      ? ErrorView(
                          title: 'Error loading projects',
                          message: projectsState.error,
                          onRetry: () => ref.read(projectsProvider.notifier).loadProjects(),
                        )
                      : filteredProjects.isEmpty
                          ? EmptyState(
                              icon: Icons.folder_off,
                              title: 'No projects found',
                              subtitle: _searchController.text.isEmpty
                                  ? 'No active projects are available.'
                                  : 'No projects match your search.',
                              action: _searchController.text.isEmpty
                                  ? null
                                  : TextButton(
                                      onPressed: () {
                                        setState(() {
                                          _searchController.clear();
                                        });
                                      },
                                      child: const Text('Clear search'),
                                    ),
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.fromLTRB(
                                AppSpacing.md,
                                0,
                                AppSpacing.md,
                                AppSpacing.md,
                              ),
                              itemCount: filteredProjects.length,
                              itemBuilder: (context, index) {
                                final project = filteredProjects[index];
                                final client = (project.client ?? '').trim();
                                return Card(
                                  margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                                  child: ListTile(
                                    leading: CircleAvatar(
                                      child: Text(
                                        (project.name.isNotEmpty ? project.name[0] : '?').toUpperCase(),
                                        style: const TextStyle(fontWeight: FontWeight.w700),
                                      ),
                                    ),
                                    title: Text(project.name),
                                    subtitle: client.isEmpty
                                        ? null
                                        : Padding(
                                            padding: const EdgeInsets.only(top: AppSpacing.xs),
                                            child: Wrap(
                                              spacing: AppSpacing.xs,
                                              runSpacing: AppSpacing.xxs,
                                              children: [
                                                Chip(
                                                  visualDensity: VisualDensity.compact,
                                                  label: Text(client),
                                                ),
                                              ],
                                            ),
                                          ),
                                    trailing: IconButton.filledTonal(
                                      onPressed: () => _startTimerForProject(project),
                                      icon: const Icon(Icons.play_arrow),
                                      tooltip: 'Start timer',
                                    ),
                                    onTap: () => _startTimerForProject(project),
                                  ),
                                );
                              },
                            ),
            ),
          ),
        ],
      ),
    );
  }
}
