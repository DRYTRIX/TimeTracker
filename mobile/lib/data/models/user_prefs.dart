/// Resolved display preferences for the current user (from /api/v1/users/me).
/// date_format and time_format are the resolved keys (user override or system default).
class UserPrefs {
  final String dateFormat;
  final String timeFormat;
  final String timezone;

  const UserPrefs({
    this.dateFormat = 'YYYY-MM-DD',
    this.timeFormat = '24h',
    this.timezone = 'Europe/Rome',
  });

  factory UserPrefs.fromJson(Map<String, dynamic> json) {
    return UserPrefs(
      dateFormat: json['date_format'] as String? ?? 'YYYY-MM-DD',
      timeFormat: json['time_format'] as String? ?? '24h',
      timezone: json['timezone'] as String? ?? 'Europe/Rome',
    );
  }
}
