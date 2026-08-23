/**
 * Floating Timer Bar - Persistent mini-timer visible on all pages
 * One-click start/stop without navigating away from the current page when possible
 */
(function () {
    'use strict';

    const POLL_INTERVAL_MS = 30000;

    function syncFabDesktopHide(timerData) {
        try {
            var md = typeof window.matchMedia === 'function' && window.matchMedia('(min-width: 768px)').matches;
            var active = !!timerData;
            document.body.classList.toggle('fab-hide-desktop-timer-active', md && active);
        } catch (e) { /* ignore */ }
    }

    class FloatingTimerBar {
        constructor() {
            this.bar = null;
            this.pollTimer = null;
            this.elapsedInterval = null;
            this.timerData = null;
            this.startTime = null;
            this.startLabel = 'Start Timer';
            this.stopLabel = 'Stop';
            this.pauseLabel = 'Pause';
            this.resumeLabel = 'Resume';
            this.init();
        }

        init() {
            if (!document.getElementById('floatingTimerBar')) return;
            this.bar = document.getElementById('floatingTimerBar');
            this.startLabel = this.bar.dataset.startLabel || 'Start Timer';
            this.stopLabel = this.bar.dataset.stopLabel || 'Stop';
            this.pauseLabel = this.bar.dataset.pauseLabel || 'Pause';
            this.resumeLabel = this.bar.dataset.resumeLabel || 'Resume';
            this.render();
            this.fetchStatus();
            this.pollTimer = setInterval(() => this.fetchStatus(), POLL_INTERVAL_MS);
            window.addEventListener('focus', () => this.fetchStatus());
        }

        async fetchStatus() {
            try {
                const res = await fetch('/timer/status', { credentials: 'same-origin' });
                const data = await res.json();
                if (data.active && data.timer) {
                    this.timerData = data.timer;
                    this.startTime = new Date(data.timer.start_time).getTime();
                    this.render();
                    this.startElapsedUpdater();
                } else {
                    this.timerData = null;
                    this.startTime = null;
                    this.stopElapsedUpdater();
                    this.render();
                }
                syncFabDesktopHide(this.timerData);
            } catch (e) {
                console.warn('FloatingTimerBar: fetch status failed', e);
            }
        }

        startElapsedUpdater() {
            this.stopElapsedUpdater();
            const update = () => {
                if (!this.timerData || !this.bar) return;
                let elapsedSec;
                if (this.timerData.paused) {
                    elapsedSec = this.timerData.current_duration || 0;
                } else {
                    elapsedSec = this.timerData.current_duration != null
                        ? this.timerData.current_duration
                        : (this.startTime ? Math.floor((Date.now() - this.startTime) / 1000) : 0);
                }
                const h = Math.floor(elapsedSec / 3600);
                const m = Math.floor((elapsedSec % 3600) / 60);
                const s = elapsedSec % 60;
                const formatted = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
                const el = this.bar.querySelector('[data-timer-elapsed]');
                if (el) el.textContent = formatted;
                const progressEl = this.bar.querySelector('[data-timer-progress]');
                if (progressEl) progressEl.style.width = this.getProgressPercent(elapsedSec) + '%';
            };
            update();
            this.elapsedInterval = setInterval(update, 1000);
        }

        stopElapsedUpdater() {
            if (this.elapsedInterval) {
                clearInterval(this.elapsedInterval);
                this.elapsedInterval = null;
            }
        }

        startTimer() {
            const startBtn = document.querySelector('#openStartTimer');
            if (startBtn) {
                startBtn.click();
                return;
            }
            const dashboardUrl = this.bar?.dataset?.dashboardUrl || '/';
            window.location.href = dashboardUrl + (dashboardUrl.indexOf('#') >= 0 ? '' : '#start-timer');
        }

        async postTimerAction(url) {
            const token = this.getCsrfToken();
            try {
                await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': token,
                        'Accept': 'application/json',
                    },
                    body: 'csrf_token=' + encodeURIComponent(token),
                    credentials: 'same-origin',
                    redirect: 'manual',
                });
                await this.fetchStatus();
                this.refreshDashboardTimerWidget();
            } catch (e) {
                console.error('Timer action failed:', url, e);
                if (window.toastManager) {
                    window.toastManager.error('Timer action failed', 'Error', 3000);
                }
            }
        }

        stopTimer() {
            return this.postTimerAction('/timer/stop');
        }

        pauseTimer() {
            return this.postTimerAction('/timer/pause');
        }

        resumeTimer() {
            return this.postTimerAction('/timer/resume');
        }

        refreshDashboardTimerWidget() {
            document.dispatchEvent(new CustomEvent('tt:timer-status-changed'));
        }

        getCsrfToken() {
            const tokenEl = document.querySelector('meta[name="csrf-token"]');
            return tokenEl ? tokenEl.getAttribute('content') || '' : '';
        }

        getLabel() {
            if (!this.timerData) return '';
            return this.timerData.project_name || this.timerData.client_name || 'Timer';
        }

        getDailyTargetSeconds() {
            const raw = this.bar && this.bar.dataset.dailyTargetHours;
            const hours = raw ? parseFloat(raw, 10) : 8;
            const safeHours = isNaN(hours) || hours <= 0 ? 8 : hours;
            return Math.round(safeHours * 3600);
        }

        getProgressPercent(elapsedSec) {
            const target = this.getDailyTargetSeconds();
            if (!target) return 0;
            return Math.min(100, Math.round((elapsedSec / target) * 100));
        }

        render() {
            if (!this.bar) return;

            const roundBtn = 'floating-timer-bar__round flex items-center justify-center w-8 h-8 rounded-full text-text-light dark:text-text-dark hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm transition-colors shrink-0';

            if (this.timerData) {
                const isPaused = this.timerData.paused;
                const pulseClass = isPaused ? 'bg-amber-500' : 'bg-green-500 animate-pulse';
                const elapsedSec = this.timerData.current_duration != null
                    ? this.timerData.current_duration
                    : (this.startTime ? Math.floor((Date.now() - this.startTime) / 1000) : 0);
                const progressPct = this.getProgressPercent(elapsedSec);
                const label = escapeHtml(this.getLabel());
                const elapsed = this.timerData.duration_formatted || '00:00:00';
                const pauseResumeLabel = isPaused ? this.resumeLabel : this.pauseLabel;
                const pauseResumeIcon = isPaused ? 'play' : 'pause';
                const pauseResumeAction = isPaused ? 'resumeTimer' : 'pauseTimer';

                this.bar.className = 'flex shrink-0 items-center gap-1 floating-timer-bar--active';
                this.bar.innerHTML = `
                    <div class="relative flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 border border-border-light dark:border-border-dark" title="${label}${isPaused ? ' (Paused)' : ''}">
                        <span class="absolute top-0.5 left-2 w-2 h-2 rounded-full ${pulseClass}" aria-hidden="true"></span>
                        <span class="floating-timer-bar__elapsed font-mono text-xs font-semibold tabular-nums text-text-light dark:text-text-dark pl-3 min-w-[4.5rem]" data-timer-elapsed>${elapsed}</span>
                        <button type="button" class="${roundBtn}" onclick="window.floatingTimerBar.${pauseResumeAction}()" title="${escapeHtml(pauseResumeLabel)}" aria-label="${escapeHtml(pauseResumeLabel)}">
                            <i class="fas fa-${pauseResumeIcon} text-xs"></i>
                        </button>
                        <button type="button" class="${roundBtn}" onclick="window.floatingTimerBar.stopTimer()" title="${escapeHtml(this.stopLabel)}" aria-label="${escapeHtml(this.stopLabel)}">
                            <i class="fas fa-stop text-xs"></i>
                        </button>
                        <div class="absolute -bottom-0.5 left-2 right-2 h-0.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden" aria-hidden="true">
                            <div class="h-full bg-primary transition-all duration-1000" data-timer-progress style="width: ${progressPct}%;"></div>
                        </div>
                    </div>
                `;
                this.startElapsedUpdater();
            } else {
                this.bar.className = 'flex shrink-0 items-center justify-center';
                this.bar.innerHTML = `
                    <button type="button" class="${roundBtn} w-9 h-9" onclick="window.floatingTimerBar.startTimer()" title="${escapeHtml(this.startLabel)}" aria-label="${escapeHtml(this.startLabel)}">
                        <i class="fas fa-play text-base"></i>
                    </button>
                `;
            }
            syncFabDesktopHide(this.timerData);
        }

        destroy() {
            this.stopElapsedUpdater();
            if (this.pollTimer) clearInterval(this.pollTimer);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    const style = document.createElement('style');
    style.textContent = `
        .floating-timer-bar__round { cursor: pointer; }
        .floating-timer-bar--active { max-width: 11rem; }
        @media (prefers-reduced-motion: reduce) {
            .floating-timer-bar__round .animate-pulse { animation: none; }
        }
    `;
    document.head.appendChild(style);

    window.addEventListener('DOMContentLoaded', () => {
        const container = document.getElementById('floatingTimerBar');
        if (container) {
            window.floatingTimerBar = new FloatingTimerBar();
        }
    });
})();
