"""FastAPI 依赖。"""

import logging
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from app.agent import AgentExecutor
from app.core.config import Settings, get_settings
from app.db.session import create_session_factory
from app.llm.openai_client import OpenAIClient
from app.rag.embedding import HashEmbedding, create_embedding
from app.repositories.context_repository import ContextRepository, RedisContextRepository
from app.repositories.mysql.records import UserRecord
from app.repositories.mysql_repository import MySQLRepository
from app.repositories.vector import VectorRepository, create_vector_repository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.message_service import MessageService
from app.services.session_service import SessionService
from app.tools.order_tool import OrderQueryTool
from app.tools.product_tool import ProductQueryTool
from app.tools.registry import SimpleToolRegistry


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_app_settings() -> Settings:
    """返回缓存后的应用配置。"""
    return get_settings()


@lru_cache(maxsize=1)
def get_db_session_factory() -> sessionmaker[Session]:
    """返回缓存后的 SQLAlchemy Session 工厂。"""
    return create_session_factory(get_app_settings())


def get_db_session() -> Iterator[Session]:
    """创建请求级数据库 Session，并统一提交或回滚事务。"""
    session = get_db_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_mysql_repository() -> MySQLRepository:
    """创建独立事务边界的 MySQL 仓储，供后台任务使用。"""
    return MySQLRepository(get_app_settings(), get_db_session_factory()())


def get_mysql_repository(session: Session = Depends(get_db_session)) -> MySQLRepository:
    """返回请求级 MySQL 仓储。

    Args:
        session: 当前请求的数据库 Session。
    """
    return MySQLRepository(get_app_settings(), session)


@lru_cache(maxsize=1)
def get_embedding() -> HashEmbedding:
    """返回缓存后的 embedding 实例。"""
    settings = get_app_settings()
    return create_embedding(settings.embedding_backend, settings.embedding_model)


@lru_cache(maxsize=1)
def get_vector_repository() -> VectorRepository:
    """返回缓存后的向量仓储。"""
    settings = get_app_settings()
    embedding = get_embedding()
    if settings.vector_backend == "memory":
        logger.warning("VECTOR_BACKEND=memory 仅适合本地开发，服务重启或多进程部署会丢失向量索引")
    return create_vector_repository(
        settings.vector_backend,
        embedding.dimension,
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
    )


@lru_cache(maxsize=1)
def get_context_repository() -> ContextRepository:
    """返回 Redis 上下文仓储。"""
    return RedisContextRepository(get_app_settings())


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAIClient:
    """返回缓存后的 OpenAI 兼容客户端。"""
    settings = get_app_settings()
    return OpenAIClient(
        settings.openai_api_key,
        settings.openai_base_url,
        settings.openai_model,
        settings.reference_limit,
        settings.reference_max_chars,
        create_mysql_repository,
    )


def get_auth_service(repository: MySQLRepository = Depends(get_mysql_repository)) -> AuthService:
    """返回用户认证服务。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
    """
    settings = get_app_settings()
    return AuthService(repository, settings.auth_session_ttl_minutes)


def get_session_service(repository: MySQLRepository = Depends(get_mysql_repository)) -> SessionService:
    """返回聊天会话服务。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
    """
    return SessionService(repository, get_context_repository())


def get_message_service(repository: MySQLRepository = Depends(get_mysql_repository)) -> MessageService:
    """返回聊天消息服务。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
    """
    return MessageService(repository)


def get_knowledge_base_service(repository: MySQLRepository = Depends(get_mysql_repository)) -> KnowledgeBaseService:
    """返回多知识库管理服务。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
    """
    settings = get_app_settings()
    return KnowledgeBaseService(
        repository,
        get_vector_repository(),
        get_embedding(),
        settings.chunk_size,
        settings.chunk_overlap,
    )


def create_knowledge_base_service() -> KnowledgeBaseService:
    """创建独立会话的知识库服务，供后台任务使用。"""
    settings = get_app_settings()
    return KnowledgeBaseService(
        create_mysql_repository(),
        get_vector_repository(),
        get_embedding(),
        settings.chunk_size,
        settings.chunk_overlap,
    )


def process_knowledge_file_background(
    knowledge_base_id: int,
    file_id: int,
    original_name: str,
    saved_path: Path,
) -> None:
    """在后台任务中用独立数据库会话处理知识库文件。

    Args:
        knowledge_base_id: 要处理的知识库 ID。
        file_id: 上传文件记录 ID。
        original_name: 上传文件原始名称。
        saved_path: 上传文件保存路径。
    """
    service = create_knowledge_base_service()
    try:
        service.process_uploaded_file(knowledge_base_id, file_id, original_name, saved_path)
        service.mysql_repository.commit()
    except Exception:
        logger.exception("知识库后台任务失败：knowledge_base_id=%s file_id=%s path=%s", knowledge_base_id, file_id, saved_path)
        service.mysql_repository.rollback()
        raise
    finally:
        service.mysql_repository.close()


def get_tool_registry(repository: MySQLRepository = Depends(get_mysql_repository)) -> SimpleToolRegistry:
    """返回聊天工具注册表。

    当前注册订单查询、商品查询工具；后续新增业务查询能力时，在这里继续追加工具实例即可。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
    """
    return SimpleToolRegistry([OrderQueryTool(repository), ProductQueryTool(repository)])


def get_agent_executor(
    tool_registry: SimpleToolRegistry = Depends(get_tool_registry),
) -> AgentExecutor:
    """返回远程模型工具调用执行器。

    Args:
        tool_registry: 聊天工具注册表实例。
    """
    settings = get_app_settings()
    return AgentExecutor(get_llm_client(), tool_registry, settings.agent_max_tool_rounds)


def get_chat_service(
    repository: MySQLRepository = Depends(get_mysql_repository),
    tool_registry: SimpleToolRegistry = Depends(get_tool_registry),
    agent_executor: AgentExecutor = Depends(get_agent_executor),
) -> ChatService:
    """返回聊天问答服务。

    Args:
        repository: 当前请求使用的 MySQL 仓储实例。
        tool_registry: 聊天工具注册表实例。
        agent_executor: 远程模型工具调用执行器。
    """
    settings = get_app_settings()
    return ChatService(
        get_embedding(),
        get_vector_repository(),
        get_llm_client(),
        settings.top_k,
        settings.reference_limit,
        settings.reference_max_chars,
        repository,
        get_context_repository(),
        tool_registry,
        agent_executor,
    )


def get_bearer_token(request: Request) -> str:
    """从 Authorization 请求头中解析 Bearer token。

    Args:
        request: 当前接口接收的请求体或请求对象。
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证无效")
    return token.strip()


def get_current_user(token: str = Depends(get_bearer_token), service: AuthService = Depends(get_auth_service)) -> UserRecord:
    """返回当前登录用户。

    Args:
        token: 认证访问令牌。
        service: 当前接口注入的业务服务实例。
    """
    user = service.authenticate_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    return user
