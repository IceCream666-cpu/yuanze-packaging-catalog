import {t,translateMessage,translateValue,getLanguage,onLanguageChange,startLocalization,localize} from './i18n.js';
import {requestJSON} from './api-client.js';

startLocalization({container:document.querySelector('.login-box')});
function loginDestination(role, search = location.search) {
  if (role === 'client') return '/client';
  const code = (new URLSearchParams(search).get('code') || '').toUpperCase();
  return /^YZ-BC-\d{6,}$/.test(code)
    ? '/?code=' + encodeURIComponent(code)
    : (role === 'admin' ? '/admin' : '/');
}

const loginForm = document.querySelector('#loginForm');
const usernameInput = loginForm.elements.username;
const passwordInput = loginForm.elements.password;
const togglePassword = document.querySelector('#togglePassword');
const inputHint = document.querySelector('#loginInputHint');
let capsLock = false, extraInputHint = '';
onLanguageChange(()=>checkLoginInput(extraInputHint));
function checkLoginInput(extra = '') {
  extraInputHint = extra;
  const notes = [];
  if (/[\u200B-\u200D\u2060\uFEFF]/u.test(usernameInput.value + passwordInput.value)) notes.push('输入中含有不可见字符，请清空后重新复制账号或密码。');
  if (passwordInput.value && passwordInput.value !== passwordInput.value.trim()) notes.push('密码首尾有空白，请确认是否复制了多余空格。');
  if (/[\uFF01-\uFF5E]/u.test(usernameInput.value)) notes.push('账号中含有全角字符，请使用英文输入法。');
  if (capsLock) notes.push('大写锁定已开启，请核对字母大小写。');
  if (extra) notes.push(extra);
  inputHint.textContent = notes.map(translateMessage).join(' ');
  inputHint.hidden = !notes.length;
}
function setPasswordVisible(visible) {
  passwordInput.type = visible ? 'text' : 'password';
  togglePassword.textContent = visible ? '隐藏密码' : '显示密码';
  togglePassword.setAttribute('aria-pressed', String(visible));
}
togglePassword.addEventListener('click', () => setPasswordVisible(passwordInput.type === 'password'));
for (const input of [usernameInput, passwordInput]) input.addEventListener('input', () => checkLoginInput());
passwordInput.addEventListener('keyup', event => {capsLock = event.getModifierState?.('CapsLock') || false;checkLoginInput();});
passwordInput.addEventListener('blur', () => {capsLock = false;checkLoginInput();});
document.addEventListener('visibilitychange', () => {if (document.hidden) setPasswordVisible(false);});

loginForm.addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const button = form.querySelector('button[type="submit"]');
  if (button.disabled) return;
  const error = document.querySelector('#error');
  button.disabled = true;
  button.textContent = '正在登录…';
  form.setAttribute('aria-busy', 'true');
  error.textContent = '';
  checkLoginInput();
  setPasswordVisible(false);
  try {
    const result = await requestJSON('/api/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    if (!['admin', 'employee', 'client'].includes(result.role)) throw Error('登录结果异常，请稍后重试。');
    // Confirm the browser retained the cookie before leaving the form.
    try {
      const current = await requestJSON('/api/session');
      if (current.role !== result.role) throw Error('登录身份未同步，请刷新页面后重新登录。');
    } catch (error) {
      if (error.status === 401) throw Error('浏览器未保存登录状态，请允许此网站使用 Cookie 后重试。');
      throw error;
    }
    location.href = loginDestination(result.role);
  } catch (err) {
    if (err.status === 401) checkLoginInput('可点“显示密码”核对大小写，或清空浏览器自动填入的密码后重新粘贴。');
    error.textContent = err.status === 401 ? (err.payload?.error || '账号或密码不正确')
      : err.code === 'timeout' ? '登录响应超时，请稍后重新登录。无需更改密码。' + (err.requestId ? `（参考编号：${err.requestId}）` : '')
      : err.message;
  } finally {
    button.disabled = false;
    button.textContent = '登录';
    form.removeAttribute('aria-busy');
  }
});
