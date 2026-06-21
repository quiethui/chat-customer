# AI Customer Service — AGENTS.md

本文档是 AI 开发助手在本项目中工作时必须遵守的规范。所有新增和修改代码的行为都应遵循以下规则。

> `CLAUDE.md` 是本文件的软链接，供 Claude Code 自动加载；两者内容一致，只需维护本文件。

---

## 项目概述

一个基于 FastAPI + React 的完整 AI 客服系统。终端客户通过轻量挂件（`widget/`）获得 RAG 知识库问答 + 工具调用（订单/商品查询）自动化服务，需要时可一键转人工，坐席在管理端工作台（`web/`）实时接入并双向对话。系统支持匿名访客、注册升级、登录会话合并、满意度评分、管理员后台（知识库、客户、坐席、对话记录管理）。

**核心角色体系**：
- **Customer（客户）**：终端用户，通过 `widget/` 挂件咨询，支持匿名访客 → 注册 → 登录流程
- **Manager（坐席/管理员）**：客服人员，通过 `web/` 管理端登录，分为普通坐席与管理员两级权限
- **系统 AI**：自动应答模式，通过 RAG + 工具调用回答客户问题


---

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy ORM（PyMySQL 驱动）
- **管理端前端**: React 19 / TypeScript / Ant Design Pro v6 / UmiJS Max / antd v6 / Biome（`web/`）
- **客户端前端**: React 19 / TypeScript / Vite（`widget/`，独立轻量）
- **LLM**: OpenAI 兼容 API（支持 OpenAI / Deepseek / 本地模型）
- **Embedding**: BAAI/bge-M3（可切换为 hash 本地模式）
- **向量库**: Milvus / Milvus Lite（可切换为 memory 模式）
- **数据库**: MySQL
- **缓存**: Redis（上下文缓存 + 客户端 token）
- **实时通信**: SSE（Server-Sent Events）事件流
- **测试**: pytest（`tests/` 目录）
- **包管理**: 后端 uv，前端 npm

---

## 项目目录结构

```
├── app/                    # 后端 FastAPI 应用
│   ├── agent/              # AgentExecutor：Function Calling 多轮工具调用执行器
│   ├── api/                # 路由层：auth / customer_auth / customer_chat / chat / knowledge_base
│   │   │                   #        session / message / customer / manager / llm_log
│   │   └── mappers/        # API 响应模型转换器
│   ├── core/               # 配置加载（config.py）与统一响应（response.py）
│   ├── db/                 # 数据库会话管理与依赖注入
│   ├── dependencies.py     # FastAPI 依赖注入（get_current_customer / get_current_admin_manager 等）
│   ├── llm/                # OpenAI 兼容客户端封装（openai_client.py）
│   ├── models/             # SQLAlchemy ORM 模型（对应数据库表）
│   ├── rag/                # RAG 全流程：解析 / 切块 / embedding / 检索 / prompt
│   ├── repositories/       # 数据访问层
│   │   ├── mysql/          # MySQL 仓储（ORM mixin，按业务域拆分 + records + mappers）
│   │   ├── vector/         # 向量库仓储（Milvus / Memory）
│   │   ├── context/        # Redis 上下文缓存
│   │   └── conversation_bus.py  # 实时消息总线（SSE 事件流）
│   ├── schemas/            # Pydantic 请求/响应模型
│   ├── services/           # 业务编排层（chat / conversation / customer_auth / manager / knowledge）
│   ├── tools/              # Tool Calling 工具（订单查询 / 商品查询）
│   ├── uploads/            # 上传文件存储目录
│   └── utils/              # 通用工具函数
├── web/                    # 管理端前端（Ant Design Pro，React 19）
│   ├── config/             # UmiJS 配置（config.ts / routes.ts）
│   └── src/
│       ├── pages/          # 页面：knowledge / system-customer / system-manager / agent-desk / llm-log
│       ├── services/       # 后端接口：auth / knowledge / customer / manager
│       ├── access.ts       # 权限定义（canAccess / canAdmin）
│       ├── app.tsx         # 运行时配置（getInitialState / request / layout）
│       └── requestErrorConfig.ts  # 统一响应适配 + Bearer Token 注入
├── widget/                 # 客户端挂件（独立轻量，React 19 + Vite）
│   └── src/
│       ├── widget/         # 挂件组件：ChatWidget / ChatWindow / AuthModal / ConversationList
│       ├── api/            # 客户端接口：auth / chat
│       ├── hooks/          # 业务 Hooks：useVisitor / useChatStream
│       └── DemoShop.tsx    # 演示页面（模拟电商网站嵌入挂件）
├── tests/                  # pytest 测试
├── schema.sql              # MySQL 初始化建表与演示数据
├── AGENTS.md               # 本文件（CLAUDE.md 为其软链接）
└── .env.example            # 环境变量模板
```

---

## 后端开发规则

### 代码规范

- 所有函数和方法必须有类型注解。
- 所有函数和类必须有 docstring（中文）。
- 单个文件不超过 500 行；超出时拆分为多个模块。
- 禁止在 service 或 tool 中直接写 SQL；数据库操作必须放在 `repositories/` 中。
- 新增数据库表或字段时，必须同步更新 `schema.sql`，并对已有库执行对应的 `ALTER`。

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
3. 工具返回的 `ToolExecution.content` 只包含当前客户可见的数据。
4. 客户私有数据查询必须通过 `customer_id` 做数据隔离；全局数据（如商品目录）可不隔离但需注明。
5. 远程模型路径由 `app/agent/AgentExecutor` 驱动多轮工具调用，轮数由 `AGENT_MAX_TOOL_ROUNDS` 配置；无需修改执行器即可接入新工具。

### 新增 API 接口

1. 在 `app/schemas/` 中定义请求和响应的 Pydantic 模型。
2. 在 `app/api/` 中创建路由文件，只做参数校验和调用 service。
3. 在 `app/services/` 中实现业务逻辑。
4. 在 `app/main.py` 中注册路由。
5. 客户端接口通过 `dependencies.py` 中的 `get_current_customer` 获取当前客户。
6. 坐席端接口通过 `get_current_manager` 获取当前坐席。
7. **仅管理员**可访问的接口（如坐席管理、客户管理）使用 `get_current_admin_manager` 依赖，非管理员返回 `403`。管理员身份由 `managers.is_admin` 决定。

### 数据库操作

- 使用 SQLAlchemy ORM；ORM 模型定义在 `app/models/`，按业务域拆分的查询封装在 `app/repositories/mysql/` 的各 Mixin 中，统一由 `MySQLRepository` 聚合。
- 请求级 Session 由 `app/dependencies.py` 的 `get_db_session` 管理，统一提交/回滚；后台任务用 `create_mysql_repository()` 获取独立事务边界的仓储。
- 查询使用 SQLAlchemy 表达式（`select(...)`），禁止手写字符串拼接 SQL。
- 查询结果通过 `app/repositories/mysql/mappers.py` 的 `map_xxx()` 函数转换为 frozen dataclass（`records.py`），业务层不直接接触 ORM 对象。
- 软删除：会话、订单、客户、坐席等通过 `deleted_at` 字段标记删除（`NULL` 表示未删除）；登录/鉴权与列表查询必须过滤已删除记录。

---

## 前端开发规则

### 管理端前端（`web/`，Ant Design Pro）

> 详细约定见 [`web/CLAUDE.md`](web/CLAUDE.md)，以下为要点。

- 使用 React 19 + Ant Design Pro v6 + UmiJS Max；包管理用 **npm**（非 pnpm/yarn）。
- **禁止编辑 `src/services/ant-design-pro/`**（OpenAPI 自动生成）；业务接口新建独立目录（如 `src/services/customer/`）。
- 代码检查只用 **Biome**；`npm run lint`（Biome + tsc）与 `npx antd lint ./src` 必须通过。
- 写 antd 组件前先 `npx antd info <组件>` 核对 v6 API；组件内用 `App.useApp()` 获取 `message`。
- 路由在 `config/routes.ts` 配置，`name` 对应 `src/locales/*/menu.ts` 的 `menu.xxx`，`access` 字段控制菜单可见性（`canAccess`=已登录，`canAdmin`=管理员）。
- 后端统一响应 `{success, code, message, msg, data}` 由 `src/requestErrorConfig.ts` 适配；Bearer Token 由请求拦截器从 localStorage 注入，`401` 自动清 token 跳登录。
- 接口调用放在 `src/services/<模块>/`，页面放在 `src/pages/<模块>/`。

#### 新增页面（web）

1. 在 `src/services/<模块>/` 新建接口与类型。
2. 在 `src/pages/<模块>/` 新建页面组件。
3. 在 `config/routes.ts` 注册路由（含 `access`），在 `src/locales/{zh-CN,en-US}/menu.ts` 补 `menu.<模块>`。

### 客户端挂件（`widget/`，独立轻量）

- 使用 React 19 + TypeScript + Vite；包管理用 **npm**。
- 构建产物为单个 JS 文件，可嵌入任意页面（零配置接入）。
- API 调用放在 `src/api/`，业务逻辑封装在 `src/hooks/`，UI 组件放在 `src/widget/`。
- 自动处理匿名访客、注册、登录、会话恢复逻辑，前端无需额外配置。
- 实时消息通过 SSE 订阅 `/customer/conversations/{id}/events` 接收坐席回复。

---

## 开发流程

### 新功能开发步骤

1. 更新 `schema.sql`（如涉及数据库变更），并对已有库执行 `ALTER`。
2. 在 `app/repositories/mysql/` 实现数据访问（ORM mixin + `records.py` + `mappers.py`）。
3. 在 `app/schemas/` 定义数据模型。
4. 在 `app/services/` 实现业务逻辑。
5. 在 `app/api/` 创建路由，并在 `app/main.py` 注册。
6. 前端对接：
   - 管理端：在 `web/src/services/` 对接接口、`web/src/pages/` 实现界面，在 `web/config/routes.ts` 注册路由。
   - 客户端：在 `widget/src/api/` 对接接口、`widget/src/widget/` 实现 UI 组件。
7. 补充测试用例（`tests/` 目录）。
8. 更新 `README.md` 中的功能说明。

### 环境变量

新增后端配置项时：
- 在 `app/core/config.py` 的 `Settings` dataclass 中添加字段。
- 在 `get_settings()` 中从环境变量读取。
- 在 `.env.example` 中添加说明和默认值。

前端配置：
- 管理端（`web/`）：后端地址由 `web/.env` 的 `UMI_APP_API_BASE` 配置，开发端口由 `PORT` 配置（默认 8001，避开后端 8000）。
- 客户端（`widget/`）：后端地址在构建时通过环境变量注入，或运行时由挂件初始化参数指定。

---

## RAG 流程说明

文档上传后的处理链路：

```
文档上传 → 文本解析(parser) → 切块(splitter) → Embedding(embedding) → 存入向量库(repositories/vector)
```

客户提问时的处理链路：

```
客户问题 → Embedding → 向量检索(repositories/vector) → 获取相关 chunks
         → AgentExecutor 工具调用(如有匹配) → 拼接 Prompt(prompt) → 调用 LLM → 返回回答
```

**实时消息流**：
- **客户端挂件**：通过 SSE 订阅 `/customer/conversations/{id}/events` 接收坐席消息与状态变更
- **坐席工作台**：通过 SSE 订阅 `/agent/conversations/{id}/events` 接收客户消息
- **消息总线**：`ConversationBus`（`app/repositories/conversation_bus.py`）负责会话事件的发布/订阅

---

## 数据隔离与权限原则

- 所有客户数据查询必须携带 `customer_id` 过滤。
- 会话、消息、订单等数据均通过 `customer_id` 隔离不同客户。
- Redis 上下文 key 格式：`chat:context:{customer_id}:{session_id}`。
- Redis 客户端 token key 格式：`customer:token:{token}`。
- 禁止跨客户访问数据。
- 管理操作（如坐席管理、客户管理）必须经 `get_current_admin_manager` 校验；禁止删除/禁用当前登录账号。
- 删除采用软删除（`deleted_at`），已删除账号禁止登录、不出现在列表中。

---

## 禁止事项

- 禁止直接修改 `ROADMAP.md`、`README.md`、`schema.sql`、`.env`、`.env.example`，除非用户明确要求。
- 禁止引入 LangChain、LangGraph 等复杂框架，除非用户明确要求。
- 禁止在后端代码中直接操作数据库连接（必须通过 Repository）。
- 禁止在路由层写业务逻辑。
- 禁止跳过类型注解和 docstring。
- 禁止编辑管理端前端 `web/src/services/ant-design-pro/`（OpenAPI 自动生成）。
- 禁止混淆 `customer`（客户）与 `manager`（坐席/管理员）两个角色体系。
