"""MySQL 查询结果对应的只读数据模型。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class UserRecord:
    """用户表记录。"""

    id: int  # 用户自增主键。
    username: str  # 用户登录名。
    password_hash: str  # 加盐哈希后的密码，不保存明文密码。
    salt: str  # 生成密码哈希时使用的随机盐。
    nickname: str | None  # 用户昵称，可能为空。
    avatar: str | None  # 用户头像地址，可能为空。
    status: int  # 用户状态，1 表示正常可登录。


@dataclass(frozen=True)
class AuthSessionRecord:
    """用户登录会话记录。"""

    id: int  # 会话自增主键。
    user_id: int  # 会话所属用户 ID。
    token: str  # 登录 token，前端以 Bearer 方式携带。
    expires_at: datetime  # token 过期时间。


@dataclass(frozen=True)
class ChatSessionRecord:
    """聊天会话表记录。"""

    id: str  # 会话 ID，使用 UUID 字符串。
    user_id: int  # 会话所属用户 ID，用于数据隔离。
    session_title: str  # 会话标题。
    session_content: str | None  # 会话摘要或首轮问题。
    remark: str | None  # 会话备注。
    created_at: datetime  # 会话创建时间。
    updated_at: datetime  # 会话最后更新时间。


@dataclass(frozen=True)
class ChatMessageRecord:
    """聊天消息表记录。"""

    id: int  # 消息自增主键。
    session_id: str  # 消息所属会话 ID。
    user_id: int  # 消息所属用户 ID，用于数据隔离。
    role: str  # 消息角色，通常为 user 或 assistant。
    content: str  # 消息正文。
    model_name: str | None  # 助手消息使用的模型名，用户消息为空。
    total_tokens: int  # token 消耗，未统计时为 0。
    references_text: str | None  # 多条引用以换行符拼接后的文本。
    created_at: datetime  # 消息创建时间。


@dataclass(frozen=True)
class OrderRecord:
    """订单表记录。"""

    id: int  # 订单自增主键。
    user_id: int  # 订单所属用户 ID，用于隔离不同用户的订单数据。
    order_no: str  # 对用户展示和查询使用的唯一订单号。
    product_name: str  # 订单商品名称，当前简化为单个主商品名称。
    product_quantity: int  # 商品购买数量。
    order_amount: Decimal  # 订单实付或应付金额。
    currency: str  # 订单金额币种，例如 CNY。
    order_status: str  # 订单状态机编码，例如 paid、shipped。
    paid_at: datetime | None  # 订单支付时间，未支付时为空。
    shipped_at: datetime | None  # 订单发货时间，未发货时为空。
    remark: str | None  # 订单备注信息。
    created_at: datetime  # 订单创建时间。
    updated_at: datetime  # 订单更新时间。


@dataclass(frozen=True)
class KnowledgeBaseRecord:
    """知识库主表记录。"""

    id: int  # 知识库自增主键。
    name: str  # 知识库名称。
    description: str | None  # 知识库描述。
    created_at: datetime  # 知识库创建时间。


@dataclass(frozen=True)
class KnowledgeFileRecord:
    """知识库文件表记录。"""

    id: int  # 文件自增主键。
    knowledge_base_id: int  # 所属知识库 ID。
    filename: str  # 用户上传的原始文件名。
    file_path: str  # 文件保存路径。
    status: str  # 文件状态：processing/active/deleted/failed。
    created_at: datetime  # 文件创建时间。


@dataclass(frozen=True)
class KnowledgeChunkRecord:
    """知识库切块表记录。"""

    id: int  # 切块自增主键。
    knowledge_base_id: int  # 所属知识库 ID。
    file_id: int  # 所属文件 ID。
    chunk_index: int  # 切块序号，从 1 开始。
    content: str  # 切块文本内容。
    vector_id: str  # 向量库中的向量业务 ID。
    created_at: datetime  # 切块创建时间。
