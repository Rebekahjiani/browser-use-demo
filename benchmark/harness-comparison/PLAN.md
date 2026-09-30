# 维度 B：阿器与 Claude Code 的 Context Model 抽取比较

状态（2026-09-30）：用户已执行 Claude Code，26页输出齐全。相同原始任务的历史产物比较已完成，结论见 `../BENCHMARK_B_CONCLUSION_20260930.md`。下文预检与预注册设计保留为历史；它们没有全部按原设计执行，不宣称严格受控实验。无需继续解决之前独立CLI入口问题。

## 比较问题

在相同证据与用户任务下，阿器和 Claude Code 搭配同一 `sophnet/DeepSeek-V4-Flash-0731`，哪个更准确地抽取实体、属性和关系。harness 自身系统提示词、工具和编排属于比较对象；共同任务提示词、证据文件、输出 schema、模型版本及预算固定。不能宣称两套完整系统提示词相同。

按用户最新决定，直接沿用阿器原始 entity-extract 任务，放弃改用 53 个标准化 AX 快照的方案。已将原始 TASK.md、INDEX.json、schema.json 和 26 页 inputs/ 共 81 个文件复制至 `claudecode-original-task/entity-extract/`，逐文件 SHA256 与源文件一致。输入包括原有页面树、page.json 和 endpoints.jsonl；不改变素材或输出契约。排除已有 output/ 和未启用的 stage2/。复制清单见 `claudecode-original-task/input-manifest.json`。

用户提示词仅替换任务根路径，见 `claudecode-original-task/PROMPT.md`。Claude Code 应在副本的逐页 output/concepts.json 写出结果。此次仅准备目录，尚未启动 Claude Code。输入里的 sources 元数据保留原文，不改写来源路径；本阶段只使用 inputs/ 已提供的素材。

## 正式运行前的冻结项

1. 单独、隔离的两个工作目录，复制字节一致的证据包；保存文件 SHA256。
2. 同一用户任务和 JSON schema：实体、属性、关系逐项给出相对文件路径、JSON Pointer、原文证据；支持同义词，未知不猜测。页面导航对象与业务实体区分，搜索输入条件不冒充商品实例字段。
3. 固定模型路由与参数；保存服务端返回模型名及实际调用记录。两边先通过无 benchmark 材料的连接与工具读取预检。
4. 相同 600 秒上限；记录实际 token、调用次数、失败、超时和完成时间。harness 无法完全对齐的默认采样/上下文策略显式记录，不宣称严格控制所有内部参数。
5. 在正式候选产生前冻结答案、别名映射、实体/属性/关系评分规则。主要指标是有证据的精确率与召回率，另列引用可定位率、遗漏和无证据断言；不把未知强判为错误。开放实体命名需保留逐项裁定记录。
6. 无人工中途补提示、无引导修正失败结果；预检与正式运行分开。第一次运行给工程选型结论，单次结果不代表稳定性排序。

## 当前预检结果（2026-09-29）

- Claude Code 已安装：2.1.268。
- 阿器配置模型为 `tlaic/sophnet/DeepSeek-V4-Flash-0731`；AT provider 为 `openai-completions`。
- 当前网关 `https://platform.tlaic.ac.cn/api/gateway/v1/chat/completions` 对相同 Flash 模型请求返回 200，服务端模型名 `DeepSeek-V4-Flash-0731`。
- 同网关 `/v1/messages` 返回 404，正文为 `not found`；Claude Code 原生 Messages 协议的无工具预检同样失败。详见 `claude-flash-smoke.v1.json`。这不是正式抽取失败，更不是 Claude Code 实体抽取能力差的证据。
- 无凭据写入报告，未修改全局 Claude/AT 设置。

需要确认 Claude Code 的兼容连接方式：使用用户已有的同模型 Anthropic Messages 入口，或增加本机 Messages→OpenAI 协议适配器。若选择适配器，必须先验证工具调用、流式响应、usage/model 记录，并把适配器作为实验环境的一部分披露；不得悄悄换成 Claude 模型。
