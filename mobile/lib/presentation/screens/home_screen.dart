import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/core/theme/app_tokens.dart';
import '../providers/timer_provider.dart';
import '../providers/time_entries_provider.dart';
import '../providers/projects_provider.dart';
import '../providers/user_prefs_provider.dart';
import 'package:timetracker_mobile/utils/date_format_utils.dart';
import '../widgets/empty_state.dart';
import 'timer_screen.dart';
import 'projects_screen.dart';
import 'time_entries_screen.dart';
import 'settings_screen.dart';
import 'dart:async';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const DashboardTab(),
    const ProjectsScreen(),
    const TimeEntriesScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.folder_outlined),
            selectedIcon: Icon(Icons.folder),
            label: 'Projects',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: 'Entries',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
      floatingActionButton: _currentIndex == 0
          ? FloatingActionButton.extended(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const TimerScreen(),
                  ),
                );
              },
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start Timer'),
            )
          : null,
    );
  }
}

class DashboardTab extends ConsumerStatefulWidget {
  const DashboardTab({super.key});

  @override
  ConsumerState<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends ConsumerState<DashboardTab> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {});
      }
    });
    
    // Load data on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(timerProvider.notifier).checkTimerStatus();
      ref.read(projectsProvider.notifier).loadProjects();
      final now = DateTime.now();
      ref.read(timeEntriesProvider.notifier).loadTimeEntries(
        startDate: now.toIso8601String().split('T')[0],
        endDate: now.toIso8601String().split('T')[0],
      );
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String _projectName(int? projectId, List<Project> projects) {
    if (projectId == null) return 'Unknown project';
    try {
      final p = projects.firstWhere((p) => p.id == projectId);
      return p.name;
    } catch (_) {
      return 'Unknown project';
    }
  }

  @override
  Widget build(BuildContext context) {
    final timerState = ref.watch(timerProvider);
    final entriesState = ref.watch(timeEntriesProvider);
    final projectsState = ref.watch(projectsProvider);
    final theme = Theme.of(context);

    // Calculate today's total
    final todayTotal = entriesState.entries.fold<int>(
      0,
      (sum, entry) => sum + (entry.durationSeconds ?? 0),
    );

    final hours = todayTotal ~/ 3600;
    final minutes = (todayTotal % 3600) ~/ 60;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Active Timer Card
            Card(
              child: InkWell(
                onTap: timerState.isRunning
                    ? () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const TimerScreen(),
                          ),
                        )
                    : null,
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Active Timer',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      if (timerState.isRunning && timerState.activeTimer != null)
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _formatTimer(ref.read(timerProvider.notifier).getElapsedTime()),
                              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                    color: Theme.of(context).colorScheme.primary,
                                  ),
                            ),
                            const SizedBox(height: AppSpacing.xs),
                            Text(
                              'Tap to view details',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                                  ),
                            ),
                          ],
                        )
                      else
                        Text(
                          'No active timer',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            // Today's Summary Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Today\'s Summary',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      entriesState.isLoading
                          ? 'Loading...'
                          : '${hours}h ${minutes}m',
                      style: theme.textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: entriesState.isLoading
                                ? theme.colorScheme.onSurfaceVariant
                                : null,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Recent Entries',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: AppSpacing.sm),
            if (entriesState.isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.xl),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (entriesState.entries.isEmpty)
              const EmptyState(
                icon: Icons.history,
                title: 'No recent entries',
                subtitle: 'Start a timer or add a time entry to see them here.',
              )
            else
              ...entriesState.entries.take(5).map((entry) {
                final projectName = _projectName(entry.projectId, projectsState.projects);
                final subtitle = (entry.notes != null && entry.notes!.trim().isNotEmpty)
                    ? entry.notes!.trim()
                    : formatDateRange(
                        entry.startTime,
                        entry.endTime,
                        ref.watch(userPrefsProvider).valueOrNull?.dateFormat,
                      );
                return Card(
                  margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: ListTile(
                    leading: CircleAvatar(
                      child: const Icon(Icons.timer),
                    ),
                    title: Text(
                      projectName,
                      style: projectName == 'Unknown project'
                          ? theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            )
                          : null,
                    ),
                    subtitle: Text(subtitle),
                    trailing: Text(
                      entry.formattedDuration,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  String _formatTimer(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);
    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:'
             '${minutes.toString().padLeft(2, '0')}:'
             '${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:'
           '${seconds.toString().padLeft(2, '0')}';
  }
}
