# AI Customer Service Web

Vue 3 + Element Plus X 前端页面，已对接当前 FastAPI 后端。

## 功能

- 用户名密码注册与登录。
- Bearer token 自动附加到请求头。
- 登录用户独立会话列表。
- 指定会话消息记录加载。
- 发送聊天消息时携带 `sessionId`，后端使用 MySQL 记录消息并使用 Redis 维护上下文。
- 文件上传调用 `POST /upload` 导入知识库。

## 运行

```bash
pnpm install
pnpm dev
```

后端地址通过 `VITE_API_URL` 配置，例如：

```env
VITE_API_URL=http://127.0.0.1:8000
```

## 构建

```bash
pnpm build
```

构建产物输出到 `web/dist`，FastAPI 启动后可通过 `/web/` 访问。
