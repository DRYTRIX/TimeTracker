/**
 * Options page: connect (password + 2FA or API token), read-only server
 * policy display, local preferences, disconnect.
 */

import {
  ApiClient,
  normalizeServerUrl,
  originFromServerUrl,
} from '../lib/api.js';
import { icons } from '../lib/icons.js';

const el = (id) => document.getElementById(id);

const els = {
  message: el('message'),
  connectCard: el('connect-card'),
  connection: el('connection'),
  accountSection: el('account-section'),
  serverUrl: el('server-url'),
  username: el('username'),
  password: el('password'),
  twofaRow: el('twofa-row'),
  twofaCode: el('twofa-code'),
  loginBtn: el('login-btn'),
  apiToken: el('api-token'),
  tokenBtn: el('token-btn'),
  serverValue: el('server-value'),
  serverStatusText: el('server-status-text'),
  serverStatusIcon: el('server-status-icon'),
  avatar: el('avatar'),
  userName: el('user-name'),
  userSub: el('user-sub'),
  badgeToggle: el('badge-toggle'),
  idleValue: el('idle-value'),
  idleActionValue: el('idle-action-value'),
  shortcutToggle: el('shortcut-toggle'),
  shortcutPopup: el('shortcut-popup'),
  disconnectBtn: el('disconnect-btn'),
};

el('managed-1').querySelector('.managed-icon').innerHTML = icons.lock;
el('managed-2').querySelector('.managed-icon').innerHTML = icons.lock;
els.serverStatusIcon.innerHTML = icons['check-circle'];
els.disconnectBtn.querySelector('.danger-icon').innerHTML = icons['log-out'];

let pending2fa = null; // { baseUrl, tempToken }

function showMessage(text, kind = 'error') {
  els.message.textContent = text;
  els.message.className = `toast ${kind}`;
  els.message.classList.remove('hidden');
}

function clearMessage() {
  els.message.classList.add('hidden');
  els.message.textContent = '';
}

function setBusy(button, busy) {
  button.disabled = busy;
}

async function requestHostAccess(serverUrl) {
  const originPattern = originFromServerUrl(serverUrl);
  if (!originPattern) {
    return { ok: false, message: 'Server URL is not valid.' };
  }
  const already = await chrome.permissions.contains({ origins: [originPattern] });
  if (already) return { ok: true };
  const granted = await chrome.permissions.request({ origins: [originPattern] });
  if (!granted) {
    return {
      ok: false,
      message: 'Permission to reach this server was denied. Allow access when prompted.',
    };
  }
  return { ok: true };
}

async function persistSession(serverUrl, token) {
  await chrome.storage.local.set({
    server_url: normalizeServerUrl(serverUrl),
    api_token: token,
    logged_out: false,
  });
  chrome.runtime.sendMessage({ type: 'refresh_timer' }).catch(() => {});
}

async function connectWithPassword() {
  clearMessage();
  const serverUrl = normalizeServerUrl(els.serverUrl.value);
  const username = els.username.value.trim();
  const password = els.password.value;
  if (!serverUrl || !username || !password) {
    showMessage('Server URL, username, and password are required.');
    return;
  }

  setBusy(els.loginBtn, true);
  try {
    const access = await requestHostAccess(serverUrl);
    if (!access.ok) {
      showMessage(access.message);
      return;
    }

    const info = await ApiClient.testPublicServerInfo(serverUrl);
    if (!info.ok) {
      showMessage(info.message);
      return;
    }

    if (!pending2fa) {
      const login = await ApiClient.loginWithPassword(serverUrl, username, password);
      if (!login.ok && login.requires_2fa && login.temp_token) {
        pending2fa = { baseUrl: serverUrl, tempToken: login.temp_token };
        els.twofaRow.classList.remove('hidden');
        els.twofaCode.focus();
        showMessage('Enter the 6-digit code from your authenticator app.', 'success');
        return;
      }
      if (!login.ok) {
        showMessage(login.message);
        return;
      }
      await finishLogin(serverUrl, login.token, password);
      return;
    }

    const code = els.twofaCode.value.trim();
    if (!code) {
      showMessage('Enter your two-factor code.');
      return;
    }
    const verify = await ApiClient.verifyLogin2fa(serverUrl, pending2fa.tempToken, code);
    if (!verify.ok) {
      showMessage(verify.message);
      return;
    }
    await finishLogin(serverUrl, verify.token, password);
  } catch (error) {
    showMessage(error?.message || 'Connect failed. Check the URL and try again.');
  } finally {
    setBusy(els.loginBtn, false);
  }
}

async function finishLogin(serverUrl, token, password) {
  const client = new ApiClient(serverUrl, token);
  const session = await client.validateSession();
  if (!session.ok) {
    showMessage(session.message);
    return;
  }
  pending2fa = null;
  els.twofaRow.classList.add('hidden');
  els.twofaCode.value = '';
  els.password.value = '';
  await persistSession(serverUrl, token);
  showMessage('Connected successfully.', 'success');
  await renderStatus();
}

async function connectWithToken() {
  clearMessage();
  const serverUrl = normalizeServerUrl(els.serverUrl.value);
  const token = els.apiToken.value.trim();
  if (!serverUrl || !token) {
    showMessage('Server URL and API token are required.');
    return;
  }
  if (!token.startsWith('tt_')) {
    showMessage('Token must start with tt_.');
    return;
  }

  setBusy(els.tokenBtn, true);
  try {
    const access = await requestHostAccess(serverUrl);
    if (!access.ok) {
      showMessage(access.message);
      return;
    }

    const info = await ApiClient.testPublicServerInfo(serverUrl);
    if (!info.ok) {
      showMessage(info.message);
      return;
    }

    const client = new ApiClient(serverUrl, token);
    const session = await client.validateSession();
    if (!session.ok) {
      showMessage(session.message);
      return;
    }

    await persistSession(serverUrl, token);
    els.apiToken.value = '';
    showMessage('Token saved successfully.', 'success');
    await renderStatus();
  } catch (error) {
    showMessage(error?.message || 'Token save failed. Check the URL and try again.');
  } finally {
    setBusy(els.tokenBtn, false);
  }
}

async function disconnect() {
  clearMessage();
  pending2fa = null;
  await chrome.storage.local.set({
    api_token: null,
    logged_out: true,
    last_timer_status: { active: false, timer: null },
  });
  chrome.runtime.sendMessage({ type: 'refresh_timer' }).catch(() => {});
  showMessage('Disconnected.', 'success');
  await renderStatus();
}

function showConnected(visible) {
  els.connection.classList.toggle('hidden', !visible);
  els.accountSection.classList.toggle('hidden', !visible);
  els.connectCard.classList.toggle('hidden', visible);
}

async function renderStatus() {
  const { server_url, api_token, logged_out } = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
  ]);
  const configured = Boolean(server_url && api_token && !logged_out);
  showConnected(configured);
  if (server_url) els.serverUrl.value = server_url;
  if (!configured) return;

  els.serverValue.textContent = server_url;

  const client = new ApiClient(server_url, api_token);
  const session = await client.validateSession();
  if (session.ok && session.user) {
    const name = session.user.username || session.user.email || 'Signed in';
    els.avatar.textContent = (session.user.username || session.user.email || '?')
      .charAt(0)
      .toUpperCase();
    els.userName.textContent = name;
    els.userSub.textContent = session.user.email
      ? `${session.user.email} · signed in`
      : 'Signed in';
    els.serverStatusText.textContent = 'Connected';
  } else {
    els.serverStatusText.textContent = 'Token invalid — sign in again';
    els.serverStatusIcon.style.color = 'var(--tt-red)';
  }

  // Server-managed idle policy — read-only display (Issue #722 semantics)
  try {
    const status = await client.getTimerStatus();
    const minutes = Number(status?.idle_timeout_minutes) || 30;
    els.idleValue.textContent = `After ${minutes} min`;
    const action = String(status?.idle_unanswered_action || 'review');
    els.idleActionValue.textContent =
      action === 'auto_stop'
        ? 'Auto-stop credited to last activity'
        : 'Keep running · flag for review';
  } catch {
    els.idleValue.textContent = '—';
    els.idleActionValue.textContent = '—';
  }
}

async function renderShortcuts() {
  try {
    const commands = await chrome.commands.getAll();
    const toggle = commands.find((c) => c.name === 'toggle-timer');
    const popup = commands.find((c) => c.name === '_execute_action');
    if (toggle?.shortcut) els.shortcutToggle.textContent = toggle.shortcut;
    if (popup?.shortcut) els.shortcutPopup.textContent = popup.shortcut;
  } catch {
    /* keep suggested defaults */
  }
}

async function renderBadgePref() {
  const { badge_show_elapsed = true } = await chrome.storage.local.get('badge_show_elapsed');
  els.badgeToggle.checked = Boolean(badge_show_elapsed);
}

els.badgeToggle.addEventListener('change', async () => {
  await chrome.storage.local.set({ badge_show_elapsed: els.badgeToggle.checked });
});

els.loginBtn.addEventListener('click', connectWithPassword);
els.tokenBtn.addEventListener('click', connectWithToken);
els.disconnectBtn.addEventListener('click', disconnect);
els.password.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') connectWithPassword();
});
els.twofaCode.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') connectWithPassword();
});

renderBadgePref();
renderShortcuts();
renderStatus();
