"""AI 客服 MVP 的 FastAPI 应用工厂模块。"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversation import router as conversation_router
from app.api.customer import router as customer_router
from app.api.customer_auth import router as customer_auth_router
from app.api.customer_chat import router as customer_chat_router
from app.api.knowledge_base import router as knowledge_base_router
from app.api.llm_log import router as llm_log_router
from app.api.manager import router as manager_router
from app.api.message import router as message_router
from app.api.session import router as session_router
from app.core.config import get_settings
from app.core.response import (
    generic_exception_handler,
    http_exception_handler,
    success_response,
    validation_exception_handler,
)


class SPAStaticFiles(StaticFiles):
    """为 Vue history 路由提供 index.html 回退。"""

    async def get_response(self, path: str, scope: dict[str, Any]) -> Any:
        """静态资源不存在时返回前端入口，支持刷新子路由页面。

        Args:
            path: 目标文件路径或请求路径。
            scope: 当前 ASGI 请求作用域。
        """
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    settings = get_settings()
    application = FastAPI(title=settings.app_name)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        # 带凭证的跨域请求不允许使用通配符来源，因此仅在收紧来源后才启用 credentials。
        allow_credentials="*" not in settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)
    application.include_router(auth_router)
    application.include_router(chat_router)
    application.include_router(conversation_router)
    application.include_router(customer_router)
    application.include_router(customer_auth_router)
    application.include_router(customer_chat_router)
    application.include_router(knowledge_base_router)
    application.include_router(llm_log_router)
    application.include_router(manager_router)
    application.include_router(message_router)
    application.include_router(session_router)

    @application.get("/")
    async def root() -> dict[str, Any]:
        """服务根路径，用于快速确认后端已经启动。"""
        return success_response(data={"service": settings.app_name}, message="AI 客服系统已启动")

    @application.get("/health")
    async def health_check() -> dict[str, Any]:
        """健康检查接口，部署平台可用它判断服务存活。"""
        return success_response(data={"status": "ok"})

    web_dist_dir = Path(__file__).resolve().parents[1] / "web" / "dist"
    if web_dist_dir.exists():
        application.mount("/web", SPAStaticFiles(directory=web_dist_dir, html=True), name="web")

    return application


app = create_app()
