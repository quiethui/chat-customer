"""用户认证接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import get_auth_service, get_bearer_token, get_current_user
from app.repositories.mysql.records import UserRecord
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: LoginRequest, service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    """处理用户登录请求，并返回前端需要保存的访问令牌。

    Args:
        request: 当前接口接收的请求体或请求对象。
        service: 当前接口注入的业务服务实例。
    """
    result = run_with_value_error(
        lambda: service.login(request.username, request.password),
        status.HTTP_401_UNAUTHORIZED,
    )
    response = LoginResponse(
        token=result.token,
        access_token=result.token,
        userInfo=_to_login_user(result.user),
    )
    return success_response(data=response.model_dump(), message="登录成功")


@router.post("/register")
def register(request: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    """处理用户注册请求，成功后返回新用户基础信息。

    Args:
        request: 当前接口接收的请求体或请求对象。
        service: 当前接口注入的业务服务实例。
    """
    user = run_with_value_error(
        lambda: service.register(request.username, request.password, request.confirmPassword),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data=_to_login_user(user).model_dump(), message="注册成功")


@router.post("/logout")
def logout(token: str = Depends(get_bearer_token), service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    """退出登录，将当前 Bearer token 标记为已失效。

    Args:
        token: 认证访问令牌。
        service: 当前接口注入的业务服务实例。
    """
    service.logout(token)
    return success_response(message="退出成功")


@router.get("/me")
def me(user: UserRecord = Depends(get_current_user)) -> dict[str, Any]:
    """获取当前登录用户信息，供前端刷新页面后恢复登录态。

    Args:
        user: 当前登录用户记录。
    """
    return success_response(data=_to_login_user(user).model_dump(), message="获取成功")


def _to_login_user(user: UserRecord) -> LoginUser:
    """将数据库用户记录转换为认证接口的前端响应模型。

    Args:
        user: 当前登录用户记录。
    """
    return LoginUser(
        userId=user.id,
        username=user.username,
        nickName=user.nickname or user.username,
        avatar=user.avatar,
    )
