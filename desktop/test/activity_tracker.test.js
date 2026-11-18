'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const tracker = require('../src/main/activity-tracker');

describe('activity-tracker helpers', () => {
  it('isExcluded matches app or title substrings case-insensitively', () => {
    assert.equal(tracker.isExcluded('Chrome', 'Inbox', ['bank']), false);
    assert.equal(tracker.isExcluded('1Password', 'Vault', ['password']), true);
    assert.equal(tracker.isExcluded('Code', 'secret-notes.md', ['SECRET']), true);
    assert.equal(tracker.isExcluded('Slack', 'general', []), false);
  });

  it('pruneSamples drops entries older than retention', () => {
    const now = Date.now();
    const samples = [
      { timestamp: new Date(now - 20 * 86400000).toISOString(), app: 'old' },
      { timestamp: new Date(now - 2 * 86400000).toISOString(), app: 'recent' },
    ];
    const kept = tracker.pruneSamples(samples, 7);
    assert.equal(kept.length, 1);
    assert.equal(kept[0].app, 'recent');
  });

  it('purgeLocal clears the sample file under userDataPath', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tt-activity-'));
    const fakeStore = {
      data: { activity_tracker_enabled: false },
      get(key, def) {
        return Object.prototype.hasOwnProperty.call(this.data, key) ? this.data[key] : def;
      },
      set(key, value) {
        this.data[key] = value;
      },
    };
    tracker.start({ store: fakeStore, userDataPath: dir });
    const file = path.join(dir, 'activity-samples.json');
    fs.writeFileSync(
      file,
      JSON.stringify({
        samples: [{ timestamp: new Date().toISOString(), app: 'x', title: 'y', duration: 1 }],
      })
    );
    const result = tracker.purgeLocal();
    assert.equal(result.purged, true);
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.deepEqual(raw.samples, []);
    tracker.stop();
  });

  it('start respects feature flag off', () => {
    const fakeStore = {
      get(key, def) {
        if (key === 'activity_tracker_enabled') return false;
        return def;
      },
    };
    const result = tracker.start({ store: fakeStore, userDataPath: os.tmpdir() });
    assert.equal(result.started, false);
    assert.equal(result.reason, 'feature_flag_off');
    assert.equal(tracker.isEnabled(), false);
  });
});
