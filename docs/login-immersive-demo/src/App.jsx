import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, Pause, Play, Check, Globe2, Upload, X, CircleAlert } from 'lucide-react';
import { authenticate, createPreviewTransport, inputWarnings } from './login-contract.js';

export const VIDEO_URL = new URL('../assets/login-atmosphere.mp4', import.meta.url).href;
const copy = {
  zh: {
    subtitle: '登录你的源泽包材库账号', username: '账号', password: '密码',
    userPlaceholder: '请输入公司分配的账号', passwordPlaceholder: '请输入密码',
    show: '显示密码', hide: '隐藏密码', login: '登录', busy: '正在登录…',
    help: '请使用公司分配的账号', contact: '账号问题？', contactLink: '联系管理员',
    contactInfo: '请联系为你分配账号的源泽管理员，核对账号或重置密码。',
    roleHint: '登录后自动进入你的工作空间',
    pause: '暂停背景视频', play: '播放背景视频', fallback: '视频暂不可用，登录不受影响',
    loadingVideo: '正在加载视频', preview: '界面预览 · 不连接正式账号', demo: '填入演示账号',
    upload: '选择本地视频', uploadHint: '视频只在本机预览，未上传', fileError: '请选择 MP4 或 WebM 视频文件。',
    success: '登录交互演示完成', successHint: '正式接入后，将按原有账号权限进入对应页面。',
    back: '返回登录预览', client: '客户工作空间', employee: '业务员工作空间', admin: '管理员工作空间',
    error: '账号或密码不正确。预览请使用下方“填入演示账号”。',
    offline: '当前网络不可用，请恢复网络后重试。', timeout: '登录响应超时，请稍后重试，无需更改密码。',
    cookie_missing: '浏览器未保存登录状态，请允许 Cookie 后重试。',
    role_mismatch: '登录身份未同步，请刷新后重新登录。', invalid_role: '登录结果异常，请稍后重试。',
    unknown: '暂时无法登录，请稍后重试。',
    invisible: '输入中含有不可见字符，请清空后重新复制。', whitespace: '密码首尾有空格，请核对。',
    fullwidth: '账号含有全角字符，请使用英文输入法。', caps: '大写锁定已开启。',
  },
  en: {
    subtitle: 'Sign in to your account', username: 'Account', password: 'Password',
    userPlaceholder: 'Enter your company account', passwordPlaceholder: 'Enter your password',
    show: 'Show password', hide: 'Hide password', login: 'Sign in', busy: 'Signing in…',
    help: 'Use the account provided by your company', contact: 'Need account help?', contactLink: 'Contact your administrator',
    contactInfo: 'Contact your Yuanze account administrator to check your account or reset your password.',
    roleHint: 'Your account takes you to the right workspace',
    pause: 'Pause background video', play: 'Play background video', fallback: 'Video unavailable. You can still sign in.',
    loadingVideo: 'Loading video', preview: 'Interface preview · No live account connection', demo: 'Fill demo account',
    upload: 'Choose local video', uploadHint: 'Local preview only. Nothing is uploaded.', fileError: 'Choose an MP4 or WebM video.',
    success: 'Sign-in preview complete', successHint: 'When connected, your existing account permissions determine your workspace.',
    back: 'Back to sign-in preview', client: 'Client workspace', employee: 'Sales workspace', admin: 'Admin workspace',
    error: 'Incorrect account or password. Use “Fill demo account” below for this preview.',
    offline: 'You are offline. Reconnect and try again.', timeout: 'Sign-in timed out. Try again later; there is no need to change your password.',
    cookie_missing: 'Your browser did not save the session. Allow cookies and try again.',
    role_mismatch: 'Your session did not sync. Refresh and sign in again.', invalid_role: 'Unexpected sign-in result. Please try again later.',
    unknown: 'Unable to sign in right now. Please try again later.',
    invisible: 'Invisible characters detected. Clear and paste your credentials again.', whitespace: 'Check the spaces at the beginning or end of your password.',
    fullwidth: 'Your account contains full-width characters.', caps: 'Caps Lock is on.',
  },
};

export default function App({ transport, initialScenario } = {}) {
  const [language, setLanguage] = useState('zh');
  const t = copy[language];
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const [capsLock, setCapsLock] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [result, setResult] = useState(null);
  const [source, setSource] = useState(VIDEO_URL);
  const [videoState, setVideoState] = useState('loading');
  const [playing, setPlaying] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const backgroundVideo = useRef(null), panelVideo = useRef(null), videoInput = useRef(null), heading = useRef(null);
  const objectUrl = useRef(null);
  const warnings = inputWarnings(username, password, capsLock);
  const scenario = initialScenario || new URLSearchParams(window.location.search).get('scenario') || 'success';

  useEffect(() => {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  }, [language]);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => { if (query.matches) setPlaying(false); };
    const onHidden = () => { if (document.hidden) { setVisible(false); setPlaying(false); } };
    query.addEventListener('change', onChange);
    document.addEventListener('visibilitychange', onHidden);
    return () => {
      query.removeEventListener('change', onChange);
      document.removeEventListener('visibilitychange', onHidden);
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    };
  }, []);

  useEffect(() => {
    for (const video of [backgroundVideo.current, panelVideo.current]) {
      if (!video) continue;
      if (playing) video.play()?.catch(error => {
        if (error.name === 'NotAllowedError') setPlaying(false);
      });
      else video.pause();
    }
  }, [playing, source]);

  useEffect(() => {
    setVideoState('loading');
    const timer = setTimeout(() => setVideoState(state => state === 'loading' ? 'unavailable' : state), 12000);
    return () => clearTimeout(timer);
  }, [source]);

  useEffect(() => { if (result) heading.current?.focus(); }, [result]);

  async function submit(event) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true); setError(''); setVisible(false); setCapsLock(false);
    try {
      const value = await authenticate(transport || createPreviewTransport(scenario), { username, password }, window.location.search);
      setPassword('');
      setResult(value);
    } catch (err) {
      setError(err.status === 401 ? 'error' : ['offline', 'timeout'].includes(err.code) ? err.code
        : ['cookie_missing', 'role_mismatch', 'invalid_role'].includes(err.message) ? err.message : 'unknown');
    } finally {
      submitting.current = false; setBusy(false);
    }
  }

  function useLocalVideo(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!['video/mp4', 'video/webm'].includes(file.type)) { setError('fileError'); return; }
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    objectUrl.current = URL.createObjectURL(file);
    setSource(objectUrl.current); setPlaying(!window.matchMedia('(prefers-reduced-motion: reduce)').matches); setError('');
  }

  const videoProps = { src: source, autoPlay: playing, muted: true, loop: true, playsInline: true, preload: 'metadata', tabIndex: -1, 'aria-hidden': true };

  return (
    <div className="relative isolate flex min-h-screen flex-col items-center justify-center bg-black px-4 py-7 text-[#17171b] sm:px-8 sm:py-12">
      <div className="pointer-events-none fixed inset-0 -z-20 overflow-hidden bg-black" aria-hidden="true">
        <video ref={backgroundVideo} {...videoProps} className="h-full w-full scale-105 object-cover" />
      </div>
      <div className="pointer-events-none fixed inset-0 -z-10 bg-black/10 backdrop-blur-sm" aria-hidden="true" />

      <main className="login-card relative z-10 flex w-full max-w-[1040px] flex-col rounded-[2.5rem] border border-gray-200 bg-white p-3 shadow-[0_32px_100px_rgba(0,0,0,0.48)] md:min-h-[650px] md:flex-row" aria-label="源泽登录">
        <section className="video-panel relative h-[225px] shrink-0 overflow-hidden rounded-[2rem] bg-[#0c0c0e] sm:h-[280px] md:h-auto md:w-[45%]" aria-label={language === 'zh' ? '灵感视频' : 'Inspiration video'}>
          <video ref={panelVideo} {...videoProps} className="absolute inset-0 h-full w-full object-cover" onLoadedData={() => setVideoState('ready')} onPlaying={() => setVideoState('ready')} onError={() => setVideoState('unavailable')} />
          {videoState !== 'ready' && <div className="fallback-composition pointer-events-none absolute inset-0 flex flex-col justify-between px-8 py-9 text-white md:px-10 md:py-11">
            <div className="flex items-center gap-2.5 text-[10px] tracking-[0.3em] text-white/65"><span className="h-1.5 w-1.5 rounded-full bg-[#ff7847]" /> A WORLD OF POSSIBILITIES</div>
            <div><p className="fallback-title text-[33px] font-medium leading-[1.12] tracking-[-0.05em] sm:text-[42px] md:text-[52px]">Good ideas.<br /><span className="text-white/45">Great beginnings.</span></p><p className="mt-5 hidden text-[10px] tracking-[0.3em] text-white/50 md:block">YUANZE MATERIAL LIBRARY</p></div>
            <div className="hidden h-px w-12 bg-white/30 md:block" />
          </div>}
          <div className="absolute bottom-5 left-6 right-5 flex items-center justify-between gap-2 text-white">
            <span className="text-[10px] leading-4 text-white/65">{videoState === 'unavailable' ? t.fallback : videoState === 'loading' ? t.loadingVideo : 'MOTION / INSPIRATION'}</span>
            {videoState === 'ready' && <button type="button" onClick={() => setPlaying(!playing)} className="motion-toggle flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-black/35 text-white backdrop-blur-md" aria-label={playing ? t.pause : t.play} aria-pressed={!playing}>{playing ? <Pause size={15} /> : <Play size={15} />}</button>}
          </div>
        </section>

        <section className="login-form-panel relative flex min-w-0 flex-1 flex-col justify-center px-5 pb-7 pt-14 sm:px-10 md:w-[55%] md:px-12 md:py-16" aria-labelledby="loginTitle">
          <div className="pointer-events-none absolute left-0 top-0 h-64 w-64 rounded-full bg-gradient-to-br from-[#FF512F] to-[#F09819] opacity-20 blur-[80px]" aria-hidden="true" />
          <button type="button" className="language-button absolute right-5 top-4 z-10 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-xs text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 md:right-7 md:top-5" onClick={() => setLanguage(language === 'zh' ? 'en' : 'zh')} aria-label={language === 'zh' ? 'Switch to English' : '切换到中文'}><Globe2 size={14} />{language === 'zh' ? 'English' : '中文'}</button>
          <div className="relative z-10 mx-auto w-full max-w-[386px]">
            <div className="mb-8 flex items-center justify-center">
              <svg className="h-11 w-[94px]" viewBox="1198 262 367 174" role="img" aria-label="YUANZE 源泽"><image href="/yuanze-brand-guide.png" width="1800" height="1520" /></svg>
            </div>

            {result ? <div className="text-center">
              <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"><Check size={24} /></div>
              <h1 id="loginTitle" ref={heading} tabIndex={-1} className="text-[30px] font-semibold tracking-tight outline-none">{t.success}</h1>
              <p className="mt-4 text-sm leading-7 text-gray-500">{t.successHint}</p>
              <div className="my-7 rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm"><span>{t[result.role]}</span><code className="mt-1 block text-xs text-gray-500">{result.destination}</code></div>
              <button type="button" onClick={() => { setResult(null); setError(''); }} className="w-full rounded-2xl bg-[#141417] px-4 py-4 text-sm font-medium text-white">{t.back}</button>
            </div> : <>
              <header className="text-center"><h1 id="loginTitle" className="text-[40px] font-semibold leading-[1.18] tracking-[-0.05em] text-[#151519]">Welcome back</h1><p className="mt-3 text-sm text-gray-500">{t.subtitle}</p></header>
              <form className="mt-9" onSubmit={submit} aria-busy={busy} aria-describedby="loginHelp" autoComplete="on">
                <div className="field-group rounded-[1.25rem] border border-gray-200 bg-gray-50 p-2 transition focus-within:border-gray-900 focus-within:bg-white">
                  <div className="px-3 py-1.5"><label htmlFor="username" className="block text-[11px] font-medium text-gray-500">{t.username}</label><input id="username" name="username" type="text" className="mt-1 block min-h-7 w-full bg-transparent text-[16px] text-gray-900 outline-none placeholder:text-gray-400" placeholder={t.userPlaceholder} autoComplete="username" autoCapitalize="none" autoCorrect="off" spellCheck={false} required value={username} onChange={event => { setUsername(event.target.value); setError(''); }} aria-describedby={warnings.length ? 'inputHint' : undefined} /></div>
                </div>
                <div className="field-group mt-3 flex items-center gap-1 rounded-[1.25rem] border border-gray-200 bg-gray-50 p-2 transition focus-within:border-gray-900 focus-within:bg-white">
                  <div className="min-w-0 flex-1 px-3 py-1.5"><label htmlFor="password" className="block text-[11px] font-medium text-gray-500">{t.password}</label><input id="password" name="password" type={visible ? 'text' : 'password'} className="mt-1 block min-h-7 w-full bg-transparent text-[16px] text-gray-900 outline-none placeholder:text-gray-400" placeholder={t.passwordPlaceholder} autoComplete="current-password" autoCapitalize="none" autoCorrect="off" spellCheck={false} required value={password} onChange={event => { setPassword(event.target.value); setError(''); }} onKeyUp={event => setCapsLock(event.getModifierState('CapsLock'))} onBlur={() => setCapsLock(false)} aria-describedby={warnings.length ? 'inputHint' : undefined} aria-invalid={error === 'error' ? true : undefined} /></div>
                  <button type="button" className="eye-button flex h-11 w-9 shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-900" aria-label={visible ? t.hide : t.show} aria-controls="password" aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={17} strokeWidth={1.6} /> : <Eye size={17} strokeWidth={1.6} />}</button>
                  <button type="submit" className="submit-orb group relative m-1 flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-full" disabled={busy} aria-label={busy ? t.busy : t.login}>
                    <span className="orb-glow pointer-events-none absolute -inset-1 rounded-full opacity-0 blur-[9px] transition-opacity duration-300" aria-hidden="true" />
                    <span className="orb-border pointer-events-none absolute inset-0 rounded-full" aria-hidden="true" />
                    <span className="orb-core relative flex h-[44px] w-[44px] items-center justify-center rounded-full bg-[#08080b] text-white shadow-[inset_0_1px_4px_rgba(255,255,255,0.2)]">{busy ? <LoaderCircle size={20} className="loading-spinner" aria-hidden="true" /> : <ArrowRight size={21} className="transition-transform duration-200 group-hover:translate-x-0.5 group-focus-visible:translate-x-0.5" aria-hidden="true" />}</span>
                  </button>
                </div>
                <div className="mt-3 min-h-6" aria-live="polite" aria-atomic="true"><p className="text-right text-[11px] text-gray-500">{busy ? t.busy : t.roleHint}</p></div>
                {warnings.length > 0 && <p id="inputHint" role="status" className="mt-2 text-xs leading-5 text-amber-800">{warnings.map(key => t[key]).join(' ')}</p>}
                {error && <p role="alert" className="mt-3 flex items-start gap-2 rounded-xl bg-red-50 p-3 text-xs leading-5 text-red-700"><CircleAlert size={15} className="mt-0.5 shrink-0" />{t[error] || t.unknown}</p>}
              </form>
              <div className="my-6 flex items-center gap-3" aria-hidden="true"><span className="h-px flex-1 bg-gradient-to-l from-gray-200 to-transparent" /><LockKeyhole size={12} className="text-gray-400" /><span className="h-px flex-1 bg-gradient-to-r from-gray-200 to-transparent" /></div>
              <p id="loginHelp" className="text-center text-xs leading-6 text-gray-500">{t.help}</p>
              <p className="mt-1 flex flex-wrap items-center justify-center gap-x-1.5 text-center text-xs leading-6 text-gray-500">{t.contact}<button type="button" onClick={() => setHelpOpen(!helpOpen)} aria-expanded={helpOpen} aria-controls="accountHelp" className="help-link min-h-8 rounded-md bg-gradient-to-r from-[#d83a1d] to-[#ab5a05] bg-clip-text font-semibold text-transparent">{t.contactLink}</button></p>
              {helpOpen && <div id="accountHelp" className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs leading-6 text-gray-600">{t.contactInfo}</div>}
            </>}
          </div>
        </section>
      </main>

      <aside className="preview-tools relative z-10 mt-5 flex max-w-[1040px] flex-wrap items-center justify-center gap-x-4 gap-y-1 rounded-2xl bg-black/55 px-4 py-1 text-[11px] leading-5 text-white/80 backdrop-blur-md" aria-label="预览工具">
        <span>{t.preview}</span><button type="button" onClick={() => { setUsername('demo.employee'); setPassword('YuanzeDemo2026'); setResult(null); setError(''); }} className="min-h-10 rounded-md px-1 text-white/85 underline decoration-white/25 underline-offset-4">{t.demo}</button>
        <button type="button" onClick={() => videoInput.current?.click()} className="flex min-h-10 items-center gap-1.5 rounded-md px-1 text-white/85"><Upload size={12} />{t.upload}</button>
        <input ref={videoInput} type="file" accept="video/mp4,video/webm" className="hidden" onChange={useLocalVideo} aria-label={t.upload} />
        {source.startsWith('blob:') && <span>{t.uploadHint}<button type="button" aria-label="恢复原视频地址 / Restore source video" className="ml-2 inline-flex rounded p-1 align-middle" onClick={() => setSource(VIDEO_URL)}><X size={12} /></button></span>}
      </aside>
    </div>
  );
}
