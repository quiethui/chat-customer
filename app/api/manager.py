"""管理员管理接口模块（仅管理员可访问）。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.errors import run_with_value_error
from app.core.response import success_response
from app.dependencies import get_current_admin_manager, get_manager_service
from app.repositories.mysql.records import ManagerRecord
from app.schemas.manager import ManagerCreateRequest, ManagerResponse, ManagerStatusRequest, ManagerUpdateRequest
from app.services.manager_service import ManagerService

router = APIRouter(prefix="/system/manager", tags=["manager"])


@router.get("/list")
def list_managers(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=25, ge=1, le=100),
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: ManagerService = Depends(get_manager_service),
) -> dict[str, Any]:
    """分页查询管理员列表（仅管理员）。

    Args:
        pageNum: 前端传入的分页页码。
        pageSize: 前端传入的每页条数。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    managers, total = service.list_managers(pageNum, pageSize)
    data = {"list": [_to_response(item).model_dump() for item in managers], "total": total}
    return success_response(data=data, message="获取成功")


@router.post("")
def create_manager(
    request: ManagerCreateRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: ManagerService = Depends(get_manager_service),
) -> dict[str, Any]:
    """创建管理员（仅管理员）。

    Args:
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    manager = run_with_value_error(
        lambda: service.create_manager(request.username, request.password, request.nickname, request.isAdmin),
        status.HTTP_400_BAD_REQUEST,
    )
    return success_response(data=_to_response(manager).model_dump(), message="创建成功")


@router.put("")
def update_manager(
    request: ManagerUpdateRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: ManagerService = Depends(get_manager_service),
) -> dict[str, Any]:
    """更新管理员信息（仅管理员）。

    Args:
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    _ = admin
    manager = service.update_manager(request.id, request.nickname, request.isAdmin, request.password)
    if not manager:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return success_response(data=_to_response(manager).model_dump(), message="更新成功")


@router.put("/{manager_id}/status")
def set_manager_status(
    manager_id: int,
    request: ManagerStatusRequest,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: ManagerService = Depends(get_manager_service),
) -> dict[str, Any]:
    """启用或禁用管理员（仅管理员，禁止禁用自己）。

    Args:
        manager_id: 目标管理员 ID。
        request: 当前接口接收的请求体。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    if request.status == 0 and admin.id == manager_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用当前登录账号")
    manager = service.set_status(manager_id, request.status)
    if not manager:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return success_response(data=_to_response(manager).model_dump(), message="操作成功")


@router.delete("/{manager_id}")
def delete_manager(
    manager_id: int,
    admin: ManagerRecord = Depends(get_current_admin_manager),
    service: ManagerService = Depends(get_manager_service),
) -> dict[str, Any]:
    """软删除管理员（仅管理员，禁止删除自己）。

    Args:
        manager_id: 目标管理员 ID。
        admin: 当前登录的管理员。
        service: 当前接口注入的业务服务实例。
    """
    if admin.id == manager_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录账号")
    manager = service.delete_manager(manager_id)
    if not manager:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return success_response(message="删除成功")


def _to_response(manager: ManagerRecord) -> ManagerResponse:
    """将管理员记录转换为前端响应模型。

    Args:
        manager: 待转换的管理员记录。
    """
    return ManagerResponse(
        id=manager.id,
        username=manager.username,
        nickName=manager.nickname or manager.username,
        avatar=manager.avatar,
        status=manager.status,
        isAdmin=bool(manager.is_admin),
        createTime=manager.created_at,
        updateTime=manager.updated_at,
    )
