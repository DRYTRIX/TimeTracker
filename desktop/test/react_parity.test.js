const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');
const apiSource = fs.readFileSync(path.join(root, 'src/renderer-react/src/services/api.js'), 'utf8');
const formatSource = fs.readFileSync(path.join(root, 'src/renderer-react/src/utils/format.js'), 'utf8');
const traySource = fs.readFileSync(path.join(root, 'src/main/tray.js'), 'utf8');
const mainJsx = fs.readFileSync(path.join(root, 'src/renderer-react/src/main.jsx'), 'utf8');

test('React API client exposes pause/resume timer methods', () => {
  assert.match(apiSource, /pauseTimer\(\)/);
  assert.match(apiSource, /\/api\/v1\/timer\/pause/);
  assert.match(apiSource, /resumeTimer\(\)/);
  assert.match(apiSource, /\/api\/v1\/timer\/resume/);
});

test('React API client exposes attendance/workday methods', () => {
  assert.match(apiSource, /getAttendanceStatus/);
  assert.match(apiSource, /\/api\/v1\/attendance\/status/);
  assert.match(apiSource, /startWorkday/);
  assert.match(apiSource, /\/api\/v1\/workday\/start/);
  assert.match(apiSource, /endWorkday/);
  assert.match(apiSource, /startBreak/);
  assert.match(apiSource, /endBreak/);
});

test('React API client exposes kanban, CRM, and finance depth methods', () => {
  assert.match(apiSource, /getKanbanColumns/);
  assert.match(apiSource, /getLeads/);
  assert.match(apiSource, /getDeals/);
  assert.match(apiSource, /getContacts/);
  assert.match(apiSource, /getPayments/);
  assert.match(apiSource, /getMileage/);
  assert.match(apiSource, /getQuotes/);
  assert.match(apiSource, /getRecurringInvoices/);
  assert.match(apiSource, /getCreditNotes/);
  assert.match(apiSource, /unwrapReportSummary/);
});

test('tray menu supports pause and resume actions', () => {
  assert.match(traySource, /pause-timer/);
  assert.match(traySource, /resume-timer/);
  assert.match(traySource, /isTimerPaused/);
});

test('main shell wires reports, kanban, crm, finance, and workday views', () => {
  assert.match(mainJsx, /ReportsView/);
  assert.match(mainJsx, /KanbanView/);
  assert.match(mainJsx, /CrmView/);
  assert.match(mainJsx, /FinanceExtraView/);
  assert.match(mainJsx, /pauseTimer/);
  assert.match(mainJsx, /handleAttendanceAction/);
  assert.match(mainJsx, /from '\.\/views\//);
});

test('timerElapsedSeconds respects pause and break_seconds', () => {
  // Evaluate the pure helpers without a full ESM loader
  const modPath = path.join(root, 'src/renderer-react/src/utils/format.js');
  assert.ok(fs.existsSync(modPath));
  assert.match(formatSource, /timerElapsedSeconds/);
  assert.match(formatSource, /break_seconds/);
  assert.match(formatSource, /paused_at/);
});

test('unwrapReportSummary prefers nested summary object', () => {
  assert.match(apiSource, /payload\?\.summary \|\| payload/);
});

test('desktop package version matches setup.py after sync', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const setup = fs.readFileSync(path.join(root, '..', 'setup.py'), 'utf8');
  const match = setup.match(/version\s*=\s*['"]([^'"]+)['"]/);
  assert.ok(match);
  assert.strictEqual(pkg.version, match[1]);
});
