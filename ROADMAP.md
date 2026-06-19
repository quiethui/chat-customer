# Roadmap

本文件记录 AI Customer Service 的架构概览、已完成能力与后续计划。功能使用说明见 [README.md](README.md)，开发约定见 [AGENTS.md](AGENTS.md)。

## 架构概览

```
┌────────────┐   ┌──────────────┐   ┌─────────────────────────────────────────────┐
│  Vue 3 前端 │ → │ FastAPI 路由层 │ → │ Service 编排层                               │
└────────────┘   └──────────────┘   │  ├─ RAG：Embedding → 向量检索 → 上下文精选     │
                                     │  ├─ AgentExecutor：多轮 Function Calling 工具  │
                                     │  └─ Prompt 拼接 → LLM 生成                     │
                                     └─────────────────────────────────────────────┘
                                            │              │              │
                                       MySQL(ORM)       Redis(上下文)   向量库(Milvus)
```

分层职责：路由层（`app/api`）只做校验与转发 → 业务层（`app/services`）编排 → 数据层（`app/repositories`：MySQL ORM / 向量库 / Redis）。工具调用由独立的 `app/agent/AgentExecutor` 驱动。

## 已完成

- **核心 RAG 问答**：文档解析 → 切块 → Embedding → 向量库 → 检索精选 → Prompt → LLM。
- **多知识库管理**：知识库 CRUD、文件上传/列表/删除/重传、查看 Chunk、重新解析、重新 Embedding。
- **用户体系**：用户名密码注册/登录、Bearer Token、`/auth/me`。
- **会话与消息**：会话 CRUD、消息持久化（MySQL）、最近上下文缓存（Redis），按 `user_id` + `session_id` 隔离。
- **工具调用 Agent**：`AgentExecutor` 驱动 OpenAI 兼容 Function Calling 多轮循环，轮数可配（`AGENT_MAX_TOOL_ROUNDS`），含执行 trace。
  - 订单查询工具（按用户隔离）。
  - 商品查询工具（全局商品目录）。
- **RAG 测试模式**：`/chat` 支持 `ragTest`，只返回检索调试信息，不调用模型。
- **可切换后端**：Embedding（hash / sentence_transformers）、向量库（memory / milvus）。
- **测试**：`tests/` 下 pytest 覆盖 AgentExecutor、工具、认证、上下文选择、聊天编排。

## 后续计划

- [ ] **更多业务工具**：优惠券查询、退款进度、物流轨迹等（实现 `ChatTool` 协议并注册即可）。
- [ ] **轻量意图路由**：在多工具规模增长后引入意图分类，减少无效工具调用。
- [ ] **SSE 流式输出**：`/chat` 支持流式返回，提升交互体验。
- [ ] **可观测性增强**：将 AgentExecutor 的工具调用 trace 接入结构化日志 / 链路追踪。
- [ ] **管理后台**：知识库与商品数据的可视化管理。

## 设计原则

1. 保持简单，按需演进，不提前引入复杂框架。
2. 严格分层，业务层不直接接触 ORM 对象与数据库连接。
3. 所有用户私有数据查询强制 `user_id` 隔离。
4. 一个功能一条链路（schema → repository → service → api → 前端）闭环交付。
