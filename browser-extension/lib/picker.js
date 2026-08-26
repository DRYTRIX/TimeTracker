/**
 * Searchable combobox with optional inline "Create …" row for the extension popup.
 * Mirrors app/static/searchable-select.js behaviour without depending on the web app.
 */

/**
 * @param {HTMLSelectElement} select
 * @param {{
 *   kind?: string,
 *   canCreate?: boolean,
 *   placeholder?: string,
 *   onCreate?: (typedName: string) => void | Promise<void>,
 *   canCreateGuard?: () => boolean,
 *   canCreateGuardHint?: string,
 * }} options
 */
export function enhanceSelect(select, options = {}) {
  if (!select || select.tagName !== 'SELECT') return null;
  if (select.dataset.pickerEnhanced === '1') {
    return select._ttPicker || null;
  }

  const kind = options.kind || select.getAttribute('data-searchable-select') || 'option';
  const canCreate =
    options.canCreate != null
      ? options.canCreate
      : select.getAttribute('data-can-create') === '1';
  const createLabels = { client: 'Create client', project: 'Create project', task: 'Create task' };

  select.dataset.pickerEnhanced = '1';
  select.classList.add('sr-only');
  select.setAttribute('aria-hidden', 'true');
  select.tabIndex = -1;

  const wrapper = document.createElement('div');
  wrapper.className = 'tt-picker relative';

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'tt-picker-input';
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-expanded', 'false');
  input.placeholder = options.placeholder || select.getAttribute('data-search-placeholder') || 'Type to search…';

  const list = document.createElement('ul');
  list.className = 'tt-picker-list hidden';
  list.setAttribute('role', 'listbox');

  select.parentNode.insertBefore(wrapper, select);
  wrapper.appendChild(input);
  wrapper.appendChild(list);
  wrapper.appendChild(select);

  function selectedLabel() {
    const opt = select.options[select.selectedIndex];
    return opt ? (opt.textContent || '').trim() : '';
  }

  function readOptions() {
    const opts = [];
    Array.prototype.forEach.call(select.options, (opt) => {
      opts.push({
        value: opt.value,
        label: (opt.textContent || '').trim(),
        disabled: opt.disabled,
      });
    });
    return opts;
  }

  function closeList() {
    list.classList.add('hidden');
    input.setAttribute('aria-expanded', 'false');
  }

  function setValue(value, label) {
    select.value = value;
    input.value = label || selectedLabel();
    try {
      select.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (_) {}
    closeList();
  }

  function renderList(query) {
    const q = (query || '').trim().toLowerCase();
    const optionsList = readOptions();
    const filtered = optionsList.filter((o) => {
      if (!q) return true;
      return (o.label || '').toLowerCase().includes(q);
    });

    list.innerHTML = '';
    if (!filtered.length && !(canCreate && q)) {
      const empty = document.createElement('li');
      empty.className = 'tt-picker-empty';
      empty.textContent = 'No matches';
      list.appendChild(empty);
    }

    filtered.forEach((o) => {
      const li = document.createElement('li');
      li.className = 'tt-picker-option';
      li.setAttribute('role', 'option');
      li.textContent = o.label || '(empty)';
      if (o.value === select.value) li.classList.add('is-selected');
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        setValue(o.value, o.label);
      });
      list.appendChild(li);
    });

    if (canCreate && q) {
      const exact = optionsList.some((o) => (o.label || '').toLowerCase() === q);
      if (!exact) {
        const guardOk =
          typeof options.canCreateGuard !== 'function' || options.canCreateGuard();
        if (!guardOk) {
          const hint = document.createElement('li');
          hint.className = 'tt-picker-hint';
          hint.textContent = options.canCreateGuardHint || 'Not available';
          list.appendChild(hint);
        } else {
          const createLi = document.createElement('li');
          createLi.className = 'tt-picker-create';
          createLi.setAttribute('role', 'option');
          createLi.textContent = `${createLabels[kind] || 'Create'} “${query.trim()}”`;
          createLi.addEventListener('mousedown', (e) => {
            e.preventDefault();
            closeList();
            if (typeof options.onCreate === 'function') {
              options.onCreate(query.trim());
            }
          });
          list.appendChild(createLi);
        }
      }
    }

    list.classList.remove('hidden');
    input.setAttribute('aria-expanded', 'true');
  }

  input.value = selectedLabel();

  input.addEventListener('focus', () => {
    renderList(input.value === selectedLabel() ? '' : input.value);
  });
  input.addEventListener('input', () => renderList(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeList();
      input.value = selectedLabel();
    } else if (e.key === 'Enter') {
      const createRow = list.querySelector('.tt-picker-create');
      const first = list.querySelector('.tt-picker-option');
      if (!list.classList.contains('hidden')) {
        e.preventDefault();
        if (createRow && !first) {
          createRow.dispatchEvent(new Event('mousedown'));
        } else if (first) {
          first.dispatchEvent(new Event('mousedown'));
        }
      }
    }
  });

  // Reset visible input when user types but does not commit a selection (Issue #728)
  input.addEventListener('blur', () => {
    setTimeout(() => {
      input.value = selectedLabel();
      closeList();
    }, 150);
  });

  document.addEventListener('click', (e) => {
    if (!wrapper.contains(e.target)) closeList();
  });

  select.addEventListener('change', () => {
    input.value = selectedLabel();
  });

  const api = {
    refresh() {
      input.value = selectedLabel();
    },
    setCanCreate(v) {
      options.canCreate = !!v;
    },
  };
  select._ttPicker = api;
  return api;
}
