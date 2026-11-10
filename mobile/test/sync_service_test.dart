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

  group('queue helpers', () {
    test('normalizeQueueOp fills defaults', () {
      final op = normalizeQueueOp({'op': 'timer_stop'});
      expect(op['status'], 'pending');
      expect(op['attempts'], 0);
      expect(op['lastError'], '');
      expect(op['id'], isNotEmpty);
      expect(op['createdAt'], isNotEmpty);
    });

    test('markOpAttemptFailure increments attempts and sets backoff', () {
      final now = DateTime.utc(2026, 1, 1, 12);
      final failedOnce = markOpAttemptFailure(
        {'op': 'timer_start', 'status': 'pending', 'attempts': 0},
        Exception('network down'),
        now: now,
      );
      expect(failedOnce['attempts'], 1);
      expect(failedOnce['status'], 'pending');
      expect(failedOnce['lastError'], contains('network down'));
      expect(failedOnce['nextAttemptAt'], isNotNull);
      final nextAt = DateTime.parse(failedOnce['nextAttemptAt'] as String);
      expect(nextAt.isAfter(now), isTrue);
    });

    test('markOpAttemptFailure marks failed after max attempts', () {
      final op = markOpAttemptFailure(
        {
          'op': 'create_time_entry',
          'status': 'pending',
          'attempts': maxSyncAttempts - 1,
        },
        Exception('still failing'),
      );
      expect(op['attempts'], maxSyncAttempts);
      expect(op['status'], 'failed');
      expect(op.containsKey('nextAttemptAt'), isFalse);
    });

    test('shouldSkipUntilNextAttempt respects nextAttemptAt and failed', () {
      final now = DateTime.utc(2026, 1, 1, 12);
      expect(
        shouldSkipUntilNextAttempt({
          'status': 'pending',
          'nextAttemptAt': now.add(const Duration(minutes: 5)).toIso8601String(),
        }, now: now),
        isTrue,
      );
      expect(
        shouldSkipUntilNextAttempt({
          'status': 'pending',
          'nextAttemptAt': now.subtract(const Duration(minutes: 1)).toIso8601String(),
        }, now: now),
        isFalse,
      );
      expect(shouldSkipUntilNextAttempt({'status': 'failed'}, now: now), isTrue);
    });

    test('resetOpForRetry clears failure metadata', () {
      final reset = resetOpForRetry({
        'op': 'timer_stop',
        'status': 'failed',
        'attempts': 8,
        'lastError': 'boom',
        'nextAttemptAt': DateTime.now().toIso8601String(),
      });
      expect(reset['status'], 'pending');
      expect(reset['attempts'], 0);
      expect(reset['lastError'], '');
      expect(reset.containsKey('nextAttemptAt'), isFalse);
    });

    test('syncBackoffForAttempt grows exponentially', () {
      expect(syncBackoffForAttempt(1), const Duration(seconds: 1));
      expect(syncBackoffForAttempt(2), const Duration(seconds: 2));
      expect(syncBackoffForAttempt(3), const Duration(seconds: 4));
      expect(syncBackoffForAttempt(9).inSeconds, lessThanOrEqualTo(300));
    });
  });
}
