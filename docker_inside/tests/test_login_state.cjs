// Run with: node docker_inside/tests/test_login_state.cjs
// Evaluate the actual detector against DOM fixtures; no account or network needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '../login_state.js'), 'utf8');

function inspect({host = 'jhk.juhaokai.cn', route = '/index', avatar = true,
                  main = true, password = false, ready = true, selector = '',
                  logout = false, custom = false, title = '', frame = null,
                  accountTag = null, githubUser = '', readyState = null,
                  body = '聚好开工作台：企业管理、业务管理、发票管理、系统设置'} = {}) {
  const element = (textContent = '', shown = true) => ({
    textContent, tagName: 'SPAN', type: 'text', autocomplete: '',
    getClientRects: () => shown ? [{}] : [], getAttribute: () => null,
  });
  const avatarEl = element();
  const mainEl = element();
  const passwordEl = {...element(), type: 'password'};
  // A hidden dropdown item must not be treated as visible logout evidence.
  const logoutEl = element('退出登录', logout);
  const frameEl = frame ? {...element('', frame.visible !== false), tagName: 'IFRAME',
    src: frame.src, title: frame.title || '', contentDocument: null} : null;
  const document = {
    title, readyState: readyState || (ready ? 'complete' : 'loading'),
    body: {innerText: body},
    querySelectorAll(query) {
      if (query === '*') return [avatarEl, mainEl, logoutEl, ...(frameEl ? [frameEl] : [])];
      if (query === 'input') return password ? [passwordEl] : [];
      if (query.startsWith('button,')) return [logoutEl];
      if (query === '.app-wrapper .navbar .avatar-wrapper') return avatar ? [avatarEl] : [];
      if (query === '.app-wrapper .main-container .app-main') return main ? [mainEl] : [];
      if (query === '#custom') return custom ? [mainEl] : [];
      if (query.startsWith('[class*="avatar"]')) return accountTag ? [{...element(), tagName: accountTag}] : [];
      return [];
    },
    querySelector(query) {
      if (query === 'meta[name="user-login"]' && githubUser) return {content: githubUser};
      return null;
    },
  };
  return vm.runInNewContext(`(${script})(selector)`, {
    document, selector,
    location: {hostname: host, pathname: route, hash: '', href: `https://${host}${route}`},
    getComputedStyle: () => ({visibility: 'visible', display: 'block'}), URL,
  });
}

const cases = [
  ['authenticated layout with hidden logout', {}, true],
  ['login route with stale layout', {route: '/login'}, false],
  ['registration route', {route: '/register'}, false],
  ['expired session password dialog', {password: true}, false],
  ['loading', {ready: false}, false],
  ['short authenticated page', {body: '首页'}, true],
  ['empty page', {body: ''}, false],
  ['public page', {avatar: false, main: false}, false],
  ['partial layout', {main: false}, false],
  ['unrelated domain', {host: 'example.com'}, false],
  ['lookalike domain', {host: 'jhk.juhaokai.cn.example.com'}, false],
  ['explicit selector overrides default', {selector: '#custom'}, false],
  ['explicit selector succeeds', {selector: '#custom', custom: true}, true],
  ['existing visible logout rule', {host: 'example.com', logout: true}, true],
  ['GitHub authenticated dashboard marker', {host: 'github.com', githubUser: 'Rebekahjiani'}, true],
  ['GitHub login route remains blocked', {host: 'github.com', route: '/login', githubUser: ''}, false],
];
for (const [name, options, expected] of cases) {
  assert.equal(inspect(options).authenticated, expected, name);
}
console.log(`PASS: ${cases.length} login detector regression cases`);
const evidence = inspect({host: 'example.com', logout: true, accountTag: 'SPAN'});
assert.deepEqual(Array.from(evidence.authEvidence), ['visible_logout', 'account_identity']);
assert.equal(evidence.confidence, 0.95);
const weakEvidence = inspect({host: 'example.com', accountTag: 'SPAN'});
assert.deepEqual(Array.from(weakEvidence.authEvidence), ['account_identity']);
assert.equal(weakEvidence.confidence, 0.45);
console.log('PASS: generic authentication evidence and confidence');
assert.equal(inspect({host:'mail.example.com', title:'登录邮箱'}).blocked, true);
assert.equal(inspect({host:'example.com', frame:{src:'https://id.example.com/oauth/authorize'}}).blocked, true);
assert.equal(inspect({host:'example.com', frame:{src:'https://id.example.com/oauth/authorize', visible:false}}).blocked, false);
assert.equal(inspect({host:'example.com', accountTag:'INPUT'}).identity, false);
assert.equal(inspect({host:'example.com', accountTag:'SPAN'}).identity, true);
assert.equal(inspect({host:'example.com', readyState:'interactive'}).ready, true);
console.log('PASS: 6 embedded-login, identity and loading regression cases');
