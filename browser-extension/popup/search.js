/**
 * Unified project search: filters the project list by name or client name,
 * keyboard navigable, with an inline "create project" escape hatch.
 */

import { colorForProject } from '../lib/format.js';
import { displayHtml } from './text.js';
import { icons } from '../lib/icons.js';

export function createProjectSearch({ wrapEl, input, listEl, getProjects, onSelect, onCreate }) {
  let open = false;
  let items = [];
  let activeIndex = -1;
  let query = '';

  function currentProjects() {
    return typeof getProjects === 'function' ? getProjects() : [];
  }

  function close() {
    open = false;
    activeIndex = -1;
    listEl.classList.add('hidden');
    listEl.innerHTML = '';
  }

  function filtered() {
    const q = query.trim().toLowerCase();
    const projects = currentProjects();
    if (!q) return projects.slice(0, 8);
    return projects
      .filter((p) => {
        const haystack = `${p.name} ${p.clientName || ''}`.toLowerCase();
        return haystack.includes(q);
      })
      .slice(0, 8);
  }

  function render() {
    const matches = filtered();
    const q = query.trim();
    const exact = q
      ? currentProjects().some((p) => p.name.toLowerCase() === q.toLowerCase())
      : true;
    const canCreate = q.length >= 2 && !exact;

    items = [...matches];
    if (canCreate) items.push({ __create: true, name: q });

    listEl.innerHTML = '';
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'result-empty';
      empty.textContent = 'No projects match your search';
      listEl.appendChild(empty);
    }

    items.forEach((item, index) => {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'result';
      row.setAttribute('role', 'option');
      if (index === activeIndex) row.classList.add('is-active');
      if (item.__create) {
        row.classList.add('result-create');
        row.innerHTML = `${icons.plus}<span>Create project “${displayHtml(item.name)}”</span>`;
      } else {
        const dot = `<span class="pdot" style="background:${colorForProject(item.id)}"></span>`;
        const star = item.favorite
          ? `<span class="r-star">${icons.star}</span>`
          : '';
        const client = item.clientName
          ? `<span class="r-client">${displayHtml(item.clientName)}</span>`
          : '';
        row.innerHTML = `${dot}<span>${displayHtml(item.name)}</span>${star}${client}`;
      }
      // mousedown fires before the input's blur, so selection survives it
      row.addEventListener('mousedown', (event) => {
        event.preventDefault();
        pick(index);
      });
      listEl.appendChild(row);
    });

    open = true;
    listEl.classList.remove('hidden');
  }

  function pick(index) {
    const item = items[index];
    if (!item) return;
    close();
    input.value = '';
    query = '';
    if (item.__create) onCreate?.(item.name);
    else onSelect?.(item);
  }

  function move(delta) {
    if (!items.length) return;
    activeIndex = (activeIndex + delta + items.length) % items.length;
    render();
  }

  input.addEventListener('input', () => {
    query = input.value;
    activeIndex = -1;
    render();
  });

  input.addEventListener('focus', () => render());

  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!open) render();
      else move(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      move(-1);
    } else if (event.key === 'Enter') {
      if (open && items.length) {
        event.preventDefault();
        pick(activeIndex >= 0 ? activeIndex : 0);
      }
    } else if (event.key === 'Escape') {
      close();
      input.blur();
    }
  });

  input.addEventListener('blur', () => {
    // allow mousedown selection to run first
    setTimeout(() => {
      if (!listEl.matches(':hover')) close();
    }, 120);
  });

  return { close };
}

