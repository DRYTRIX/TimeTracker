import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';
import 'package:timetracker_mobile/data/models/user_prefs.dart';
import 'package:timetracker_mobile/presentation/providers/api_provider.dart';

/// Fetches current user from /api/v1/users/me and exposes resolved date/time format and timezone.
/// When not authenticated or on error, returns default prefs.
final userPrefsProvider = FutureProvider<UserPrefs>((ref) async {
  final client = await ref.watch(apiClientProvider.future);
  if (client == null) {
    return const UserPrefs();
  }
  try {
    final user = await client.getCurrentUser();
    return UserPrefs.fromJson(user);
  } catch (_) {
    return const UserPrefs();
  }
});
