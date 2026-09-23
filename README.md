# browser-use 自动操作浏览器演示

这是一个基于 `browser-use` 的可视化浏览器自动化 Demo。它会在本机启动独立的 Chrome Profile，执行一个自然语言任务，并在浏览器中完成页面交互。当前仓库默认以 Windows / PowerShell 为主，并支持在 `.env` 中配置 OpenAI 兼容网关或 ArtifactTrace 的 `settings.json` 路径。

## 目录结构

- `demo.py`：主入口脚本，负责创建 LLM、浏览器、Agent 和结果输出。
- `human_interaction.py`：页面内人工接管逻辑，支持暂停、继续、取消和恢复。
- `handoff_panel.js`：页面浮层脚本，用于在浏览器中显示人工接管提示。
- `start.sh`：Unix/macOS 启动入口。
- `tests/`：回归测试。
- `runs/`：每次运行生成的结果目录，包含 `result.json`、截图和 agent 历史。
- `.env.example`：示例配置模板。

## 先决条件

- Python 3.12+
- Google Chrome（Windows 推荐直接安装到本机）
- 可用的 OpenAI 兼容 API 网关，或者 ArtifactTrace 的 `settings.json`

## 1. 安装依赖

在仓库根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

如果你是在 macOS/Linux 环境，`start.sh` 也可以直接用；默认会调用 `.venv/bin/python`。

## 2. 配置环境变量

推荐直接使用 `.env` 中的 OpenAI 兼容配置：

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-gateway/v1
MODEL=your-model-id
BROWSER_EXECUTABLE_PATH=C:/Program Files/Google/Chrome/Application/chrome.exe
ANONYMIZED_TELEMETRY=false
BROWSER_USE_CLOUD_SYNC=false
```

如果你已经有 ArtifactTrace 的配置文件，也可以改成：

```dotenv
AT_SETTINGS_PATH=C:/path/to/settings.json
```

说明：
- `AT_SETTINGS_PATH` 会优先覆盖直接的 `OPENAI_API_KEY` / `MODEL`。
- 如果要复用这个 demo，建议把真实 API Key 放在 `.env` 中，并让 `AT_SETTINGS_PATH` 保持为空或注释掉。
- 脚本会优先读取 `.env` 中的环境变量，再回退到 `AT_SETTINGS_PATH`。

## 3. 启动演示

启动默认任务：

```powershell
cd C:\Users\bulin\browser-use-demo
.\.venv\Scripts\python.exe demo.py
```

只检查浏览器可用性，不调用模型：

```powershell
.\.venv\Scripts\python.exe demo.py --smoke --no-wait
```

自定义任务：

```powershell
.\.venv\Scripts\python.exe demo.py --task "打开 https://books.toscrape.com/，先进入 Travel 分类，再比较书价并给出最便宜书名。" --max-steps 15
```

默认任务会打开 Books to Scrape，进入 Travel 分类，比较价格，并返回最便宜书的中文结果。浏览器窗口会保留到任务结束；如果需要自动关闭，可使用 `--no-wait`。如果中途需要手动中断，可按 `Ctrl+C`。

## 4. 页面内人工接管

脚本支持页面内人工接管：agent 会在浏览器中暂停，并弹出浮层提示用户继续操作。用户可以直接在页面中填写表单、点击分类、完成登录，再点击“继续执行”，然后 agent 会重新读取页面并恢复执行。

示例：

```powershell
.\.venv\Scripts\python.exe demo.py --task "打开 https://books.toscrape.com/，先进入 Travel 分类。然后调用 handoff_browser 暂停，让我在页面左侧自己切换到 Mystery 分类，点击继续后报告新分类名称和图书总数。" --max-steps 15
```

交互时序：
1. agent 进入目标页面并显示暂停提示。
2. 用户在网页中执行动作。
3. 点击“继续执行”恢复 agent。
4. agent 重新读取当前页面并继续任务。

这部分逻辑是由 `human_interaction.py` 和 `handoff_panel.js` 共同维护的，不需要回到终端输入文本。

## 5. 输出文件

每次运行都会在 `runs/<timestamp>/` 下生成结果目录，其中包括：

- `result.json`：任务执行 summary
- `final.png`：带截图的最终页面
- `history.json`：agent 历史记录（完整任务时）
- `agent-files/`：agent 生成的文件和状态

## 6. 回归测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖：
- 人工等待超过步骤超时
- 继续前不恢复
- 确认后写入历史
- 取消任务
- 页面导航重试
- 浏览器关闭场景

## 7. 打包与分发

如果需要把项目发给别人，可以直接打包当前仓库，但建议排除本地运行目录与敏感配置：

```powershell
$src = "C:\Users\bulin\browser-use-demo"
$dst = "C:\Users\bulin\browser-use-demo\browser-use-demo-release.zip"
Compress-Archive -Path "$src\demo.py", "$src\human_interaction.py", "$src\handoff_panel.js", "$src\start.sh", "$src\requirements.txt", "$src\README.md", "$src\.env.example", "$src\tests", "$src\docs" -DestinationPath $dst -Force
```

该压缩包适合交付源码和运行说明；`.env`、`.venv`、`.browser-profile`、`runs/` 不建议一并打包。

## 8. 重要说明

- 本脚本默认使用独立的浏览器 Profile，不会读取你日常 Chrome 登录状态。
- 任务结果和截图都保留在 `runs/` 下，便于复盘。
- API Key 不会写死在代码里，推荐统一保存在 `.env`。
- 默认任务是自然语言驱动，所以不同模型和网络状态可能导致操作步骤数略有变化。

## 参考链接

- [Browser Use 官方快速开始](https://docs.browser-use.com/open-source/quickstart)
- [Books to Scrape](https://books.toscrape.com/)
