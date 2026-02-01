import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timetracker_mobile/main.dart';

void main() {
  testWidgets('App initializes', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const ProviderScope(child: TimeTrackerApp()));

    // Verify that the app starts (splash screen or login)
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
