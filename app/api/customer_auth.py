"""客户端（对外 AI 客服）认证接口模块。"""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import (
    get_bearer_token,
    get_client_ip,
    get_current_customer,
    get_customer_auth_service,
    get_optional_bearer_token,
    get_optional_customer,
)
from app.repositories.mysql.records import CustomerRecord
from app.schemas.customer import (
    CustomerAuthResponse,
    CustomerLoginRequest,
    CustomerRegisterRequest,
    CustomerResponse,
    VisitorResponse,
)
from app.services.customer_auth_service import CustomerAuthService

router = APIRouter(prefix="/customer", tags=["customer"])


@router.post("/visitor")
def create_visitor(service: CustomerAuthService = Depends(get_customer_auth_service)) -> dict[str, Any]:
    """领取匿名访客身份，返回客户端后续请求需要携带的 token。

    Args:
        service: 当前接口注入的客户认证服务实例。
    """
    result = service.create_visitor()
    response = VisitorResponse(
        token=result.token,
        access_token=result.token,
        customer=_to_customer_response(result.customer),
    )
    return success_response(data=response.model_dump(), message="欢迎咨询")


@router.post("/register")
def register(
    request: CustomerRegisterRequest,
    current: CustomerRecord | None = Depends(get_optional_customer),
    current_token: str | None = Depends(get_optional_bearer_token),
    service: CustomerAuthService = Depends(get_customer_auth_service),
) -> dict[str, Any]:
    """客户端注册：携匿名 token 则就地升级该行，否则新建注册客户。

    Args:
        request: 当前接口接收的注册请求体。
        current: 来访的当前客户（匿名访客或 None）。
        current_token: 来访携带的客户端 token，可空。
        service: 当前接口注入的客户认证服务实例。
    """
    result = run_with_value_error(
        lambda: service.register(request.username, request.password, request.nickname, current, current_token),
        status.HTTP_400_BAD_REQUEST,
    )
    response = CustomerAuthResponse(
        token=result.token,
        access_token=result.token,
        customer=_to_customer_response(result.customer),
    )
    return success_response(data=response.model_dump(), message="注册成功")


@router.post("/login")
def login(
    request: CustomerLoginRequest,
    current: CustomerRecord | None = Depends(get_optional_customer),
    client_ip: str | None = Depends(get_client_ip),
    service: CustomerAuthService = Depends(get_customer_auth_service),
) -> dict[str, Any]:
    """客户端登录：校验账号密码，携匿名身份时合并当前会话到该账号。

    Args:
        request: 当前接口接收的登录请求体。
        current: 来访的当前客户（匿名访客或 None）。
        client_ip: 来访真实 IP，记录到 last_login_ip。
        service: 当前接口注入的客户认证服务实例。
    """
    result = run_with_value_error(
        lambda: service.login(request.username, request.password, current, client_ip),
        status.HTTP_400_BAD_REQUEST,
    )
    response = CustomerAuthResponse(
        token=result.token,
        access_token=result.token,
        customer=_to_customer_response(result.customer),
    )
    return success_response(data=response.model_dump(), message="登录成功")


@router.post("/logout")
def logout(
    token: str = Depends(get_bearer_token),
    service: CustomerAuthService = Depends(get_customer_auth_service),
) -> dict[str, Any]:
    """客户端登出：撤销当前 token，前端随后回落匿名身份。

    Args:
        token: 当前客户端登录凭证 token。
        service: 当前接口注入的客户认证服务实例。
    """
    service.logout(token)
    return success_response(message="已退出登录")


@router.get("/me")
def me(customer: CustomerRecord = Depends(get_current_customer)) -> dict[str, Any]:
    """获取当前客户信息，供客户端刷新后恢复会话身份。

    Args:
        customer: 当前客户端登录的客户记录。
    """
    return success_response(data=_to_customer_response(customer).model_dump(), message="获取成功")


def _to_customer_response(customer: CustomerRecord) -> CustomerResponse:
    """将客户记录转换为客户端响应模型。

    Args:
        customer: 客户数据库记录。
    """
    return CustomerResponse(
        customerId=customer.id,
        customerNo=customer.customer_no,
        username=customer.username,
        nickname=customer.nickname,
        avatar=customer.avatar,
        isAnonymous=bool(customer.is_anonymous),
        source=customer.source,
        lastLoginAt=customer.last_login_at,
    )
