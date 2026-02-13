import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/models/time_entry_requirements.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Fetches time entry requirements from /api/v1/users/me.
/// Returns default (all optional) when not authenticated or on error.
final timeEntryRequirementsProvider = FutureProvider<TimeEntryRequirements>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) {
    return const TimeEntryRequirements();
  }
  try {
    final data = await client.getUsersMe();
    final req = data['time_entry_requirements'];
    return TimeEntryRequirements.fromJson(req is Map ? Map<String, dynamic>.from(req as Map) : null);
  } catch (_) {
    return const TimeEntryRequirements();
  }
});
