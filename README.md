# browser-use 有头浏览器演示

部署与验证日期：2026-09-14。本机 macOS / Apple Silicon，Python 3.12.12，browser-use 0.13.10，调用本机 Google Chrome。

## 安装与启动

需要安装 uv、Python 3.12 和 Google Chrome。首次克隆后在终端运行：

```bash
git clone https://github.com/Rebekahjiani/browser-use-demo.git
cd browser-use-demo
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
```

编辑 `.env`，选择现有 ArtifactTrace 配置文件，或填写自己的 OpenAI 兼容服务配置。配置完成后启动：

```bash
./start.sh
```

已安装好的本机副本可直接运行 `./start.sh`，无需重复复制 `.env`。

无需激活虚拟环境。脚本自动使用本目录 `.venv` 中的 Python。

你会看到一个独立演示用 Chrome 窗口，agent 在窗口中打开 Books to Scrape，点击 Travel 分类，比较书价，打开最低价书籍并返回中文结果。终端显示每步动作。任务结束后窗口保留，回到终端按 Enter 关闭；Ctrl+C 可中断。请串行运行演示，避免多个进程争用同一演示 profile。

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

## 中途询问与浏览器人工接管

已接入两个工具，由模型在需要时调用：

| 工具 | 适用场景 | 操作方式 |
|---|---|---|
| `ask_human` | 缺少城市、日期、分类等非敏感信息 | 在终端回答并按 Enter，agent 收到答案继续 |
| `handoff_browser` | 登录、验证码或需要亲自完成的页面操作 | 直接操作已打开的 Chrome，完成后回终端按 Enter |

等待期间不会执行后续浏览器动作，也不会继续调用模型。两种交互都可在终端输入 `/cancel` 取消当前任务并关闭演示浏览器；空的问题答复会要求重输。终端输入关闭或没有交互式终端时，会结束任务并记录取消原因。

有输入框不代表必须询问：已知信息仍可由 agent 填写，缺失的信息才请求用户补充。触发时机依赖模型的判断与任务指令，不是对所有登录页的确定性检测。密码、验证码应在浏览器中填写，不要在问答终端输入；普通问答会进入模型上下文和本地历史记录。

同时演示两种交互：

```bash
./start.sh --task '打开 https://books.toscrape.com/ 。先询问我想查看哪个图书分类，收到回答后进入该分类。然后把浏览器交给我，让我手动切换到另一个分类，等我确认后再读取当前页面，报告新分类的名称和图书数量。'
```

演示步骤：终端出现问题时输入 `Travel`；浏览器交给你后，在左侧手动点击 `Mystery`；回到终端按 Enter。agent 应从最新页面读取分类与数量，不能继续沿用 Travel 页面。

实现使用 browser-use 0.13.10 的 `on_step_end`：工具先登记请求并终止当前动作序列，步骤结束后在计时之外等待输入。用户回答写入下一步上下文及历史；人工接管完成后的下一步重新读取浏览器状态。原有 150 秒步骤超时和 90 秒模型调用超时保留，人为等待不占用这些时间。交互请求本身仍占一个 agent 步骤，所以演示需要足够的 `--max-steps`。

`--no-wait` 仅省略任务结束后的窗口保留，不会跳过任务中途的人机交互。Docker 中使用 `docker exec -it` 等交互式终端，并通过 noVNC 操作容器浏览器。当前没有 Web 聊天输入界面。

回归验证：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

测试覆盖超出步骤时限的人工等待、答案进入历史、人工确认、空答复重试、取消及输入关闭。

2026-09-16 本机有头验证：终端实际输入 `Travel` 后任务恢复；另一次真实模型与浏览器联调用脚本模拟人工在接管期间切换到 `Mystery`，恢复后正确读出该分类共 32 本书。后一项验证了页面变化后的恢复，不代表已测试真实网站的登录或验证码流程。

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
4. 显示服务就绪后运行同一个 demo.py。若要保留终端 Enter 交互，使用交互式终端；服务化触发任务可用 `--no-wait`。
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
