"""应用配置模块，从环境变量和本地 .env 文件加载运行参数。"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """应用运行时配置，所有字段都从环境变量或默认值读取。"""

    app_name: str  # FastAPI 应用标题和健康检查中展示的服务名称。
    openai_api_key: str | None  # OpenAI 兼容 API Key；为空时使用本地 fallback 回答。
    openai_base_url: str | None  # OpenAI 兼容接口地址；可指向第三方或本地模型服务。
    openai_model: str  # 聊天补全模型名称。
    embedding_backend: str  # embedding 后端，hash 表示本地轻量模式。
    embedding_model: str  # sentence_transformers 模式下加载的 embedding 模型名。
    vector_backend: str  # 向量库后端，memory 或 milvus。
    milvus_uri: str  # Milvus 服务地址或 Milvus Lite 本地文件路径。
    milvus_token: str | None  # Milvus 鉴权 token；本地或无鉴权服务可为空。
    milvus_collection: str  # 存储知识库 chunk 的 Milvus collection 名称。
    upload_dir: Path  # 上传文件在后端机器上的保存目录。
    max_upload_bytes: int  # 单个上传文件允许的最大字节数。
    chunk_size: int  # 文档切块的最大字符数。
    chunk_overlap: int  # 超长文本切块时相邻块的重叠字符数。
    top_k: int  # 向量检索返回的候选 chunk 数量。
    reference_limit: int  # 返回给前端的引用条数上限。
    reference_max_chars: int  # 单条引用展示的最大字符数。
    mysql_host: str  # MySQL 主机地址。
    mysql_port: int  # MySQL 端口。
    mysql_user: str  # MySQL 用户名。
    mysql_password: str  # MySQL 密码。
    mysql_database: str  # MySQL 数据库名。
    mysql_charset: str  # MySQL 连接字符集，默认 utf8mb4 支持 emoji。
    mysql_connect_timeout: int  # MySQL 建立连接超时时间，单位秒。
    redis_url: str  # Redis 连接 URL，用于缓存会话上下文。
    redis_context_ttl_seconds: int  # Redis 聊天上下文过期时间，单位秒。
    chat_context_limit: int  # 每个会话最多缓存的历史消息条数。
    auth_session_ttl_minutes: int  # 登录会话 token 的有效期，单位分钟。


def load_dotenv(dotenv_path: Path) -> None:
    """从本地 .env 文件加载简单的 KEY=VALUE 配置。

    Args:
        dotenv_path: 要加载的 .env 文件路径。
    """
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_settings() -> Settings:
    """从环境变量构建应用配置。"""
    root_dir = Path(__file__).resolve().parents[2]
    # 先加载项目根目录的 .env，后续 os.getenv 才能读到本地开发配置。
    load_dotenv(root_dir / ".env")
    return Settings(
        app_name=os.getenv("APP_NAME", "AI Customer Service MVP"),
        openai_api_key=_get_optional_env("OPENAI_API_KEY"),
        openai_base_url=_get_optional_env("OPENAI_BASE_URL"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_backend=os.getenv("EMBEDDING_BACKEND", "hash"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
        vector_backend=os.getenv("VECTOR_BACKEND", "memory"),
        milvus_uri=os.getenv("APP_MILVUS_URI") or os.getenv("MILVUS_URI", "http://localhost:19530"),
        milvus_token=_get_optional_env("MILVUS_TOKEN"),
        milvus_collection=os.getenv("MILVUS_COLLECTION", "customer_service_chunks"),
        upload_dir=Path(os.getenv("UPLOAD_DIR", str(root_dir / "app" / "uploads"))),
        max_upload_bytes=_get_int_env("MAX_UPLOAD_BYTES", 20 * 1024 * 1024),
        chunk_size=_get_int_env("CHUNK_SIZE", 800),
        chunk_overlap=_get_int_env("CHUNK_OVERLAP", 120),
        top_k=_get_int_env("TOP_K", 4),
        reference_limit=_get_int_env("REFERENCE_LIMIT", 3),
        reference_max_chars=_get_int_env("REFERENCE_MAX_CHARS", 240),
        mysql_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        mysql_port=_get_int_env("MYSQL_PORT", 3306),
        mysql_user=os.getenv("MYSQL_USER", "customer_service"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "customer_service"),
        mysql_database=os.getenv("MYSQL_DATABASE", "customer_service"),
        mysql_charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        mysql_connect_timeout=_get_int_env("MYSQL_CONNECT_TIMEOUT", 5),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        redis_context_ttl_seconds=_get_int_env("REDIS_CONTEXT_TTL_SECONDS", 86400),
        chat_context_limit=_get_int_env("CHAT_CONTEXT_LIMIT", 10),
        auth_session_ttl_minutes=_get_int_env("AUTH_SESSION_TTL_MINUTES", 1440),
    )


def _get_optional_env(name: str) -> str | None:
    """读取可为空的环境变量。

    Args:
        name: 环境变量名或知识库名称。
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_int_env(name: str, default: int) -> int:
    """读取整数环境变量，格式错误时返回默认值。

    Args:
        name: 环境变量名或知识库名称。
        default: 环境变量缺失或格式错误时使用的默认值。
    """
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
