# AI Customer Service MVP

基于 FastAPI + Vue 的 AI 客服 RAG 系统。当前版本支持知识库上传、检索问答、用户登录、用户会话区分、消息记录持久化、Redis 消息上下文缓存，以及按用户隔离的订单查询 Tool Calling。

## 功能

- `POST /auth/register`：使用用户名和密码注册用户。
- `POST /auth/login`：使用用户名和密码登录，返回 Bearer token。
- `POST /auth/logout`：注销当前登录会话。
- `GET /auth/me`：获取当前登录用户信息。
- `POST /upload`：上传 `txt`、`md`、`pdf`、`docx` 文档并写入向量库。
- `POST /upload/chunks`：上传知识库文档，直接返回解析后的文本切块，不写入向量库。
- `POST /upload/vectors`：上传知识库文档，直接返回文本切块和 embedding 向量值，不写入向量库。
- `POST /upload/with-vectors`：上传知识库文档，写入向量库后返回文本切块和 embedding 向量值。
- `POST /knowledge-bases`：创建知识库，例如订单知识库、商品知识库、售后知识库。
- `GET /knowledge-bases`：获取知识库列表。
- `POST /knowledge-bases/{id}/files`：上传文件到指定知识库，写入 MySQL chunk 和向量库。
- `GET /knowledge-bases/{id}/files`：获取指定知识库下的文件列表。
- `DELETE /knowledge-bases/{id}/files/{fileId}`：删除文件、MySQL chunk 和对应向量。
- `PUT /knowledge-bases/{id}/files/{fileId}`：重新上传文件，先删除旧向量再写入新向量。
- `GET /knowledge-bases/{id}/files/{fileId}/chunks`：查看指定文件的 Chunk 列表。
- `POST /knowledge-bases/{id}/files/{fileId}/reparse`：按原始文件重新解析、切块并重建向量。
- `POST /knowledge-bases/{id}/files/{fileId}/re-embedding`：基于现有 Chunk 文本重新生成 embedding 并替换向量。
- `POST /chat`：提交用户问题，按用户会话读取 Redis 上下文，识别订单问题时先查询订单 Tool，再结合知识库调用大模型生成回答。
- `GET /system/session/list`：获取当前用户的聊天会话列表。
- `POST /system/session`：创建当前用户的聊天会话。
- `PUT /system/session`：更新当前用户的聊天会话标题等信息。
- `DELETE /system/session/{ids}`：删除当前用户的聊天会话。
- `GET /system/message/list?sessionId=...`：获取当前用户指定会话的消息记录。

## 快速开始

```bash
uv sync
cp .env.example .env
mysql -u root -p < schema.sql
uv run uvicorn app.main:app --reload
```

`schema.sql` 会初始化默认账号：用户名 `admin`，密码 `admin123`。生产环境请删除或修改该账号。

打开服务后访问：

- `GET http://127.0.0.1:8000/`
- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/auth/register`
- `POST http://127.0.0.1:8000/auth/login`
- `POST http://127.0.0.1:8000/upload`
- `POST http://127.0.0.1:8000/upload/chunks`
- `POST http://127.0.0.1:8000/upload/vectors`
- `POST http://127.0.0.1:8000/upload/with-vectors`
- `POST http://127.0.0.1:8000/chat`

## 数据库与缓存

- MySQL 保存用户、登录 token、会话列表和消息记录。
- MySQL `user_orders` 表保存订单号、订单金额、状态、创建时间、商品名称、支付时间、发货时间等订单信息，并通过 `user_id` 区分用户。
- MySQL `knowledge_bases`、`knowledge_files`、`knowledge_chunks` 表保存多个知识库、文件和切块信息；每个 chunk 都关联 `knowledge_base_id` 和 `file_id`。
- Redis 保存每个用户会话的最近消息上下文，key 格式为 `chat:context:{user_id}:{session_id}`。
- 初始化表结构在根目录 `schema.sql`。

## 多知识库管理

系统支持创建多个知识库，例如：

- 订单知识库
- 商品知识库
- 售后知识库

每个知识库支持上传文件、查看文件列表、删除文件、重新上传文件。上传后会解析文本、切块、生成 embedding、写入向量库，并将 chunk 信息保存到 MySQL。删除和重传会同步删除旧 MySQL chunk 和旧向量。
文件列表中还支持查看 Chunk、重新解析和重新 embedding。重新解析会读取本地原始文件重新切块并重建向量；重新 embedding 会保留当前 MySQL Chunk 文本，仅替换向量库中的向量。

## 订单查询

订单查询不新增复杂 Agent 架构，当前实现为简单 Tool Calling：

1. 用户在 `/chat` 中提问订单、物流、发货、金额等相关问题。
2. `OrderQueryTool` 从问题中识别订单意图和订单号，例如 `OD202605280001`。
3. 后端只查询当前登录用户 `user_id` 名下的 `user_orders` 数据。
4. 查询结果会进入 Prompt 的“业务查询结果”，模型据此生成客服回复。

默认初始化账号 `admin/admin123` 会写入两条演示订单，可直接提问：

- `查询我的最近订单`
- `订单 OD202605280001 发货了吗？`
- `我的订单金额是多少？`

## 知识库调试接口

为了方便查看知识库导入效果，上传模块新增三个调试型接口：

- `/upload/chunks`：只解析并切块，返回 `chunks[index, content, char_count]`，不会写入向量库。
- `/upload/vectors`：解析、切块并生成向量，返回 `embedding_dimension` 和每个切块的 `vector`，不会写入向量库。
- `/upload/with-vectors`：写入向量库，同时返回 `document_id`、切块和向量值。

注意：这些 `/upload*` 接口是调试/兼容入口，生产环境推荐使用 `/knowledge-bases/{id}/files` 管理知识库文件；写入型 legacy 上传不会关联知识库文件状态，默认聊天检索不会命中这类调试向量。向量数组可能较大，生产环境建议仅在调试或管理后台中使用这些接口。

## 环境变量

核心配置在 `.env.example` 中。

- `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`：MySQL 连接配置。
- `REDIS_URL`：Redis 连接地址。
- `REDIS_CONTEXT_TTL_SECONDS`：Redis 上下文过期时间，默认 1 天。
- `CHAT_CONTEXT_LIMIT`：每个会话缓存的上下文消息条数。
- `AUTH_SESSION_TTL_MINUTES`：登录 token 有效期。
- `OPENAI_API_KEY`：模型服务 API Key；第三方服务不要求时可留空。
- `OPENAI_BASE_URL`：第三方 OpenAI 协议地址；官方 OpenAI 留空。
- `OPENAI_MODEL`：模型名称。
- `EMBEDDING_BACKEND=hash`：默认本地 embedding。
- `EMBEDDING_BACKEND=sentence_transformers`：使用 `BAAI/bge-m3`。
- `HF_TOKEN`：可选 HuggingFace Token，仅放本地环境变量或 `.env`，不要提交真实值。
- `VECTOR_BACKEND=memory`：内存向量库，仅适合本地开发；服务重启或多进程部署会丢失向量索引。
- `VECTOR_BACKEND=milvus`：使用 Milvus 或 Milvus Lite，生产环境推荐使用。
- `MAX_UPLOAD_BYTES`：单个上传文件最大字节数，默认 20MB。
- `REFERENCE_LIMIT`、`REFERENCE_MAX_CHARS`：聊天接口参考片段展示配置。

## 前端页面

前端在 `web/` 目录，已对接当前 FastAPI 用户、会话、消息和聊天接口。
知识库管理页面为独立页面，生产构建后访问 `http://127.0.0.1:8000/web/knowledge`，本地开发访问 `http://127.0.0.1:5173/knowledge`。

```bash
cd web
pnpm install
pnpm dev
```

生产构建：

```bash
cd web
pnpm build
```

启动 FastAPI 后可访问后端托管的 `http://127.0.0.1:8000/web/`。

## API 示例

注册用户：

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456","confirmPassword":"123456"}'
```

登录：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}' | jq -r '.data.token')
```

创建会话：

```bash
SESSION_ID=$(curl -s -X POST http://127.0.0.1:8000/system/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"sessionTitle":"退款咨询","sessionContent":"水果可以退款吗？"}' | jq -r '.data.id')
```

上传文档：

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules.txt"
```

预览文档切块：

```bash
curl -X POST http://127.0.0.1:8000/upload/chunks \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules.txt"
```

预览文档切块和向量：

```bash
curl -X POST http://127.0.0.1:8000/upload/vectors \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules.txt"
```

上传并返回切块和向量：

```bash
curl -X POST http://127.0.0.1:8000/upload/with-vectors \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules.txt"
```

创建知识库：

```bash
curl -X POST http://127.0.0.1:8000/knowledge-bases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"订单知识库","description":"订单查询、订单状态、订单规则相关知识"}'
```

获取知识库列表：

```bash
curl http://127.0.0.1:8000/knowledge-bases \
  -H "Authorization: Bearer $TOKEN"
```

上传文件到知识库：

```bash
curl -X POST http://127.0.0.1:8000/knowledge-bases/1/files \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules.txt"
```

获取知识库文件列表：

```bash
curl http://127.0.0.1:8000/knowledge-bases/1/files \
  -H "Authorization: Bearer $TOKEN"
```

删除知识库文件：

```bash
curl -X DELETE http://127.0.0.1:8000/knowledge-bases/1/files/1 \
  -H "Authorization: Bearer $TOKEN"
```

重新上传知识库文件：

```bash
curl -X PUT http://127.0.0.1:8000/knowledge-bases/1/files/1 \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@refund_rules_v2.txt"
```

发起聊天：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"question\":\"水果可以退款吗？\",\"sessionId\":\"$SESSION_ID\"}"
```

RAG 测试模式：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"question\":\"水果可以退款吗？\",\"sessionId\":\"$SESSION_ID\",\"ragTest\":true}"
```

前端聊天输入框左下角有 `RAG测试` 开关。开启后 `/chat` 只返回向量检索命中的 chunks、相似度 score、chunk 内容、命中文件/知识库、最终 Prompt 和耗时，不调用大模型。

查询订单：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"question\":\"订单 OD202605280001 发货了吗？\",\"sessionId\":\"$SESSION_ID\"}"
```

## 项目结构

```text
app/
├── api/              # FastAPI 路由
├── core/             # 配置与统一响应
├── llm/              # OpenAI 客户端
├── rag/              # 解析、切块、embedding、检索、prompt、Milvus
├── repositories/     # MySQL、Redis、向量仓储
├── schemas/          # 请求响应模型
├── services/         # 业务编排
├── tools/            # 简单 Tool Calling 工具，例如订单查询
├── uploads/          # 上传文件目录
└── utils/            # 工具函数
```
