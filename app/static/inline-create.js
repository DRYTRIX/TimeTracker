/**
 * Unified inline Create Client / Project / Task modals (Issue #728).
 *
 * Expects the shared partials:
 *   #createClientModal / #inlineCreateClientForm
 *   #createProjectModal / #inlineCreateProjectForm
 *   #createTaskInlineModal / #inlineCreateTaskForm
 *
 * Public API:
 *   window.ttInlineCreate.open(kind, { targetSelect, name, clientId, projectId })
 *
 * Also honours legacy click triggers:
 *   #openCreateClientModal, [data-open-create-client]
 *   #openCreateProjectModal, [data-open-create-project]
 *   #openCreateTaskModal, [data-open-create-task]
 */
(function () {
  'use strict';

  function getCsrfToken() {
    var tokenMeta = document.querySelector('meta[name="csrf-token"]');
    return tokenMeta ? tokenMeta.getAttribute('content') : '';
  }

  function resolveSelect(kind, trigger) {
    if (kind === 'client') {
      var cid = trigger && trigger.getAttribute('data-client-select-id');
      if (cid) return document.getElementById(cid);
      return (
        document.querySelector('[data-inline-client-select]') ||
        document.getElementById('client_id') ||
        document.getElementById('startTimerClient') ||
        document.getElementById('editTimerClient')
      );
    }
    if (kind === 'project') {
      var pid = trigger && trigger.getAttribute('data-project-select-id');
      if (pid) return document.getElementById(pid);
      return (
        document.querySelector('[data-inline-project-select]') ||
        document.getElementById('project_id') ||
        document.getElementById('startTimerProject')
      );
    }
    // task
    var tid = trigger && trigger.getAttribute('data-task-select-id');
    if (tid) return document.getElementById(tid);
    return (
      document.querySelector('[data-inline-task-select]') ||
      document.getElementById('task_id') ||
      document.getElementById('startTimerTask')
    );
  }

  function resolvePreferredClientId(trigger) {
    var fromAttr = trigger && trigger.getAttribute('data-preferred-client-id');
    if (fromAttr) return fromAttr;
    var clientSelect =
      document.querySelector('[data-inline-client-select]') ||
      document.getElementById('client_id') ||
      document.getElementById('startTimerClient') ||
      document.getElementById('editTimerClient');
    if (clientSelect && clientSelect.value) return clientSelect.value;
    return '';
  }

  function resolvePreferredProjectId(trigger) {
    var fromAttr = trigger && trigger.getAttribute('data-preferred-project-id');
    if (fromAttr) return fromAttr;
    var projectSelect =
      document.querySelector('[data-inline-project-select]') ||
      document.getElementById('project_id') ||
      document.getElementById('startTimerProject');
    if (projectSelect && projectSelect.value) return projectSelect.value;
    return '';
  }

  function appendOption(select, id, name, attrs) {
    if (!select || select.tagName !== 'SELECT') return;
    var existing = null;
    Array.prototype.forEach.call(select.options, function (o) {
      if (String(o.value) === String(id)) existing = o;
    });
    if (existing) {
      select.value = String(id);
      try {
        select.dispatchEvent(new Event('change', { bubbles: true }));
      } catch (_) {}
      return;
    }
    var opt = document.createElement('option');
    opt.value = String(id);
    opt.textContent = name;
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (attrs[k] != null) opt.setAttribute(k, String(attrs[k]));
      });
    }
    select.appendChild(opt);
    select.value = String(id);
    try {
      select.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (_) {}
  }

  // ---- Client ----
  var clientState = { targetSelect: null };

  function showClientModal(opts) {
    var modal = document.getElementById('createClientModal');
    var form = document.getElementById('inlineCreateClientForm');
    if (!modal || !form) return;
    opts = opts || {};
    clientState.targetSelect = opts.targetSelect || resolveSelect('client', null);
    var errorEl = document.getElementById('createClientError');
    var nameInput = document.getElementById('inline_client_name') || document.getElementById('client_name');
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    if (nameInput && opts.name) nameInput.value = opts.name;
    setTimeout(function () {
      if (nameInput) nameInput.focus();
    }, 0);
  }

  function hideClientModal() {
    var modal = document.getElementById('createClientModal');
    var form = document.getElementById('inlineCreateClientForm');
    var errorEl = document.getElementById('createClientError');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    if (form) form.reset();
    clientState.targetSelect = null;
  }

  // ---- Project ----
  var projectState = { targetSelect: null };

  function showProjectModal(opts) {
    var modal = document.getElementById('createProjectModal');
    var form = document.getElementById('inlineCreateProjectForm');
    if (!modal || !form) return;
    opts = opts || {};
    projectState.targetSelect = opts.targetSelect || resolveSelect('project', null);
    var errorEl = document.getElementById('createProjectError');
    var nameInput = document.getElementById('inline_project_name');
    var clientSelect = document.getElementById('inline_project_client_id');
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    var preferred = opts.clientId || '';
    if (clientSelect) {
      if (preferred) {
        clientSelect.value = preferred;
        clientSelect.disabled = true;
        clientSelect.setAttribute('data-locked', '1');
      } else {
        clientSelect.disabled = false;
        clientSelect.removeAttribute('data-locked');
      }
    }
    if (nameInput && opts.name) nameInput.value = opts.name;
    setTimeout(function () {
      if (nameInput) nameInput.focus();
    }, 0);
  }

  function hideProjectModal() {
    var modal = document.getElementById('createProjectModal');
    var form = document.getElementById('inlineCreateProjectForm');
    var errorEl = document.getElementById('createProjectError');
    var clientSelect = document.getElementById('inline_project_client_id');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    if (form) form.reset();
    var billable = document.getElementById('inline_project_billable');
    if (billable) billable.checked = true;
    if (clientSelect) {
      clientSelect.disabled = false;
      clientSelect.removeAttribute('data-locked');
    }
    projectState.targetSelect = null;
  }

  // ---- Task ----
  var taskState = { targetSelect: null };

  function showTaskModal(opts) {
    var modal = document.getElementById('createTaskInlineModal');
    var form = document.getElementById('inlineCreateTaskForm');
    if (!modal || !form) return;
    opts = opts || {};
    taskState.targetSelect = opts.targetSelect || resolveSelect('task', null);
    var errorEl = document.getElementById('createTaskInlineError');
    var nameInput = document.getElementById('inline_task_name');
    var projectSelect = document.getElementById('inline_task_project_id');
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    var preferred = opts.projectId || '';
    if (projectSelect && preferred) {
      projectSelect.value = preferred;
    }
    if (nameInput && opts.name) nameInput.value = opts.name;
    setTimeout(function () {
      if (nameInput) nameInput.focus();
    }, 0);
  }

  function hideTaskModal() {
    var modal = document.getElementById('createTaskInlineModal');
    var form = document.getElementById('inlineCreateTaskForm');
    var errorEl = document.getElementById('createTaskInlineError');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.textContent = '';
    }
    if (form) form.reset();
    taskState.targetSelect = null;
  }

  function setLoading(form, submitBtnId, creatingText, on) {
    var submitBtn = document.getElementById(submitBtnId);
    if (on) {
      if (submitBtn) {
        submitBtn.dataset.originalHtml = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>' + (creatingText || 'Creating...');
        submitBtn.disabled = true;
      }
      form.classList.add('loading');
    } else {
      if (submitBtn) {
        submitBtn.innerHTML = submitBtn.dataset.originalHtml || submitBtn.innerHTML;
        submitBtn.disabled = false;
      }
      form.classList.remove('loading');
    }
  }

  function initClientForm() {
    var form = document.getElementById('inlineCreateClientForm');
    if (!form || form.dataset.ttBound === '1') return;
    form.dataset.ttBound = '1';

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var errorEl = document.getElementById('createClientError');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }
      setLoading(form, 'submitCreateClient', form.dataset.creatingText, true);
      try {
        var formData = new FormData(form);
        var resp = await fetch(form.dataset.createUrl || '/clients/create', {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
          },
          body: formData,
          credentials: 'same-origin',
        });
        if (!resp.ok) {
          var msg = form.dataset.errorText || 'Could not create client. Please try again.';
          try {
            var errData = await resp.json();
            if (errData && (errData.message || (errData.messages && errData.messages[0]))) {
              msg = errData.message || errData.messages[0];
            }
          } catch (_) {}
          if (errorEl) {
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
          }
        } else {
          var data = await resp.json();
          var select = clientState.targetSelect || resolveSelect('client', null);
          if (select && select.tagName === 'INPUT' && select.type === 'hidden') {
            hideClientModal();
            if (window.toastManager) window.toastManager.success(form.dataset.createdText || 'Client created');
            window.location.reload();
            return;
          }
          appendOption(select, data.id, data.name, {
            'data-default-rate': data.default_hourly_rate,
          });
          // Also refresh inline project modal client list
          var projectClientSelect = document.getElementById('inline_project_client_id');
          if (projectClientSelect && projectClientSelect.tagName === 'SELECT') {
            appendOption(projectClientSelect, data.id, data.name, null);
            // Don't leave it selected on the modal select unless creating a project
            if (projectClientSelect !== select) {
              /* leave current modal value alone if user was mid-create */
            }
          }
          hideClientModal();
          if (window.toastManager) window.toastManager.success(form.dataset.createdText || 'Client created');
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = form.dataset.networkErrorText || 'Network error while creating client';
          errorEl.classList.remove('hidden');
        }
      } finally {
        setLoading(form, 'submitCreateClient', null, false);
      }
    });
  }

  function initProjectForm() {
    var form = document.getElementById('inlineCreateProjectForm');
    if (!form || form.dataset.ttBound === '1') return;
    form.dataset.ttBound = '1';

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var errorEl = document.getElementById('createProjectError');
      var clientSelect = document.getElementById('inline_project_client_id');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }
      // Re-enable temporarily so FormData includes the value when locked
      var wasLocked = clientSelect && clientSelect.disabled;
      if (wasLocked) clientSelect.disabled = false;
      if (!clientSelect || !clientSelect.value) {
        if (wasLocked) clientSelect.disabled = true;
        if (errorEl) {
          errorEl.textContent = form.dataset.clientRequiredText || 'Please select a client first';
          errorEl.classList.remove('hidden');
        }
        return;
      }
      setLoading(form, 'submitCreateProject', form.dataset.creatingText, true);
      try {
        var formData = new FormData(form);
        var billable = document.getElementById('inline_project_billable');
        if (billable && billable.checked) {
          formData.set('billable', 'on');
        } else {
          formData.delete('billable');
        }
        var resp = await fetch(form.dataset.createUrl || '/projects/create', {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
            Accept: 'application/json',
          },
          body: formData,
          credentials: 'same-origin',
        });
        if (!resp.ok) {
          var msg = form.dataset.errorText || 'Could not create project. Please try again.';
          try {
            var errData = await resp.json();
            if (errData && (errData.message || (errData.messages && errData.messages[0]))) {
              msg = errData.message || errData.messages[0];
            }
          } catch (_) {}
          if (errorEl) {
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
          }
        } else {
          var data = await resp.json();
          var select = projectState.targetSelect || resolveSelect('project', null);
          appendOption(select, data.id, data.name, {
            'data-client-id': data.client_id,
            'data-parent-id': data.client_id,
          });
          // Auto-select owning client on page client select (UI hierarchy)
          if (data.client_id) {
            var pageClient =
              document.querySelector('[data-inline-client-select]') ||
              document.getElementById('client_id') ||
              document.getElementById('startTimerClient') ||
              document.getElementById('editTimerClient');
            if (pageClient && pageClient.tagName === 'SELECT' && !pageClient.value) {
              pageClient.value = String(data.client_id);
              try {
                pageClient.dispatchEvent(new Event('change', { bubbles: true }));
              } catch (_) {}
            }
          }
          hideProjectModal();
          if (window.toastManager) window.toastManager.success(form.dataset.createdText || 'Project created');
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = form.dataset.networkErrorText || 'Network error while creating project';
          errorEl.classList.remove('hidden');
        }
      } finally {
        if (wasLocked && clientSelect) clientSelect.disabled = true;
        setLoading(form, 'submitCreateProject', null, false);
      }
    });
  }

  function initTaskForm() {
    var form = document.getElementById('inlineCreateTaskForm');
    if (!form || form.dataset.ttBound === '1') return;
    form.dataset.ttBound = '1';

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var errorEl = document.getElementById('createTaskInlineError');
      var nameInput = document.getElementById('inline_task_name');
      var projectSelect = document.getElementById('inline_task_project_id');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }
      var name = nameInput ? nameInput.value.trim() : '';
      var projectId = projectSelect ? projectSelect.value : '';
      // Prefer page project if modal select empty
      if (!projectId) {
        projectId = resolvePreferredProjectId(null);
      }
      if (!name || !projectId) {
        if (errorEl) {
          errorEl.textContent = form.dataset.projectRequiredText || 'Select a project and enter a task name';
          errorEl.classList.remove('hidden');
        }
        return;
      }
      setLoading(form, 'submitCreateTaskInline', form.dataset.creatingText, true);
      try {
        var resp = await fetch(form.dataset.createUrl || '/api/tasks/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({ name: name, project_id: parseInt(projectId, 10) }),
          credentials: 'same-origin',
        });
        if (!resp.ok) {
          var msg = form.dataset.errorText || 'Could not create task. Please try again.';
          try {
            var errData = await resp.json();
            if (errData && (errData.message || errData.error)) {
              msg = errData.message || errData.error;
            }
          } catch (_) {}
          if (errorEl) {
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
          }
        } else {
          var data = await resp.json();
          var taskId = data.id || (data.task && data.task.id);
          var taskName = data.name || (data.task && data.task.name) || name;
          var select = taskState.targetSelect || resolveSelect('task', null);
          if (select) {
            select.disabled = false;
            appendOption(select, taskId, taskName, {
              'data-parent-id': projectId,
            });
            if (window.ttEnhanceSearchableSelects) {
              window.ttEnhanceSearchableSelects();
            }
          }
          hideTaskModal();
          if (window.toastManager) window.toastManager.success(form.dataset.createdText || 'Task created');
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = form.dataset.networkErrorText || 'Network error while creating task';
          errorEl.classList.remove('hidden');
        }
      } finally {
        setLoading(form, 'submitCreateTaskInline', null, false);
      }
    });
  }

  function init() {
    initClientForm();
    initProjectForm();
    initTaskForm();

    var closeClient = document.getElementById('closeCreateClientModal');
    var cancelClient = document.getElementById('cancelCreateClient');
    if (closeClient) closeClient.addEventListener('click', hideClientModal);
    if (cancelClient) cancelClient.addEventListener('click', hideClientModal);

    var closeProject = document.getElementById('closeCreateProjectModal');
    var cancelProject = document.getElementById('cancelCreateProject');
    if (closeProject) closeProject.addEventListener('click', hideProjectModal);
    if (cancelProject) cancelProject.addEventListener('click', hideProjectModal);

    var closeTask = document.getElementById('closeCreateTaskInlineModal');
    var cancelTask = document.getElementById('cancelCreateTaskInline');
    if (closeTask) closeTask.addEventListener('click', hideTaskModal);
    if (cancelTask) cancelTask.addEventListener('click', hideTaskModal);

    document.addEventListener('click', function (e) {
      var openClient = e.target.closest('#openCreateClientModal, [data-open-create-client]');
      if (openClient) {
        e.preventDefault();
        showClientModal({
          targetSelect: resolveSelect('client', openClient),
          name: '',
        });
        return;
      }
      var openProject = e.target.closest('#openCreateProjectModal, [data-open-create-project]');
      if (openProject) {
        e.preventDefault();
        showProjectModal({
          targetSelect: resolveSelect('project', openProject),
          clientId: resolvePreferredClientId(openProject),
          name: '',
        });
        return;
      }
      var openTask = e.target.closest('#openCreateTaskModal, [data-open-create-task]');
      if (openTask) {
        e.preventDefault();
        showTaskModal({
          targetSelect: resolveSelect('task', openTask),
          projectId: resolvePreferredProjectId(openTask),
          name: '',
        });
        return;
      }
      if (e.target.closest('[data-close-create-client]')) hideClientModal();
      if (e.target.closest('[data-close-create-project]')) hideProjectModal();
      if (e.target.closest('[data-close-create-task]')) hideTaskModal();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var clientModal = document.getElementById('createClientModal');
      var projectModal = document.getElementById('createProjectModal');
      var taskModal = document.getElementById('createTaskInlineModal');
      if (clientModal && !clientModal.classList.contains('hidden')) hideClientModal();
      if (projectModal && !projectModal.classList.contains('hidden')) hideProjectModal();
      if (taskModal && !taskModal.classList.contains('hidden')) hideTaskModal();
    });
  }

  window.ttInlineCreate = {
    open: function (kind, opts) {
      opts = opts || {};
      if (kind === 'client') {
        showClientModal(opts);
      } else if (kind === 'project') {
        showProjectModal(opts);
      } else if (kind === 'task') {
        showTaskModal(opts);
      }
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
