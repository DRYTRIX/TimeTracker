import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/project.dart';
import '../providers/projects_provider.dart';
import '../providers/timer_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/error_view.dart';
import 'timer_screen.dart';

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
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: const InputDecoration(
                hintText: 'Search projects...',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: (_) => setState(() {}),
            ),
          ),
          Expanded(
            child: projectsState.isLoading
                ? const Center(child: CircularProgressIndicator())
                : projectsState.error != null
                    ? ErrorView(
                        title: 'Error loading projects',
                        message: projectsState.error,
                        onRetry: () => ref.read(projectsProvider.notifier).loadProjects(),
                      )
                    : filteredProjects.isEmpty
                        ? const EmptyState(
                            icon: Icons.folder_off,
                            title: 'No projects found',
                            subtitle: 'No projects match your search.',
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: filteredProjects.length,
                            itemBuilder: (context, index) {
                              final project = filteredProjects[index];
                              return Card(
                                margin: const EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: const CircleAvatar(
                                    child: Icon(Icons.folder),
                                  ),
                                  title: Text(project.name),
                                  subtitle: Text(project.client ?? 'No client'),
                                  trailing: const Icon(Icons.chevron_right),
                                  onTap: () async {
                                    // Start timer with this project
                                    final timerState = ref.read(timerProvider);
                                    if (timerState.isRunning) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Please stop the current timer first'),
                                        ),
                                      );
                                      return;
                                    }

                                    // Navigate to timer screen with project pre-selected
                                    // For now, just navigate to timer screen
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => const TimerScreen(),
                                      ),
                                    );
                                  },
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
