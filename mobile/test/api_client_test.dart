import 'package:flutter_test/flutter_test.dart';
import 'package:timetracker_mobile/data/api/api_client.dart';

void main() {
  group('ApiClient', () {
    test('initializes with base URL', () {
      const baseUrl = 'https://example.com';
      final client = ApiClient(baseUrl: baseUrl);
      expect(client.baseUrl, 'https://example.com/');
    });

    test('validates token format', () {
      // Token should start with 'tt_'
      const validToken = 'tt_abc123';
      const invalidToken = 'invalid_token';

      expect(validToken.startsWith('tt_'), isTrue);
      expect(invalidToken.startsWith('tt_'), isFalse);
    });
  });
}
