/**
 * Populate description/notes autocomplete from recent time entries.
 * Targets #notes with optional #notesSuggestions datalist, scoped by #project_id.
 */
(function () {
    'use strict';

    if (window.__ttNotesAutocompleteLoaded) return;
    window.__ttNotesAutocompleteLoaded = true;

    function getProjectId() {
        var projectSelect = document.getElementById('project_id');
        return projectSelect && projectSelect.value ? projectSelect.value : '';
    }

    function ensureDatalist() {
        var datalist = document.getElementById('notesSuggestions');
        if (!datalist) {
            datalist = document.createElement('datalist');
            datalist.id = 'notesSuggestions';
            document.body.appendChild(datalist);
        }
        return datalist;
    }

    function ensureChipContainer() {
        var host = document.getElementById('notes_editor');
        var anchor = host ? host.parentElement : document.getElementById('notes');
        if (!anchor) return null;
        var container = document.getElementById('notesSuggestionChips');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notesSuggestionChips';
            container.className = 'mt-2 flex flex-wrap gap-1.5';
            anchor.insertAdjacentElement('afterend', container);
        }
        return container;
    }

    function applyNotesValue(value) {
        var notesInput = document.getElementById('notes');
        if (notesInput) notesInput.value = value || '';
        if (window.mdEditor && typeof window.mdEditor.setMarkdown === 'function') {
            try { window.mdEditor.setMarkdown(value || ''); } catch (_) {}
        }
    }

    function renderChips(suggestions) {
        var container = ensureChipContainer();
        if (!container) return;
        container.innerHTML = '';
        if (!suggestions.length) return;
        suggestions.slice(0, 8).forEach(function (text) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'px-2 py-1 rounded-md text-xs bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark text-text-light dark:text-text-dark hover:border-primary';
            btn.textContent = text.length > 48 ? text.slice(0, 47) + '…' : text;
            btn.title = text;
            btn.addEventListener('click', function () { applyNotesValue(text); });
            container.appendChild(btn);
        });
    }

    function populateDatalist(suggestions) {
        var notesInput = document.getElementById('notes');
        if (!notesInput) return;
        var datalist = ensureDatalist();
        notesInput.setAttribute('list', 'notesSuggestions');
        datalist.innerHTML = '';
        suggestions.forEach(function (text) {
            var opt = document.createElement('option');
            opt.value = text;
            datalist.appendChild(opt);
        });
    }

    var loadTimer = null;
    function scheduleLoad() {
        if (loadTimer) clearTimeout(loadTimer);
        loadTimer = setTimeout(loadSuggestions, 200);
    }

    function loadSuggestions() {
        var projectId = getProjectId();
        var url = '/api/timer/notes-suggestions' + (projectId ? ('?project_id=' + encodeURIComponent(projectId)) : '');
        fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                var suggestions = (data && data.suggestions) || [];
                populateDatalist(suggestions);
                renderChips(suggestions);
            })
            .catch(function () {});
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.getElementById('notes')) return;
        var projectSelect = document.getElementById('project_id');
        if (projectSelect) {
            projectSelect.addEventListener('change', scheduleLoad);
        }
        loadSuggestions();
    });
})();
