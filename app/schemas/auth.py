"""认证接口的数据模型定义。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体，前端登录表单会提交该模型。"""

    username: str = Field(..., min_length=2, max_length=64, description="登录用户名，长度限制为 2 到 64 个字符。")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码，长度限制为 6 到 128 个字符。")


class RegisterRequest(BaseModel):
    """注册请求体，用于创建新用户。"""

    username: str = Field(..., min_length=2, max_length=64, description="新用户登录名，必须保持唯一。")
    password: str = Field(..., min_length=6, max_length=128, description="新用户密码，服务层会加盐哈希后保存。")
    confirmPassword: str | None = Field(default=None, max_length=128, description="确认密码，传入时必须与 password 一致。")
    code: str | None = Field(default=None, description="预留验证码字段，当前后端暂不校验。")


class ProfileUpdateRequest(BaseModel):
    """当前登录管理员自助更新基本信息请求体。"""

    nickName: str | None = Field(default=None, max_length=64, description="新昵称；为空表示不修改。")
    avatar: str | None = Field(default=None, max_length=500, description="头像 URL；传入空字符串表示清空头像。")


class PasswordChangeRequest(BaseModel):
    """当前登录管理员自助修改密码请求体。"""

    oldPassword: str = Field(..., min_length=6, max_length=128, description="当前密码，用于校验身份。")
    newPassword: str = Field(..., min_length=6, max_length=128, description="新密码，服务层会加盐哈希后保存。")


class LoginManager(BaseModel):
    """登录后返回给前端展示的管理员基础信息。"""

    userId: int = Field(..., description="管理员数据库主键 ID。")
    username: str = Field(..., description="登录名。")
    nickName: str | None = Field(default=None, description="昵称；为空时前端可回退展示 username。")
    avatar: str | None = Field(default=None, description="头像 URL；为空时前端展示默认头像。")
    isAdmin: bool = Field(default=False, description="是否管理员，前端据此控制管理菜单与权限。")


class LoginResponse(BaseModel):
    """登录成功响应数据。"""

    token: str = Field(..., description="登录凭证，兼容旧前端字段名。")
    access_token: str = Field(..., description="Bearer Token，前端后续请求放入 Authorization 头。")
    userInfo: LoginManager = Field(..., description="当前登录管理员信息。")
