# AI Customer Service

> 基于 FastAPI + Ant Design Pro（React）的 AI 智能客服系统：知识库 RAG 问答 + 多工具调用 Agent + 用户与权限管理。

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![React](https://img.shields.io/badge/React-19-61dafb)
![Ant Design Pro](https://img.shields.io/badge/Ant%20Design%20Pro-6-1677ff)
![License](https://img.shields.io/badge/License-MIT-green)

一个可运行的智能客服系统：用户上传知识库文档后，系统通过**向量检索 + 大模型生成**回答问题，并通过 **Function Calling 工具调用**接入订单查询、商品查询等业务能力。支持用户登录、会话管理、Redis 消息上下文、按用户隔离的业务数据查询，以及面向管理员的用户管理。

> **前端定位**：系统含两个前端——**客户端挂件 `widget/`（面向客户，建设中）** 嵌入电商页供终端客户咨询；**管理端 `web/`（面向坐席与运营）** 提供知识库、用户、坐席工作台等管理能力。旧 Vue 前端 `web/` 已废弃，仅留作历史参考、不再维护。

## ✨ 功能特性

- **知识库 RAG 问答**：上传 `txt`/`md`/`pdf`/`docx`，自动解析、切块、Embedding、写入向量库，检索后由大模型生成回答。
- **多知识库管理**：创建多个知识库（订单/商品/售后等），支持文件上传、列表、删除、重传、查看 Chunk、重新解析、重新 Embedding。
- **工具调用 Agent**：基于 OpenAI 兼容 Function Calling 的多轮工具调用执行器（`AgentExecutor`），内置订单查询（按用户隔离）、商品查询（全局目录）。
- **用户与权限管理**：用户表区分**管理员**与普通用户；管理员可对用户进行新增、编辑（含重置密码）、启用/禁用、删除（软删除，可在数据库恢复）。非管理员登录后**看不到用户管理菜单**，调用用户管理接口返回 `403`；禁止删除/禁用当前登录账号。
- **用户体系与上下文**：用户名密码注册/登录（Bearer Token），会话与消息持久化到 MySQL，最近上下文缓存在 Redis。
- **客户账号体系（C 端）**：终端客户支持「匿名访客 → 注册（就地升级，聊天记录零迁移）→ 登录（自动合并当前匿名会话，呈现连续对话）→ 登出（回落匿名仍可聊天）」；客户端挂件（`widget/`）提供登录/注册入口与历史会话列表，复访自动恢复最近会话。
- **后台客户管理**：管理员可分页检索（按账号 / 状态 / 注册时间 / 登录 IP）、查看详情、新建、编辑（含重置密码）、启用/禁用、软删除客户；非管理员调用返回 `403`。
- **RAG 测试模式**：`/chat` 可只返回检索命中的 chunks、相似度、最终 Prompt 和耗时，便于调试召回质量。
- **优雅降级**：未配置远程模型时走本地兜底回答；Redis 不可用时回源 MySQL。

## 🏗️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+ · FastAPI · SQLAlchemy ORM（PyMySQL 驱动） |
| 前端（当前） | React 19 · TypeScript · Ant Design Pro v6 · UmiJS Max · antd v6 · Biome（`web/`） |
| 前端（迁移前） | Vue 3 · TypeScript · Element Plus · Pinia · Vite · UnoCSS（`web/`，逐步退役） |
| LLM | OpenAI 兼容 API |
| Embedding | `BAAI/bge-m3`（可切换为本地 hash 模式） |
| 向量库 | Milvus / Milvus Lite（可切换为内存模式） |
| 存储 | MySQL（业务数据） · Redis（上下文缓存） |
| 包管理 | 后端 `uv` · 前端 `npm`（`web/`，旧 `web/` 用 `pnpm`） |

## 🚀 快速开始

### 后端

```bash
uv sync                          # 安装依赖
cp .env.example .env             # 复制并按需修改配置
mysql -u root -p < schema.sql    # 初始化表结构与演示数据
uv run uvicorn app.main:app --reload
```

启动后：

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

> `schema.sql` 会初始化默认管理员账号 **`admin / 123456`**，并写入演示订单与商品数据。**生产环境请务必删除或修改该账号。**

### 前端（Ant Design Pro · `web/`）

```bash
cd web
npm install
npm run dev      # 开发：http://127.0.0.1:8001（已关闭 mock，直连后端）
npm run build    # 生产构建
```

后端地址通过 `web/.env` 的 `UMI_APP_API_BASE` 配置（默认 `http://127.0.0.1:8000`）。前端开发端口固定为 `8001`，以避开后端默认占用的 `8000`。

> 旧 Vue 前端 `web/` 已废弃（保留作历史参考，不再维护）；新功能一律在 `web/`（管理端）与 `widget/`（客户端）开发。

## ⚙️ 配置

所有后端配置通过环境变量读取，完整清单见 [`.env.example`](.env.example)。常用项：

| 变量 | 说明 | 默认 |
|---|---|---|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | 大模型服务；留空则走本地兜底回答 | 空 |
| `EMBEDDING_BACKEND` | `hash`（本地占位）或 `sentence_transformers`（`bge-m3`） | `hash` |
| `VECTOR_BACKEND` | `memory`（仅本地开发）或 `milvus` | `memory` |
| `MYSQL_*` | MySQL 连接配置 | 见示例 |
| `REDIS_URL` / `REDIS_CONTEXT_TTL_SECONDS` / `CHAT_CONTEXT_LIMIT` | Redis 上下文缓存 | — |
| `AGENT_MAX_TOOL_ROUNDS` | Agent 单次问答最大工具调用轮数 | `3` |
| `CORS_ALLOW_ORIGINS` | 允许跨域来源（逗号分隔），生产应收紧 | `*` |

> ⚠️ 默认 `EMBEDDING_BACKEND=hash` 为无语义的本地占位向量，召回质量较差，**生产请设置为 `sentence_transformers`**。

## 🧩 API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/auth/register` · `/auth/login` · `/auth/logout` | 注册 / 登录 / 注销 |
| `GET` | `/auth/me` | 当前登录用户信息（含 `isAdmin`） |
| `POST` | `/chat` | 聊天问答（RAG + 工具调用，支持 `ragTest`） |
| `POST` | `/customer/visitor` | 领取匿名访客身份（客户端挂件） |
| `POST` | `/customer/register` · `/customer/login` · `/customer/logout` | 客户注册（携匿名 token 则就地升级）/ 登录（合并当前匿名会话）/ 登出 |
| `GET` | `/customer/conversations` | 当前客户的会话列表（复访恢复 / 历史会话） |
| `GET/POST/PUT/DELETE` | `/system/session...` | 会话列表 / 创建 / 更新 / 删除 |
| `GET` | `/system/message/list` | 指定会话的消息记录 |
| `POST/GET` | `/knowledge-bases` | 创建 / 列出知识库 |
| `POST/GET/PUT/DELETE` | `/knowledge-bases/{id}/files...` | 文件上传 / 列表 / 重传 / 删除 |
| `GET` | `/knowledge-bases/{id}/files/{fileId}/chunks` | 查看文件 Chunk |
| `POST` | `.../reparse` · `.../re-embedding` | 重新解析 / 重新 Embedding |
| `GET` | `/system/user/list` | 用户列表（**仅管理员**） |
| `POST` · `PUT` | `/system/user` | 新增 / 编辑用户（**仅管理员**） |
| `PUT` | `/system/user/{id}/status` | 启用 / 禁用用户（**仅管理员**） |
| `DELETE` | `/system/user/{id}` | 删除用户（软删除，**仅管理员**） |
| `GET` | `/system/customer/list` · `/system/customer/{id}` | 客户列表（分页+筛选）/ 详情（**仅管理员**） |
| `POST` · `PUT` | `/system/customer` | 新建 / 编辑客户（**仅管理员**） |
| `PUT` | `/system/customer/{id}/status` | 启用 / 禁用客户（**仅管理员**） |
| `DELETE` | `/system/customer/{id}` | 删除客户（软删除，**仅管理员**） |

完整交互式文档见 `/docs`（Swagger UI）。

### 示例

```bash
# 登录拿 token（默认管理员 admin / 123456）
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' | jq -r '.data.token')

# 上传文件到知识库 1
curl -X POST http://127.0.0.1:8000/knowledge-bases/1/files \
  -H "Authorization: Bearer $TOKEN" -F "file=@refund_rules.txt"

# 创建一个普通用户（仅管理员可调）
curl -X POST http://127.0.0.1:8000/system/user \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"username":"alice","password":"alice123","nickname":"Alice","isAdmin":false}'
```

## 🤖 Agent 与工具调用

聊天流程在 RAG 检索之外，通过 `AgentExecutor` 驱动 OpenAI 兼容 Function Calling 的多轮工具循环：

```
用户问题 → RAG 检索知识库 → AgentExecutor（模型自主选工具 → 执行 → 回传结果 → 再问模型，最多 N 轮）
        → 工具结果 + 知识库片段 + 历史上下文 → 大模型生成客服回答
```

- 工具实现 `ChatTool` 协议，注册在 `app/dependencies.py` 的 `get_tool_registry()`；新增能力只需新增工具类并注册。
- 所有用户私有数据（如订单）查询强制携带 `user_id` 隔离；商品目录为全局数据。
- 最大工具轮数由 `AGENT_MAX_TOOL_ROUNDS` 配置，超出后强制收敛为一次普通回答。

## 🧪 测试

```bash
uv run pytest
```

覆盖 `AgentExecutor` 工具循环、订单/商品工具、认证服务、RAG 上下文选择、聊天编排等。

## 📁 项目结构

```text
app/                    # 后端 FastAPI 应用
├── agent/              # AgentExecutor：Function Calling 多轮工具调用执行器
├── api/                # 路由层：auth / chat / knowledge_base / session / message / user
├── core/               # 配置加载与统一响应
├── llm/                # OpenAI 兼容客户端
├── rag/                # 解析、切块、Embedding、检索、Prompt
├── repositories/       # 数据访问层：mysql/（ORM mixin，含 user.py）、vector/、context（Redis）
├── schemas/            # Pydantic 请求/响应模型（含 user.py）
├── services/           # 业务编排层（含 user_service.py）
├── tools/              # Tool Calling 工具（订单、商品）
└── utils/              # 通用工具
web/                  # 前端 React 应用（Ant Design Pro，当前主力）
│   └── src/
│       ├── pages/      # 页面：knowledge（知识库）、system-user（用户管理）、user/login
│       ├── services/   # 后端接口：auth、knowledge、user
│       └── ...         # app.tsx（运行时配置）、access.ts（权限）、requestErrorConfig.ts（请求层）
web/                    # 前端 Vue 3 应用（已废弃，保留作历史参考）
tests/                  # pytest 测试
schema.sql              # MySQL 建表与演示数据
```

## 🗺️ Roadmap

规划与已完成能力见 [ROADMAP.md](ROADMAP.md)。

## 🤝 贡献

欢迎提交 Issue 与 PR，开发约定见 [AGENTS.md](AGENTS.md)（`CLAUDE.md` 为其软链接，供 Claude Code 自动加载）。

## 📄 License

本项目基于 [MIT](web/LICENSE) 协议开源。
