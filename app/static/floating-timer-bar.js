/**
 * Floating Timer Bar - Persistent mini-timer visible on all pages
 * One-click start/stop without navigating to dashboard
 */
(function () {
    'use strict';

    const POLL_INTERVAL_MS = 30000;

    class FloatingTimerBar {
        constructor() {
            this.bar = null;
            this.pollTimer = null;
            this.elapsedInterval = null;
            this.timerData = null;
            this.startTime = null;
            this.startLabel = 'Start Timer';
            this.stopLabel = 'Stop';
            this.init();
        }

        init() {
            if (!document.getElementById('floatingTimerBar')) return;
            this.bar = document.getElementById('floatingTimerBar');
            this.startLabel = this.bar.dataset.startLabel || 'Start Timer';
            this.stopLabel = this.bar.dataset.stopLabel || 'Stop';
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
                const btn = this.bar.querySelector('button');
                const label = this.timerData.paused ? (this.bar.dataset.resumeLabel || 'Resume') : (this.stopLabel || 'Stop');
                if (btn) btn.title = (this.getLabel() || 'Timer') + (this.timerData.paused ? ' (Paused) – ' : ' – ') + formatted + ' – ' + label;
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
            } else {
                const url = this.bar?.dataset?.manualUrl || '/timer/manual';
                window.location.href = url;
            }
        }

        async stopTimer() {
            const token = this.getCsrfToken();
            try {
                const res = await fetch('/timer/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': token },
                    body: 'csrf_token=' + encodeURIComponent(token),
                    credentials: 'same-origin'
                });
                if (res.redirected) {
                    window.location.href = res.url;
                } else {
                    await this.fetchStatus();
                }
            } catch (e) {
                console.error('Stop timer failed', e);
                if (window.toastManager) {
                    window.toastManager.error('Failed to stop timer', 'Error', 3000);
                }
            }
        }

        async resumeTimer() {
            const token = this.getCsrfToken();
            try {
                const res = await fetch('/timer/resume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': token },
                    body: 'csrf_token=' + encodeURIComponent(token),
                    credentials: 'same-origin'
                });
                if (res.redirected) {
                    window.location.href = res.url;
                } else {
                    await this.fetchStatus();
                }
            } catch (e) {
                console.error('Resume timer failed', e);
                if (window.toastManager) {
                    window.toastManager.error('Failed to resume timer', 'Error', 3000);
                }
            }
        }

        getCsrfToken() {
            const tokenEl = document.querySelector('meta[name="csrf-token"]');
            return tokenEl ? tokenEl.getAttribute('content') || '' : '';
        }

        getLabel() {
            if (!this.timerData) return '';
            return this.timerData.project_name || this.timerData.client_name || 'Timer';
        }

        render() {
            if (!this.bar) return;

            const baseClass = 'floating-timer-bar__round flex items-center justify-center w-10 h-10 rounded-full text-text-light dark:text-text-dark hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 text-sm transition-colors';
            const actionLabel = this.timerData && this.timerData.paused ? (this.bar.dataset.resumeLabel || 'Resume') : (this.stopLabel || 'Stop');
            const title = this.timerData
                ? (escapeHtml(this.getLabel()) + (this.timerData.paused ? ' (Paused) – ' : ' – ') + (this.timerData.duration_formatted || '00:00:00') + ' – ' + escapeHtml(actionLabel))
                : escapeHtml(this.startLabel);

            if (this.timerData) {
                const isPaused = this.timerData.paused;
                const pulseClass = isPaused ? 'bg-amber-500' : 'bg-green-500 animate-pulse';
                const clickHandler = isPaused ? 'window.floatingTimerBar.resumeTimer()' : 'window.floatingTimerBar.stopTimer()';
                this.bar.innerHTML = `
                    <button type="button" class="${baseClass} relative" onclick="${clickHandler}" title="${title}" aria-label="${escapeHtml(actionLabel)} – ${escapeHtml(this.getLabel())}">
                        <span class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full ${pulseClass}" aria-hidden="true"></span>
                        <i class="fas fa-${isPaused ? 'pause' : 'stopwatch'} text-base"></i>
                        <span class="floating-timer-bar__elapsed sr-only" data-timer-elapsed>${this.timerData.duration_formatted || '00:00:00'}</span>
                    </button>
                `;
                this.startElapsedUpdater();
            } else {
                this.bar.innerHTML = `
                    <button type="button" class="${baseClass}" onclick="window.floatingTimerBar.startTimer()" title="${title}" aria-label="${escapeHtml(this.startLabel)}">
                        <i class="fas fa-play text-base"></i>
                    </button>
                `;
            }
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
