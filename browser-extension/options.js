/**
 * Options page: server URL + password login (with 2FA) or pasted API token.
 */

import { ApiClient, normalizeServerUrl, originFromServerUrl } from './lib/api.js';

const els = {
  serverUrl: document.getElementById('server-url'),
  username: document.getElementById('username'),
  password: document.getElementById('password'),
  apiToken: document.getElementById('api-token'),
  loginBtn: document.getElementById('login-btn'),
  tokenBtn: document.getElementById('token-btn'),
  disconnectBtn: document.getElementById('disconnect-btn'),
  message: document.getElementById('message'),
  statusLine: document.getElementById('status-line'),
  loginSection: document.getElementById('login-section'),
  totpSection: document.getElementById('totp-section'),
  totpCode: document.getElementById('totp-code'),
  totpBtn: document.getElementById('totp-btn'),
  totpCancelBtn: document.getElementById('totp-cancel-btn'),
  suggestFromTab: document.getElementById('suggest-from-tab'),
};

/** @type {{ serverUrl: string, tempToken: string }|null} */
let pending2fa = null;

function showMessage(text, kind = 'error') {
  els.message.textContent = text;
  els.message.className = kind === 'success' ? 'success' : 'error';
  els.message.classList.remove('hidden');
}

function clearMessage() {
  els.message.classList.add('hidden');
  els.message.textContent = '';
}

function showTotpStep(serverUrl, tempToken) {
  pending2fa = { serverUrl, tempToken };
  els.loginSection.classList.add('hidden');
  els.totpSection.classList.remove('hidden');
  els.totpCode.value = '';
  els.totpCode.focus();
}

function hideTotpStep() {
  pending2fa = null;
  els.totpSection.classList.add('hidden');
  els.loginSection.classList.remove('hidden');
  els.totpCode.value = '';
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

async function finishWithToken(serverUrl, token) {
  const client = new ApiClient(serverUrl, token);
  const session = await client.validateSession();
  if (!session.ok) {
    showMessage(session.message);
    return false;
  }
  await persistSession(serverUrl, token);
  els.password.value = '';
  hideTotpStep();
  showMessage('Connected successfully.', 'success');
  await updateStatus();
  return true;
}

async function updateStatus() {
  const { server_url, api_token, logged_out, suggest_from_tab } = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
    'suggest_from_tab',
  ]);
  if (server_url) els.serverUrl.value = server_url;
  els.suggestFromTab.checked = Boolean(suggest_from_tab);
  if (!server_url || !api_token || logged_out) {
    els.statusLine.textContent = 'Not connected.';
    return;
  }
  const client = new ApiClient(server_url, api_token);
  const result = await client.validateSession();
  if (result.ok) {
    const name = result.user?.username || result.user?.email || 'signed in';
    els.statusLine.textContent = `Connected to ${server_url} as ${name}.`;
  } else {
    els.statusLine.textContent = `Saved credentials for ${server_url}, but validation failed: ${result.message}`;
  }
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

  els.loginBtn.disabled = true;
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

    const login = await ApiClient.loginWithPassword(serverUrl, username, password);
    if (login.requires_2fa && login.temp_token) {
      showTotpStep(serverUrl, login.temp_token);
      showMessage('Enter your two-factor authentication code.', 'success');
      return;
    }
    if (!login.ok) {
      showMessage(login.message);
      return;
    }

    await finishWithToken(serverUrl, login.token);
  } catch (error) {
    showMessage(error?.message || 'Connect failed. Check the URL and try again.');
  } finally {
    els.loginBtn.disabled = false;
  }
}

async function verifyTotp() {
  clearMessage();
  if (!pending2fa) {
    hideTotpStep();
    return;
  }
  const code = els.totpCode.value.trim();
  if (!code) {
    showMessage('Enter the authentication code.');
    return;
  }

  els.totpBtn.disabled = true;
  try {
    const result = await ApiClient.verifyLogin2fa(pending2fa.serverUrl, pending2fa.tempToken, code);
    if (!result.ok) {
      showMessage(result.message);
      return;
    }
    await finishWithToken(pending2fa.serverUrl, result.token);
  } catch (error) {
    showMessage(error?.message || 'Verification failed.');
  } finally {
    els.totpBtn.disabled = false;
  }
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

  els.tokenBtn.disabled = true;
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
    await updateStatus();
  } catch (error) {
    showMessage(error?.message || 'Token save failed. Check the URL and try again.');
  } finally {
    els.tokenBtn.disabled = false;
  }
}

async function disconnect() {
  clearMessage();
  hideTotpStep();
  await chrome.storage.local.set({
    api_token: null,
    logged_out: true,
    last_timer_status: { active: false, timer: null },
  });
  chrome.runtime.sendMessage({ type: 'refresh_timer' }).catch(() => {});
  showMessage('Disconnected.', 'success');
  await updateStatus();
}

els.loginBtn.addEventListener('click', connectWithPassword);
els.totpBtn.addEventListener('click', verifyTotp);
els.totpCancelBtn.addEventListener('click', () => {
  clearMessage();
  hideTotpStep();
});
els.totpCode.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    verifyTotp();
  }
});
els.tokenBtn.addEventListener('click', connectWithToken);
els.disconnectBtn.addEventListener('click', disconnect);
els.suggestFromTab.addEventListener('change', async () => {
  const enabled = els.suggestFromTab.checked;
  if (enabled) {
    try {
      const granted = await chrome.permissions.request({ permissions: ['activeTab'] });
      if (!granted) {
        els.suggestFromTab.checked = false;
        showMessage('activeTab permission is required for URL suggestions.');
        return;
      }
    } catch {
      // Firefox may grant activeTab implicitly when used from the popup.
    }
  }
  await chrome.storage.local.set({ suggest_from_tab: els.suggestFromTab.checked });
});

updateStatus();
