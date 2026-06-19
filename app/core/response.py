"""统一 API 响应和异常处理工具。"""

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def success_response(data: Any = None, message: str = "success") -> dict[str, Any]:
    """生成统一成功响应，保持 message 和 msg 两个兼容字段一致。

    Args:
        data: 响应体中携带的业务数据。
        message: 响应消息或待转换的消息记录。
    """
    return {"success": True, "code": 200, "message": message, "msg": message, "data": data}


def error_response(message: str, data: Any = None, code: int = 500) -> dict[str, Any]:
    """生成统一失败响应，供异常处理器和路由错误分支复用。

    Args:
        message: 响应消息或待转换的消息记录。
        data: 响应体中携带的业务数据。
        code: 响应体中的业务状态码。
    """
    return {"success": False, "code": code, "message": message, "msg": message, "data": data}


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """将 FastAPI/Starlette HTTPException 转换为项目统一错误格式。

    Args:
        request: 当前接口接收的请求体或请求对象。
        exc: 框架捕获到的异常对象。
    """
    _ = request
    return JSONResponse(status_code=exc.status_code, content=error_response(message=str(exc.detail), code=exc.status_code))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """将请求参数校验错误转换为统一 422 响应。

    Args:
        request: 当前接口接收的请求体或请求对象。
        exc: 框架捕获到的异常对象。
    """
    _ = request
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(message="请求参数错误", data=exc.errors(), code=status.HTTP_422_UNPROCESSABLE_ENTITY),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底处理未捕获异常，避免将内部堆栈直接暴露给前端。

    Args:
        request: 当前接口接收的请求体或请求对象。
        exc: 框架捕获到的异常对象。
    """
    _ = request
    _ = exc
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(message="服务器内部错误", code=status.HTTP_500_INTERNAL_SERVER_ERROR),
    )
