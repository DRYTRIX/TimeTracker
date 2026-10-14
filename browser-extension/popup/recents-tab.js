/**
 * Recents tab: recent entries grouped by day with one-click "track again".
 */

import { colorForProject, formatClock, formatTimeOf, groupEntriesByDay, entryDurationSeconds } from '../lib/format.js';
import { icons } from '../lib/icons.js';
import { decodeEntities } from './text.js';

const el = (id) => document.getElementById(id);

export function initRecentsTab(ctx) {
  const els = {
    list: el('recents-list'),
    historyBtn: el('btn-history'),
    historyArrow: el('history-arrow'),
  };

  els.historyArrow.innerHTML = icons['arrow-up-right'];
  els.historyBtn.addEventListener('click', () => {
    const url = ctx.state.serverUrl;
    if (url) chrome.tabs.create({ url });
  });

  function render() {
    const entries = ctx.state.recentEntries || [];
    if (!entries.length) {
      els.list.innerHTML = '<div class="card"><p class="block-sub">No entries in the last 7 days.</p></div>';
      return;
    }

    els.list.innerHTML = '';
    for (const group of groupEntriesByDay(entries)) {
      const card = document.createElement('div');
      card.className = 'card';

      const head = document.createElement('div');
      head.className = 'group-h';
      head.textContent = group.label;
      card.appendChild(head);

      for (const entry of group.entries) {
        card.appendChild(renderEntry(entry));
      }
      els.list.appendChild(card);
    }
  }

  function renderEntry(entry) {
    const row = document.createElement('div');
    row.className = 'entry';

    const dot = document.createElement('span');
    dot.className = 'pdot';
    dot.style.background = colorForProject(entry.project_id);
    row.appendChild(dot);

    const main = document.createElement('div');
    main.className = 'entry-main';
    const name = document.createElement('strong');
    name.textContent = decodeEntities(entry.project || entry.client || `Project #${entry.project_id ?? ''}`);
    const range = entry.is_active
      ? `${formatTimeOf(entry.start_time)}–now`
      : `${formatTimeOf(entry.start_time)}–${formatTimeOf(entry.end_time)}`;
    const sub = decodeEntities([entry.task, range].filter(Boolean).join(' · '));
    const subEl = document.createElement('span');
    subEl.textContent = sub;
    main.append(name, subEl);
    row.appendChild(main);

    const side = document.createElement('div');
    side.className = 'entry-side';
    const duration = document.createElement('strong');
    duration.textContent = formatClock(entryDurationSeconds(entry));
    side.appendChild(duration);

    const again = document.createElement('button');
    again.type = 'button';
    again.className = 'iconbtn';
    again.innerHTML = icons['rotate-ccw'];
    again.setAttribute(
      'aria-label',
      `Track again: ${entry.project || entry.client || 'entry'}`
    );
    again.setAttribute('data-tooltip', 'Track again');
    again.addEventListener('click', () => {
      void ctx.startTracking({
        projectId: entry.project_id,
        clientId: entry.client_id ?? null,
        taskId: entry.task_id ?? null,
      });
      ctx.switchTab('timer');
    });
    side.appendChild(again);
    row.appendChild(side);

    return row;
  }

  return { render };
}
