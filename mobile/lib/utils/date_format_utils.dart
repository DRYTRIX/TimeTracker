import 'package:intl/intl.dart';

/// API date format keys (from backend)
const String dateFormatYmd = 'YYYY-MM-DD';
const String dateFormatMdy = 'MM/DD/YYYY';
const String dateFormatDmy = 'DD/MM/YYYY';
const String dateFormatDmY = 'DD.MM.YYYY';

/// API time format keys
const String timeFormat24h = '24h';
const String timeFormat12h = '12h';

/// Maps API date format key to Dart intl DateFormat pattern (date only).
String dateFormatPatternFromKey(String? key) {
  switch (key) {
    case dateFormatMdy:
      return 'MM/dd/yyyy';
    case dateFormatDmy:
      return 'dd/MM/yyyy';
    case dateFormatDmY:
      return 'dd.MM.yyyy';
    case dateFormatYmd:
    default:
      return 'yyyy-MM-dd';
  }
}

/// Maps API time format key to Dart intl DateFormat pattern (time only).
String timeFormatPatternFromKey(String? key) {
  switch (key) {
    case timeFormat12h:
      return 'hh:mm a';
    case timeFormat24h:
    default:
      return 'HH:mm';
  }
}

/// Format a [DateTime] as date string using the API date format key.
String formatDate(DateTime? date, String? dateFormatKey) {
  if (date == null) return '';
  final pattern = dateFormatPatternFromKey(dateFormatKey);
  return DateFormat(pattern).format(date);
}

/// Format a [DateTime] as time string using the API time format key.
String formatTime(DateTime? date, String? timeFormatKey) {
  if (date == null) return '';
  final pattern = timeFormatPatternFromKey(timeFormatKey);
  return DateFormat(pattern).format(date);
}

/// Format a [DateTime] as date and time using API keys.
String formatDateTime(DateTime? date, String? dateFormatKey, String? timeFormatKey) {
  if (date == null) return '';
  final d = formatDate(date, dateFormatKey);
  final t = formatTime(date, timeFormatKey);
  return '$d $t';
}

/// Format a date range (e.g. for time entry start–end display).
String formatDateRange(DateTime? start, DateTime? end, String? dateFormatKey) {
  if (start == null && end == null) return 'No date';
  if (start != null && end != null) {
    final s = formatDate(start, dateFormatKey);
    final e = formatDate(end, dateFormatKey);
    if (s == e) return s;
    return '$s - $e';
  }
  if (start != null) return formatDate(start, dateFormatKey);
  if (end != null) return formatDate(end, dateFormatKey);
  return 'No date';
}
