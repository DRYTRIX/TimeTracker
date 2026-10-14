/**
 * Insights tab: today stats, weekly goal, 7-day chart, top projects.
 * Data comes from /reports/summary, /time-entries and /weekly-goals —
 * no server changes required.
 */

import { dailyTotals, formatHM, colorForProject } from '../lib/format.js';
import { decodeEntities } from './text.js';

const el = (id) => document.getElementById(id);

function round1(n) {
  return Math.round(n * 10) / 10;
}

function formatHours(n) {
  return `${round1(n).toFixed(1).replace(/\.0$/, '')} h`;
}

export function initInsightsTab(ctx) {
  const els = {
    statToday: el('stat-today'),
    statBillable: el('stat-billable'),
    statEntries: el('stat-entries'),
    goalCard: el('goal-card'),
    goalLabel: el('goal-label'),
    goalFill: el('goal-fill'),
    goalSub: el('goal-sub'),
    weekAvg: el('week-avg'),
    weekChart: el('week-chart'),
    topProjects: el('top-projects'),
  };

  function renderStats() {
    const activeSeconds = ctx.activeElapsedSeconds();
    const activeBillable = ctx.state.timer?.billable ? activeSeconds : 0;
    els.statToday.textContent = formatHM((ctx.state.todaySeconds || 0) + activeSeconds);
    els.statBillable.textContent = formatHM((ctx.state.billableSecondsToday || 0) + activeBillable);
    els.statEntries.textContent = String(ctx.state.todayEntries ?? 0);
  }

  function renderGoal(goal) {
    if (!goal || !Number(goal.target_hours)) {
      els.goalCard.hidden = true;
      return;
    }
    const target = Number(goal.target_hours);
    const actual = Number(goal.actual_hours) || 0;
    const progress = Math.min(100, Math.round((Number(goal.progress_percentage) || 0)));
    els.goalCard.hidden = false;
    els.goalLabel.textContent = `${round1(actual)} / ${round1(target)} h`;
    els.goalFill.style.width = `${progress}%`;
    const remaining = Math.max(0, target - actual);
    els.goalSub.textContent =
      progress >= 100 ? 'Weekly goal reached' : `${round1(remaining)} h left this week`;
  }

  function renderChart(entries, now) {
    const daily = dailyTotals(entries, 7, now);
    const W = 316;
    const BASE = 78;
    const MAX_H = 56;
    const LABEL_Y = 95;
    const barW = 30;
    const gap = (W - 16 - barW * 7) / 6;
    const max = Math.max(4, ...daily.map((d) => d.hours));

    const rects = [];
    const labels = [];
    daily.forEach((d, i) => {
      const x = 8 + i * (barW + gap);
      const h = d.hours > 0 ? Math.max(6, (d.hours / max) * MAX_H) : 3;
      const y = BASE - h;
      const isToday = i === daily.length - 1;
      const rx = h >= 12 ? 8 : h / 2;
      rects.push(
        `<rect class="bar${isToday ? ' today' : ''}" x="${x}" y="${y.toFixed(1)}" ` +
          `width="${barW}" height="${h.toFixed(1)}" rx="${rx}"></rect>`
      );
      if (isToday && d.hours > 0) {
        rects.push(
          `<text class="val" x="${(x + barW / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" ` +
            `text-anchor="middle">${round1(d.hours)}</text>`
        );
      }
      labels.push(
        `<text x="${(x + barW / 2).toFixed(1)}" y="${LABEL_Y}" text-anchor="middle">${d.letter}</text>`
      );
    });

    const total = daily.reduce((sum, d) => sum + d.hours, 0);
    els.weekAvg.textContent = `avg ${round1(total / 7)} h`;
    els.weekChart.innerHTML =
      `<svg viewBox="0 0 ${W} 100" role="img" aria-label="Hours tracked per day over the last seven days">` +
      `<title>Hours per day for the last 7 days, average ${round1(total / 7)} hours</title>` +
      rects.join('') +
      labels.join('') +
      '</svg>';
  }

  function renderTopProjects(byProject) {
    const top = [...(byProject || [])]
      .sort((a, b) => (b.hours || 0) - (a.hours || 0))
      .slice(0, 3);
    if (!top.length) {
      els.topProjects.innerHTML = '<p class="block-sub">No time tracked in the last 7 days.</p>';
      return;
    }
    const max = top[0].hours || 1;
    els.topProjects.innerHTML = '';
    for (const p of top) {
      const row = document.createElement('div');
      row.className = 'top-row';
      const name = p.project_name || `Project #${p.project_id ?? ''}`;
      row.innerHTML =
        `<span class="pdot" style="background:${colorForProject(p.project_id)}"></span>` +
        `<span class="top-name"></span><span class="top-h">${formatHours(p.hours || 0)}</span>`;
      row.querySelector('.top-name').textContent = decodeEntities(name);
      els.topProjects.appendChild(row);

      const track = document.createElement('div');
      track.className = 'top-track';
      const fill = document.createElement('div');
      fill.style.width = `${Math.max(3, Math.round(((p.hours || 0) / max) * 100))}%`;
      fill.style.background = colorForProject(p.project_id);
      track.appendChild(fill);
      els.topProjects.appendChild(track);
    }
  }

  function renderAll() {
    renderStats();
    renderGoal(ctx.state.weeklyGoal);
    renderChart(ctx.state.weekEntries || [], new Date());
    renderTopProjects(ctx.state.weekByProject || []);
  }

  return { renderAll };
}
