import 'package:hive_flutter/hive_flutter.dart';
import '../../../core/constants/app_constants.dart';

class HiveService {
  static Future<void> init() async {
    await Hive.initFlutter();
    
    // Note: Using JSON storage instead of type adapters for simplicity
    // Models are serialized to/from JSON when storing in Hive
    // To use type adapters instead, add @HiveType() annotations to models
    // and run: flutter pub run build_runner build
  }
  
  // Time Entries Box
  static Box get timeEntriesBox => Hive.box(AppConstants.boxTimeEntries);
  static Future<Box> openTimeEntriesBox() async {
    return await Hive.openBox(AppConstants.boxTimeEntries);
  }
  
  // Projects Box
  static Box get projectsBox => Hive.box(AppConstants.boxProjects);
  static Future<Box> openProjectsBox() async {
    return await Hive.openBox(AppConstants.boxProjects);
  }
  
  // Tasks Box
  static Box get tasksBox => Hive.box(AppConstants.boxTasks);
  static Future<Box> openTasksBox() async {
    return await Hive.openBox(AppConstants.boxTasks);
  }
  
  // Sync Queue Box
  static Box get syncQueueBox => Hive.box(AppConstants.boxSyncQueue);
  static Future<Box> openSyncQueueBox() async {
    return await Hive.openBox(AppConstants.boxSyncQueue);
  }
  
  // Favorites Box
  static Box get favoritesBox => Hive.box(AppConstants.boxFavorites);
  static Future<Box> openFavoritesBox() async {
    return await Hive.openBox(AppConstants.boxFavorites);
  }
  
  // Initialize all boxes
  static Future<void> initBoxes() async {
    await openTimeEntriesBox();
    await openProjectsBox();
    await openTasksBox();
    await openSyncQueueBox();
    await openFavoritesBox();
  }
  
  // Clear all data (logout)
  static Future<void> clearAll() async {
    await timeEntriesBox.clear();
    await projectsBox.clear();
    await tasksBox.clear();
    await syncQueueBox.clear();
    await favoritesBox.clear();
  }
}
