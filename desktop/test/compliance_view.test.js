'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

test('desktop ComplianceView and Workforce wire Belgium attendance APIs', () => {
  const root = path.join(__dirname, '..');
  const compliance = fs.readFileSync(path.join(root, 'src/renderer-react/src/views/ComplianceView.jsx'), 'utf8');
  const workforce = fs.readFileSync(path.join(root, 'src/renderer-react/src/views/WorkforceView.jsx'), 'utf8');
  const api = fs.readFileSync(path.join(root, 'src/renderer-react/src/services/api.js'), 'utf8');

  assert.match(compliance, /getBelgiumAttendanceReport/);
  assert.match(compliance, /requestAttendanceCorrection/);
  assert.match(compliance, /getAttendanceHistory/);
  assert.match(workforce, /CompliancePanel/);
  assert.match(api, /\/api\/v1\/attendance\/history/);
  assert.match(api, /\/api\/v1\/attendance\/corrections/);
  assert.match(api, /belgium-attendance/);
});
