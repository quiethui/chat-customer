"""管理员管理接口的数据模型定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ManagerCreateRequest(BaseModel):
    """管理员后台创建管理员请求体。"""

    username: str = Field(..., min_length=2, max_length=64, description="登录名，全局唯一。")
    password: str = Field(..., min_length=6, max_length=128, description="初始密码，服务层会加盐哈希后保存。")
    nickname: str | None = Field(default=None, max_length=64, description="昵称，为空时默认使用 username。")
    isAdmin: bool = Field(default=False, description="是否管理员。")


class ManagerUpdateRequest(BaseModel):
    """管理员后台更新管理员请求体，只更新非空字段。"""

    id: int = Field(..., ge=1, description="要更新的管理员 ID。")
    nickname: str | None = Field(default=None, max_length=64, description="新昵称；为空表示不修改。")
    isAdmin: bool | None = Field(default=None, description="新的管理员标记；为空表示不修改。")
    password: str | None = Field(default=None, min_length=6, max_length=128, description="新密码；为空表示不修改。")


class ManagerStatusRequest(BaseModel):
    """启用/禁用管理员请求体。"""

    status: int = Field(..., ge=0, le=1, description="目标状态：1=启用，0=禁用。")


class ManagerResponse(BaseModel):
    """管理员管理接口返回给前端的管理员数据。"""

    id: int = Field(..., description="管理员 ID。")
    username: str = Field(..., description="登录名。")
    nickName: str | None = Field(default=None, description="昵称。")
    avatar: str | None = Field(default=None, description="头像 URL。")
    status: int = Field(..., description="状态：1=正常，0=禁用。")
    isAdmin: bool = Field(..., description="是否管理员。")
    createTime: datetime = Field(..., description="创建时间。")
    updateTime: datetime = Field(..., description="最后更新时间。")
