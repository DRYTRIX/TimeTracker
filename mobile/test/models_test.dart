import 'package:flutter_test/flutter_test.dart';
import 'package:timetracker_mobile/data/models/time_entry.dart';
import 'package:timetracker_mobile/data/models/project.dart';
import 'package:timetracker_mobile/data/models/task.dart';

void main() {
  group('TimeEntry', () {
    test('creates from JSON', () {
      final json = {
        'id': 1,
        'user_id': 1,
        'project_id': 1,
        'start_time': '2024-01-01T10:00:00Z',
        'end_time': '2024-01-01T12:00:00Z',
        'duration_seconds': 7200,
        'source': 'manual',
        'billable': true,
        'paid': false,
        'created_at': '2024-01-01T10:00:00Z',
        'updated_at': '2024-01-01T12:00:00Z',
      };

      final entry = TimeEntry.fromJson(json);

      expect(entry.id, 1);
      expect(entry.userId, 1);
      expect(entry.projectId, 1);
      expect(entry.durationSeconds, 7200);
      expect(entry.source, 'manual');
      expect(entry.billable, true);
    });

    test('formats duration correctly', () {
      final entry = TimeEntry(
        id: 1,
        userId: 1,
        startTime: DateTime.now().subtract(const Duration(hours: 2, minutes: 30)),
        source: 'auto',
        billable: true,
        paid: false,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        durationSeconds: 9000, // 2h 30m
      );

      expect(entry.formattedDuration, '2h 30m');
    });
  });

  group('Project', () {
    test('creates from JSON', () {
      final json = {
        'id': 1,
        'name': 'Test Project',
        'client': 'Test Client',
        'status': 'active',
        'billable': true,
        'created_at': '2024-01-01T10:00:00Z',
        'updated_at': '2024-01-01T10:00:00Z',
      };

      final project = Project.fromJson(json);

      expect(project.id, 1);
      expect(project.name, 'Test Project');
      expect(project.client, 'Test Client');
      expect(project.status, 'active');
    });
  });

  group('Task', () {
    test('creates from JSON', () {
      final json = {
        'id': 1,
        'project_id': 1,
        'name': 'Test Task',
        'status': 'todo',
        'priority': 'medium',
        'created_by': 1,
        'created_at': '2024-01-01T10:00:00Z',
        'updated_at': '2024-01-01T10:00:00Z',
      };

      final task = Task.fromJson(json);

      expect(task.id, 1);
      expect(task.projectId, 1);
      expect(task.name, 'Test Task');
      expect(task.status, 'todo');
    });
  });
}
