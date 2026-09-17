(token, instructions, finished) => {
  const id = 'browser-use-handoff';
  let host = document.getElementById(id);
  if (host && host.dataset.token === token) return host.dataset.response || 'waiting';
  if (!document.body) return 'waiting';
  if (host) host.remove();
  host = document.createElement('div');
  host.id = id;
  host.dataset.token = token;
  host.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:2147483647;';
  const root = host.attachShadow({mode: 'open'});
  root.innerHTML = `
    <style>
      :host {all:initial;font-family:system-ui,-apple-system,sans-serif;color:#18243a}
      section {box-sizing:border-box;width:min(420px,calc(100vw - 40px));max-height:calc(100vh - 40px);overflow:auto;padding:20px;background:#fff;border:1px solid #dce3ee;border-radius:16px;box-shadow:0 8px 36px #13233b33}
      header {display:flex;align-items:center;justify-content:space-between;gap:12px}
      strong {font-size:17px} p {font-size:14px;line-height:1.6;white-space:pre-wrap;margin:14px 0}
      small {display:block;color:#64748b;font-size:12px;margin:12px 0}
      footer {display:flex;gap:10px} button {font:inherit;font-size:14px;cursor:pointer;border:1px solid #dce3ee;border-radius:8px;padding:10px 14px;background:#fff;color:#344155}
      #continue {background:#2463eb;color:#fff;border-color:#2463eb;flex:1}
      #toggle {border:0;padding:4px;background:transparent;font-size:12px}
      [hidden] {display:none}
    </style>
    <section aria-label="Browser-use 演示控制" role="region">
      <header><strong></strong><button id="toggle" aria-expanded="true">收起</button></header>
      <div id="body"><p></p><small></small><footer><button id="cancel">结束任务</button><button id="continue"></button></footer></div>
    </section>`;
  root.querySelector('strong').textContent = finished ? '任务已完成' : '已暂停 · 请你操作';
  root.querySelector('p').textContent = instructions;
  root.querySelector('small').textContent = finished
    ? '结果已保存，可以继续查看当前页面。'
    : '请直接操作网页，完成后点击“继续执行”。Agent 当前已暂停。';
  root.querySelector('#continue').textContent = finished ? '关闭演示' : '继续执行';
  root.querySelector('#cancel').hidden = finished;
  root.querySelector('#continue').onclick = () => {host.dataset.response = 'continue';};
  root.querySelector('#cancel').onclick = () => {host.dataset.response = 'cancel';};
  root.querySelector('#toggle').onclick = (event) => {
    const body = root.querySelector('#body');
    body.hidden = !body.hidden;
    event.target.textContent = body.hidden ? '展开' : '收起';
    event.target.setAttribute('aria-expanded', String(!body.hidden));
  };
  document.body.append(host);
  return 'waiting';
}
