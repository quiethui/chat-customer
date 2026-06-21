"""MySQL 查询结果对应的只读数据模型。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ManagerRecord:
    """管理员（管理后台用户/坐席）表记录。"""

    id: int  # 管理员自增主键。
    username: str  # 管理员登录名。
    password_hash: str  # 加盐哈希后的密码，不保存明文密码。
    salt: str  # 生成密码哈希时使用的随机盐。
    nickname: str | None  # 管理员昵称，可能为空。
    avatar: str | None  # 管理员头像地址，可能为空。
    status: int  # 管理员状态，1 表示正常可登录。
    is_admin: int = 0  # 是否管理员，1 表示管理员，0 表示普通坐席。
    created_at: datetime | None = None  # 管理员创建时间。
    updated_at: datetime | None = None  # 管理员最后更新时间。
    deleted_at: datetime | None = None  # 软删除时间，None 表示未删除。


@dataclass(frozen=True)
class ManagerSessionRecord:
    """管理员登录会话记录。"""

    id: int  # 会话自增主键。
    manager_id: int  # 会话所属管理员 ID。
    token: str  # 登录 token，前端以 Bearer 方式携带。
    expires_at: datetime  # token 过期时间。


@dataclass(frozen=True)
class CustomerRecord:
    """客户表记录（对外 AI 客服服务对象，含匿名访客）。"""

    id: int  # 客户自增主键。
    customer_no: str  # 客户编号，全局唯一。
    nickname: str | None  # 客户昵称，可能为空。
    phone: str | None  # 客户手机号，可能为空。
    email: str | None  # 客户邮箱，可能为空。
    password_hash: str | None  # 加盐哈希密码，匿名访客为空。
    salt: str | None  # 密码哈希随机盐，匿名访客为空。
    source: str  # 客户来源渠道，例如 web。
    is_anonymous: int  # 是否匿名访客，1 表示匿名。
    status: int  # 客户状态，1 表示正常。
    created_at: datetime | None = None  # 客户创建时间。
    updated_at: datetime | None = None  # 客户最后更新时间。
    deleted_at: datetime | None = None  # 软删除时间，None 表示未删除。
    username: str | None = None  # 登录账号，全局唯一；匿名访客为空。
    avatar: str | None = None  # 客户头像 URL，可能为空。
    last_login_at: datetime | None = None  # 上次登录时间；匿名访客为空。
    last_login_ip: str | None = None  # 上次登录 IP，可能为空。


@dataclass(frozen=True)
class CustomerSessionRecord:
    """客户登录会话记录。"""

    id: int  # 会话自增主键。
    customer_id: int  # 会话所属客户 ID。
    token: str  # 登录 token，前端以 Bearer 方式携带。
    expires_at: datetime  # token 过期时间。


@dataclass(frozen=True)
class ChatSessionRecord:
    """聊天会话表记录。"""

    id: str  # 会话 ID，使用 UUID 字符串。
    customer_id: int  # 会话所属客户 ID，用于数据隔离。
    session_title: str  # 会话标题。
    session_content: str | None  # 会话摘要或首轮问题。
    remark: str | None  # 会话备注。
    created_at: datetime  # 会话创建时间。
    updated_at: datetime  # 会话最后更新时间。
    mode: str = "bot"  # 服务模式：bot/agent。
    status: str = "bot"  # 会话状态：bot/waiting/serving/closed。
    assigned_agent_id: int | None = None  # 当前接管坐席的用户 ID，未接管为空。
    last_message_at: datetime | None = None  # 最近一条消息时间，用于坐席队列排序。
    rating: int | None = None  # 客户满意度评分，未评价为空。
    rating_comment: str | None = None  # 客户满意度评价文字，未评价为空。


@dataclass(frozen=True)
class ChatMessageRecord:
    """聊天消息表记录。"""

    id: int  # 消息自增主键。
    session_id: str  # 消息所属会话 ID。
    customer_id: int  # 消息所属客户 ID，用于数据隔离。
    role: str  # 消息角色（供 LLM 上下文），通常为 user 或 assistant。
    content: str  # 消息正文。
    model_name: str | None  # 助手消息使用的模型名，其他消息为空。
    total_tokens: int  # token 消耗，未统计时为 0。
    references_text: str | None  # 多条引用以换行符拼接后的文本。
    created_at: datetime  # 消息创建时间。
    sender_type: str = "customer"  # 消息发送方：customer/bot/agent。
    agent_id: int | None = None  # 人工消息的坐席用户 ID，非人工消息为空。


@dataclass(frozen=True)
class OrderRecord:
    """订单表记录。"""

    id: int  # 订单自增主键。
    customer_id: int  # 订单所属客户 ID，用于隔离不同客户的订单数据。
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
class ProductRecord:
    """商品表记录（全局商品目录）。"""

    id: int  # 商品自增主键。
    product_sku: str  # 商品 SKU，全局唯一，可与订单 product_sku 关联。
    name: str  # 商品名称。
    category: str | None  # 商品类目，可能为空。
    price: Decimal  # 商品售价。
    currency: str  # 售价币种，例如 CNY。
    stock: int  # 商品库存数量。
    status: str  # 商品状态编码，例如 on_sale、off_shelf、sold_out。
    description: str | None  # 商品简介，可能为空。
    created_at: datetime  # 商品创建时间。
    updated_at: datetime  # 商品更新时间。


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


@dataclass(frozen=True)
class LLMRequestLogRecord:
    """大模型请求日志表记录。"""

    id: int  # 日志自增主键。
    model: str  # 本次请求使用的模型名称。
    base_url: str | None  # OpenAI 兼容接口基础地址，可能为空。
    request_payload: str  # 完整请求参数 JSON 文本。
    response_payload: str | None  # 完整响应数据 JSON 文本；失败时为空。
    prompt_tokens: int | None  # 提示词消耗 token 数，可能为空。
    completion_tokens: int | None  # 补全消耗 token 数，可能为空。
    total_tokens: int | None  # 本次请求总消耗 token 数，可能为空。
    latency_ms: int | None  # 请求往返耗时（毫秒），可能为空。
    status: str  # 请求结果状态，success 或 error。
    error_message: str | None  # 请求失败时的错误摘要，可能为空。
    created_at: datetime  # 日志创建时间。
