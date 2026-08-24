/**
 * Progressive enhancement: turn <select data-searchable-select> into a
 * filterable combobox with an optional inline "Create …" row (Issue #728).
 *
 * The native <select> stays in the DOM (hidden) so form posts and existing
 * change listeners keep working. Inline-create modals remain the create path.
 *
 * Optional attributes:
 *   data-searchable-select="client|project|task"
 *   data-can-create="1"
 *   data-filter-by="<parent select id>"  — only show options whose
 *     data-parent-id / data-client-id matches the parent value
 *   data-search-placeholder="…"
 */
(function () {
  'use strict';

  var DEFAULT_CREATE_LABEL = {
    client: 'Create client',
    project: 'Create project',
    task: 'Create task',
  };

  function getCreateLabel(kind) {
    var labels = window.ttCreateLabels || {};
    return labels[kind] || DEFAULT_CREATE_LABEL[kind] || 'Create';
  }

  function getCreatePermission(select) {
    return select.getAttribute('data-can-create') === '1';
  }

  function getKind(select) {
    return select.getAttribute('data-searchable-select') || 'option';
  }

  function getParentSelect(select) {
    var parentId = select.getAttribute('data-filter-by');
    if (!parentId) return null;
    return document.getElementById(parentId);
  }

  function optionParentId(opt) {
    return (
      opt.getAttribute('data-parent-id') ||
      opt.getAttribute('data-client-id') ||
      ''
    );
  }

  function readOptions(select) {
    var parent = getParentSelect(select);
    var parentValue = parent ? String(parent.value || '') : null;
    var opts = [];
    Array.prototype.forEach.call(select.options, function (opt) {
      // Empty placeholder is always included
      var isEmpty = !opt.value;
      if (!isEmpty && parentValue !== null) {
        // When a parent is selected, only show options matching that parent
        // (or options with no parent id — treated as "any"/global placeholders).
        // When parent is empty, show all options so the user can pick freely.
        if (parentValue) {
          var pid = optionParentId(opt);
          if (pid && pid !== parentValue) return;
        }
      }
      opts.push({
        value: opt.value,
        label: (opt.textContent || '').trim(),
        selected: opt.selected,
        disabled: opt.disabled,
        parentId: optionParentId(opt),
      });
    });
    return opts;
  }

  function selectedLabel(select) {
    var opt = select.options[select.selectedIndex];
    return opt ? (opt.textContent || '').trim() : '';
  }

  function openCreateModal(kind, select, typedName) {
    var parent = getParentSelect(select);
    var opts = {
      targetSelect: select,
      name: typedName || '',
    };
    if (kind === 'project') {
      // Prefer page client select, then parent filter
      var clientSelect =
        document.querySelector('[data-inline-client-select]') ||
        document.getElementById('client_id') ||
        document.getElementById('startTimerClient') ||
        document.getElementById('editTimerClient') ||
        parent;
      if (clientSelect && clientSelect.value) {
        opts.clientId = clientSelect.value;
      }
    }
    if (kind === 'task') {
      var projectSelect =
        parent ||
        document.querySelector('[data-inline-project-select]') ||
        document.getElementById('project_id') ||
        document.getElementById('startTimerProject');
      if (projectSelect && projectSelect.value) {
        opts.projectId = projectSelect.value;
      }
    }

    if (window.ttInlineCreate && typeof window.ttInlineCreate.open === 'function') {
      window.ttInlineCreate.open(kind, opts);
      return;
    }

    // Fallback: click legacy trigger / open modal DOM directly
    var triggerSelector =
      kind === 'client'
        ? '#openCreateClientModal, [data-open-create-client]'
        : kind === 'project'
          ? '#openCreateProjectModal, [data-open-create-project]'
          : '#openCreateTaskModal, [data-open-create-task]';
    var trigger = document.querySelector(triggerSelector);
    var nameInputId =
      kind === 'client'
        ? 'inline_client_name'
        : kind === 'project'
          ? 'inline_project_name'
          : 'inline_task_name';

    if (typedName) {
      setTimeout(function () {
        var input = document.getElementById(nameInputId);
        if (input) {
          input.value = typedName;
          try {
            input.dispatchEvent(new Event('input', { bubbles: true }));
          } catch (_) {}
        }
      }, 50);
    }

    if (trigger) {
      trigger.click();
      return;
    }

    var modalId =
      kind === 'client'
        ? 'createClientModal'
        : kind === 'project'
          ? 'createProjectModal'
          : 'createTaskInlineModal';
    var modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
    }
  }

  function ensureSelectId(select) {
    if (select.id) return select.id;
    var kind = getKind(select);
    var generated =
      'tt-searchable-' +
      kind +
      '-' +
      Math.random().toString(36).slice(2, 9);
    select.id = generated;
    return generated;
  }

  function optionDomId(listId, opt) {
    var raw = opt.value === '' ? 'empty' : String(opt.value);
    var safe = raw.replace(/[^a-zA-Z0-9_-]/g, '_');
    return listId + '-opt-' + safe;
  }

  function enhanceSelect(select) {
    if (!select || select.tagName !== 'SELECT') return;
    if (select.dataset.searchableEnhanced === '1') {
      // Already enhanced: refresh display if options changed
      var existingInput = select.parentNode && select.parentNode.querySelector('.tt-searchable-input');
      if (existingInput) existingInput.value = selectedLabel(select);
      return;
    }
    // Skip locked/hidden auto-client inputs (macro renders INPUT, not SELECT)
    if (select.disabled && select.options.length <= 1) return;

    select.dataset.searchableEnhanced = '1';
    select.classList.add('sr-only');
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;

    var kind = getKind(select);
    var canCreate = getCreatePermission(select);
    var selectId = ensureSelectId(select);
    var listId = selectId + '-searchable-list';
    var wrapper = document.createElement('div');
    wrapper.className = 'tt-searchable-select relative';
    wrapper.setAttribute('data-searchable-kind', kind);

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-input w-full tt-searchable-input';
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', listId);
    input.placeholder = select.getAttribute('data-search-placeholder') || 'Type to search…';
    input.value = selectedLabel(select);

    var list = document.createElement('ul');
    list.id = listId;
    list.className =
      'tt-searchable-list hidden absolute z-40 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg py-1';
    list.setAttribute('role', 'listbox');

    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(list);
    // Keep select after input so label[for] still works; visually hidden
    wrapper.appendChild(select);

    var activeIndex = -1;
    var filtered = [];

    function clearActiveDescendant() {
      input.removeAttribute('aria-activedescendant');
      activeIndex = -1;
      list.querySelectorAll('[role="option"]').forEach(function (el) {
        el.setAttribute('aria-selected', 'false');
        el.classList.remove('bg-blue-100', 'dark:bg-blue-800');
      });
    }

    function closeList() {
      list.classList.add('hidden');
      input.setAttribute('aria-expanded', 'false');
      clearActiveDescendant();
    }

    function openList() {
      list.classList.remove('hidden');
      input.setAttribute('aria-expanded', 'true');
    }

    function setValue(value, label) {
      select.value = value;
      input.value = label || selectedLabel(select);
      try {
        select.dispatchEvent(new Event('change', { bubbles: true }));
      } catch (_) {}
      closeList();
    }

    function renderList(query) {
      var q = (query || '').trim().toLowerCase();
      var options = readOptions(select);
      filtered = options.filter(function (o) {
        if (!q) return true;
        return (o.label || '').toLowerCase().indexOf(q) !== -1;
      });

      list.innerHTML = '';
      clearActiveDescendant();

      if (filtered.length === 0 && !(canCreate && q)) {
        var empty = document.createElement('li');
        empty.className = 'px-3 py-2 text-sm text-gray-500 dark:text-gray-400';
        empty.textContent = 'No matches';
        list.appendChild(empty);
      }

      filtered.forEach(function (o, idx) {
        var li = document.createElement('li');
        li.id = optionDomId(listId, o);
        li.className =
          'px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-900 dark:text-gray-100';
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', o.value === select.value ? 'true' : 'false');
        li.setAttribute('data-index', String(idx));
        li.setAttribute('data-value', o.value);
        li.textContent = o.label || '(empty)';
        if (o.value === select.value) {
          li.classList.add('bg-blue-50', 'dark:bg-blue-900/40', 'font-medium');
        }
        li.addEventListener('mousedown', function (e) {
          e.preventDefault();
          setValue(o.value, o.label);
        });
        list.appendChild(li);
      });

      if (canCreate && q) {
        var exact = options.some(function (o) {
          return (o.label || '').toLowerCase() === q;
        });
        // For task/project create, require a parent when filter-by is set
        var parent = getParentSelect(select);
        var parentOk = !parent || !!parent.value || kind === 'client';
        // Project can be created with client from page even without filter-by parent
        if (kind === 'project') parentOk = true;
        if (kind === 'task' && parent && !parent.value) parentOk = false;

        if (!exact && parentOk) {
          var createLi = document.createElement('li');
          createLi.id = listId + '-opt-create';
          createLi.className =
            'px-3 py-2 text-sm cursor-pointer border-t border-gray-100 dark:border-gray-700 text-primary hover:bg-blue-50 dark:hover:bg-blue-900/30 font-medium';
          createLi.setAttribute('role', 'option');
          createLi.setAttribute('aria-selected', 'false');
          createLi.setAttribute('data-create', '1');
          var createPrefix = getCreateLabel(kind);
          createLi.innerHTML =
            '<i class="fas fa-plus mr-1"></i>' +
            createPrefix +
            ' &ldquo;<span class="tt-create-name"></span>&rdquo;';
          createLi.querySelector('.tt-create-name').textContent = query.trim();
          createLi.addEventListener('mousedown', function (e) {
            e.preventDefault();
            closeList();
            openCreateModal(kind, select, query.trim());
          });
          list.appendChild(createLi);
        }
      }

      openList();
    }

    function highlight(delta) {
      var items = list.querySelectorAll('[role="option"]');
      if (!items.length) return;
      activeIndex = (activeIndex + delta + items.length) % items.length;
      items.forEach(function (el, i) {
        var isActive = i === activeIndex;
        el.classList.toggle('bg-blue-100', isActive);
        el.classList.toggle('dark:bg-blue-800', isActive);
        el.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      var active = items[activeIndex];
      if (active && active.id) {
        input.setAttribute('aria-activedescendant', active.id);
      } else {
        input.removeAttribute('aria-activedescendant');
      }
      active.scrollIntoView({ block: 'nearest' });
    }

    input.addEventListener('focus', function () {
      renderList(input.value === selectedLabel(select) ? '' : input.value);
    });
    input.addEventListener('input', function () {
      renderList(input.value);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (list.classList.contains('hidden')) renderList(input.value);
        else highlight(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlight(-1);
      } else if (e.key === 'Enter') {
        if (!list.classList.contains('hidden')) {
          e.preventDefault();
          var items = list.querySelectorAll('[role="option"]');
          var target = activeIndex >= 0 ? items[activeIndex] : items[0];
          if (target) {
            if (target.getAttribute('data-create') === '1') {
              openCreateModal(kind, select, input.value.trim());
              closeList();
            } else {
              setValue(target.getAttribute('data-value'), target.textContent);
            }
          }
        }
      } else if (e.key === 'Escape') {
        closeList();
        input.value = selectedLabel(select);
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrapper.contains(e.target)) closeList();
    });

    // Keep display in sync when code sets select.value / options (inline create)
    select.addEventListener('change', function () {
      input.value = selectedLabel(select);
    });
    var mo = new MutationObserver(function () {
      input.value = selectedLabel(select);
    });
    mo.observe(select, { childList: true, subtree: true, attributes: true });

    // When parent select changes, clear invalid selection and refresh display
    var parentSelect = getParentSelect(select);
    if (parentSelect) {
      parentSelect.addEventListener('change', function () {
        var current = select.options[select.selectedIndex];
        if (current && current.value) {
          var pid = optionParentId(current);
          var parentVal = String(parentSelect.value || '');
          if (parentVal && pid && pid !== parentVal) {
            select.value = '';
            input.value = selectedLabel(select);
            try {
              select.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (_) {}
          }
        }
        input.value = selectedLabel(select);
      });
    }
  }

  function initAll() {
    document.querySelectorAll('select[data-searchable-select]').forEach(enhanceSelect);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Expose for dynamically injected selects / after task option refresh
  window.ttEnhanceSearchableSelects = initAll;
})();
