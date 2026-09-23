# 容器内 browser-use 探索驱动（无弹窗登录等待版）

基于提供的 docker_inside.zip 修改，适配 browser-use==0.13.10。

本次修复：识别聚好开登录后布局，兼容隐藏的退出菜单；短正文页面不再因不足 20 字被误判为未加载；启动时先打开目标网址；初始化异常保存失败结果；校验步数、端口和等待时间，登录恢复时保留先前动作结果。

运行环境：Python 3.12+，使用 `python -m pip install -r requirements.txt` 安装固定版本依赖。Chrome 由容器启动并开放 CDP 端口，本包不包含 Docker 镜像或 Chrome。

## 部署和调用

将 browser_ape.py、human_interaction.py、login_state.js 一起复制到容器
`/opt/kaiwu/ape/bin/`，或替换镜像构建上下文中的对应文件后重新构建镜像。
旧 handoff_panel.js 已不再使用，可删除。不能只更新 browser_ape.py。

原命令不变：

```sh
"$APE_PYTHON" "$DRIVER_DIR/browser_ape.py" \
  --url "$url" \
  --capture-dir "$capture_dir" \
  --llm-api-key "$llm_key" \
  --llm-base-url "$llm_base" \
  --llm-model "$llm_model" \
  --task-template "$task_tpl" \
  --max-steps "$APE_MAX_STEPS" \
  --cdp-port "$CDP_PORT"
```

外部 Chrome 刚启动或刚恢复时，CDP 端口可能暂时可访问但尚未接受会话。驱动默认最多尝试 3 次、间隔 1 秒；可按部署环境调整 `--cdp-start-retries` 和 `--cdp-start-delay`。每次失败连接都会主动清理，成功后仍通过 `keep_alive` 保留 Chrome。

## 自定义探索提示词

browser-use 的 `Agent(task=...)` 接收自然语言任务。原有 `--task-template` 就是基础任务提示词，继续兼容。
两个可选参数（二选一）用于指定用户任务。使用默认模板时，自定义任务替代默认全站探索；显式传入基础模板时，用户任务的范围和结束条件优先：

- `--explore-prompt "你的探索要求"`：直接传入提示词。
- `--explore-prompt-file /path/explore.txt`：读取 UTF-8 文本文件，支持多行及 BOM；文件必须位于容器内可读路径，宿主文件需先挂载或复制到容器。

在原命令中加一行即可（注意上一行末尾保留反斜杠）：

```sh
  --explore-prompt "登录后重点探索工作台、审批和通讯录。逐一浏览列表和详情，记录功能入口、页面用途及异常。不要新增、修改或删除数据，最后用中文汇总。" \
```

也可以不传 `--task-template`，使用默认浏览探索任务，再通过 `--explore-prompt` 指定重点。
两种提示词均支持 `{url}` 替换。所有任务附加完成规则：逐项核对要求，满足后立即调用 `done`；无法完成时报告阻碍。`--max-steps` 是安全上限，不是必须执行的步数。自然语言完成判断仍由模型执行，不能保证任何提示词都能在上限内完成。`done` 不再被登录检测或页面加载状态拦截，结束后的回调不再等待登录。显式传入空白提示词或不可读文件会在启动前报错。
最终合并的任务保存在成功执行路径的 `ape-result.json` 的 `task` 字段（探索返回失败结果时也包含该字段；异常路径除外）。
提示词不会关闭代码层面的登录等待，也不需要额外弹窗。

## 登录等待行为

- 删除自定义页面浮层，不注入 DOM，不需要点击“继续执行”。原浮层不是 browser-use 自带组件。
- 每一步开始、动作执行前、步骤结束均检查登录状态。一次最多执行一个动作，防止“进入登录页、点击注册”被排在同一批操作中。
- 检测登录/注册 URL、可见密码框、登录表单、扫码登录提示后暂停。模型识别到其他登录场景时也可调用 handoff_browser 暂停。
- 用户通过浏览器/noVNC 自行登录。等待发生在步骤超时之外，不调用模型、不消耗探索步数，默认无限等待。
- 登录失败、切换注册页、返回公共首页、页面暂时空白都不会解除已触发的等待。
- 成功标志连续稳定至少 3 秒后自动继续，并重新读取页面。
- 通用规则保存登录页基线，结合登录前后的变化：登录阻碍消失、登录按钮消失、新出现头像/用户名，以及离开登录页或新出现会话存储标记。该组合连续稳定后恢复，支持 URL 不变但会话标记发生变化的 SPA。单独跳转、密码框消失或存在 Cookie 都不足以认定成功。
- Cookie、localStorage、sessionStorage 只检查命名包含 token/session/auth 等标记的存在性，不返回值、不记录凭据；HttpOnly Cookie 不可见，已有标记的值变化不会作为新增标记。头像选择器属于启发式识别，特殊站点仍可指定 `--login-success-selector`。
- 不自动猜测 `/me`、`/profile`、`/account` 等接口，也不额外跳转探测受保护页面；这些路径和成功返回结构需按站点确认，HTTP 200 本身不代表登录成功。
- iQuicker 默认成功标志：处于 iquicker.com.cn 或其子域的 /home 页面，页面完成加载、有实际正文且无登录特征。该规则依据公开登录控制器的成功跳转；不是服务端会话验证。
- 聚好开（jhk.juhaokai.cn）默认成功标志：登录后布局中的用户头像入口和主内容区同时可见，页面完成加载且无登录特征。退出登录菜单默认隐藏，不再要求先展开菜单；仍需连续稳定 3 秒才继续。替换容器驱动目录中的 `login_state.js` 后重启探索进程即可生效，启动参数无需改变。
- 其他网站默认通过可见的“退出登录 / Logout / Sign out”等控件判断。若无此标志，使用 `--login-success-selector '#仅登录后才显示的元素'`。配置后以此选择器为成功标志，不再使用默认成功标志；请勿选择 body 等公共元素。
- 跨域 iframe：先检查可见框架的认证 URL/标题，再通过 CDP 检查同进程或独立进程框架内的登录字段。163 邮箱真实登录框已验证。特殊 SSO、站点改版仍可能需要补充规则，识别不到成功时保持等待。
- DOM 到达 `interactive` 且有正文即可读取，避免第三方资源拖延 `complete` 导致长期无法操作。空白页允许首个导航动作，其他操作仍等待页面就绪。用户名输入框不再作为已登录身份标志。
- 可选 `--login-wait-timeout 600` 设置等待秒数；默认 0 表示不限时。超时或持续无法读取页面时停止，不自动跳过登录。
- 其他缺少用户信息的普通表单结束任务并说明，不再提供通用弹窗交互。

## 状态和结果

`<capture-dir>/ape-status.json` 提供 `waiting_for_login`、`running`、`completed`、`stopped` 状态，日志也输出暂停/恢复信息；可供宿主界面显示。该状态文件不包含凭据或页面正文。

保留原有 `ape-result.json`、`ape-history.json`、`ape-agent-files/` 产物。
成功退出码 0，失败为 1；Ctrl+C 为 130。退出前显式清理 CDP 和事件会话，不关闭由容器看门狗管理的 Chrome。

## 回归验证

```sh
python -m unittest discover -s tests -v
# 可选：使用 Node.js 验证聚好开登录检测规则（无需账号或网络）
node tests/test_login_state.cjs
# 可选：启动独立的无头 Chrome，验证真实 DOM 和 iQuicker 登录页，不调用模型
python tests/browser_smoke.py
# 本地独立 Chrome + CDP 生命周期验证，不调用模型
python tests/lifecycle_smoke.py
# 真实未登录站点只读检测，不调用模型
python tests/live_sites.py qq_mail 163_mail feishu github books feishu_public
```

覆盖登录等待、注册点击拦截、登录失败/公共页/空白页不恢复、稳定成功后恢复、模型兜底、导航重试、浏览器关闭、等待超时以及单动作执行。
实际账号登录及容器 noVNC 联调需要在部署环境验证。

2026-09-23 真实网站测试范围和限制见 `TEST_REPORT.md`。`tests/explore_live.py` 是可选本地联调工具，会使用仓库根目录 `.env` 中配置的模型服务；必须先告知测试任务并获得测试账号页面传给模型的授权。容器正式入口仍只读取命令行参数。
