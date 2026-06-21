"""管理员认证接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import get_auth_service, get_bearer_token, get_current_manager
from app.repositories.mysql.records import ManagerRecord
from app.schemas.auth import (
    LoginManager,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: LoginRequest, service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    """处理管理员登录请求，并返回前端需要保存的访问令牌。

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
        userInfo=_to_login_manager(result.manager),
    )
    return success_response(data=response.model_dump(), message="登录成功")


@router.post("/register")
def register(request: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    """处理管理员注册请求，成功后返回新管理员基础信息。

    Args:
        request: 当前接口接收的请求体或请求对象。
        service: 当前接口注入的业务服务实例。
    """
    manager = run_with_value_error(
        lambda: service.register(request.username, request.password, request.confirmPassword),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data=_to_login_manager(manager).model_dump(), message="注册成功")


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
def me(manager: ManagerRecord = Depends(get_current_manager)) -> dict[str, Any]:
    """获取当前登录管理员信息，供前端刷新页面后恢复登录态。

    Args:
        manager: 当前登录管理员记录。
    """
    return success_response(data=_to_login_manager(manager).model_dump(), message="获取成功")


@router.put("/profile")
def update_profile(
    request: ProfileUpdateRequest,
    manager: ManagerRecord = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """当前登录管理员自助更新昵称与头像。

    Args:
        request: 当前接口接收的请求体或请求对象。
        manager: 当前登录管理员记录。
        service: 当前接口注入的业务服务实例。
    """
    updated = run_with_value_error(
        lambda: service.update_profile(manager.id, request.nickName, request.avatar),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data=_to_login_manager(updated).model_dump(), message="更新成功")


@router.put("/password")
def change_password(
    request: PasswordChangeRequest,
    manager: ManagerRecord = Depends(get_current_manager),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """当前登录管理员自助修改密码，需校验当前密码。

    Args:
        request: 当前接口接收的请求体或请求对象。
        manager: 当前登录管理员记录。
        service: 当前接口注入的业务服务实例。
    """
    run_with_value_error(
        lambda: service.change_password(manager.id, request.oldPassword, request.newPassword),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(message="密码修改成功")


def _to_login_manager(manager: ManagerRecord) -> LoginManager:
    """将数据库管理员记录转换为认证接口的前端响应模型。

    Args:
        manager: 当前登录管理员记录。
    """
    return LoginManager(
        userId=manager.id,
        username=manager.username,
        nickName=manager.nickname or manager.username,
        avatar=manager.avatar,
        isAdmin=bool(manager.is_admin),
    )
