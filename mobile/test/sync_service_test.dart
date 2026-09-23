import 'package:flutter_test/flutter_test.dart';
import 'package:timetracker_mobile/data/storage/sync_service.dart';

void main() {
  group('newSyncIdempotencyKey', () {
    test('returns RFC-4122-style UUID v4', () {
      final key = newSyncIdempotencyKey();
      expect(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ).hasMatch(key),
        isTrue,
      );
    });

    test('generates distinct keys', () {
      expect(newSyncIdempotencyKey(), isNot(newSyncIdempotencyKey()));
    });
  });
}
