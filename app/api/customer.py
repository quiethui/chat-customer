"""后台客户管理接口模块。列表/详情对所有登录员工开放，增删改仅管理员可操作。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import get_current_admin_manager, get_current_manager, get_customer_service
from app.repositories.mysql.records import CustomerRecord, ManagerRecord
from app.schemas.customer import (
    CustomerAdminItem,
    CustomerCreateRequest,
    CustomerListQuery,
    CustomerStatusRequest,
    CustomerUpdateRequest,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/system/customer", tags=["system-customer"])


@router.get("/list")
def list_customers(
    query: CustomerListQuery = Depends(),
    manager: ManagerRecord = Depends(get_current_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """分页查询客户列表，支持账号/状态/注册时间/登录 IP 筛选。

    Args:
        query: 后台客户列表查询参数。
        manager: 当前登录的员工。
        service: 当前接口注入的业务服务实例。
    """
    _ = manager
    items, total = service.list_customers(query)
    data = {"list": [_to_admin_item(item).model_dump() for item in items], "total": total}
    return success_response(data=data, message="获取成功")


@router.post("")
def create_customer(
    request: CustomerCreateRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """新建客户（仅管理员）。

    Args:
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    customer = run_with_value_error(
        lambda: service.create_customer(
            request.username, request.password, request.nickname, request.avatar, request.status
        ),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data=_to_admin_item(customer).model_dump(), message="创建成功")


@router.put("")
def update_customer(
    request: CustomerUpdateRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """编辑客户信息（仅管理员）。

    Args:
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    customer = service.update_customer(request.id, request.nickname, request.avatar, request.status, request.password)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    return success_response(data=_to_admin_item(customer).model_dump(), message="更新成功")


@router.put("/{customer_id}/status")
def set_customer_status(
    customer_id: int,
    request: CustomerStatusRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """启用或禁用客户（仅管理员）。

    Args:
        customer_id: 目标客户 ID。
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    customer = service.set_status(customer_id, request.status)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    return success_response(data=_to_admin_item(customer).model_dump(), message="操作成功")


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    manager: ManagerRecord = Depends(get_current_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """查询客户详情。

    Args:
        customer_id: 目标客户 ID。
        manager: 当前登录的员工。
        service: 当前接口注入的业务服务实例。
    """
    _ = manager
    customer = service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    return success_response(data=_to_admin_item(customer).model_dump(), message="获取成功")


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: CustomerService = Depends(get_customer_service),
) -> dict[str, Any]:
    """软删除客户（仅管理员）。

    Args:
        customer_id: 目标客户 ID。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    customer = service.delete_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    return success_response(message="删除成功")


def _to_admin_item(customer: CustomerRecord) -> CustomerAdminItem:
    """将客户记录转换为后台管理响应模型。

    Args:
        customer: 待转换的客户记录。
    """
    return CustomerAdminItem(
        id=customer.id,
        customerNo=customer.customer_no,
        username=customer.username,
        nickname=customer.nickname,
        avatar=customer.avatar,
        isAnonymous=bool(customer.is_anonymous),
        status=customer.status,
        source=customer.source,
        lastLoginAt=customer.last_login_at,
        lastLoginIp=customer.last_login_ip,
        createdAt=customer.created_at,
        updatedAt=customer.updated_at,
    )
