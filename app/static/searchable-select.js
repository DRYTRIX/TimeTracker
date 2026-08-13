/**
 * Progressive enhancement: turn <select data-searchable-select> into a
 * filterable combobox with an optional inline "Create …" row (Issue #728).
 *
 * The native <select> stays in the DOM (hidden) so form posts and existing
 * change listeners keep working. Inline-create modals remain the create path.
 */
(function () {
  'use strict';

  var CREATE_LABEL = {
    client: 'Create client',
    project: 'Create project',
  };

  function getCreatePermission(select) {
    return select.getAttribute('data-can-create') === '1';
  }

  function getKind(select) {
    return select.getAttribute('data-searchable-select') || 'option';
  }

  function readOptions(select) {
    var opts = [];
    Array.prototype.forEach.call(select.options, function (opt) {
      opts.push({
        value: opt.value,
        label: (opt.textContent || '').trim(),
        selected: opt.selected,
        disabled: opt.disabled,
      });
    });
    return opts;
  }

  function selectedLabel(select) {
    var opt = select.options[select.selectedIndex];
    return opt ? (opt.textContent || '').trim() : '';
  }

  function openCreateModal(kind, select, typedName) {
    var triggerSelector =
      kind === 'client'
        ? '#openCreateClientModal, [data-open-create-client]'
        : '#openCreateProjectModal, [data-open-create-project]';
    var trigger = document.querySelector(triggerSelector);
    var nameInputId = kind === 'client' ? 'inline_client_name' : 'inline_project_name';
    // Prefer a trigger that targets this select
    var scoped =
      kind === 'client'
        ? document.querySelector(
            '[data-open-create-client][data-client-select-id="' + select.id + '"], #openCreateClientModal[data-client-select-id="' + select.id + '"]'
          )
        : document.querySelector(
            '[data-open-create-project][data-project-select-id="' + select.id + '"], #openCreateProjectModal[data-project-select-id="' + select.id + '"]'
          );
    if (scoped) trigger = scoped;

    if (typedName) {
      // Prefill after modal opens (modal resets on show, so delay slightly)
      setTimeout(function () {
        var input = document.getElementById(nameInputId) || document.getElementById('client_name');
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

    // Fallback: open modal element directly
    var modalId = kind === 'client' ? 'createClientModal' : 'createProjectModal';
    var modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
    }
  }

  function enhanceSelect(select) {
    if (!select || select.tagName !== 'SELECT') return;
    if (select.dataset.searchableEnhanced === '1') return;
    // Skip locked/hidden auto-client inputs (macro renders INPUT, not SELECT)
    if (select.disabled && select.options.length <= 1) return;

    select.dataset.searchableEnhanced = '1';
    select.classList.add('sr-only');
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;

    var kind = getKind(select);
    var canCreate = getCreatePermission(select);
    var wrapper = document.createElement('div');
    wrapper.className = 'tt-searchable-select relative';
    wrapper.setAttribute('data-searchable-kind', kind);

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-input w-full tt-searchable-input';
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', select.id + '-searchable-list');
    input.placeholder = select.getAttribute('data-search-placeholder') || 'Type to search…';
    input.value = selectedLabel(select);

    var list = document.createElement('ul');
    list.id = select.id + '-searchable-list';
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

    function closeList() {
      list.classList.add('hidden');
      input.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
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
      activeIndex = -1;

      if (filtered.length === 0 && !(canCreate && q)) {
        var empty = document.createElement('li');
        empty.className = 'px-3 py-2 text-sm text-gray-500 dark:text-gray-400';
        empty.textContent = 'No matches';
        list.appendChild(empty);
      }

      filtered.forEach(function (o, idx) {
        var li = document.createElement('li');
        li.className =
          'px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-900 dark:text-gray-100';
        li.setAttribute('role', 'option');
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
        if (!exact) {
          var createLi = document.createElement('li');
          createLi.className =
            'px-3 py-2 text-sm cursor-pointer border-t border-gray-100 dark:border-gray-700 text-primary hover:bg-blue-50 dark:hover:bg-blue-900/30 font-medium';
          createLi.setAttribute('role', 'option');
          createLi.setAttribute('data-create', '1');
          var createPrefix = CREATE_LABEL[kind] || 'Create';
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
        el.classList.toggle('bg-blue-100', i === activeIndex);
        el.classList.toggle('dark:bg-blue-800', i === activeIndex);
      });
      items[activeIndex].scrollIntoView({ block: 'nearest' });
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
  }

  function initAll() {
    document.querySelectorAll('select[data-searchable-select]').forEach(enhanceSelect);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Expose for dynamically injected selects
  window.ttEnhanceSearchableSelects = initAll;
})();
