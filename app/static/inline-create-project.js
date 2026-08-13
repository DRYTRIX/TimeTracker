/**
 * Shared inline Create Project modal (Issue #728).
 * Expects #createProjectModal / #inlineCreateProjectForm from the shared partial.
 */
(function () {
  'use strict';

  function getCsrfToken() {
    var tokenMeta = document.querySelector('meta[name="csrf-token"]');
    return tokenMeta ? tokenMeta.getAttribute('content') : '';
  }

  function resolveProjectSelect(trigger) {
    var id = trigger && trigger.getAttribute('data-project-select-id');
    if (id) {
      return document.getElementById(id);
    }
    return (
      document.querySelector('[data-inline-project-select]') ||
      document.getElementById('project_id') ||
      document.getElementById('startTimerProject')
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

  function initInlineCreateProject() {
    var modal = document.getElementById('createProjectModal');
    var form = document.getElementById('inlineCreateProjectForm');
    if (!modal || !form) return;

    var closeBtn = document.getElementById('closeCreateProjectModal');
    var cancelBtn = document.getElementById('cancelCreateProject');
    var errorEl = document.getElementById('createProjectError');
    var nameInput = document.getElementById('inline_project_name');
    var clientSelect = document.getElementById('inline_project_client_id');
    var targetSelect = null;

    function showModal(trigger) {
      targetSelect = resolveProjectSelect(trigger);
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }
      var preferred = resolvePreferredClientId(trigger);
      if (clientSelect && preferred) {
        clientSelect.value = preferred;
      }
      setTimeout(function () {
        if (nameInput) nameInput.focus();
      }, 0);
    }

    function hideModal() {
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }
      form.reset();
      var billable = document.getElementById('inline_project_billable');
      if (billable) billable.checked = true;
      targetSelect = null;
    }

    document.addEventListener('click', function (e) {
      var openBtn = e.target.closest('#openCreateProjectModal, [data-open-create-project]');
      if (openBtn) {
        e.preventDefault();
        showModal(openBtn);
        return;
      }
      if (e.target.closest('[data-close-create-project]')) {
        hideModal();
      }
    });

    if (closeBtn) closeBtn.addEventListener('click', hideModal);
    if (cancelBtn) cancelBtn.addEventListener('click', hideModal);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) hideModal();
    });

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
      }

      if (!clientSelect || !clientSelect.value) {
        if (errorEl) {
          errorEl.textContent = form.dataset.clientRequiredText || 'Please select a client first';
          errorEl.classList.remove('hidden');
        }
        return;
      }

      var submitBtn = document.getElementById('submitCreateProject');
      var originalText = submitBtn ? submitBtn.innerHTML : '';
      var creatingText = form.dataset.creatingText || 'Creating...';
      if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>' + creatingText;
        submitBtn.disabled = true;
      }
      form.classList.add('loading');

      try {
        var formData = new FormData(form);
        // Checkbox: ensure billable is sent as "on" when checked (matches Flask form expectation)
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
            'X-CSRF-Token': getCsrfToken(),
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
          var select = targetSelect || resolveProjectSelect(null);
          if (select && select.tagName === 'SELECT') {
            var opt = document.createElement('option');
            opt.value = String(data.id);
            opt.textContent = data.name;
            if (data.client_id) {
              opt.setAttribute('data-client-id', String(data.client_id));
            }
            select.appendChild(opt);
            select.value = String(data.id);
            try {
              select.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (_) {}
          }

          hideModal();
          if (window.toastManager) {
            window.toastManager.success(form.dataset.createdText || 'Project created');
          }
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = form.dataset.networkErrorText || 'Network error while creating project';
          errorEl.classList.remove('hidden');
        }
      } finally {
        if (submitBtn) {
          submitBtn.innerHTML = originalText;
          submitBtn.disabled = false;
        }
        form.classList.remove('loading');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initInlineCreateProject);
  } else {
    initInlineCreateProject();
  }
})();
