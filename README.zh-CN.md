# WhatToOffload

[English](README.md)

WhatToOffload 是一个用于改造现有会话、代码项目、SOP 和工作流的 Agent Skill。它帮助用户重新划分当前 Agent 与普通软件之间的职责边界。

它先识别原子节点，再把相关节点组合成短时、有明确边界的可卸载子流程，并为每个节点选择能够可靠完成任务的最简单执行者：确定性代码、现有工具或 API、Jev、小模型、强模型或外部 Agent，以及人工复核。

## 它能做什么

- 先检查 Agent 已经能访问的材料，再询问真正缺失的关键信息。
- 默认给出少量、有推荐顺序的卸载候选，同时说明哪些节点应该继续保留在当前 Agent 中。
- 分开判断“节点在哪里运行”和“节点由什么能力完成”。
- 用户选中候选后，展开流程图、节点表、接口、失败路径、审批点和测试方案。
- 获得明确实施授权后，保留目标项目现有技术栈，并在合适时生成可导入函数和 JSON CLI。
- 使用统一状态区分完成、缺少输入、需要语义复核、需要审批和失败。

## 它不是什么

WhatToOffload 不是工作流运行平台。第一阶段不提供持久化调度、后台 worker、跨天等待、部署、队列、控制台或密钥管理。

## 典型使用方式

1. 让 WhatToOffload 分析一个现有工作流。
2. 查看最多三个优先候选，以及建议继续留给 Agent 的节点。
3. 选中一个候选，获得与具体绘图工具解耦的详细工作流设计。
4. 如果希望修改目标项目，再明确授权实施。

真实的付费 API 调用和外部副作用发生前，Skill 会单独停下来获取确认。

## 第一阶段案例

- [测试失败与问题分诊](examples/code-triage.md)
- [网页调研与证据综合](examples/web-research.md)
- [商业入口与候选对象初筛](examples/business-screening.md)

每个案例刻意保持小体量：提供端到端规格和关键代码形态，但不维护单独的完整示例应用。

## Jev 与 TypeSafe

WhatToOffload 负责识别哪些节点适合使用有界、带类型的语义判断。进入 Jev 实施前，Agent 必须读取当前环境中的 `typesafe-ai` Skill，并查阅最新的 [TypeSafe 官方文档](https://docs.typesafe.ai/llms.txt)。控制流、确定性规则、副作用和不确定性路由仍由代码负责。

## 项目结构

- `SKILL.md` 是唯一 Skill 入口。
- `references/` 保存按需读取的第一阶段设计方法。
- `assets/templates/` 保存人类可审阅的规格模板和 JSON 协议示例。
- `examples/` 保存三个跨领域案例。
- `agents/openai.yaml` 提供可选的 Codex 展示元数据，不污染通用 Skill 指令。

## 路线图

后续阶段可能研究持久异步工作流、更多专业 Skill 路由和更好的工作流可视化。这些能力不属于第一阶段，也不会在当前 Skill 中被提前声明为可用。

## 当前状态

当前仓库只包含 Skill 源文件。它不会自动安装，也不会配置 GitHub 远端。外部 API 探测默认关闭，只有获得明确授权后才会执行。

在 2026-09-20 的开发验证中，一次获得明确授权的合成数据契约测试成功验证了 OpenRouter Decisions API 的 Choice、Noul、Score 返回，以及 DeepSeek OpenAI 兼容 Chat Completions 的严格 JSON 生成。仓库中不包含任何密钥或供应商专用运行配置；该结果只证明当次兼容性，不构成永久可用性保证。
