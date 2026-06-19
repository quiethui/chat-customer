"""API 层异常转换工具。"""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import HTTPException, status

T = TypeVar("T")


def run_with_value_error(action: Callable[[], T], status_code: int) -> T:
    """执行业务调用，并将 ValueError 转换为 HTTPException。

    Args:
        action: 待执行的业务回调函数。
        status_code: 捕获业务异常时返回的 HTTP 状态码。
    """
    try:
        return action()
    except ValueError as error:
        raise HTTPException(status_code=status_code, detail=str(error)) from error


def run_with_service_errors(
    action: Callable[[], T],
    value_status_code: int,
    runtime_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> T:
    """执行业务调用，并将常见业务异常转换为 HTTPException。

    Args:
        action: 待执行的业务回调函数。
        value_status_code: 捕获 ValueError 时返回的 HTTP 状态码。
        runtime_status_code: 捕获 RuntimeError 时返回的 HTTP 状态码。
    """
    try:
        return action()
    except ValueError as error:
        raise HTTPException(status_code=value_status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=runtime_status_code, detail=str(error)) from error


async def async_run_with_value_error(action: Callable[[], Awaitable[T]], status_code: int) -> T:
    """异步执行业务调用，并将 ValueError 转换为 HTTPException。

    Args:
        action: 待执行的业务回调函数。
        status_code: 捕获业务异常时返回的 HTTP 状态码。
    """
    try:
        return await action()
    except ValueError as error:
        raise HTTPException(status_code=status_code, detail=str(error)) from error


async def async_run_with_service_errors(
    action: Callable[[], Awaitable[T]],
    value_status_code: int,
    runtime_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> T:
    """异步执行业务调用，并将常见业务异常转换为 HTTPException。

    Args:
        action: 待执行的业务回调函数。
        value_status_code: 捕获 ValueError 时返回的 HTTP 状态码。
        runtime_status_code: 捕获 RuntimeError 时返回的 HTTP 状态码。
    """
    try:
        return await action()
    except ValueError as error:
        raise HTTPException(status_code=value_status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=runtime_status_code, detail=str(error)) from error
