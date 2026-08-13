/**
 * Shared inline Create Client modal (Issue #728).
 * Expects #createClientModal / #inlineCreateClientForm from the shared partial.
 */
(function () {
  'use strict';

  function getCsrfToken() {
    var tokenMeta = document.querySelector('meta[name="csrf-token"]');
    return tokenMeta ? tokenMeta.getAttribute('content') : '';
  }

  function resolveClientSelect(trigger) {
    var id = trigger && trigger.getAttribute('data-client-select-id');
    if (id) {
      return document.getElementById(id);
    }
    return (
      document.querySelector('[data-inline-client-select]') ||
      document.getElementById('client_id') ||
      document.getElementById('startTimerClient')
    );
  }

  function initInlineCreateClient() {
    var modal = document.getElementById('createClientModal');
    var form = document.getElementById('inlineCreateClientForm');
    if (!modal || !form) return;

    var closeBtn = document.getElementById('closeCreateClientModal');
    var cancelBtn = document.getElementById('cancelCreateClient');
    var errorEl = document.getElementById('createClientError');
    var nameInput = document.getElementById('inline_client_name') || document.getElementById('client_name');
    var targetSelect = null;

    function showModal(trigger) {
      targetSelect = resolveClientSelect(trigger);
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
      if (errorEl) {
        errorEl.classList.add('hidden');
        errorEl.textContent = '';
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
      targetSelect = null;
    }

    document.addEventListener('click', function (e) {
      var openBtn = e.target.closest('#openCreateClientModal, [data-open-create-client]');
      if (openBtn) {
        e.preventDefault();
        showModal(openBtn);
        return;
      }
      if (e.target.closest('[data-close-create-client]')) {
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
      var submitBtn = document.getElementById('submitCreateClient');
      var originalText = submitBtn ? submitBtn.innerHTML : '';
      var creatingText = form.dataset.creatingText || 'Creating...';
      if (submitBtn) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>' + creatingText;
        submitBtn.disabled = true;
      }
      form.classList.add('loading');

      try {
        var formData = new FormData(form);
        var resp = await fetch(form.dataset.createUrl || '/clients/create', {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRF-Token': getCsrfToken(),
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
          var select = targetSelect || resolveClientSelect(null);
          if (select && select.tagName === 'INPUT' && select.type === 'hidden') {
            hideModal();
            if (window.toastManager) {
              window.toastManager.success(form.dataset.createdText || 'Client created');
            }
            window.location.reload();
            return;
          }
          if (select && select.tagName === 'SELECT') {
            var opt = document.createElement('option');
            opt.value = String(data.id);
            opt.textContent = data.name;
            if (typeof data.default_hourly_rate !== 'undefined' && data.default_hourly_rate !== null) {
              opt.setAttribute('data-default-rate', String(data.default_hourly_rate));
            }
            select.appendChild(opt);
            select.value = String(data.id);
            try {
              select.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (_) {}
          }

          // Also refresh inline project modal client list if present
          var projectClientSelect = document.getElementById('inline_project_client_id');
          if (projectClientSelect && projectClientSelect.tagName === 'SELECT') {
            var pOpt = document.createElement('option');
            pOpt.value = String(data.id);
            pOpt.textContent = data.name;
            projectClientSelect.appendChild(pOpt);
          }

          hideModal();
          if (window.toastManager) {
            window.toastManager.success(form.dataset.createdText || 'Client created');
          }
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = form.dataset.networkErrorText || 'Network error while creating client';
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
    document.addEventListener('DOMContentLoaded', initInlineCreateClient);
  } else {
    initInlineCreateClient();
  }
})();
