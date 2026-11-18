import 'package:flutter_test/flutter_test.dart';
import 'package:timetracker_mobile/data/storage/sync_service.dart';

/// Widget-adjacent unit coverage for offline timer stop queueing.
/// Ensures stop ops use timer_stop + retry/backoff parity with desktop (max 8).
void main() {
  group('offline timer stop queue', () {
    test('normalizeQueueOp for timer_stop sets pending defaults', () {
      final op = normalizeQueueOp({
        'op': 'timer_stop',
        'payload': {'ended_at': '2026-01-01T12:00:00Z'},
      });
      expect(op['op'], 'timer_stop');
      expect(op['status'], 'pending');
      expect(op['attempts'], 0);
      expect(op['id'], isNotEmpty);
    });

    test('timer_stop exhausts retries then marks failed like desktop', () {
      var op = normalizeQueueOp({'op': 'timer_stop'});
      for (var i = 0; i < maxSyncAttempts; i++) {
        op = markOpAttemptFailure(op, Exception('offline'));
      }
      expect(op['attempts'], maxSyncAttempts);
      expect(op['status'], 'failed');
      expect(maxSyncAttempts, 8);
    });

    test('resetOpForRetry restores pending timer_stop', () {
      final failed = markOpAttemptFailure(
        {
          'op': 'timer_stop',
          'status': 'pending',
          'attempts': maxSyncAttempts - 1,
        },
        Exception('offline'),
      );
      expect(failed['status'], 'failed');
      final reset = resetOpForRetry(failed);
      expect(reset['status'], 'pending');
      expect(reset['attempts'], 0);
      expect(reset['op'], 'timer_stop');
    });
  });
}
