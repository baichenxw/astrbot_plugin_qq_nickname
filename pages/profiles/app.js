import { fallback, errorKeys } from './i18n.js';
const $ = id => document.getElementById(id);
const bridge = window.AstrBotPluginPage;
let offset = 0, rows = [], bots = [], revision = 0, pendingDelete = null, loading = false;
let backendOnly = false, savingSettings = false, total = 0, editMode = false, locale = 'zh-CN';
const notices = {};
function t(key, args = {}) {
  const defaultText = key.split('.').reduce((value, part) => value?.[part], fallback) ?? key;
  const value = bridge?.t ? bridge.t('pages.profiles.' + key, defaultText) : defaultText;
  return String(value).replace(/\{(\w+)\}/g, (match, name) => args[name] ?? match);
}
function errorText(value) {
  const message = value?.message || String(value);
  return errorKeys[message] ? t(errorKeys[message]) : message;
}
function notice(id, key = '', args = {}) {
  notices[id] = { key, args };
  renderNotice(id);
}
function renderNotice(id) {
  const { key, args } = notices[id] || { key: '', args: {} };
  const params = { ...args };
  if (params.error) params.error = errorText(params.error);
  $(id).textContent = key === 'error' ? errorText(args.error) : key ? t(key, params) : '';
}
function renderRows() {
  $('users').replaceChildren();
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const value of [row.nickname || t('unset'), row.qq || t('unbound')]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    const identity = document.createElement('td'), uid = document.createElement('span'), bot = document.createElement('small');
    uid.className = 'uid'; uid.textContent = row.openid; bot.textContent = row.bot_id;
    identity.append(uid, bot); tr.append(identity);
    const time = document.createElement('td');
    time.textContent = new Date(row.updated_at.replace(' ', 'T') + 'Z').toLocaleString(locale); tr.append(time);
    const actions = document.createElement('td'), editButton = document.createElement('button'), deleteButton = document.createElement('button');
    editButton.textContent = t('edit'); editButton.onclick = () => edit(row);
    deleteButton.textContent = t('delete'); deleteButton.className = 'delete'; deleteButton.onclick = () => {
      pendingDelete = row; $('delete-name').textContent = row.nickname || row.openid; $('delete-dialog').showModal();
    };
    actions.append(editButton, deleteButton); tr.append(actions); $('users').append(tr);
  }
  $('count').textContent = t('count', { total }) + (rows.length ? t('range', { start: offset + 1, end: offset + rows.length }) : '');
}
function renderContext(context) {
  locale = context.locale || 'zh-CN';
  document.documentElement.lang = locale;
  document.documentElement.classList.toggle('dark', context.isDark);
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  $('edit-title').textContent = t(editMode ? 'edit_title' : 'add_title');
  $('empty').textContent = t(backendOnly ? 'empty_admin' : 'empty');
  renderRows();
  Object.keys(notices).forEach(renderNotice);
}
function showSettings(enabled) {
  backendOnly = enabled;
  $('backend-only').checked = enabled;
  notice('settings-status', enabled ? 'enabled' : 'disabled');
  $('empty').textContent = t(enabled ? 'empty_admin' : 'empty');
}
function error(e) { notice('status', 'error', { error: e }); }
function edit(row = null) {
  editMode = Boolean(row); $('edit-title').textContent = t(editMode ? 'edit_title' : 'add_title');
  $('bot').replaceChildren();
  for (const id of new Set([...bots, ...(row ? [row.bot_id] : [])])) {
    const option = new Option(id, id); $('bot').append(option);
  }
  $('bot').value = row?.bot_id || bots[0] || '';
  $('bot').disabled = Boolean(row); $('openid').readOnly = Boolean(row);
  $('openid').value = row?.openid || ''; $('nickname').value = row?.nickname || '';
  $('qq').value = row?.qq || ''; revision = row?.revision || 0;
  notice('edit-error'); $('editor').showModal();
}
async function load() {
  if (loading || savingSettings) return;
  loading = true; $('refresh').disabled = true; $('backend-only').disabled = true; notice('status', 'loading');
  try {
    const data = await bridge.apiGet('profiles', { q: $('search').value.trim(), offset });
    rows = data.records; bots = data.bots; total = data.total;
    if (!savingSettings) {
      showSettings(data.backend_only === true);
      $('backend-only').disabled = false;
    }
    renderRows();
    $('empty').hidden = rows.length > 0;
    $('prev').disabled = offset === 0; $('next').disabled = offset + 100 >= data.total;
    notice('status'); $('add').disabled = !bots.length;
  } catch (e) { error(e); }
  finally { loading = false; $('refresh').disabled = false; }
}
$('add').onclick = () => edit(); $('cancel').onclick = () => $('editor').close();
$('refresh').onclick = load;
$('backend-only').onchange = async () => {
  const previous = backendOnly;
  savingSettings = true; $('backend-only').disabled = true;
  notice('settings-status', 'saving');
  try {
    const data = await bridge.apiPost('settings', { backend_only: $('backend-only').checked });
    showSettings(data.backend_only === true);
  } catch (e) {
    showSettings(previous);
    notice('settings-status', 'save_failed', { error: e });
  } finally {
    savingSettings = false; $('backend-only').disabled = loading;
  }
};
$('search-form').onsubmit = e => { e.preventDefault(); offset = 0; load(); };
$('prev').onclick = () => { offset = Math.max(0, offset - 100); load(); };
$('next').onclick = () => { offset += 100; load(); };
$('edit-form').onsubmit = async e => {
  e.preventDefault(); $('save').disabled = true; notice('edit-error');
  try {
    await bridge.apiPost('profiles/save', { bot_id: $('bot').value, openid: $('openid').value.trim(), nickname: $('nickname').value.trim(), qq: $('qq').value.trim(), revision });
    $('editor').close(); await load();
  } catch (e) { notice('edit-error', 'error', { error: e }); }
  finally { $('save').disabled = false; }
};
$('delete-cancel').onclick = () => $('delete-dialog').close();
$('delete-confirm').onclick = async () => {
  $('delete-confirm').disabled = true;
  try {
    await bridge.apiPost('profiles/delete', { bot_id: pendingDelete.bot_id, openid: pendingDelete.openid, revision: pendingDelete.revision });
    $('delete-dialog').close(); offset = 0; await load();
  } catch(e) { $('delete-dialog').close(); error(e); }
  finally { $('delete-confirm').disabled = false; }
};
try {
  if (!bridge) throw new Error(t('open_dashboard'));
  const context = await bridge.ready();
  notice('settings-status', 'loading_settings');
  renderContext(context);
  bridge.onContext(renderContext);
  await load();
} catch(e) { error(e); }
