/**
 * Support modal, header pulse, offline-aware outbound links, soft prompts.
 * Copy lives in Jinja / JSON (support_ui_json); this file is behavior only.
 */
(function () {
    'use strict';

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') || '' : '';
    }

    function parseSupportConfig() {
        var el = document.getElementById('support-ui-bootstrap');
        if (!el || !el.textContent) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function postTrack(cfg, event, extra) {
        if (!cfg || !cfg.trackUrl) return;
        var body = Object.assign({ event: event }, extra || {});
        fetch(cfg.trackUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(body),
            credentials: 'same-origin'
        }).catch(function () {});
    }

    function applyOfflineState(cfg) {
        var offlineEl = document.getElementById('supportModalOffline');
        var tierBtns = document.querySelectorAll('a.support-tier-btn');
        var online = typeof navigator !== 'undefined' && navigator.onLine;
        if (!offlineEl) return;
        if (!online && cfg && cfg.i18n && cfg.i18n.offlineNote) {
            offlineEl.textContent = cfg.i18n.offlineNote;
            offlineEl.classList.remove('hidden');
            tierBtns.forEach(function (a) {
                a.setAttribute('tabindex', '-1');
                a.classList.add('pointer-events-none', 'opacity-50');
            });
        } else {
            offlineEl.classList.add('hidden');
            tierBtns.forEach(function (a) {
                a.removeAttribute('tabindex');
                a.classList.remove('pointer-events-none', 'opacity-50');
            });
        }
    }

    function wireTierLinks(cfg) {
        if (!cfg || !cfg.urls) return;
        document.querySelectorAll('a.support-tier-btn[data-support-tier]').forEach(function (a) {
            var key = a.getAttribute('data-support-tier');
            if (key && cfg.urls[key]) {
                a.href = cfg.urls[key];
            }
            a.addEventListener('click', function () {
                postTrack(cfg, 'donation_clicked', { variant: key, source: 'support_modal' });
            });
        });
        var lic = document.querySelector('a[data-support-tier="license"]');
        if (lic) {
            lic.addEventListener('click', function () {
                postTrack(cfg, 'license_clicked', { source: 'support_modal' });
            });
        }
    }

    function syncStatsFromConfig(cfg) {
        if (!cfg || !cfg.stats) return;
        var h = document.getElementById('supportStatHours');
        var e = document.getElementById('supportStatEntries');
        var r = document.getElementById('supportStatReports');
        if (h) h.textContent = Number(cfg.stats.total_hours || 0).toFixed(1);
        if (e) e.textContent = String(cfg.stats.time_entries_count != null ? cfg.stats.time_entries_count : 0);
        if (r) r.textContent = String(cfg.stats.reports_generated_count != null ? cfg.stats.reports_generated_count : 0);
        var social = document.getElementById('supportSocialLine');
        if (social && cfg.socialProofLine) {
            social.textContent = cfg.socialProofLine;
        }
    }

    function openSupportModal() {
        var modal = document.getElementById('supportModal');
        if (!modal) return;
        var cfg = parseSupportConfig();
        syncStatsFromConfig(cfg);
        applyOfflineState(cfg);
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        if (cfg) postTrack(cfg, 'modal_opened', { source: 'support_modal' });
    }

    function closeSupportModal() {
        var modal = document.getElementById('supportModal');
        if (!modal) return;
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    }

    window.openSupportModal = openSupportModal;
    window.closeSupportModal = closeSupportModal;

    function showSoftToast(cfg, message, variant, source) {
        if (!window.toastManager || typeof window.toastManager.show !== 'function') return;
        window.toastManager.show({
            message: message,
            type: 'info',
            duration: 8000,
            dismissible: true,
            actionLink: '__support_modal__',
            actionLabel: (cfg && cfg.i18n && cfg.i18n.supportAction) || 'Support'
        });
        postTrack(cfg, 'prompt_shown', { variant: variant, source: source || 'toast' });
    }

    function maybeLongSessionPrompt(cfg) {
        if (!cfg || !cfg.sessionStartedAt || !cfg.softPromptUrl) return;
        var mins = Number(cfg.longSessionMinutes) || 120;
        var started = Date.parse(cfg.sessionStartedAt);
        if (!started) return;

        function check() {
            var elapsedMin = (Date.now() - started) / 60000;
            if (elapsedMin < mins) return;
            clearInterval(timer);
            fetch(cfg.softPromptUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ kind: 'long_session' }),
                credentials: 'same-origin'
            })
                .then(function (r) {
                    return r.json();
                })
                .then(function (data) {
                    if (!data || !data.show) return;
                    var msg =
                        (cfg.i18n && cfg.i18n.longSessionToast) ||
                        "You've been tracking for a while today. TimeTracker is free because of supporters like you.";
                    var act = (cfg.i18n && cfg.i18n.supportAction) || 'Support';
                    if (window.toastManager && typeof window.toastManager.show === 'function') {
                        window.toastManager.show({
                            message: msg,
                            type: 'info',
                            duration: 9000,
                            dismissible: true,
                            actionLink: '__support_modal__',
                            actionLabel: act
                        });
                    }
                    postTrack(cfg, 'prompt_shown', { variant: 'long_session', source: 'long_session_timer' });
                })
                .catch(function () {});
        }

        var timer = setInterval(check, 60000);
        setTimeout(check, 5000);
    }

    function layoutPromptFromConfig(cfg) {
        if (!cfg || !cfg.layoutPrompt || !cfg.layoutPrompt.message) return;
        showSoftToast(cfg, cfg.layoutPrompt.message, cfg.layoutPrompt.variant || 'after_report', 'layout');
    }

    function dashboardPrompt() {
        var cfg = parseSupportConfig();
        var raw = window.__TT_DASHBOARD_SUPPORT_PROMPT;
        if (!cfg || !raw || !raw.message) return;
        showSoftToast(cfg, raw.message, raw.variant || 'dashboard', raw.source || 'dashboard');
    }

    function headerPulse(btn) {
        if (!btn) return;
        try {
            if (sessionStorage.getItem('tt_support_header_pulse_done')) return;
            btn.classList.add('animate-pulse', 'ring-2', 'ring-amber-400/60');
            setTimeout(function () {
                btn.classList.remove('animate-pulse', 'ring-2', 'ring-amber-400/60');
            }, 2400);
            sessionStorage.setItem('tt_support_header_pulse_done', '1');
        } catch (e) {}
    }

    function wireModalDom(cfg) {
        var modal = document.getElementById('supportModal');
        if (!modal) return;
        modal.querySelectorAll('[data-support-modal-close], [data-support-modal-overlay]').forEach(function (el) {
            el.addEventListener('click', function () {
                closeSupportModal();
            });
        });
        document.addEventListener('keydown', function (ev) {
            if (ev.key === 'Escape' && !modal.classList.contains('hidden')) {
                closeSupportModal();
            }
        });
        var shareBtn = document.getElementById('supportShareBtn');
        if (shareBtn && cfg && cfg.shareUrl) {
            shareBtn.addEventListener('click', function () {
                var url = cfg.shareUrl;
                if (navigator.share) {
                    navigator
                        .share({
                            title: document.title,
                            url: url
                        })
                        .catch(function () {});
                } else if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(url).then(
                        function () {
                            if (window.toastManager) {
                                window.toastManager.show(
                                    (cfg.i18n && cfg.i18n.shareSuccess) || 'Copied',
                                    'success'
                                );
                            }
                        },
                        function () {
                            if (window.toastManager) {
                                window.toastManager.show(
                                    (cfg.i18n && cfg.i18n.shareFail) || 'Copy failed',
                                    'error'
                                );
                            }
                        }
                    );
                }
            });
        }
        var hdr = document.getElementById('headerSupportBtn');
        if (hdr) {
            hdr.addEventListener('click', function (e) {
                e.preventDefault();
                openSupportModal();
            });
            headerPulse(hdr);
        }
        document.querySelectorAll('.js-open-support-modal').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                openSupportModal();
            });
        });
        window.addEventListener('online', function () {
            applyOfflineState(cfg);
        });
        window.addEventListener('offline', function () {
            applyOfflineState(cfg);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var cfg = parseSupportConfig();
        if (!cfg) return;
        cfg.i18n = cfg.i18n || {};
        cfg.i18n.supportAction = cfg.i18n.supportAction || 'Support';
        wireTierLinks(cfg);
        wireModalDom(cfg);
        layoutPromptFromConfig(cfg);
        dashboardPrompt();
        maybeLongSessionPrompt(cfg);
    });
})();
