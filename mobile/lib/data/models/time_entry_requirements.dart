import 'package:flutter/foundation.dart';

@immutable
class TimeEntryRequirements {
  final bool requireTask;
  final bool requireDescription;
  final int descriptionMinLength;

  const TimeEntryRequirements({
    this.requireTask = false,
    this.requireDescription = false,
    this.descriptionMinLength = 0,
  });

  factory TimeEntryRequirements.fromJson(Map<String, dynamic>? json) {
    if (json == null || json.isEmpty) {
      return const TimeEntryRequirements();
    }
    return TimeEntryRequirements(
      requireTask: json['require_task'] == true,
      requireDescription: json['require_description'] == true,
      descriptionMinLength: (json['description_min_length'] as num?)?.toInt() ?? 0,
    );
  }
}
