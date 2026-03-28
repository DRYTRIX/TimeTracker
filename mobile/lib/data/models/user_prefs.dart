import 'package:flutter/foundation.dart';

@immutable
class UserPrefs {
  final String dateFormatKey;
  final String timeFormatKey;
  final String timezone;

  const UserPrefs({
    this.dateFormatKey = 'YYYY-MM-DD',
    this.timeFormatKey = '24h',
    this.timezone = 'UTC',
  });

  factory UserPrefs.fromJson(Map<String, dynamic>? json) {
    if (json == null || json.isEmpty) {
      return const UserPrefs();
    }
    return UserPrefs(
      dateFormatKey: (json['date_format'] ?? 'YYYY-MM-DD').toString(),
      timeFormatKey: (json['time_format'] ?? '24h').toString(),
      timezone: (json['timezone'] ?? 'UTC').toString(),
    );
  }
}
