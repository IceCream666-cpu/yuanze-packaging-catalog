// Read requests may be retried; mutations are never replayed automatically.
export class ApiError extends Error {
  constructor(message, {status = 0, code = '', payload = null, retryAfter = 0, requestId = ''} = {}) {
    const waitHint = (status === 429 || code === 'LOGIN_RATE_LIMITED') && retryAfter > 0 ? ` 请等待 ${Math.ceil(retryAfter / 1000)} 秒后重试。` : '';
    const reference = requestId && status !== 401 ? `（参考编号：${requestId}）` : '';
    super(message + waitHint + reference);
    this.name = 'ApiError';
    Object.assign(this, {status, code, payload, retryAfter, requestId});
  }
}

function retryAfterMs(value) {
  if (!value?.trim()) return 0;
  const seconds = Number(value);
  return Math.max(0, Number.isFinite(seconds) ? seconds * 1000 : Date.parse(value) - Date.now() || 0);
}

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    const abort = () => {clearTimeout(timer); reject(new DOMException('Request cancelled', 'AbortError'));};
    const timer = setTimeout(() => {signal?.removeEventListener('abort', abort); resolve();}, ms);
    if (signal?.aborted) abort();
    else signal?.addEventListener('abort', abort, {once:true});
  });
}

async function once(path, options, timeoutMs) {
  const controller = new AbortController();
  const upstream = options.signal;
  const abort = () => controller.abort();
  if (upstream?.aborted) abort();
  else upstream?.addEventListener('abort', abort, {once:true});
  let timedOut = false;
  const timer = setTimeout(() => {timedOut = true; controller.abort();}, timeoutMs);
  const isRead = options.method === 'GET';
  let requestId = '';
  try {
    const response = await fetch(path, {...options, signal:controller.signal});
    const reference = response.headers?.get('X-Request-ID') || '';
    requestId = /^[A-Za-z0-9._-]{1,128}$/.test(reference) ? reference : '';
    if (response.redirected || response.type === 'opaqueredirect' || response.status >= 300 && response.status < 400) throw new ApiError('系统接口跳转异常，请稍后重试；请联系管理员检查网站配置。', {status:response.status, code:'unexpected_redirect', requestId});
    const retryAfter = retryAfterMs(response.headers?.get('Retry-After'));
    let value;
    try {value = await response.json();} catch (error) {
      if (controller.signal.aborted) throw error;
      // A proxy may return an HTML error page; retain its HTTP status.
      if (response.ok) throw new ApiError('服务器返回的数据格式异常，请稍后重试。', {status:response.status, code:'invalid_response', requestId});
    }
    if (!response.ok) {
      const defaults = {
        401:'登录已过期，请重新登录。',
        403:'没有执行此操作的权限，或登录验证已更新。请刷新后再试。',
        429:'系统当前繁忙，请稍后重试。',
        502:'网站服务暂时不可用，请稍后重试。',
        503:'网站服务暂时不可用，请稍后重试。',
        504:'网站服务响应超时，请稍后重试。',
      };
      const message = typeof value?.error === 'string' ? value.error : typeof value?.message === 'string' ? value.message : defaults[response.status] || `请求失败（${response.status}），请稍后重试。`;
      const code = typeof value?.code === 'string' ? value.code : 'http_error';
      throw new ApiError(message, {status:response.status, code, payload:value, retryAfter, requestId});
    }
    if (!value || typeof value !== 'object') throw new ApiError('服务器返回的数据格式异常，请稍后重试。', {status:response.status, code:'invalid_response', requestId});
    return value;
  } catch (error) {
    if (upstream?.aborted) throw new DOMException('Request cancelled', 'AbortError');
    if (timedOut) throw new ApiError(isRead ? '读取资料超时，请重试。' : '请求超时，操作结果尚未确认。请先刷新核对，避免重复提交。', {code:'timeout', requestId});
    if (error instanceof ApiError) throw error;
    if (error.name === 'AbortError') throw error;
    if (error instanceof TypeError) {
      const offline = globalThis.navigator?.onLine === false;
      throw new ApiError(offline ? '当前设备已离线，请恢复网络后重试。' : '暂时无法连接系统，请检查网络后重试。', {code:offline ? 'offline' : 'network'});
    }
    throw error;
  } finally {
    clearTimeout(timer);
    upstream?.removeEventListener('abort', abort);
  }
}

export async function requestJSON(path, {timeoutMs = 30000, retries = 2, ...options} = {}) {
  const request = {credentials:'same-origin', cache:'no-store', redirect:'manual', ...options,
    method:String(options.method || 'GET').toUpperCase(),
    headers:{Accept:'application/json', ...options.headers}};
  const maxRetries = request.method === 'GET' ? Math.max(0, Math.min(2, retries)) : 0;
  for (let attempt = 0; ; attempt++) {
    try {return await once(path, request, timeoutMs);} catch (error) {
      const retryable = [429,502,503,504].includes(error.status) || ['network','timeout'].includes(error.code);
      // Never ignore a long Retry-After and retry earlier than the server asked.
      if (!retryable || attempt >= maxRetries || error.retryAfter > 5000 || request.signal?.aborted) throw error;
      await wait(Math.max(error.retryAfter || 0, 500 * 2 ** attempt + Math.random() * 250), request.signal);
    }
  }
}
