# AI Customer Service — AGENTS.md

本文档是 AI 开发助手在本项目中工作时必须遵守的规范。所有新增和修改代码的行为都应遵循以下规则。

---

## 项目概述

一个基于 FastAPI + Vue 3 的 AI 客服 RAG 系统。用户上传知识库文档后，系统通过向量检索 + 大模型生成回答，并通过 Function Calling 工具调用（订单查询、商品查询）接入业务能力，支持用户登录、会话管理、消息上下文等。

---

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy ORM（PyMySQL 驱动）
- **前端**: Vue 3 / TypeScript / Element Plus / Pinia / Vite / UnoCSS
- **LLM**: OpenAI 兼容 API
- **Embedding**: BAAI/bge-M3（可切换为 hash 本地模式）
- **向量库**: Milvus / Milvus Lite（可切换为 memory 模式）
- **数据库**: MySQL
- **缓存**: Redis
- **测试**: pytest（`tests/` 目录）
- **包管理**: 后端 uv，前端 pnpm

---

## 项目目录结构

```
├── app/                    # 后端 FastAPI 应用
│   ├── agent/              # AgentExecutor：Function Calling 多轮工具调用执行器
│   ├── api/                # 路由层，只做参数校验和调用 service
│   ├── core/               # 配置加载（config.py）和统一响应（response.py）
│   ├── dependencies.py     # FastAPI 依赖注入
│   ├── llm/                # OpenAI 兼容客户端封装（openai_client.py）
│   ├── rag/                # RAG 全流程：解析、切块、embedding、检索、prompt
│   ├── repositories/       # 数据访问层：mysql/（ORM mixin）、vector/、context（Redis）
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── services/           # 业务编排层
│   ├── tools/              # Tool Calling 工具（订单查询、商品查询）
│   ├── uploads/            # 上传文件存储目录
│   └── utils/              # 通用工具函数
├── web/                    # 前端 Vue 3 应用
│   └── src/
│       ├── api/            # 后端接口调用
│       ├── components/     # 公共组件
│       ├── hooks/          # 组合式函数
│       ├── layouts/        # 布局组件
│       ├── pages/          # 页面视图
│       ├── routers/        # 路由配置
│       ├── stores/         # Pinia 状态管理
│       └── utils/          # 工具函数
├── tests/                  # pytest 测试
├── schema.sql              # MySQL 初始化建表和演示数据
├── .env.example            # 环境变量模板
└── AGENTS.md               # 本文件
```

---

## 后端开发规则

### 代码规范

- 所有函数和方法必须有类型注解。
- 所有函数和类必须有 docstring（中文）。
- 单个文件不超过 500 行；超出时拆分为多个模块。
- 禁止在 service 或 tool 中直接写 SQL；数据库操作必须放在 `repositories/` 中。
- 新增数据库表时，必须同步更新 `schema.sql`。

### 架构分层

各层职责明确，不允许跨层调用：

| 层级 | 目录 | 职责 |
|---|---|---|
| 路由层 | `app/api/` | 参数校验、调用 service、返回统一格式 |
| 业务层 | `app/services/` | 编排多个 repository 和工具，实现业务逻辑 |
| 数据层 | `app/repositories/` | 封装 MySQL、Redis、向量库的读写操作 |
| 工具层 | `app/tools/` | 实现 `ChatTool` 协议，处理特定查询任务 |
| 模型层 | `app/schemas/` | Pydantic 数据模型，定义请求和响应结构 |

### 统一响应格式

所有 API 必须使用 `app/core/response.py` 中的函数返回：

```python
# 成功
{"success": True, "code": 200, "message": "success", "msg": "success", "data": ...}

# 失败
{"success": False, "code": 500, "message": "...", "msg": "...", "data": ...}
```

禁止在路由中直接返回自定义格式。

### 新增 Tool Calling 工具

1. 在 `app/tools/` 下创建新文件，实现 `ChatTool` 协议（`name`、`schema`、`can_handle`、`call`、`call_from_question`）。
2. 在 `app/dependencies.py` 的 `get_tool_registry()` 中注册新工具实例。
3. 工具返回的 `ToolExecution.content` 只包含当前用户可见的数据。
4. 用户私有数据查询必须通过 `user_id` 做数据隔离；全局数据（如商品目录）可不隔离但需注明。
5. 远程模型路径由 `app/agent/AgentExecutor` 驱动多轮工具调用，轮数由 `AGENT_MAX_TOOL_ROUNDS` 配置；无需修改执行器即可接入新工具。

### 新增 API 接口

1. 在 `app/schemas/` 中定义请求和响应的 Pydantic 模型。
2. 在 `app/api/` 中创建路由文件，只做参数校验和调用 service。
3. 在 `app/services/` 中实现业务逻辑。
4. 在 `app/main.py` 中注册路由。
5. 需要登录的接口通过 `dependencies.py` 中的 `get_current_user` 获取用户。

### 数据库操作

- 使用 SQLAlchemy ORM；ORM 模型定义在 `app/models/`，按业务域拆分的查询封装在 `app/repositories/mysql/` 的各 Mixin 中，统一由 `MySQLRepository` 聚合。
- 请求级 Session 由 `app/dependencies.py` 的 `get_db_session` 管理，统一提交/回滚；后台任务用 `create_mysql_repository()` 获取独立事务边界的仓储。
- 查询使用 SQLAlchemy 表达式（`select(...)`），禁止手写字符串拼接 SQL。
- 查询结果通过 `app/repositories/mysql/mappers.py` 的 `map_xxx()` 函数转换为 frozen dataclass（`records.py`），业务层不直接接触 ORM 对象。

---

## 前端开发规则

### 技术约定

- 使用 Vue 3 + Composition API + `<script setup>` 语法。
- 状态管理使用 Pinia，按模块拆分在 `stores/modules/` 中。
- 样式使用 UnoCSS，保持原子化。
- HTTP 请求封装在 `utils/request.ts`，基于 hook-fetch。
- 接口调用放在 `api/` 目录，按功能模块分文件夹。

### 新增页面

1. 在 `pages/` 下创建页面组件。
2. 在 `routers/` 中注册路由。
3. 如需全局状态，在 `stores/modules/` 中新建 Pinia store。
4. 如需调用后端接口，在 `api/` 下新建调用文件。

---

## 开发流程

### 新功能开发步骤

1. 更新 `schema.sql`（如涉及数据库变更）。
2. 在 `app/repositories/` 实现数据访问。
3. 在 `app/schemas/` 定义数据模型。
4. 在 `app/services/` 实现业务逻辑。
5. 在 `app/api/` 创建路由。
6. 在 `app/main.py` 注册路由。
7. 在前端 `web/src/api/` 对接接口。
8. 在前端 `web/src/pages/` 或 `components/` 实现界面。
9. 更新 `README.md` 中的功能说明。

### 环境变量

新增配置项时：
- 在 `app/core/config.py` 的 `Settings` dataclass 中添加字段。
- 在 `get_settings()` 中从环境变量读取。
- 在 `.env.example` 中添加说明和默认值。

---

## RAG 流程说明

文档上传后的处理链路：

```
文档上传 → 文本解析(parser) → 切块(splitter) → Embedding(embedding) → 存入向量库(repositories/vector)
```

用户提问时的处理链路：

```
用户问题 → Embedding → 向量检索(repositories/vector) → 获取相关 chunks
         → AgentExecutor 工具调用(如有匹配) → 拼接 Prompt(prompt) → 调用 LLM → 返回回答
```

---

## 数据隔离原则

- 所有用户数据查询必须携带 `user_id` 过滤。
- 会话、消息、订单等数据均通过 `user_id` 隔离不同用户。
- Redis 上下文 key 格式：`chat:context:{user_id}:{session_id}`。
- 禁止跨用户访问数据。

---

## 禁止事项

- 禁止直接修改 `ROADMAP.md`、`README.md`、`schema.sql`、`.env`、`.env.example`，除非用户明确要求。
- 禁止引入 LangChain、LangGraph 等复杂框架，除非用户明确要求。
- 禁止在后端代码中直接操作数据库连接（必须通过 Repository）。
- 禁止在路由层写业务逻辑。
- 禁止跳过类型注解和 docstring。
