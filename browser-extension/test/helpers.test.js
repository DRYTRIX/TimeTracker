import test from 'node:test';
import assert from 'node:assert/strict';
import {
  colorForProject,
  dailyTotals,
  entryDurationSeconds,
  formatClock,
  formatHM,
  groupEntriesByDay,
  localDateKey,
  noteSuggestions,
  weekdayLetter,
  addDays,
} from '../lib/format.js';

test('formatClock renders h:mm:ss above one hour and m:ss below', () => {
  assert.equal(formatClock(5077), '1:24:37');
  assert.equal(formatClock(94), '1:34');
  assert.equal(formatClock(0), '0:00');
  assert.equal(formatClock(-5), '0:00');
});

test('formatHM renders hours and minutes', () => {
  assert.equal(formatHM(5 * 3600 + 12 * 60), '5:12');
  assert.equal(formatHM(0), '0:00');
});

test('colorForProject is stable per id and valid', () => {
  assert.equal(colorForProject(1), colorForProject(1));
  assert.equal(colorForProject(1), colorForProject(9));
  assert.match(colorForProject(2), /^#[0-9a-f]{6}$/);
  assert.equal(colorForProject(undefined), colorForProject('not-a-number'));
});

test('localDateKey and addDays work on local dates', () => {
  const d = new Date(2026, 9, 13); // Oct 13 2026 local
  assert.equal(localDateKey(d), '2026-10-13');
  assert.equal(localDateKey(addDays(d, -1)), '2026-10-12');
  assert.equal(weekdayLetter(d), 'T');
});

test('entryDurationSeconds computes live elapsed for active entries', () => {
  const now = Date.parse('2026-10-13T14:26:37');
  const active = {
    is_active: true,
    start_time: '2026-10-13T13:02:00',
    paused_at: null,
    break_seconds: 0,
  };
  assert.equal(entryDurationSeconds(active, now), 5077);

  const paused = { ...active, paused_at: '2026-10-13T14:00:00' };
  assert.equal(entryDurationSeconds(paused, now), 3480);

  const withBreak = { ...active, break_seconds: 60 };
  assert.equal(entryDurationSeconds(withBreak, now), 5017);

  const finished = {
    is_active: false,
    start_time: '2026-10-13T08:00:00',
    end_time: '2026-10-13T09:00:00',
    duration_seconds: 3600,
    break_seconds: 0,
  };
  assert.equal(entryDurationSeconds(finished, now), 3600);
});

test('groupEntriesByDay buckets Today, Yesterday and weekday labels', () => {
  const now = new Date(2026, 9, 13, 18, 0); // Tuesday
  const entries = [
    { start_time: '2026-10-13T08:30:00' },
    { start_time: '2026-10-12T10:00:00' },
    { start_time: '2026-10-09T09:00:00' },
    { start_time: '2026-10-13T13:02:00' },
    { start_time: 'bogus' },
  ];
  const groups = groupEntriesByDay(entries, now);
  assert.deepEqual(
    groups.map((g) => g.label),
    ['Today', 'Yesterday', 'Friday']
  );
  assert.equal(groups[0].entries.length, 2);
});

test('dailyTotals returns exactly 7 buckets oldest-first and skips unknown days', () => {
  const now = new Date(2026, 9, 13, 18, 0);
  const entries = [
    { start_time: '2026-10-13T08:30:00', end_time: '2026-10-13T09:00:00', duration_seconds: 1800, is_active: false },
    { start_time: '2026-10-12T10:00:00', end_time: '2026-10-12T12:00:00', duration_seconds: 7200, is_active: false },
  ];
  const daily = dailyTotals(entries, 7, now);
  assert.equal(daily.length, 7);
  assert.equal(daily[6].hours > 0, true);
  assert.equal(daily[5].hours > 0, true);
  assert.equal(daily[0].hours, 0);
  assert.equal(daily[6].letter, 'T');
});

test('noteSuggestions dedupes and respects limit', () => {
  const entries = [
    { notes: 'Design review' },
    { notes: '  design review  ' },
    { notes: 'Sprint planning' },
    { notes: '' },
    { notes: 'ok' },
    { notes: 'Code review' },
  ];
  assert.deepEqual(noteSuggestions(entries, 3), ['Design review', 'Sprint planning', 'Code review']);
});

test('formatBadgeText stays compact for the toolbar', async () => {
  const { formatBadgeText } = await import('../lib/api.js');
  assert.equal(formatBadgeText(5077), '1:24');
  assert.equal(formatBadgeText(600), ':10');
  assert.equal(formatBadgeText(3600 * 12), '12h');
});
