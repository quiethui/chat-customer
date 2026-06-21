# AI Customer Service

> 基于 FastAPI + React 的 AI 智能客服系统：知识库 RAG 问答 + 多工具调用 Agent + 客户/坐席双端 + 实时人工转接。

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![React](https://img.shields.io/badge/React-19-61dafb)
![Ant Design Pro](https://img.shields.io/badge/Ant%20Design%20Pro-6-1677ff)
![License](https://img.shields.io/badge/License-MIT-green)

一个完整可用的 AI 客服系统：终端客户通过聊天挂件获得 **RAG 知识库问答 + 工具调用**（订单/商品查询）自动化服务，需要时可**一键转人工**，坐席在工作台实时接入并双向对话。系统支持匿名访客、注册升级、登录会话合并、满意度评分、管理员后台（知识库、客户、坐席、对话记录管理）。

**架构亮点**：
- 🎯 客户端挂件（`widget/`）：独立轻量，可嵌入任意电商/业务页面
- 🖥️ 管理端后台（`web/`）：Ant Design Pro，提供知识库、客户管理、坐席工作台
- 🤖 AI + 人工混合：自动应答覆盖率高，复杂问题无缝转人工
- 🔌 实时消息总线：SSE 事件流，坐席-客户双向通信零延迟
- 🛠️ 可扩展工具调用：Function Calling 驱动，新增业务工具只需实现协议并注册

## ✨ 功能特性

### 客户端（C 端，终端用户）
- **聊天挂件**：独立轻量的 React 组件（`widget/`），可嵌入任意页面右下角悬浮球
- **匿名访客**：无需注册即可咨询，系统自动分配访客身份
- **注册与登录**：注册时就地升级匿名身份（聊天记录零迁移），登录时自动合并当前匿名会话
- **历史会话**：客户复访时自动恢复最近会话，可查看历史对话列表
- **一键转人工**：AI 无法解决时可转接坐席，实时双向对话（SSE 事件流）
- **满意度评分**：会话结束后可对服务质量打分并留言

### 坐席端（B 端，客服人员）
- **工作台**：实时接收转人工请求，与客户双向对话，查看完整上下文
- **会话管理**：查看待接入/进行中/已结束会话，支持会话关闭与备注
- **客户信息**：查看客户资料、历史会话、订单数据（权限隔离）

### AI 能力
- **知识库 RAG 问答**：上传 `txt`/`md`/`pdf`/`docx`，自动解析、切块、Embedding、写入向量库，检索后由大模型生成回答
- **多知识库管理**：创建多个知识库（订单/商品/售后等），支持文件上传、列表、删除、重传、查看 Chunk、重新解析、重新 Embedding
- **工具调用 Agent**：基于 OpenAI 兼容 Function Calling 的多轮工具调用执行器（`AgentExecutor`），内置订单查询（按客户隔离）、商品查询（全局目录）
- **RAG 测试模式**：可只返回检索命中的 chunks、相似度、最终 Prompt 和耗时，便于调试召回质量

### 管理后台（管理员）
- **客户管理**：分页检索（按账号/状态/注册时间/登录 IP）、查看详情、新建、编辑（含重置密码）、启用/禁用、软删除客户
- **坐席管理**：管理员可新增、编辑、启禁用坐席账号；坐席分为普通与管理员两级权限
- **对话记录**：查看所有会话记录、消息明细、满意度评分统计
- **LLM 调用日志**：记录所有模型调用的输入/输出/耗时/token 消耗，便于成本分析与问题排查

### 技术特性
- **实时消息总线**：基于 SSE 的 `ConversationBus`，坐席-客户双向消息零延迟推送
- **数据隔离**：客户订单/会话按 `customer_id` 严格隔离，工具调用强制携带身份参数
- **优雅降级**：未配置远程模型时走本地兜底回答；Redis 不可用时回源 MySQL
- **软删除**：客户、坐席、会话采用 `deleted_at` 标记删除，可在数据库恢复

## 🏗️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy ORM（PyMySQL 驱动） |
| 管理端前端 | React 19 · TypeScript · Ant Design Pro v6 · UmiJS Max · antd v6 · Biome（`web/`） |
| 客户端前端 | React 19 · TypeScript · Vite（`widget/`，独立轻量） |
| LLM | OpenAI 兼容 API（支持 OpenAI / Deepseek / 本地模型） |
| Embedding | `BAAI/bge-m3`（可切换为本地 hash 模式） |
| 向量库 | Milvus / Milvus Lite（可切换为内存模式） |
| 数据库 | MySQL（业务数据与会话） |
| 缓存 | Redis（上下文缓存 + 客户端 token） |
| 实时通信 | SSE（Server-Sent Events）事件流 |
| 包管理 | 后端 `uv` · 前端 `npm` |

## 🚀 快速开始

### 1. 后端启动

```bash
cd /path/to/Customer
uv sync                          # 安装依赖
cp .env.example .env             # 复制并按需修改配置（见下方配置说明）
mysql -u root -p < schema.sql    # 初始化表结构与演示数据
uv run uvicorn app.main:app --reload
```

启动后：
- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

> `schema.sql` 会初始化默认管理员账号 **`admin / 123456`**，并写入演示订单与商品数据。**生产环境请务必删除或修改该账号。**

### 2. 管理端前端（Ant Design Pro）

```bash
cd web
npm install
npm run dev      # 开发：http://127.0.0.1:8001（已关闭 mock，直连后端）
npm run build    # 生产构建
```

后端地址通过 `web/.env` 的 `UMI_APP_API_BASE` 配置（默认 `http://127.0.0.1:8000`）。前端开发端口固定为 `8001`，避开后端 `8000`。

### 3. 客户端挂件（独立嵌入）

```bash
cd widget
npm install
npm run dev      # 开发：http://127.0.0.1:5173，可嵌入任意页面测试
npm run build    # 生产构建为单个 JS 文件
```

嵌入方式（生产环境）：
```html
<!-- 在目标页面引入构建产物 -->
<script src="https://your-cdn.com/widget.js"></script>
<div id="aics-widget"></div>
```

挂件会自动处理匿名访客、注册、登录、会话恢复逻辑，零配置接入。

## ⚙️ 配置

所有后端配置通过环境变量读取，完整清单见 [`.env.example`](.env.example)。常用项：

### 必填配置
| 变量 | 说明 | 示例 |
|---|---|---|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | MySQL 连接配置 | `localhost` / `3306` / `root` / `password` / `ai_customer` |
| `REDIS_URL` | Redis 连接 URL（用于上下文缓存 + 客户端 token） | `redis://localhost:6379/0` |

### AI 模型配置
| 变量 | 说明 | 默认 |
|---|---|---|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 大模型服务；留空则走本地兜底回答 | 空 |
| `EMBEDDING_BACKEND` | `hash`（本地占位）或 `sentence_transformers`（`bge-m3`） | `hash` |
| `VECTOR_BACKEND` | `memory`（仅本地开发）或 `milvus` | `memory` |

> ⚠️ 默认 `EMBEDDING_BACKEND=hash` 为无语义的本地占位向量，召回质量较差，**生产请设置为 `sentence_transformers`**。

### 业务配置
| 变量 | 说明 | 默认 |
|---|---|---|
| `REDIS_CONTEXT_TTL_SECONDS` | Redis 上下文缓存过期时间（秒） | `3600` |
| `CHAT_CONTEXT_LIMIT` | 每次问答携带的历史消息条数 | `10` |
| `AGENT_MAX_TOOL_ROUNDS` | Agent 单次问答最大工具调用轮数 | `3` |
| `CORS_ALLOW_ORIGINS` | 允许跨域来源（逗号分隔），生产应收紧 | `*` |
| `CUSTOMER_TOKEN_EXPIRE_DAYS` | 客户端 token 有效期（天） | `30` |

## 🧩 API 概览

### 客户端（C 端，`/customer` 前缀）
| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/customer/visitor` | 领取匿名访客身份（返回 token） |
| `POST` | `/customer/register` | 注册（携匿名 token 则就地升级） |
| `POST` | `/customer/login` | 登录（自动合并当前匿名会话） |
| `POST` | `/customer/logout` | 登出（前端回落匿名） |
| `GET` | `/customer/me` | 获取当前客户信息 |
| `POST` | `/customer/chat` | 非流式问答（兼容接口） |
| `GET` | `/customer/chat/stream` | SSE 流式问答（推荐） |
| `GET` | `/customer/conversations` | 当前客户的会话列表 |
| `POST` | `/customer/conversations/{id}/handoff` | 转人工 |
| `POST` | `/customer/conversations/{id}/rating` | 满意度评分 |
| `POST` | `/customer/conversations/{id}/messages` | 客户发送消息（人工模式） |
| `GET` | `/customer/conversations/{id}/messages` | 查看会话历史 |
| `GET` | `/customer/conversations/{id}/events` | 订阅会话事件流（SSE，接收坐席消息） |

### 坐席端（B 端，`/agent` 前缀，需登录）
| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/agent/conversations` | 查看待接入/进行中会话列表 |
| `POST` | `/agent/conversations/{id}/serve` | 坐席接入会话 |
| `POST` | `/agent/conversations/{id}/close` | 关闭会话 |
| `POST` | `/agent/conversations/{id}/messages` | 坐席发送消息 |
| `GET` | `/agent/conversations/{id}/messages` | 查看会话详情与历史消息 |
| `GET` | `/agent/conversations/{id}/events` | 订阅会话事件流（SSE，接收客户消息） |

### 管理后台（`/system` 前缀，管理员权限）
| 方法 | 路径 | 说明 |
|---|---|---|
| `GET/POST/PUT/DELETE` | `/system/manager...` | 坐席管理（列表/新增/编辑/启禁用/删除） |
| `GET/POST/PUT/DELETE` | `/system/customer...` | 客户管理（列表/新增/编辑/启禁用/删除） |
| `GET/POST/PUT/DELETE` | `/system/session...` | 会话管理（列表/创建/更新/删除） |
| `GET` | `/system/message/list` | 指定会话的消息记录 |
| `GET` | `/system/llm-log/list` | LLM 调用日志（分页） |

### 知识库（需登录）
| 方法 | 路径 | 说明 |
|---|---|---|
| `POST/GET` | `/knowledge-bases` | 创建/列出知识库 |
| `POST/GET/PUT/DELETE` | `/knowledge-bases/{id}/files...` | 文件上传/列表/重传/删除 |
| `GET` | `/knowledge-bases/{id}/files/{fileId}/chunks` | 查看文件 Chunk |
| `POST` | `.../reparse` · `.../re-embedding` | 重新解析/重新 Embedding |

### 认证（`/auth` 前缀，管理端/坐席端）
| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/auth/register` · `/auth/login` · `/auth/logout` | 坐席注册/登录/注销 |
| `GET` | `/auth/me` | 当前登录坐席信息（含 `isAdmin`） |

完整交互式文档见 `/docs`（Swagger UI）。

### 示例

#### 1. 客户端问答流程（匿名访客）
```bash
# 1. 领取匿名访客身份
VISITOR_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/customer/visitor | jq -r '.data.token')

# 2. 流式问答（SSE）
curl -N "http://127.0.0.1:8000/customer/chat/stream?question=如何退货" \
  -H "Authorization: Bearer $VISITOR_TOKEN"
# 输出：
# data: {"type":"status","status":"thinking"}
# data: {"type":"delta","delta":"退货"}
# data: {"type":"delta","delta":"流程"}
# data: {"type":"done","sessionId":"xxx","references":[...]}

# 3. 转人工
curl -X POST "http://127.0.0.1:8000/customer/conversations/xxx/handoff" \
  -H "Authorization: Bearer $VISITOR_TOKEN"
```

#### 2. 管理员操作（知识库 + 坐席管理）
```bash
# 登录拿 token（默认管理员 admin / 123456）
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' | jq -r '.data.token')

# 上传文件到知识库 1
curl -X POST http://127.0.0.1:8000/knowledge-bases/1/files \
  -H "Authorization: Bearer $ADMIN_TOKEN" -F "file=@refund_rules.txt"

# 创建一个普通坐席账号（非管理员）
curl -X POST http://127.0.0.1:8000/system/manager \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"alice","password":"alice123","nickname":"Alice","isAdmin":false}'
```

#### 3. 坐席接入人工会话
```bash
# 坐席登录
AGENT_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}' | jq -r '.data.token')

# 查看待接入会话列表
curl "http://127.0.0.1:8000/agent/conversations?status=waiting" \
  -H "Authorization: Bearer $AGENT_TOKEN"

# 接入会话
curl -X POST "http://127.0.0.1:8000/agent/conversations/xxx/serve" \
  -H "Authorization: Bearer $AGENT_TOKEN"

# 发送消息给客户
curl -X POST "http://127.0.0.1:8000/agent/conversations/xxx/messages" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $AGENT_TOKEN" \
  -d '{"content":"您好，我是人工客服 Alice，请问有什么可以帮您？"}'
```

## 🤖 Agent 与工具调用

聊天流程在 RAG 检索之外，通过 `AgentExecutor` 驱动 OpenAI 兼容 Function Calling 的多轮工具循环：

```
客户问题 → RAG 检索知识库 → AgentExecutor（模型自主选工具 → 执行 → 回传结果 → 再问模型，最多 N 轮）
        → 工具结果 + 知识库片段 + 历史上下文 → 大模型生成客服回答
```

**工具体系**：
- 工具实现 `ChatTool` 协议（`app/tools/`），注册在 `app/dependencies.py` 的 `get_tool_registry()`
- 新增业务能力只需新增工具类并注册，无需修改执行器
- 所有客户私有数据（如订单）查询强制携带 `customer_id` 隔离；商品目录为全局数据
- 最大工具轮数由 `AGENT_MAX_TOOL_ROUNDS` 配置，超出后强制收敛为一次普通回答

**内置工具**：
| 工具 | 功能 | 数据隔离 |
|---|---|---|
| `OrderQueryTool` | 查询客户订单状态、物流、金额 | 按 `customer_id` 隔离 |
| `ProductQueryTool` | 查询商品价格、库存、描述 | 全局商品目录 |

**新增工具示例**：
```python
# app/tools/coupon_tool.py
from app.tools.base import ChatTool, ToolExecution

class CouponQueryTool(ChatTool):
    @property
    def name(self) -> str:
        return "query_coupon"
    
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "query_coupon",
                "description": "查询客户可用优惠券",
                "parameters": {"type": "object", "properties": {...}}
            }
        }
    
    def can_handle(self, tool_name: str) -> bool:
        return tool_name == "query_coupon"
    
    def call(self, customer_id: int, **kwargs) -> ToolExecution:
        # 实现查询逻辑，强制携带 customer_id 隔离
        coupons = self.repository.get_customer_coupons(customer_id)
        return ToolExecution(content=json.dumps(coupons, ensure_ascii=False))

# app/dependencies.py
def get_tool_registry() -> list[ChatTool]:
    return [OrderQueryTool(...), ProductQueryTool(...), CouponQueryTool(...)]
```

## 🧪 测试

```bash
uv run pytest
```

覆盖 `AgentExecutor` 工具循环、订单/商品工具、认证服务、RAG 上下文选择、聊天编排等。

## 📁 项目结构

```text
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
├── AGENTS.md               # AI 开发助手工作规范（CLAUDE.md 为其软链接）
├── ROADMAP.md              # 架构概览与功能计划
└── .env.example            # 环境变量模板
```

## 🗺️ Roadmap

规划与已完成能力见 [ROADMAP.md](ROADMAP.md)。

## 📝 开发指南

贡献代码前请阅读 [AGENTS.md](AGENTS.md)（AI 开发助手规范，`CLAUDE.md` 为其软链接）。

**核心约定**：
- **严格分层**：路由层 → 业务层 → 数据层，禁止跨层调用
- **类型安全**：所有函数必须有类型注解，ORM 查询结果通过 `mappers.py` 转为 frozen dataclass
- **数据隔离**：客户私有数据查询强制携带 `customer_id`，工具调用必须透传身份参数
- **软删除**：会话/订单/客户/坐席通过 `deleted_at` 标记删除（`NULL` 表示未删除）
- **测试覆盖**：新增 API 必须补充测试用例（`tests/` 目录）

**新增功能流程**：
1. 更新 `schema.sql`（如涉及数据库变更），并对已有库执行 `ALTER`
2. 在 `app/repositories/mysql/` 实现数据访问（ORM mixin + records + mappers）
3. 在 `app/schemas/` 定义 Pydantic 模型
4. 在 `app/services/` 实现业务逻辑
5. 在 `app/api/` 创建路由，并在 `app/main.py` 注册
6. 前端对接（`web/` 或 `widget/`）
7. 补充测试用例

## 🤝 贡献

欢迎提交 Issue 与 PR！开发约定见 [AGENTS.md](AGENTS.md)（`CLAUDE.md` 为其软链接，供 Claude Code 自动加载）。

## 🙏 致谢

本项目使用了以下开源技术：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Ant Design Pro](https://pro.ant.design/) - 企业级 React 中后台框架
- [Milvus](https://milvus.io/) - 开源向量数据库
- [bge-m3](https://huggingface.co/BAAI/bge-m3) - 高质量中文 Embedding 模型

## 📄 License

本项目基于 [MIT](LICENSE) 协议开源。
