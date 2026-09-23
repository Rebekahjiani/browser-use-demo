(successSelector) => {
  const siteAuthRules = [
    {
      name: 'iquicker-home',
      hosts: [/^iquicker\.com\.cn$/i, /\.iquicker\.com\.cn$/i],
      path: /^\/home(?:\/|$)/,
    },
    {
      name: 'juhaokai-home',
      hosts: [/^jhk\.juhaokai\.cn$/i],
      selectors: ['.app-wrapper .navbar .avatar-wrapper', '.app-wrapper .main-container .app-main'],
    },
    {
      name: 'github-account-meta',
      hosts: [/^github\.com$/i],
      meta: 'meta[name="user-login"]',
    },
  ];
  const visible = el => el.getClientRects().length > 0 &&
    getComputedStyle(el).visibility !== 'hidden' && getComputedStyle(el).display !== 'none';
  const authRoute = /(?:^|[/#?=&._-])(?:login|signin|sign-in|sign_in|register|signup|sign-up|forgot-password|reset-password|captcha|verify)(?:$|[/#?=&._-])/i;
  let blocked = authRoute.test(location.pathname + location.hash.split('?')[0]);
  let signedIn = false;
  let password = false;
  let loginControl = false;
  let identity = false;
  const frameRoutes = [];
  // Embedded SSO pages are cross-origin: their fields are inaccessible from
  // the parent, but the visible frame's URL/title still identifies authentication.
  const authFrame = /(?:login|signin|passport|oauth|authorize|authentication)/i;
  const titleLogin = /^(?:登录|登入|登錄|sign\s*in|log\s*in)|(?:登录|登入|登錄)\s*$/i;
  if (titleLogin.test(document.title || '')) blocked = true;
  // "退出登录" contains "登录", but is evidence of a signed-in session.
  const logoutLabel = /^(?:退出\s*(?:登录|登入|登錄)|注销|註銷|登出|sign\s*out|log\s*out)$/i;
  const loginLabel = /^(?:(?:用户|账号|账户|手机|短信|验证码|密码|微信|扫码|快捷|立即|安全|统一|企业|重新|请先|请)\s*)*(?:登录|登入|登錄)(?:\s*[/／]\s*注册)?$|^(?:log\s*in|sign\s*in)(?:\s+to\b.*)?$/i;
  const roots = [document];
  for (let i = 0; i < roots.length; i++) {
    for (const el of roots[i].querySelectorAll('*')) {
      if (el.shadowRoot) roots.push(el.shadowRoot);
      if (el.tagName === 'IFRAME' && visible(el)) {
        const frameUrl = new URL(el.src || 'about:blank', location.href);
        try { if (!el.contentDocument) frameRoutes.push(frameUrl.origin + frameUrl.pathname); } catch (_) { frameRoutes.push(frameUrl.origin + frameUrl.pathname); }
        if (authRoute.test(frameUrl.pathname) || authFrame.test(frameUrl.hostname + frameUrl.pathname) ||
            /登录|登入|登錄|sign\s*in|log\s*in/i.test(el.title || '')) blocked = true;
        try { if (el.contentDocument) roots.push(el.contentDocument); } catch (_) {}
      }
    }
    const inputs = [...roots[i].querySelectorAll('input')].filter(visible);
    if (inputs.some(el => el.type === 'password' || el.autocomplete === 'current-password')) password = true;
    const labels = [...roots[i].querySelectorAll('button, a, [role="button"], h1, h2, h3, input[type="submit"]')]
      .filter(visible).map(el => (el.textContent || el.getAttribute('value') || '').trim());
    const loginLabels = labels.filter(s => !logoutLabel.test(s));
    if (loginLabels.some(s => loginLabel.test(s))) loginControl = true;
    if (loginLabels.some(s => loginLabel.test(s)) &&
        inputs.some(el => /^(text|email|tel|number)$/.test(el.type))) blocked = true;
    if (labels.some(s => /扫码登录|掃碼登錄|scan.*(?:log|sign)\s*in/i.test(s))) blocked = true;
    if (labels.some(s => logoutLabel.test(s))) signedIn = true;
    if ([...roots[i].querySelectorAll('[class*="avatar"], [class*="user-name"], [class*="username"], [data-testid*="avatar"], [data-testid*="user"], [data-user], [data-account], [aria-current="user"], [aria-label*="账户"], [aria-label*="Account"]')]
        .some(el => visible(el) && !/^(INPUT|LABEL|FORM)$/.test(el.tagName) && !el.querySelector?.('input'))) identity = true;
  }
  if (password) blocked = true;
  const ready = document.readyState !== 'loading' && !!document.body &&
    document.body.innerText.trim().length > 0;
  const configuredSuccess = successSelector ? [...document.querySelectorAll(successSelector)].some(visible) : false;
  const has = selector => [...document.querySelectorAll(selector)].some(visible);
  const siteAuthenticated = siteAuthRules.some(rule => {
    if (!rule.hosts.some(host => host.test(location.hostname))) return false;
    if (rule.path && !rule.path.test(location.pathname)) return false;
    if (rule.selectors && !rule.selectors.every(has)) return false;
    if (rule.meta && !document.querySelector(rule.meta)?.content?.trim()) return false;
    return true;
  });
  // Only presence flags leave the page. Never return cookie/token/user values.
  let storage = false;
  const authKey = /(?:token|session|auth|logged.?in)/i;
  try {
    storage = document.cookie.split(';').some(item => authKey.test(item.split('=')[0]) && item.includes('='));
    for (const area of [localStorage, sessionStorage]) {
      for (let i = 0; i < area.length; i++) {
        const key = area.key(i);
        if (authKey.test(key) && area.getItem(key)) storage = true;
      }
    }
  } catch (_) { /* HttpOnly cookies and restricted storage are not readable. */ }
  const route = location.origin + location.pathname + location.hash.split('?')[0];
  const authEvidence = [];
  if (configuredSuccess) authEvidence.push('configured_selector');
  if (siteAuthenticated) authEvidence.push('site_rule');
  if (signedIn) authEvidence.push('visible_logout');
  if (identity) authEvidence.push('account_identity');
  if (storage) authEvidence.push('session_marker');
  const confidence = configuredSuccess || siteAuthenticated || signedIn ? 0.95 :
    (identity && storage ? 0.8 : identity || storage ? 0.45 : 0);
  return {blocked, ready, route, identity, storage, password, loginControl, frameRoutes,
    blank: location.href === 'about:blank',
    authEvidence, confidence,
    authenticated: ready && !blocked &&
    (successSelector ? configuredSuccess : signedIn || siteAuthenticated)};
}
