class AppConstants {
  // API Configuration
  static const String apiVersion = 'v1';
  static const String defaultSyncInterval = '60'; // seconds
  static const int timerPollInterval = 5; // seconds
  
  // Storage Keys
  static const String boxTimeEntries = 'time_entries';
  static const String boxProjects = 'projects';
  static const String boxTasks = 'tasks';
  static const String boxSyncQueue = 'sync_queue';
  static const String boxFavorites = 'favorites';
  
  // Routes
  static const String routeSplash = '/';
  static const String routeLogin = '/login';
  static const String routeHome = '/home';
  static const String routeTimer = '/timer';
  static const String routeProjects = '/projects';
  static const String routeTasks = '/tasks';
  static const String routeTimeEntries = '/time-entries';
  static const String routeSettings = '/settings';
  
  // Notification IDs
  static const int notificationTimerRunning = 1;
  static const int notificationSyncStatus = 2;
  static const int notificationIdleReminder = 3;
  
  // Time Formats
  static const String timeFormat24h = 'HH:mm:ss';
  static const String timeFormat12h = 'hh:mm:ss a';
  static const String dateFormat = 'yyyy-MM-dd';
  static const String dateTimeFormat = 'yyyy-MM-dd HH:mm:ss';
}
