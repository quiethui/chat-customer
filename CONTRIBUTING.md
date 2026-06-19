# 贡献指南

感谢你对 AI Customer Service 的关注！本文档说明本地开发上手步骤与基本约定。完整的代码规范与架构约束见 [AGENTS.md](AGENTS.md)。

## 环境要求

- Python 3.11+ 与 [uv](https://github.com/astral-sh/uv)
- Node.js 18+ 与 [pnpm](https://pnpm.io/)
- MySQL 8.x、Redis（向量库本地开发可用内存模式）

## 本地开发

### 后端

```bash
uv sync                          # 安装依赖（含 dev 组）
cp .env.example .env             # 按需修改配置
mysql -u root -p < schema.sql    # 初始化表结构与演示数据
uv run uvicorn app.main:app --reload
```

### 前端

```bash
cd web
pnpm install
pnpm dev
```

## 运行测试

提交前请确保测试通过：

```bash
uv run pytest
```

新增功能或修复缺陷时，请同步补充 `tests/` 下的测试。

## 提交规范

- 遵循 [AGENTS.md](AGENTS.md) 的分层、类型注解、docstring 与数据隔离约定。
- 一个 PR 聚焦一件事；涉及数据库变更时同步更新 `schema.sql`。
- 涉及接口或功能变化时同步更新 `README.md`。
- 提交信息建议使用 [Conventional Commits](https://www.conventionalcommits.org/)（如 `feat:`、`fix:`、`docs:`、`refactor:`）。

## 提 Issue

请尽量提供：复现步骤、期望行为与实际行为、相关日志或截图、运行环境（OS / Python / Node 版本）。

## License

提交即表示你同意贡献内容以 [MIT](web/LICENSE) 协议授权。
