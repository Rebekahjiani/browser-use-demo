# browser-use 自动操作浏览器演示

部署与验证日期：2026-09-14。本机 macOS / Apple Silicon，Python 3.12.12，browser-use 0.13.10，调用本机 Google Chrome。

## 安装与启动

### 1. 准备环境

需要 Python 3.12 + Google Chrome。Windows 下推荐直接使用 venv，不依赖 uv。

```powershell
git clone https://github.com/Rebekahjiani/browser-use-demo.git
cd browser-use-demo
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. 配置环境变量

优先推荐使用 `.env` 中的 OpenAI 兼容配置，便于与其他项目集成：

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-gateway/v1
MODEL=your-model-id
BROWSER_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe
ANONYMIZED_TELEMETRY=false
BROWSER_USE_CLOUD_SYNC=false
```

如果你已经有 ArtifactTrace 的配置文件，也可以改为：

```dotenv
AT_SETTINGS_PATH=C:/path/to/settings.json
```

`AT_SETTINGS_PATH` 会优先覆盖直接的 `OPENAI_API_KEY` / `MODEL`，所以如果你要直接在其他项目中复用这个 demo，建议把真实 API Key 写进 `.env`，并保持 `AT_SETTINGS_PATH` 为空或注释掉。

### 3. 启动演示

Windows PowerShell：

```powershell
cd C:\Users\bulin\browser-use-demo
.\.venv\Scripts\python.exe demo.py
```

或直接跑 smoke 测试，验证浏览器可用：

```powershell
cd C:\Users\bulin\browser-use-demo
.\.venv\Scripts\python.exe demo.py --smoke --no-wait
```

自定义任务：

```powershell
.\.venv\Scripts\python.exe demo.py --task "打开 https://books.toscrape.com/，先进入 Travel 分类，再比较书价并给出最便宜书名。" --max-steps 15
```

你会看到一个独立演示用 Chrome 窗口，agent 在窗口中打开 Books to Scrape，点击 Travel 分类，比较书价，打开最低价书籍并返回中文结果。终端显示每步动作。任务结束后窗口保留，点击页面右下角的“关闭演示”结束；Ctrl+C 也可中断。请串行运行演示，避免多个进程争用同一演示 profile。

### 4. 作为其他项目的集成配置

这个 demo 最适合以“单独的 Python 运行环境 + `.env` 配置文件”的方式复用。其他项目可以直接复制 `.env` 模板，写好自己的 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `MODEL`，再通过子进程调用：

```python
import subprocess

subprocess.run([
    "C:/Users/bulin/browser-use-demo/.venv/Scripts/python.exe",
    "C:/Users/bulin/browser-use-demo/demo.py",
    "--task",
    "打开 https://books.toscrape.com/ 并给出最便宜图书信息",
], check=True)
```

这样不会把真实凭据硬编码进业务代码，后续只需要更新 `.env` 即可。

这是由模型实际决定操作的 agent 演示，脚本没有写死分类链接、商品链接和答案。默认任务只是自然语言目标；更换模型或网络状态可能改变步骤数和耗时。

## 实测结果

完整模型演示已成功，4 个 agent 步骤，记录中无步骤错误：

- 最便宜书籍：The Road to Little Dribbling: Adventures of an American in Britain (Notes From a Small Island #2)
- 价格：£23.21
- 库存：3 本
上述结果来自 2026-09-14 的本机验证。运行记录保留在部署机器的 `runs/`，不随仓库发布；新运行会生成自己的记录。

已独立查看分类页价格及详情页库存，与输出一致。`success` 字段本身是 agent 完成信号，不是通用的独立任务评测器。

另已完成无模型浏览器自检，并实测任务结束保留窗口及 Enter 关闭流程。首次自检曾因读取到加载中的标题误判；现在自检等待真实页面标题后判定。依赖检查 `uv pip check` 通过。

## 模型配置与有头模式

原部署通过 `.env` 引用已有配置文件，无需复制 API Key。克隆后请填写自己的路径：

```dotenv
AT_SETTINGS_PATH=/path/to/settings.json
ANONYMIZED_TELEMETRY=false
BROWSER_USE_CLOUD_SYNC=false
```

脚本读取 settings.json 的 `defaultModel`，从 `modelProviders` 找到 API Key 和 baseUrl。本次实际使用 `sophnet/DeepSeek-V4-Flash-0731`，经该文件中的 OpenAI 兼容网关调用。

本地部署的是 agent 和 Chrome，模型推理仍调用远程网关，不是离线本地模型。每次完整演示会调用该 API。

当前配置 `headless=False`，所以可以看见浏览器；`use_vision=False` 表示模型读取 DOM 文本，不接收截图。这两项控制不同东西。浏览器仍保存最终截图供人查看。不要把“有头浏览器”与“视觉模型”混为一谈。

如迁移后不使用 ArtifactTrace 配置，可以参考 `.env.example`，改用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL`。先移除 `AT_SETTINGS_PATH` 才会使用这组凭证。`MODEL` 也可以覆盖 settings.json 中的默认模型，但网关需实际提供该模型。

## 换任务与检查环境

自定义任务：

```bash
./start.sh --task '打开 https://books.toscrape.com/，进入 Mystery 分类，打开第一本书并告诉我完整书名和库存。' --max-steps 15
```

只检查有头浏览器，不调用模型：

```bash
./start.sh --smoke
```

执行完自动关闭窗口：

```bash
./start.sh --no-wait
```

查看可用参数：

```bash
./start.sh --help
```

每次运行新建 `runs/<时间>/`，包含 `result.json`、`final.png`；完整 agent 运行另有 `history.json` 和 agent 文件。API 密钥不会传入任务 prompt。

## 页面内人工接管

交互全程在有头浏览器内完成：**agent 暂停并保留页面 → 用户直接操作网页 → 点击“继续执行” → agent 重新读取页面并继续。** 不再提供终端问答，也不需要回终端按 Enter。

暂停时，页面右下角显示“已暂停 · 请你操作”和操作说明。你可以填写表单、选择分类、完成登录等，再点击“继续执行”；点击“结束任务”可取消。浮层可以收起，避免挡住网页。同一标签页跳转或刷新后，浮层会重新出现。请在当前演示标签页完成操作；跨标签页登录弹窗和浏览器内部页面尚未验收。

演示命令：

```bash
./start.sh --task '打开 https://books.toscrape.com/ ，先进入 Travel 分类。然后调用 handoff_browser 暂停，让我在网页左侧自行选择另一个分类。等我在页面点击继续执行后，重新读取当前页面，报告新分类名称和图书总数。'
```

1. 等 agent 进入 Travel 并显示暂停提示。
2. 在网页左侧点击 `Mystery`。页面跳转后，暂停提示会重新出现，agent 仍等待。
3. 点击浮层的“继续执行”。agent 应读取 Mystery 页面并报告共 32 本书。
4. 任务结束后点击“关闭演示”；也可启动时加 `--no-wait`，在完成后自动关闭。

缺少信息时，agent 使用 `handoff_browser` 请用户在目标网页直接填写或选择；用户无需在终端回答。触发时机仍依赖模型判断与任务指令，不是对所有登录页的确定性检测。这里没有独立的聊天输入框。

等待由 `on_step_end` 承担，位于 browser-use 0.13.10 的步骤超时之外；期间不调用模型、不继续执行 agent 动作，只轮询页面确认并维护浮层。点击继续后移除浮层，将确认写入上下文与历史，再由下一步重新读取页面、核实操作结果。原有 150 秒步骤超时和 90 秒模型调用超时保留，人工等待不占用这些时间。

Docker 中可通过 noVNC 操作有头浏览器及页面确认按钮，不再依赖交互式终端。Ubuntu Docker 镜像本身尚未部署验收。

回归验证：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

测试覆盖人工等待超过步骤时限、确认前不恢复、确认写入历史、取消、页面导航重试和浏览器关闭。

2026-09-16 本机有头浏览器验证通过：页面浮层、导航后恢复、确认前保持暂停、继续、取消和结束关闭。真实模型联调中，脚本模拟用户从 Travel 切换到 Mystery 并点击页面确认按钮，agent 恢复后正确报告 Mystery 共 32 本书；无终端输入。真实登录和验证码流程尚未实测。

## 本机、Docker 与 Ubuntu 的区别

| 方式 | 程序运行位置 | 浏览器画面显示在哪里 | 启动准备 |
|---|---|---|---|
| 当前本机直接运行 | macOS Python + Chrome | 本机桌面窗口 | 虚拟环境、依赖、Chrome、模型配置 |
| 本机 Docker | Docker Desktop 的 Linux 环境 | 容器虚拟桌面，或另连宿主浏览器 | 镜像、容器、显示服务、端口/目录挂载 |
| Ubuntu Docker | Ubuntu 主机上的 Linux 容器 | 通常通过 noVNC 网页观看虚拟桌面 | 同类 Linux 镜像与显示服务 |

**Python 任务循环可以复用；环境启动步骤不完全相同。** 当前 `./start.sh` 直接弹窗，容器必须先有可用 DISPLAY。设置 `headless=False` 不会自动创造桌面。

推荐用于远程演示的布局：

```text
你的电脑浏览器
    -> noVNC 网页（显示远程桌面）
    -> VNC 服务
    -> Xvfb 虚拟显示器中的 Chrome（headless=False）
    <- 同一容器内 browser-use 通过 CDP 控制 Chrome
    -> 模型网关
```

Xvfb 提供虚拟屏幕；VNC 将屏幕输出；noVNC 让观众用普通网页观看。只用 xvfb-run 能使有头 Chrome 启动，但不会单独提供远程观看界面。[noVNC 官方仓库](https://github.com/novnc/noVNC)

迁移时需要：

1. 在 Linux 镜像里重新安装 Python 3.12 与 `requirements.txt`，安装 Chrome/Chromium 和其 Linux 系统依赖。不要复制 macOS `.venv`。
2. 安装并启动 Xvfb、窗口管理器、VNC/noVNC，设置 DISPLAY（如 `:99`）；设置 `BROWSER_EXECUTABLE_PATH` 指向镜像里实际存在的浏览器。
3. 把模型配置挂载进容器，修改 `AT_SETTINGS_PATH` 为容器内路径；或者改用三个独立模型环境变量。结果目录需挂载才会跨容器保留。
4. 显示服务就绪后运行同一个 demo.py。人工接管在页面浮层确认；服务化运行若需任务完成后自动关闭，可用 `--no-wait`。
5. 在 Ubuntu 上检查架构。当前 Mac 是 arm64，Ubuntu 可能是 amd64；应在目标架构构建镜像或构建多架构镜像。

容器里的 `localhost` 指容器本身。若目标网站或 Chrome 在另一容器，应使用 Docker 网络中的服务名；Docker Desktop 访问宿主服务通常用 `host.docker.internal`。Ubuntu Docker Engine 应按实际网络配置处理，不能照搬 macOS 假设。[Docker 网络文档](https://docs.docker.com/desktop/features/networking/)

当前脚本自己启动 Chrome，所以不需要预先启动 9222 服务。只有选择连接一个已运行的远程 Chrome 时才使用 `cdp_url`；这条连接必须能从 agent 所在容器访问。

本次仅实际部署并验证本机有头版，尚未构建或验收 Ubuntu Docker 镜像。上面是迁移设计说明，不是已经跑通的 Docker 启动命令。

## 重建本机环境

当前已经安装好，无需重复执行。换机器时可参考：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

macOS 默认使用 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`；其它路径用 `BROWSER_EXECUTABLE_PATH` 指定。脚本使用专门的 `.browser-profile/`，不读取你的日常 Chrome profile。

[Browser Use 官方快速开始](https://docs.browser-use.com/open-source/quickstart)

## 调研报告

- [用户提供的原始调研报告](docs/research/web-agent-survey.md)
- [原报告的补充与修正](docs/research/web-agent-survey-补充修正.md)
- [Web 自动探索开源代码调研](docs/research/web自动探索开源代码调研.md)
- [调研报告 PDF](docs/research/web自动探索开源代码调研.pdf)

原始报告按原文保留；涉及实现边界、停止条件和部署方式时，请同时阅读补充修正。报告是标注日期的调研快照，不代表持续更新的排行榜。

## 本地文件

`.env`、`.venv/`、`.browser-profile/`、`runs/` 和缓存均由 `.gitignore` 排除。仓库只提供配置模板，不包含 API Key、日常浏览器登录信息或运行历史。
