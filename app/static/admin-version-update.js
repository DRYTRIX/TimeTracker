/**
 * Admin-only: fetch /api/version/check and show a non-blocking update card.
 */
(function () {
  var LS_KEY = "tt_dismissed_release_version";
  var NOTE_PREVIEW_LEN = 280;

  function getCsrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") || "" : "";
  }

  function localDismissedMatches(latest) {
    try {
      return latest && localStorage.getItem(LS_KEY) === latest;
    } catch (e) {
      return false;
    }
  }

  function setLocalDismissed(latest) {
    try {
      if (latest) localStorage.setItem(LS_KEY, latest);
    } catch (e) {}
  }

  function hide(root) {
    if (root) root.classList.add("hidden");
  }

  function show(root) {
    if (root) root.classList.remove("hidden");
  }

  function postDismiss(latest, onDone) {
    fetch("/api/version/dismiss", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ latest_version: latest }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, json: j };
        });
      })
      .then(function (res) {
        if (typeof onDone === "function") onDone(res.ok);
      })
      .catch(function () {
        if (typeof onDone === "function") onDone(false);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("adminVersionUpdateRoot");
    if (!root) return;

    fetch("/api/version/check", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401 || r.status === 403) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.latest_version) return;
        if (localDismissedMatches(data.latest_version)) return;
        if (!data.update_available) return;

        var title = document.getElementById("adminVersionUpdateTitle");
        var published = document.getElementById("adminVersionUpdatePublished");
        var notesEl = document.getElementById("adminVersionUpdateNotes");
        var readMore = document.getElementById("adminVersionUpdateReadMore");
        var viewLink = document.getElementById("adminVersionUpdateViewRelease");
        var closeBtn = document.getElementById("adminVersionUpdateClose");
        var dismissBtn = document.getElementById("adminVersionUpdateDismiss");
        var dismissVerBtn = document.getElementById("adminVersionUpdateDismissVersion");

        if (title) {
          title.textContent =
            String.fromCodePoint(0x1f680) + " New version available: " + data.latest_version;
        }

        if (published) {
          if (data.published_at) {
            try {
              var d = new Date(data.published_at);
              published.textContent = window.formatUserDateTime
                ? window.formatUserDateTime(d)
                : d.toLocaleString(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  });
            } catch (e) {
              published.textContent = data.published_at;
            }
          } else {
            published.textContent = "";
          }
        }

        var notes = data.release_notes || "";
        var expanded = false;
        function renderNotes() {
          if (!notesEl) return;
          if (!notes) {
            notesEl.textContent = "";
            if (readMore) readMore.classList.add("hidden");
            return;
          }
          if (expanded || notes.length <= NOTE_PREVIEW_LEN) {
            notesEl.textContent = notes;
            if (readMore) readMore.classList.add("hidden");
          } else {
            notesEl.textContent = notes.slice(0, NOTE_PREVIEW_LEN).trimEnd() + "\u2026";
            if (readMore) {
              readMore.classList.remove("hidden");
              readMore.onclick = function () {
                expanded = true;
                notesEl.textContent = notes;
                readMore.classList.add("hidden");
              };
            }
          }
        }
        renderNotes();

        if (viewLink) {
          if (data.release_url) {
            viewLink.href = data.release_url;
            viewLink.classList.remove("pointer-events-none", "opacity-50");
          } else {
            viewLink.href = "#";
            viewLink.classList.add("pointer-events-none", "opacity-50");
          }
        }

        function wireClose() {
          hide(root);
        }
        if (closeBtn) closeBtn.addEventListener("click", wireClose);
        if (dismissBtn) dismissBtn.addEventListener("click", wireClose);
        if (dismissVerBtn) {
          dismissVerBtn.addEventListener("click", function () {
            postDismiss(data.latest_version, function () {
              hide(root);
              setLocalDismissed(data.latest_version);
            });
          });
        }

        show(root);
      })
      .catch(function () {});
  });
})();
