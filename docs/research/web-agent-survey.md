# Web自动探索开源项目调研报告

> 调研时间：2026-09-11 | 覆盖范围：2023–2025 年主要项目

---

## 目录

1. [整体技术格局](#整体技术格局)
2. [核心项目详解](#核心项目详解)
   - [browser-use](#browser-use)
   - [Playwright MCP](#playwright-mcp)
   - [Skyvern](#skyvern)
   - [OpenHands](#openhands)
   - [LaVague](#lavague)
   - [AWorld](#aworld)
3. [研究性项目](#研究性项目)
   - [WebVoyager](#webvoyager)
   - [SeeAct](#seeact)
   - [LASER](#laser)
   - [Agent-E](#agent-e)
4. [收敛机制横向对比](#收敛机制横向对比)
5. [基准测试对比](#基准测试对比)
6. [项目综合对比表](#项目综合对比表)
7. [关键技术趋势](#关键技术趋势)
8. [技术选型建议](#技术选型建议)

---

## 整体技术格局

Web 自动探索（Web Agent）在2024–2025 年迎来快速演进。核心挑战从"能否让 LLM 操作浏览器"转变为三个具体子问题：

1. **观测表示**：用什么描述当前页面状态给 LLM？（截图、DOM、可访问性树、混合）
2. **元素定位（Grounding）**：LLM 的意图（"点击购买按钮"）如何映射到实际 DOM 元素？
3. **动作效率**：如何减少 LLM 调用次数同时保证成功率？

这三个问题的不同解答产生了当前的技术分叉。

---

## 核心项目详解

### browser-use

**仓库：** https://github.com/browser-use/browser-use  
**Stars：** ~50,000+ | **License：** MIT | **语言：** Python

#### 架构

```
browser_use/
├── agent/— Agent 类、消息管理、结构化输出
├── browser/    — BrowserSession（直接 CDP 层）
├── dom/        — DOM 提取、AX 树合并、序列化
├── tools/      — 20+ 内置动作注册表
├── llm/        — 20+ 模型 provider适配器
└── mcp/        — MCP server 集成
```

#### 核心技术决策

**1. 直接 CDP，不用Playwright Python API**

绕过 Playwright 高层封装，直接使用 Chrome DevTools Protocol：
- `DOMSnapshot.captureSnapshot` — 单次 CDP 获取布局 + 计算样式
- `Accessibility.getFullAXTree` — 每frame 独立，支持跨域iframe（深度 ≤5）
- `getEventListeners` — 检测纯 JS绑定的可点击元素

**2. 混合 DOM：Snapshot + 可访问性树合并**

`EnhancedDOMTreeNode` 同时携带：
- 布局边界（来自 DOMSnapshot，像素坐标）
- ARIA 语义（来自 AX Tree，角色/名称/状态）

**3. Pydantic 结构化输出——零字符串解析**

```python
class AgentOutput(BaseModel):
    thinking: str | None
    evaluation_previous_goal: str | None
    memory: str | None
    plan_update: list[str] | None
    action: list[ActionModel]# 动态构建的discriminated union
```

LLM 收到 JSON Schema 直接输出合法对象，无 XML 标签、无正则匹配。

**4. Paint-order 过滤**

用 DOMSnapshot 的 z-index 信息过滤掉被遮挡元素，再传给 LLM。竞品中罕见。

**5. 每步多动作 + 双层中止**

- 最多 5 个动作/LLM 调用（减少 round-trip）
- 静态中止：`terminates_sequence=True`（navigate/search/go_back后停止）
- 动态中止：检测 URL/焦点变化，实时终止剩余队列

#### Agent 循环（每步 3阶段）

```
PERCEIVE  → get_browser_state_summary() → BrowserStateSummary
              (DOM + AX tree + 截图 + tab列表)
    ↓
DECIDE    → llm.ainvoke(messages, output_format=AgentOutput)
              (结构化输出，无字符串解析)
    ↓
ACT       → multi_act(actions)
              (最多 5 个动作/步，双层中止保护)
```

#### 提示词结构（每步）

```
SystemMessage [cached]          ← 系统提示模板
UserMessage [cached]
  <user_request>任务描述 </user_request>
  <agent_history> 历史步骤摘要 </agent_history>
  <agent_state> 文件系统/TODO/计划 </agent_state>
  <browser_state>
    Tab 列表 + 当前 URL
    可交互元素（序列化 DOM，上限 ~40k chars）
  </browser_state>
  <page_specific_actions>   ← 域名过滤后的可用动作
  [截图 Base64 PNG，如启用视觉]
```

#### 模型感知配置

| 配置项 | 适用模型 |
|---|---|
| 坐标点击启用 | claude-sonnet-4, claude-opus-4, claude-fable-5, gemini-3-pro |
| 视觉禁用 | DeepSeek, Grok-3, grok-code |
| 截图缩放至 (1400,850) | Claude Sonnet |
| Flash mode（简化schema） | browser-use/*微调模型 |

#### 收敛机制

四层，最完善：

| 层次 | 机制 |
|---|---|
| 主动终止 | LLM 调用 `done(success, text)` 动作 → 立即退出（唯一合法终止动作，不能与其他动作并列） |
| 步数上限 | `max_steps=500`（默认），超出强制停止 |
| 失败上限 | `consecutive_failures >= max_failures` → 停止 |
| 循环检测 | `ActionLoopDetector`：对最近 20 步动作做 SHA-256 滚动哈希，5/8/12 次重复时注入升级提示（nudge），不硬停但干预 LLM |

---

### Playwright MCP

**仓库：** https://github.com/microsoft/playwright-mcp  
**Stars：** ~37,000 | **License：** Apache-2.0 | **语言：** TypeScript  
**创建时间：** 2025 年 3 月

#### 架构定位：纯 MCP 服务，无内置 LLM

```
MCP Client (LLM)──工具调用── Playwright MCP Server (Node.js)
                                        ↓
                              Playwright API → Browser
                                        ↓
                可访问性树 /截图 / 结果
```

#### 两种观测模式

**模式 1：Snapshot 模式（默认，推荐）**

`browser_snapshot` 工具返回可访问性树的结构化文本：
- 所有交互元素（角色、名称、值、状态）
- 每个元素有稳定的 `ref` 标识符（如 `ref="e42"`）
- 工具描述明确写道：**"this is better than screenshot"**

**模式 2：Screenshot 模式（可选，只读）**

工具描述明确写道：**"You can't perform actions based on the screenshot"**  
截图仅用于人工检查或补充 VLM 上下文，不可用于坐标定位。

#### 能力分层（Capability Tiers）

| 标志 | 解锁内容 |
|---|---|
| 默认 | 导航、点击、输入、拖拽、文件上传、JS 执行、截图、AX 快照 |
| `--caps=vision` | 坐标鼠标操作（click_xy, drag_xy, wheel） |
| `--caps=pdf` | PDF 保存 |
| `--caps=testing` | 生成稳定的 Playwright locator |
| `--caps=network` | 请求 mock、离线模拟 |
| `--caps=devtools` | CDP 工具 |

#### 独特设计

- **代码生成 sidecar**：`--codegen=typescript|python` 将每次LLM 驱动操作同时记录为Playwright 测试代码
- **Secrets脱敏**：`secrets` 配置项替换返回给 LLM 的敏感值
- **工作区隔离**：不同项目自动使用不同 Browser profile（基于路径哈希）
- **`browser_run_code_unsafe`诚实标注**：工具描述直接写"RCE-equivalent"

#### 收敛机制

自身无收敛机制。Playwright MCP 是纯 MCP 服务器，无 agent 循环。何时停止完全由接入它的 MCP 客户端（LLM/上层agent）决定。

---

### Skyvern

**仓库：** https://github.com/Skyvern-AI/skyvern  
**Stars：** ~11,000 | **License：** AGPL-3.0 | **语言：** Python + TypeScript  
**Stack：** FastAPI + Playwright + PostgreSQL

#### 核心循环：感知 → 标注 → 推理 → 执行

```
1. PERCEIVE   → Playwright 截图 + DOM 解析（提取可交互元素 + 边界框）
2. ANNOTATE   → 编号边界框叠加在截图上（Set-of-Marks风格）
3. REASON     → 标注截图 + 元素列表 + 任务描述 → VLM → 结构化动作
4. ACT        → Playwright 执行动作
```

#### 动作空间

| 动作 | 说明 |
|---|---|
| `CLICK` | 点击标注编号元素 |
| `INPUT_TEXT` | 输入文本 |
| `SELECT_OPTION` | 下拉选择 |
| `UPLOAD_FILE` | 文件上传 |
| `DOWNLOAD_FILE` | 文件下载 |
| `SCROLL` | 滚动 |
| `WAIT` | 显式等待 |
| `COMPLETE` | 任务完成，携带结构化提取数据 |
| `TERMINATE` | 任务不可完成，终止 |
| `NULL` | 无操作，重新评估 |

`COMPLETE` 动作携带结构化 payload，使Skyvern 同时具备自动化执行与数据提取能力。

#### 核心差异化

- DOM 语义+ 视觉截图**双通道**（语义补偿视觉失效，视觉补偿 DOM 变化）
- 面向**生产环境**：REST API、Cloud托管、人工接管钩子（CAPTCHA / 支付确认）
- 安全凭证注入（不在 prompt 中暴露密码）
- 支持多步骤工作流 DSL

#### 收敛机制

两个专用终止动作：

- `COMPLETE`：任务成功，携带结构化提取数据 payload → 循环结束
- `TERMINATE`：任务不可完成，主动放弃 → 循环结束

LLM 每步从动作空间中选一个，选 `COMPLETE` 或 `TERMINATE` 时退出。无公开的步数上限或循环检测机制。

---

### OpenHands

**仓库：** https://github.com/All-Hands-AI/OpenHands  
**Stars：** 87,290 | **License：** MIT  
**原名：** OpenDevin

#### 定位：通用 AI 软件工程师平台

OpenHands 是一个通用的 AI 代码/任务执行平台，Web浏览是其能力之一（BrowsingAgent）。

#### BrowsingAgent 实现

**动作空间配置：**
```python
action_space = HighLevelActionSet(
    subsets=['chat', 'bid', 'nav'],
    strict=False,      # 宽松的 LLM 输出解析
    multiaction=True   # 每步可链接多个动作
)
```

**单步循环：**
1. 获取最新 `BrowserOutputObservation`（含 AX 树 + 截图 + DOM）
2. `flatten_axtree_to_str(axtree_object, filter_visible_only=True)` → 文本化可访问性树
3. 构建提示词（当前 URL + AX 树文本 + 历史动作列表）
4. LLM 输出 Python 函数调用代码块
5. 解析并执行 `BrowseInteractiveAction(browser_actions=code_string)`

**观测结构`BrowserOutputObservation`：**
```python
url: str
screenshot: str# Base64 PNG
set_of_marks: str            # SOM叠加图（Base64）
dom_object: dict             # 完整 DOM（CDP DOMSnapshot）
axtree_object: dict          # 可访问性树（CDP Accessibility）
focused_element_bid: str
last_browser_action: str
last_browser_action_error: str
```

**LLM 集成：** 通过 LiteLLM 支持所有主流 provider

#### 收敛机制

两条出口：

- LLM 调用 `send_msg_to_user(text)` → 转换为 `MessageAction` → 任务结束（主动终止）
- 连续 **5 次**动作执行失败 → 自动失败退出

无步数上限，无循环检测，依赖 LLM 主动调用通信动作来收敛。

---

### LaVague

**仓库：** https://github.com/lavague-ai/LaVague  
**Stars：** 6,390 | **License：** Apache-2.0

#### 定位：Large Action Model (LAM) 框架

LaVague 使用"大动作模型"框架，受 LeCun 模块化AI 论文启发，明确分离感知、世界建模和动作生成。

#### 三组件流水线

```
用户目标
    ↓
[World Model]← 截图 + HTML（VLM，GPT-4o）
    ↓ 子目标指令
[Action Engine]
    ├── Navigation Engine→ HTML RAG → LLM → Selenium/Playwright 代码
    ├── Python Engine      → RAG → LLM → 任意 Python
    └── Navigation Control → 预编码滚动/等待
    ↓
[Driver]        → 执行代码 → 更新页面
    ↓
[World Model]   ← 循环
```

#### HTML RAG 机制（Navigation Engine）

1. 对页面 HTML 分块
2. 嵌入模型（`text-embedding-3-large`）检索最相关片段
3. 相关片段 + 指令 → GPT-4o → Python 代码
4. 提取纯净代码执行
5. 重试逻辑：最多 5 次，每次间隔 1.5s

**关键设计**：不直接用可访问性树，而是对原始 HTML 做 RAG 检索 → 减少大页面的 token 消耗。

#### LLM 集成：基于 LlamaIndex

支持 OpenAI、Gemini、Azure、Fireworks（Mixtral）等，可替换任何 `llama_index.llms` 对象。

#### 独特功能

- `agent.demo()` 启动 Gradio UI快速原型
- LaVague QA：将Gherkin 规格文件转为可执行测试
- 内置 token 计数和成本估算
- 主动收集数据到 HuggingFace（BigAction org）用于 LAM 训练

#### 收敛机制

两级：

- **全局**：World Model（GPT-4o）判断全局目标已完成 → 停止迭代（主要出口）
- **单步**：Action Engine重试上限 `n_attempts=5`，间隔 1.5s，超出报错

World Model 是核心决策者，负责拆解子目标并判断整体何时结束。无全局步数上限，无循环检测。

---

### AWorld

**仓库：** https://github.com/inclusionAI/AWorld  
**Stars：** ~1,230 | **License：** MIT

#### 定位：Agent Harness — 多智能体编排平台

#### 目录结构

```
aworld/          — 核心框架 (agent, tools, memory, MCP client, runners)
aworld-skills/   — 可复用技能包(agent-browser, youtube_search 等)
aworld-tools/    — 工具扩展
examples/        — 基准测试示例 (browser_use, visualwebarena, gaia等)
```

#### Web 探索实现

**方法 1：agent-browser Skill（Playwright CLI封装）**
- 可访问性树优先，返回 `@ref` 元素 ID
- LLM 通过 `@e1`, `@e2` 等 ref 操作页面，不使用像素坐标
- 截图作为辅助（双模态）

**方法 2：Recon-Act系统（VisualWebArena 排名#1）**

两阶段多智能体协作：
1. **侦察团队**：探索目标网站，自动生成网站专属工具（如 `CategoryGuide.py`、`ClassifiedsPriceSorter.py`）
2. **行动团队**：使用生成工具 + VLM（AX 树 + 截图 + BLIP-2 图像描述）完成任务

关键创新：**自动生成领域工具**，将多步导航压缩为单次工具调用。

#### 收敛机制

两阶段各自收敛：

- **侦察阶段**：探索完成、领域工具生成完毕 → 阶段结束（有界）
- **行动阶段**：VLM 判断任务完成 → 输出结果

通过侦察阶段把"无限探索"预先压缩成"有限工具集"，间接约束了行动阶段的操作空间，是结构性收敛而非步数限制。

#### 基准测试成绩

| 基准 | 成绩 | 时间 |
|---|---|---|
| VisualWebArena | **36.48%（全球 #1）** | 2025-09 |
| OSWorld（桌面 GUI） | **58.0%（全球 #1）** | 2025-09 |
| GAIA | 67.89% Pass@1 | 2025-08 |
| IMO 2025 | 5/6 道题 | 2025-07 |

---

## 研究性项目

### WebVoyager

**论文：** "WebVoyager: Building an End-to-End Web Agent with Large Multimodal Models"  
**会议：** ACL 2024| **arXiv：** 2401.13919
**代码：** https://github.com/MinorJerry/WebVoyager

#### 方法

截图 + Set-of-Marks（SoM）标注 + GPT-4V，基于 Selenium 在真实网站运行。

**8 个动作：** Click [id] / Type [id]; text / Scroll / Wait / GoBack / GoHome / Google / ANSWER

#### 评测（15 个真实网站，643 任务）

| 系统 | 成功率 |
|---|---|
| WebVoyager (GPT-4V + SoM) | **59.1%** |
| GPT-4 纯文本 (含 HTML) | 23.5% |
| GPT-3.5 agent | 16.3% |
| 人类 | 89.4% |

核心发现：视觉（SoM）相比纯文本 GPT-4 提升 **+36pp**。

#### 收敛机制

单一终止动作：LLM 输出 `ANSWER; [text]` → 循环结束。8 个动作中只有 `ANSWER` 是终止动作，其余（Click/Type/Scroll 等）均为继续动作。无步数上限，无循环检测。

---

### SeeAct

**论文：** "GPT-4V(ision) is a Generalist Web Agent, if Grounded"  
**会议：** ICML 2024 | **arXiv：** 2401.01614  
**代码：** https://github.com/OSU-NLP-Group/SeeAct

#### 核心论点

GPT-4V 有足够的语义理解能力，但在实践中失败的原因是 **Grounding 瓶颈**：如何将意图（"点击加入购物车"）映射到实际 DOM 元素。

#### 四种 Grounding 策略对比

| 策略 | 机制 | 元素准确率 |
|---|---|---|
| 无 Grounding | 纯 GPT-4V 预测 | ~8–10% |
| 元素属性（HTML 属性） | 标签、aria-label、text 等 | ~42% |
| 文本候选列表 | 编号候选元素列表呈现给 GPT-4V | ~48–50% |
| 图像标注（边界框） | 彩色边界框 + 字母标签在截图上 | ~35–40% |
| **文本 + 图像组合** | 两者结合 | **~55%（最优）** |

#### 评测结果

- **离线（MIND2Web，2000 任务）**：Cross-Task 元素准确率 55.4%，步骤成功率 16.2%
- **在线（50 任务，真实网站）**：最优 Grounding → **51.1%**，无 Grounding → **9.7%**

Grounding 差距（9.7% → 51.1%）成为整个领域后续工作的研究重心。

#### 收敛机制

两阶段，第二阶段有终止信号：Stage 1（GPT-4V 生成意图）→ Stage 2（Grounding 定位元素）。当 Stage 1 判断任务完成时输出终止信号，跳过 Stage 2 直接退出。收敛依赖 GPT-4V 的任务完成判断，无显式循环检测。

---

### LASER

**论文：** "LLM Agent with State-Space Exploration"  
**arXiv：** 2309.08172

#### 核心创新：显式回溯（Backtracking）

将 Web 导航建模为状态空间搜索，agent 检测失败后可回滚到先前状态。

| 系统 | WebArena 成功率 |
|---|---|
| LASER (GPT-4) | **24.6%** |
| GPT-4 基线 | 14.9% |

仅通过添加回溯机制提升 **+10 pp**，现已成为生产 agent 的基础配置。

#### 收敛机制

将 Web导航建模为**状态空间搜索**，是所有项目中唯一把收敛显式建模的：

-维护已访问状态集合，检测到"死局"（当前状态无可行动作或重复访问）→ 回滚到上一状态
- 到达终止状态（任务完成）→ 停止
- 回溯本身就是一种有界机制：状态空间有限，不会无限循环

---

### Agent-E

**论文：** "Agent-E: From Autonomous Web Navigation to Foundational Design Principles"  
**机构：** Cisco | **arXiv：** 2407.13032

#### 两层创新

**1. 层级多agent（AutoGen）：** 编排者+ 专用子agent  
**2. DOM蒸馏：** 自定义算法将完整 DOM 压缩到任务相关元素（减少约 90% token），分配稳定元素 ID

| 系统 | WebVoyager 基准成功率 |
|---|---|
| Agent-E (GPT-4o) | **73.2%** |
| WebVoyager (GPT-4V) | 59.1% |
| GPT-4 纯文本 | 41.6% |

任务分解+ DOM 蒸馏带来 **+14 pp** 提升。

#### 收敛机制

层级终止：

- 编排者（Orchestrator）Agent 判断整体任务完成 → 通知子 agent 停止
- 子 agent 完成子任务后返回结果给编排者，编排者决定是否继续
- DOM 蒸馏（~90% token 压缩）间接限制每步动作范围，减少漫游概率

---

## 收敛机制横向对比

### 核心模式

收敛机制本质上只有两种：**LLM 主动选择终止动作**（绝大多数）和**框架硬性约束**（少数）。

###汇总表

| 项目 | 终止动作 | 步数上限 | 失败上限 | 循环检测 | 回溯 |
|---|---|---|---|---|---|
| **browser-use** | `done()` | 500（默认） | 可配置 | SHA-256 滚动哈希（20步窗口） | 无 |
| **Playwright MCP** | 无（客户端决定） | — | — | — | — |
| **Skyvern** | `COMPLETE` / `TERMINATE` | 未公开 | 无 | 无 | 无 |
| **OpenHands** | `send_msg_to_user()` | 无 | 5次连续失败 | 无 | 无 |
| **LaVague** | World Model 判断完成 | 无 | 每步5次重试 | 无 | 无 |
| **AWorld** | VLM 判断完成 | 无 | 无 | 无 | 无（侦察阶段结构性约束） |
| **WebVoyager** | `ANSWER` | 无 | 无 | 无 | 无 |
| **SeeAct** | GPT-4V 终止信号 | 无 | 无 | 无 | 无 |
| **LASER** | 终止状态（状态空间搜索） | 无 | 无 | 无 | **有（核心机制）** |
| **Agent-E** | 编排者 Agent 判断完成 | 无 | 无 | 无 | 无 |

### 规律总结

1. **绝大多数项目依赖 LLM 判断**：通过保留一个特殊终止动作（`done`/`COMPLETE`/`ANSWER`），让模型决定何时结束，无自动化保障
2. **browser-use 是最完善的**：唯一同时具备步数上限 + 失败计数 + 自动循环检测三层机制
3. **LASER 是唯一结构性收敛**：把搜索问题建模为状态空间，回溯是算法保证而非依赖 LLM 判断
4. **AWorld 的创新是间接收敛**：侦察阶段把开放搜索收缩为有限工具集，在任务开始前就限制了行动空间
5. **无循环检测是主流盲点**：除browser-use 外，其余项目均无自动检测重复行为的机制

### WebArena（812 任务，5 个自托管网站，程序化功能正确性评估）

| 时间 | 系统 | 成功率 |
|---|---|---|
| 2023| GPT-4 基线 | 14.9% |
| 2023 | GPT-3.5-turbo | 5.3% |
| 2024 | LASER (GPT-4) | 24.6% |
| 2024 | 树搜索 + GPT-4 方案 | 35–45% |
| 2025 | OpenAI Operator | 38.1% |
| — | 人类 | ~78% |

###VisualWebArena（910 个视觉条件任务）

| 系统 | 成功率 |
|---|---|
| GPT-4V + SoM | ~19% |
| GPT-4V 纯文本 | 16.4% |
| AWorld Recon-Act | **36.48%（#1）** |
| 人类 | ~88% |

### WebVoyager 基准（15 个真实网站，643 任务）

| 系统 | 成功率 |
|---|---|
| GPT-4纯文本 | 23.5% |
| WebVoyager (GPT-4V + SoM) | 59.1% |
| Agent-E (GPT-4o) | **73.2%** |
| 人类 | 89.4% |

---

## 项目综合对比表

| 项目 | 类型 | 观测方式 | 动作空间 | LLM 集成 | WebArena SR | Stars | License |
|---|---|---|---|---|---|---|---|
| **browser-use** | Python库 | AX树+ DOM 混合（CDP） | Pydantic 结构化工具 | 20+ provider适配器 | ~40–60% | ~50k | MIT |
| **Playwright MCP** | MCP Server | 可访问性树快照 | 预定义 MCP 工具 | MCP 客户端无关 | 未测| ~37k | Apache2.0 |
| **Skyvern** | Agent/SaaS | 截图 + DOM 混合（SoM） | 结构化（8 个动作） | GPT-4V/Claude |未发布 | ~11k | AGPL-3.0 |
| **OpenHands** | 开发平台 | 可访问性树（文本） | Python函数调用（BID） | LiteLLM（任意） | 不定 | 87k | MIT |
| **LaVague** | Agent框架 | 截图（世界）+ HTML RAG（动作） | 无边界 Selenium/Playwright 代码 | LlamaIndex（任意） | 未发布 | 6.4k | Apache2.0 |
| **AWorld** | Agent Harness | AX 树 + 截图（双模态） | MCP 工具 + 自生成领域工具 | 任意 | 36.48%（VWA） | ~1.2k | MIT |
| **WebVoyager** | 研究 agent | 截图 + SoM | 8 个动作（编号元素） | GPT-4V | 59.1%* | ~2k | — |
| **SeeAct** | 研究 agent | 截图 + HTML Grounding | 点击/输入/选择 | GPT-4V | 51.1%† | ~1k | Apache 2.0 |
| **Agent-E** | 研究 agent | DOM蒸馏 | 层级 NL + 低层动作 | GPT-4o | 73.2%* | ~2k | Apache 2.0 |
| **LASER** | 研究 agent | AX +回溯状态 | WebArena 动作集+ 回溯 | GPT-4 | 24.6% | ~500 | — |

*WebVoyager 基准（15 个网站，643 任务），非标准 WebArena 812 任务集
†在线真实网站评测，50 个任务

---

## 关键技术趋势

### 1. 视觉持续优于纯文本

SeeAct 证明了 Grounding 差距（9.7% → 51.1%），WebVoyager 证明 SoM 视觉优于纯文本 GPT-4（+36 pp）。SoM 标注已成为截图方案的标准配置。

### 2. Grounding 是核心瓶颈

"模型推理正确但元素定位失败"的 SeeAct 发现将后续工作重心转向更好的 Grounding 机制：SoM 标注、BID 系统、DOM 蒸馏。

### 3. DOM 压缩是非协商性需求

真实页面含 100k+ HTML token。各项目独立开发了不同压缩方案：
- Agent-E：DOM 蒸馏（~90% token 减少）
- OpenHands：BID 系统 + 可访问性树过滤
- Browser Use：DOM 修剪 + Paint-order 过滤
- LaVague：HTML RAG 检索

### 4. 层级多 agent 在复杂任务上领先

Agent-E 的 +14 pp 提升来自任务分解（编排者 + 专用子 agent）。AWorld 的 Recon-Act（侦察 + 行动双团队）位居 VisualWebArena 第一。

### 5. 回溯是高性价比优化

LASER 仅通过显式状态回溯提升 +10 pp，现已成为生产 agent 基础配置。

### 6. 可访问性树 vs. 截图仍是真实的设计争论

- **AX 树阵营**：Playwright MCP（明确声称"优于截图"）、OpenHands、browser-use
- **截图阵营**：Skyvern、WebVoyager、OpenAI Operator
- 结论：两者性能差距在Grounding 改进后缩小，高性能系统（AWorld）倾向混合使用

### 7. 自动生成领域工具（新兴趋势）

AWorld Recon-Act 的核心创新：先探索网站生成专属工具，再用工具完成任务。将多步导航压缩为单次工具调用，是目前 VisualWebArena 第一名的关键。

### 8. 基准成绩两年内翻倍

WebArena：14.9%（GPT-4，2023）→ 38.1%（Operator，2025）。人类水平（~78%）是近期目标，尚未在开源方案中稳定实现。

### 9. 商业产品持续领先开源

OpenAI Operator 和 Claude Computer Use 均在基准上领先，RL 微调（web交互轨迹）效果显著，但尚不可在开源中复现。

### 10. 框架整合加速

browser-use 正成为事实标准接口，定制模拟器被真实浏览器 Playwright 方案取代。

---

## 技术选型建议

### 通用场景

| 场景 | 推荐方案 | 理由 |
|---|---|---|
| 快速集成，生产 web 自动化 | **browser-use** | MIT，50k stars，Pydantic 结构化，多 provider |
| 作为 MCP 工具暴露浏览器 | **Playwright MCP** | 微软背书，无 LLM 耦合，AX 树原生 |
| 企业级 SaaS，抗 UI 变化 | **Skyvern** | 双通道鲁棒性，HITL 支持，REST API |
| 复杂多 agent 编排 | **AWorld** 或 **OpenHands** | 多 agent 支持，自生成工具，SOTA 成绩 |

### Ubuntu Docker 环境下的 Python 方案选型

**需求**：Ubuntu Docker 容器内控制浏览器，纯 Python，需要能在无头（headless）环境运行。

**推荐：browser-use**

理由：

- **纯 Python**：`pip install browser-use`，无需 Node.js 运行时
- **Playwright后端**：Playwright 对 Docker/headless 支持成熟，官方提供 `mcr.microsoft.com/playwright/python` 基础镜像
- **CDP 直连**：可通过 `cdp_url` 连接容器内已运行的 Chrome，无需再起一个进程
- **收敛机制最完善**：步数上限 + 失败计数 + 循环检测，Docker 长跑任务不会卡死
- **活跃维护**：50k stars，社区最大，Docker 相关 issue 有完整解答

**Docker 典型配置：**

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

RUN pip install browser-use
```

```python
import asyncio
from browser_use import Agent
from browser_use.browser import BrowserSession

async def main():
    agent = Agent(
        task="在网站上完成某个任务",
        llm=...,  # 任意 provider
        # 连接容器内已运行的 Chrome（CDP 端口）
        browser_session=BrowserSession(cdp_url="http://localhost:9222"),
        max_steps=50,
    )
    result = await agent.run()

asyncio.run(main())
```

**次选：Playwright Python +自定义 agent循环**

适合需要完全控制收敛逻辑的场景（自定义步数、自定义循环检测）：

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    # 自己写agent 循环 + LLM 调用
```

**不推荐在此场景用：**

- **Playwright MCP**：需要 Node.js，在纯 Python 项目中引入额外依赖
- **LaVague**：Selenium为主，Docker 内headless 配置比Playwright 繁琐，HTML RAG 依赖较重
- **Skyvern**：依赖完整 FastAPI 服务栈 + PostgreSQL，为单容器简单任务引入过多基础设施

---

*报告基于截至 2026-09-11 的公开信息，live star 数据来自实时抓取，论文数据来自发表时报告。*
