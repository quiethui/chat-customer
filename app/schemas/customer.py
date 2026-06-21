"""客户端（对外 AI 客服）相关数据模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerResponse(BaseModel):
    """返回给客户端展示的客户基础信息。"""

    customerId: int = Field(..., description="客户数据库主键 ID。")
    customerNo: str = Field(..., description="客户编号，全局唯一。")
    username: str | None = Field(default=None, description="登录账号；匿名访客为空。")
    nickname: str | None = Field(default=None, description="客户昵称；为空时前端展示默认值。")
    avatar: str | None = Field(default=None, description="客户头像 URL；为空时前端展示默认头像。")
    isAnonymous: bool = Field(default=True, description="是否匿名访客。")
    source: str = Field(default="web", description="客户来源渠道，例如 web、widget。")
    lastLoginAt: datetime | None = Field(default=None, description="上次登录时间；匿名访客为空。")


class VisitorResponse(BaseModel):
    """领取匿名访客身份成功后的响应数据。"""

    token: str = Field(..., description="客户端登录凭证，前端保存后放入 Authorization 头。")
    access_token: str = Field(..., description="Bearer Token，含义同 token，兼容前端字段名。")
    customer: CustomerResponse = Field(..., description="新建的匿名访客信息。")


class CustomerRegisterRequest(BaseModel):
    """客户端注册请求体。"""

    username: str = Field(..., min_length=2, max_length=64, description="登录账号，全局唯一。")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码，服务层会加盐哈希后保存。")
    nickname: str | None = Field(default=None, max_length=64, description="客户昵称，可选。")


class CustomerLoginRequest(BaseModel):
    """客户端登录请求体。"""

    username: str = Field(..., min_length=2, max_length=64, description="登录账号。")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码。")


class CustomerAuthResponse(BaseModel):
    """注册或登录成功后的响应数据。"""

    token: str = Field(..., description="客户端登录凭证，前端保存后放入 Authorization 头。")
    access_token: str = Field(..., description="Bearer Token，含义同 token，兼容前端字段名。")
    customer: CustomerResponse = Field(..., description="注册或登录命中的客户信息。")


class CustomerListQuery(BaseModel):
    """后台客户列表查询参数（作为查询字符串注入）。"""

    model_config = ConfigDict(populate_by_name=True)

    current: int = Field(default=1, ge=1, description="当前页码，从 1 开始。")
    pageSize: int = Field(default=20, ge=1, le=100, description="每页条数。")
    username: str | None = Field(default=None, description="按登录账号模糊筛选。")
    status: int | None = Field(default=None, ge=0, le=1, description="按状态筛选：1=正常，0=禁用。")
    registeredFrom: str | None = Field(default=None, description="注册时间下界（YYYY-MM-DD）。")
    registeredTo: str | None = Field(default=None, description="注册时间上界（YYYY-MM-DD）。")
    lastLoginIp: str | None = Field(default=None, description="按登录 IP 模糊筛选。")


class CustomerAdminItem(BaseModel):
    """后台客户管理接口返回给前端的客户数据。"""

    id: int = Field(..., description="客户 ID。")
    customerNo: str = Field(..., description="客户编号，全局唯一。")
    username: str | None = Field(default=None, description="登录账号；匿名访客为空。")
    nickname: str | None = Field(default=None, description="客户昵称。")
    avatar: str | None = Field(default=None, description="客户头像 URL。")
    isAnonymous: bool = Field(..., description="是否匿名访客。")
    status: int = Field(..., description="状态：1=正常，0=禁用。")
    source: str = Field(..., description="客户来源渠道。")
    lastLoginAt: datetime | None = Field(default=None, description="上次登录时间。")
    lastLoginIp: str | None = Field(default=None, description="上次登录 IP。")
    createdAt: datetime | None = Field(default=None, description="注册/创建时间。")
    updatedAt: datetime | None = Field(default=None, description="最后更新时间。")


class CustomerCreateRequest(BaseModel):
    """后台新建客户请求体。"""

    username: str = Field(..., min_length=2, max_length=64, description="登录账号，全局唯一。")
    password: str = Field(..., min_length=6, max_length=128, description="初始密码，服务层会加盐哈希后保存。")
    nickname: str | None = Field(default=None, max_length=64, description="客户昵称，可选。")
    avatar: str | None = Field(default=None, max_length=500, description="客户头像 URL，可选。")
    status: int = Field(default=1, ge=0, le=1, description="状态：1=正常，0=禁用。")


class CustomerUpdateRequest(BaseModel):
    """后台编辑客户请求体，只更新非空字段。"""

    id: int = Field(..., ge=1, description="要更新的客户 ID。")
    nickname: str | None = Field(default=None, max_length=64, description="新昵称；为空表示不修改。")
    avatar: str | None = Field(default=None, max_length=500, description="新头像 URL；为空表示不修改。")
    status: int | None = Field(default=None, ge=0, le=1, description="新状态；为空表示不修改。")
    password: str | None = Field(default=None, min_length=6, max_length=128, description="新密码；为空表示不修改。")


class CustomerStatusRequest(BaseModel):
    """启用/禁用客户请求体。"""

    status: int = Field(..., ge=0, le=1, description="目标状态：1=启用，0=禁用。")
