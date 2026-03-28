import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';
import 'package:timetracker_mobile/data/models/timer.dart' as tt;
import 'package:timetracker_mobile/data/models/time_entry.dart';

class LocalStorage {
  LocalStorage._();

  static const _boxName = 'timetracker_local_v1';
  static const _kTimer = 'timer';
  static const _kEntries = 'time_entries';
  static const _kQueue = 'sync_queue';

  static Box<String>? _box;

  static Future<void> init() async {
    await Hive.initFlutter();
    _box = await Hive.openBox<String>(_boxName);
  }

  static Box<String> get _b {
    final b = _box;
    if (b == null) {
      throw StateError('LocalStorage.init() was not called');
    }
    return b;
  }

  static Future<tt.Timer?> getTimer() async {
    final raw = _b.get(_kTimer);
    if (raw == null || raw.isEmpty) return null;
    final map = jsonDecode(raw) as Map<String, dynamic>;
    return tt.Timer.fromJson(map);
  }

  static Future<void> saveTimer(tt.Timer timer) async {
    await _b.put(_kTimer, jsonEncode(timer.toJson()));
  }

  static Future<void> clearTimer() async {
    await _b.delete(_kTimer);
  }

  static Future<List<TimeEntry>> getAllTimeEntries() async {
    final raw = _b.get(_kEntries);
    if (raw == null || raw.isEmpty) return [];
    final list = jsonDecode(raw) as List<dynamic>;
    return list
        .map((e) => TimeEntry.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  static Future<void> saveTimeEntry(TimeEntry entry) async {
    final all = await getAllTimeEntries();
    final idx = all.indexWhere((e) => e.id == entry.id);
    if (idx >= 0) {
      all[idx] = entry;
    } else {
      all.add(entry);
    }
    await _persistEntries(all);
  }

  static Future<void> deleteTimeEntry(int entryId) async {
    final all = await getAllTimeEntries();
    all.removeWhere((e) => e.id == entryId);
    await _persistEntries(all);
  }

  static Future<void> _persistEntries(List<TimeEntry> entries) async {
    await _b.put(
      _kEntries,
      jsonEncode(entries.map((e) => e.toJson()).toList()),
    );
  }

  static Future<List<Map<String, dynamic>>> getSyncQueue() async {
    final raw = _b.get(_kQueue);
    if (raw == null || raw.isEmpty) return [];
    final list = jsonDecode(raw) as List<dynamic>;
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  static Future<void> setSyncQueue(List<Map<String, dynamic>> queue) async {
    await _b.put(_kQueue, jsonEncode(queue));
  }
}
