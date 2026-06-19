# AI Customer Service MVP

## 1. Project Goal

开发一个最小可运行的 AI 客服系统。

第一版目标：

用户输入问题后：

1. 从知识库检索相关内容
2. 调用大模型生成答案
3. 返回给用户

只实现最核心 RAG 流程。

暂不实现：

- 管理后台
- 多租户
- 复杂 Agent
- 工作流
- 权限系统

---

# 2. Tech Stack

Backend:
- Python
- FastAPI

LLM:
- OpenAI API

Embedding:
- BGE-M3

Vector Database:
- Milvus

Frontend:
- 简单 HTML 页面（后期再换 Vue）

---

# 3. MVP Features

## 3.1 Knowledge Upload

支持上传：

- txt
- md
- pdf
- docx

上传后：

- 自动解析文本
- 自动切块
- 自动生成 embedding
- 自动存入 Milvus

---

## 3.2 Chat API

用户发送问题：

```text
POST /chat
```

流程：

```text
用户问题
↓
Embedding
↓
Milvus 检索
↓
获取相关 chunks
↓
拼接 Prompt
↓
调用 OpenAI
↓
返回答案
```

---

# 4. Project Structure

```text
ai-customer-service/

├── app/
│
│   ├── main.py
│   │
│   ├── api/
│   │   ├── chat.py
│   │   └── upload.py
│   │
│   ├── rag/
│   │   ├── parser.py
│   │   ├── splitter.py
│   │   ├── embedding.py
│   │   ├── milvus_db.py
│   │   ├── retrieval.py
│   │   └── prompt.py
│   │
│   ├── llm/
│   │   └── OpenAI.py
│   │
│   ├── uploads/
│   │
│   └── utils/
│
├── requirements.txt
│
├── .env
│
├── README.md
│
└── PROJECT_PLAN.md
```

---

# 5. RAG Flow

## Step 1 Upload

上传文档：

```text
refund_rules.docx
```

---

## Step 2 Parse

提取文本：

```text
生鲜商品不支持退款
退款将在3-5个工作日到账
```

---

## Step 3 Split

切块：

```text
chunk1:
生鲜商品不支持退款

chunk2:
退款将在3-5个工作日到账
```

---

## Step 4 Embedding

使用：

```text
BAAI/bge-m3
```

生成向量。

---

## Step 5 Save

保存到 Milvus：

```json
{
  "content": "生鲜商品不支持退款",
  "embedding": [...]
}
```

---

## Step 6 Retrieval

用户问题：

```text
水果可以退款吗？
```

生成 embedding 后：

去 Milvus 检索最相近内容。

---

## Step 7 LLM

拼接 Prompt：

```text
你是商城客服。

知识库内容：
生鲜商品不支持退款。

用户问题：
水果可以退款吗？
```

调用 OpenAI。

---

## Step 8 Response

返回：

```text
您好，生鲜商品暂不支持退款。
```

---

# 6. API Design

## Upload API

```text
POST /upload
```

上传知识库文件。

---

## Chat API

```text
POST /chat
```

Request:

```json
{
  "message": "水果可以退款吗？"
}
```

Response:

```json
{
  "answer": "您好，生鲜商品暂不支持退款。"
}
```

---

# 7. Milvus Design

Collection Name:

```text
knowledge
```

Fields:

- id
- content
- embedding

---

# 8. Environment Variables

```env
OpenAI_API_KEY=

MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

# 9. Development Steps

## Phase 1

初始化 FastAPI 项目。

---

## Phase 2

实现文档上传。

---

## Phase 3

实现文本切块。

---

## Phase 4

实现 embedding。

---

## Phase 5

实现 Milvus 存储。

---

## Phase 6

实现检索。

---

## Phase 7

实现 OpenAI 调用。

---

## Phase 8

完成聊天接口。

---

# 10. Important Principles

原则：

1. 先跑通
2. 先简单
3. 不提前设计复杂架构
4. 一个功能一个功能完成
5. 先保证检索准确

---

# 11. Future Plans

后续可增加：

- Vue 前端
- 多轮对话
- Redis Memory
- 商品查询
- 订单查询
- Agent
- LangChain
- LangGraph

但第一版暂不开发。
---

# 12. User Session And Message Context Extension

本次扩展在 MVP RAG 流程上新增用户体系、消息记录和上下文能力。

## 12.1 用户登录

- 用户使用用户名和密码注册、登录。
- 登录成功后生成 Bearer token，写入 MySQL `user_sessions`。
- 前端保存 token，并在后续请求中通过 `Authorization: Bearer <token>` 区分用户会话。

## 12.2 用户消息记录

- MySQL 新增 `users`、`user_sessions`、`chat_sessions`、`chat_messages` 表。
- `chat_sessions` 保存每个用户的对话列表。
- `chat_messages` 保存每轮用户问题与助手回答。
- 初始化 SQL 放在根目录 `schema.sql`。

## 12.3 消息上下文

- Redis 保存最近上下文，key 格式：`chat:context:{user_id}:{session_id}`。
- 每次聊天先读取 Redis 上下文；缓存为空时从 MySQL 最近消息回填。
- 每次问答完成后将用户问题和助手回答同时写入 MySQL 与 Redis。

## 12.4 前端同步

- 登录弹窗改为用户名密码注册/登录。
- 会话列表改为读取 `/system/session/list`。
- 聊天记录改为读取 `/system/message/list`。
- 发送消息调用 `/chat` 时携带 `sessionId`，由后端按用户与会话隔离上下文。

---

# 13. Order Query Tool Calling Extension

本次扩展在用户会话、消息上下文和 RAG 问答基础上，新增订单查询能力。

## 13.1 目标

用户提问订单相关问题时：

1. 系统识别订单意图和订单号。
2. 按当前登录用户查询订单表。
3. 将订单结果放入 Prompt 的“业务查询结果”。
4. 大模型基于真实查询结果返回客服回复。

示例问题：

```text
查询我的最近订单
订单 OD202605280001 发货了吗？
我的订单金额是多少？
```

## 13.2 订单数据表

MySQL 新增 `user_orders` 表，初始化 SQL 放在根目录 `schema.sql`。

核心字段：

- `user_id`：订单所属用户 ID，用于用户数据隔离。
- `order_no`：订单号。
- `product_name`：订单商品名称。
- `product_sku`：商品 SKU 编码。
- `product_quantity`：商品数量。
- `order_amount`：订单金额。
- `currency`：金额币种。
- `order_status`：订单状态。
- `paid_at`：支付时间。
- `shipped_at`：发货时间。
- `receiver_name`、`receiver_phone`：收货信息脱敏字段。
- `remark`：订单备注。
- `created_at`、`updated_at`、`deleted_at`：创建、更新和软删除时间。

## 13.3 简单 Tool Calling 设计

当前不引入复杂 Agent、LangChain 或工作流，只新增轻量工具层：

```text
用户问题
↓
SimpleToolRegistry 判断是否命中工具
↓
OrderQueryTool 查询当前用户订单
↓
业务查询结果 + 知识库内容 + 历史上下文
↓
调用 OpenAI 兼容模型
↓
返回客服回答
```

代码位置：

- `app/tools/registry.py`：简单工具注册表。
- `app/tools/order_tool.py`：订单查询工具。
- `app/repositories/mysql_repository.py`：订单表查询方法 `list_user_orders`。
- `app/services/chat_service.py`：聊天流程中调用工具并拼接 Prompt。
- `app/rag/prompt.py`：Prompt 新增“业务查询结果”。

后续新增商品查询、优惠券查询等能力时，只需要新增 Tool 类并注册到 `get_tool_registry()`。

## 13.4 前端同步

- 前端仍使用现有 `/chat` 接口，不新增单独订单页面。
- 欢迎页新增订单查询示例问题，提示用户可直接在聊天框查询订单。

## 13.5 初始化演示数据

`schema.sql` 会给默认账号 `admin/admin123` 初始化两条订单：

- `OD202605280001`：智能恒温水杯，状态已发货。
- `OD202605270002`：无线降噪耳机，状态已付款。

---

# 14. Knowledge Upload Debug API Extension

本次扩展新增知识库上传调试接口，用于直接查看文档解析后的切块和 embedding 向量值。

## 14.1 目标

开发和调试知识库时，可以不进入聊天流程，直接确认：

1. 上传文件是否能被正确解析。
2. 文本切块是否符合预期。
3. 每个切块生成的向量值和向量维度。
4. 需要时仍可写入向量库并同时返回明细。

## 14.2 新增接口

- `POST /upload/chunks`：上传 `txt`、`md`、`pdf`、`docx` 文档，只返回文本切块，不写入向量库。
- `POST /upload/vectors`：上传文档，返回文本切块和 embedding 向量值，不写入向量库。
- `POST /upload/with-vectors`：上传文档，写入向量库，并返回 `document_id`、文本切块和 embedding 向量值。

## 14.3 响应结构

切块预览响应：

```json
{
  "file_name": "refund_rules.txt",
  "chunk_count": 2,
  "chunks": [
    {
      "index": 1,
      "content": "生鲜商品不支持退款",
      "char_count": 10
    }
  ]
}
```

向量预览响应：

```json
{
  "file_name": "refund_rules.txt",
  "document_id": null,
  "chunk_count": 2,
  "embedding_dimension": 384,
  "chunks": [
    {
      "index": 1,
      "content": "生鲜商品不支持退款",
      "char_count": 10,
      "vector": [0.0, 0.1]
    }
  ]
}
```

## 14.4 代码位置

- `app/api/upload.py`：新增上传调试接口。
- `app/schemas/upload.py`：新增切块和向量响应模型。
- `app/services/knowledge_service.py`：新增切块预览、向量预览和导入明细方法。
- `web/src/api/chat/index.ts`：新增前端 API 调用封装。

## 14.5 使用原则

- `/upload` 保持原有行为，只返回导入统计，供正常业务使用。
- `/upload/chunks` 和 `/upload/vectors` 不写入向量库，适合调试切块和 embedding。
- `/upload/with-vectors` 会写入向量库，适合管理后台调试导入效果。
- 向量值数据量较大，生产环境应避免在普通用户页面频繁调用。

---

# 15. Multiple Knowledge Bases Management Extension

本次扩展新增多个知识库管理能力，保持 MVP 简单实现，不引入微服务、复杂 Agent 或过度抽象。

## 15.1 目标

系统支持创建多个知识库，例如：

- 订单知识库
- 商品知识库
- 售后知识库

每个知识库可以：

1. 上传文件。
2. 查看文件列表。
3. 删除文件。
4. 重新上传文件。

## 15.2 数据库表

新增 MySQL 表：

- `knowledge_bases`：知识库主表，字段包含 `id`、`name`、`description`、`created_at`。
- `knowledge_files`：知识库文件表，字段包含 `id`、`knowledge_base_id`、`filename`、`file_path`、`status`、`created_at`。
- `knowledge_chunks`：知识库切块表，字段包含 `id`、`knowledge_base_id`、`file_id`、`chunk_index`、`content`、`vector_id`、`created_at`。

所有 chunk 必须关联：

- `knowledge_base_id`
- `file_id`

## 15.3 数据流程

上传文件：

```text
校验知识库存在
↓
保存上传文件
↓
写入 knowledge_files
↓
解析文本
↓
切块
↓
生成 embedding
↓
写入向量库
↓
写入 knowledge_chunks
```

删除文件：

```text
查询文件
↓
按 file_id 删除向量库向量
↓
删除 knowledge_chunks
↓
knowledge_files 标记 deleted
↓
删除本地文件
```

重新上传文件：

```text
校验新文件可解析切块
↓
删除旧向量和旧 chunk
↓
更新 knowledge_files 文件名和路径
↓
重新生成 embedding
↓
写入新向量和新 chunk
```

## 15.4 API

- `POST /knowledge-bases`：创建知识库。
- `GET /knowledge-bases`：获取知识库列表。
- `POST /knowledge-bases/{knowledge_base_id}/files`：上传文件。
- `GET /knowledge-bases/{knowledge_base_id}/files`：获取文件列表。
- `DELETE /knowledge-bases/{knowledge_base_id}/files/{file_id}`：删除文件。
- `PUT /knowledge-bases/{knowledge_base_id}/files/{file_id}`：重新上传文件。

## 15.5 代码位置

- `app/api/knowledge_base.py`：知识库管理接口。
- `app/schemas/knowledge_base.py`：知识库管理请求和响应模型。
- `app/services/knowledge_base_service.py`：知识库、文件、chunk 和向量的简单业务编排。
- `app/repositories/mysql_repository.py`：知识库相关 MySQL CRUD。
- `app/repositories/vector_repository.py`：新增按文件 ID 删除向量能力。
- `schema.sql`：新增知识库、文件、切块表结构和默认知识库。

---

# 16. Knowledge Chunk Management Extension

本次扩展在知识库管理页面中增加 Chunk 查看能力，并补充文件级重建操作。

## 16.1 新增能力

- 查看文件 Chunk 列表。
- 重新解析：读取已保存的原始文件，重新解析、切块、写入 MySQL chunk，并重建向量。
- 重新 embedding：保留现有 MySQL chunk 文本，只重新生成 embedding 并替换向量。

## 16.2 新增 API

- `GET /knowledge-bases/{knowledge_base_id}/files/{file_id}/chunks`
- `POST /knowledge-bases/{knowledge_base_id}/files/{file_id}/reparse`
- `POST /knowledge-bases/{knowledge_base_id}/files/{file_id}/re-embedding`

## 16.3 前端页面

知识库管理页文件表新增操作：

- `查看 Chunk`：右侧抽屉展示 chunk 序号、内容、字符数、vector_id 和创建时间。
- `重新解析`：调用后端重新解析接口。
- `重新 embedding`：调用后端重新 embedding 接口。
