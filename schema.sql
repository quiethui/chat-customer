CREATE DATABASE IF NOT EXISTS `customer_service`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- CREATE USER IF NOT EXISTS 'customer_service'@'%' IDENTIFIED BY 'customer_service';
-- GRANT ALL PRIVILEGES ON `customer_service`.* TO 'customer_service'@'%';

USE `customer_service`;

-- 管理员表：存储管理后台用户（管理员/坐席）的基本信息
CREATE TABLE IF NOT EXISTS `managers` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '管理员自增主键',
  `username` VARCHAR(64) NOT NULL COMMENT '管理员登录名，全局唯一，用于登录和注册判重',
  `password_hash` CHAR(64) NOT NULL COMMENT '加盐哈希后的密码（SHA-256），不保存明文',
  `salt` VARCHAR(64) NOT NULL COMMENT '生成密码哈希时使用的随机盐值（32位十六进制）',
  `nickname` VARCHAR(64) DEFAULT NULL COMMENT '管理员昵称，展示用；为空时回退展示 username',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '管理员头像 URL 地址；为空时前端展示默认头像',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '管理员状态：1=正常可登录，0=禁用',
  `is_admin` TINYINT NOT NULL DEFAULT 0 COMMENT '是否管理员：1=管理员，0=普通坐席',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '管理员注册时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '管理员信息最后更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '软删除时间；NULL=未删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_managers_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员表（管理后台用户/坐席）';

-- 管理员登录会话表：存储管理员的登录 Token 及过期时间
CREATE TABLE IF NOT EXISTS `manager_sessions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '登录会话自增主键',
  `manager_id` BIGINT UNSIGNED NOT NULL COMMENT '会话所属管理员 ID，关联 managers.id',
  `token` VARCHAR(128) NOT NULL COMMENT '登录凭证 Token，前端以 Bearer 方式携带在 Authorization 头中',
  `expires_at` DATETIME NOT NULL COMMENT 'Token 过期时间（UTC），过期后需重新登录',
  `revoked_at` DATETIME DEFAULT NULL COMMENT 'Token 撤销时间（退出登录时写入）；NULL 表示当前有效',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录会话创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_manager_sessions_token` (`token`),
  KEY `idx_manager_sessions_manager_id` (`manager_id`),
  KEY `idx_manager_sessions_expires_at` (`expires_at`),
  CONSTRAINT `fk_manager_sessions_manager_id` FOREIGN KEY (`manager_id`) REFERENCES `managers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员登录会话表（Token 管理）';

-- 客户表：对外 AI 客服的服务对象，含匿名访客与已注册客户
CREATE TABLE IF NOT EXISTS `customers` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '客户自增主键',
  `customer_no` VARCHAR(64) NOT NULL COMMENT '客户编号，全局唯一，对外展示与检索使用',
  `username` VARCHAR(64) DEFAULT NULL COMMENT '登录账号，全局唯一；匿名访客为 NULL',
  `nickname` VARCHAR(64) DEFAULT NULL COMMENT '客户昵称，展示用；匿名访客可自动生成',
  `phone` VARCHAR(32) DEFAULT NULL COMMENT '客户手机号，可空（匿名访客无）',
  `email` VARCHAR(128) DEFAULT NULL COMMENT '客户邮箱，可空',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '客户头像 URL；为空时前端展示默认头像',
  `password_hash` CHAR(64) DEFAULT NULL COMMENT '加盐哈希后的密码（SHA-256）；匿名访客为空',
  `salt` VARCHAR(64) DEFAULT NULL COMMENT '生成密码哈希使用的随机盐；匿名访客为空',
  `source` VARCHAR(32) NOT NULL DEFAULT 'web' COMMENT '客户来源渠道，例如 web、widget、app',
  `is_anonymous` TINYINT NOT NULL DEFAULT 1 COMMENT '是否匿名访客：1=匿名访客，0=已注册客户',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '客户状态：1=正常，0=禁用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '客户信息最后更新时间',
  `last_login_at` DATETIME DEFAULT NULL COMMENT '上次登录时间；匿名访客为空',
  `last_login_ip` VARCHAR(64) DEFAULT NULL COMMENT '上次登录 IP（取 X-Forwarded-For 真实 IP）',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '软删除时间；NULL=未删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_customers_customer_no` (`customer_no`),
  UNIQUE KEY `uk_customers_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户表（对外 AI 客服服务对象，含匿名访客）';

-- 客户登录会话表：存储客户端 Token 及过期时间（镜像 manager_sessions）
CREATE TABLE IF NOT EXISTS `customer_sessions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '客户会话自增主键',
  `customer_id` BIGINT UNSIGNED NOT NULL COMMENT '会话所属客户 ID，关联 customers.id',
  `token` VARCHAR(128) NOT NULL COMMENT '客户端登录凭证 Token，前端以 Bearer 方式携带在 Authorization 头中',
  `expires_at` DATETIME NOT NULL COMMENT 'Token 过期时间（UTC），过期后需重新领取身份',
  `revoked_at` DATETIME DEFAULT NULL COMMENT 'Token 撤销时间；NULL 表示当前有效',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '客户会话创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_customer_sessions_token` (`token`),
  KEY `idx_customer_sessions_customer_id` (`customer_id`),
  KEY `idx_customer_sessions_expires_at` (`expires_at`),
  CONSTRAINT `fk_customer_sessions_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户登录会话表（Token 管理，镜像 manager_sessions）';

-- 聊天会话表：存储客户的 AI 客服对话会话，并记录机器人/人工服务状态
CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` VARCHAR(64) NOT NULL COMMENT '会话 ID（UUID hex 字符串），前端用于标识一次对话',
  `customer_id` BIGINT UNSIGNED NOT NULL COMMENT '会话所属客户 ID，用于数据隔离，关联 customers.id',
  `session_title` VARCHAR(120) NOT NULL COMMENT '会话标题，通常取客户首个问题的前120个字符',
  `session_content` TEXT DEFAULT NULL COMMENT '会话摘要或客户首轮提问内容，用于会话列表预览',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '会话备注信息，客户或系统可附加的说明',
  `mode` VARCHAR(20) NOT NULL DEFAULT 'bot' COMMENT '当前服务模式：bot=机器人，agent=人工坐席',
  `status` VARCHAR(20) NOT NULL DEFAULT 'bot' COMMENT '会话状态：bot=机器人服务中，waiting=等待人工接入，serving=人工服务中，closed=已结束',
  `assigned_agent_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '当前接管坐席的管理员 ID，关联 managers.id；未接管为空',
  `last_message_at` DATETIME DEFAULT NULL COMMENT '最近一条消息时间，用于坐席队列排序',
  `rating` TINYINT DEFAULT NULL COMMENT '客户满意度评分（如 1-5）；未评价为空',
  `rating_comment` VARCHAR(500) DEFAULT NULL COMMENT '客户满意度评价文字；未评价为空',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '会话创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '会话最后更新时间（新消息写入时自动刷新）',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '会话软删除时间；NULL 表示未删除，非空表示已移入回收站',
  PRIMARY KEY (`id`),
  KEY `idx_chat_sessions_customer_updated` (`customer_id`, `updated_at`),
  KEY `idx_chat_sessions_status_last_msg` (`status`, `last_message_at`),
  CONSTRAINT `fk_chat_sessions_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_sessions_agent_id` FOREIGN KEY (`assigned_agent_id`) REFERENCES `managers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 客服聊天会话表';

-- 聊天消息表：存储会话中每一轮的客户提问、机器人回复与人工坐席消息
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息自增主键',
  `session_id` VARCHAR(64) NOT NULL COMMENT '消息所属会话 ID，关联 chat_sessions.id',
  `customer_id` BIGINT UNSIGNED NOT NULL COMMENT '消息所属客户 ID，用于数据隔离，关联 customers.id',
  `role` VARCHAR(20) NOT NULL COMMENT '消息角色（供 LLM 上下文构建）：user=客户提问，assistant=AI 回复，system=系统消息',
  `sender_type` VARCHAR(20) NOT NULL DEFAULT 'customer' COMMENT '消息发送方：customer=客户，bot=机器人，agent=人工坐席',
  `agent_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '人工消息的坐席管理员 ID，关联 managers.id；非人工消息为空',
  `content` MEDIUMTEXT NOT NULL COMMENT '消息正文内容',
  `model_name` VARCHAR(100) DEFAULT NULL COMMENT '助手回复使用的模型名称（如 gpt-4o）；其他消息为空',
  `total_tokens` INT NOT NULL DEFAULT 0 COMMENT '本条消息消耗的 token 数；当前未精确统计时为 0',
  `references_text` MEDIUMTEXT DEFAULT NULL COMMENT '助手回答的引用来源，多条引用以换行符拼接；包含知识库检索结果和工具调用结果',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_chat_messages_session_id` (`session_id`, `id`),
  KEY `idx_chat_messages_customer_id` (`customer_id`),
  CONSTRAINT `fk_chat_messages_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_messages_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_messages_agent_id` FOREIGN KEY (`agent_id`) REFERENCES `managers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 客服聊天消息表';

-- 订单表：存储客户的订单信息，供 AI 客服工具查询（表名保留 user_orders）
CREATE TABLE IF NOT EXISTS `user_orders` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单自增主键',
  `customer_id` BIGINT UNSIGNED NOT NULL COMMENT '订单所属客户 ID，用于区分不同客户的订单数据，关联 customers.id',
  `order_no` VARCHAR(64) NOT NULL COMMENT '订单号，对用户展示并支持按订单号查询，全局唯一',
  `product_name` VARCHAR(255) NOT NULL COMMENT '订单商品名称，当前保存订单中的主商品名称',
  `product_sku` VARCHAR(100) DEFAULT NULL COMMENT '商品SKU编码，可用于后续对接商品系统',
  `product_quantity` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '商品购买数量',
  `order_amount` DECIMAL(10,2) NOT NULL COMMENT '订单金额（实付/应付），保留两位小数',
  `currency` VARCHAR(10) NOT NULL DEFAULT 'CNY' COMMENT '订单金额币种，默认人民币 CNY',
  `order_status` VARCHAR(32) NOT NULL COMMENT '订单状态：pending_payment=待付款，paid=已付款，shipped=已发货，completed=已完成，cancelled=已取消，refunded=已退款',
  `paid_at` DATETIME DEFAULT NULL COMMENT '订单支付时间；未支付时为空',
  `shipped_at` DATETIME DEFAULT NULL COMMENT '订单发货时间；未发货时为空',
  `receiver_name` VARCHAR(64) DEFAULT NULL COMMENT '收货人姓名，用于客服核对订单',
  `receiver_phone` VARCHAR(32) DEFAULT NULL COMMENT '收货人手机号（脱敏值，如 138****0001），用于客服核对订单',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '订单备注信息，如物流说明、发货备注等',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '订单创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '订单最后更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '订单软删除时间；NULL 表示未删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_orders_order_no` (`order_no`),
  KEY `idx_user_orders_customer_created` (`customer_id`, `created_at`),
  KEY `idx_user_orders_customer_status` (`customer_id`, `order_status`),
  CONSTRAINT `fk_user_orders_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表（供 AI 客服工具调用查询）';

-- 商品表：全局商品目录（非用户私有），供 AI 客服查询商品价格、库存、规格等
CREATE TABLE IF NOT EXISTS `products` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '商品自增主键',
  `product_sku` VARCHAR(100) NOT NULL COMMENT '商品SKU编码，全局唯一，可与订单 product_sku 关联',
  `name` VARCHAR(255) NOT NULL COMMENT '商品名称',
  `category` VARCHAR(64) DEFAULT NULL COMMENT '商品类目，例如 数码配件、办公家居',
  `price` DECIMAL(10,2) NOT NULL COMMENT '商品售价（应付），保留两位小数',
  `currency` VARCHAR(10) NOT NULL DEFAULT 'CNY' COMMENT '售价币种，默认人民币 CNY',
  `stock` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '商品库存数量',
  `status` VARCHAR(32) NOT NULL DEFAULT 'on_sale' COMMENT '商品状态：on_sale=在售，off_shelf=已下架，sold_out=已售罄',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '商品简介，供客服回答商品咨询',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '商品创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '商品最后更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '商品软删除时间；NULL 表示未删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_products_sku` (`product_sku`),
  KEY `idx_products_name` (`name`),
  KEY `idx_products_category` (`category`),
  KEY `idx_products_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品表（供 AI 客服工具调用查询）';

-- 知识库主表：支持订单知识库、商品知识库、售后知识库等多个知识库
CREATE TABLE IF NOT EXISTS `knowledge_bases` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '知识库自增主键',
  `name` VARCHAR(100) NOT NULL COMMENT '知识库名称，例如订单知识库、商品知识库、售后知识库',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '知识库描述，用于说明该知识库的业务范围',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '知识库创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_knowledge_bases_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库主表';

-- 知识库文件表：记录每个知识库下上传的原始文件
CREATE TABLE IF NOT EXISTS `knowledge_files` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '文件自增主键',
  `knowledge_base_id` BIGINT UNSIGNED NOT NULL COMMENT '所属知识库 ID，关联 knowledge_bases.id',
  `filename` VARCHAR(255) NOT NULL COMMENT '用户上传的原始文件名',
  `file_path` VARCHAR(1000) NOT NULL COMMENT '文件保存路径，用于重新解析或排查问题',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '文件状态：processing=处理中，active=可用，deleted=已删除，failed=处理失败',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '文件创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_knowledge_files_base_id` (`knowledge_base_id`),
  CONSTRAINT `fk_knowledge_files_base_id` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库文件表';

-- 知识库切块表：保存文件解析切块后的文本，所有 chunk 必须关联知识库和文件
CREATE TABLE IF NOT EXISTS `knowledge_chunks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '切块自增主键',
  `knowledge_base_id` BIGINT UNSIGNED NOT NULL COMMENT '所属知识库 ID，关联 knowledge_bases.id',
  `file_id` BIGINT UNSIGNED NOT NULL COMMENT '所属文件 ID，关联 knowledge_files.id',
  `chunk_index` INT UNSIGNED NOT NULL COMMENT '切块序号，从 1 开始',
  `content` MEDIUMTEXT NOT NULL COMMENT '切块文本内容',
  `vector_id` VARCHAR(128) NOT NULL COMMENT '向量库中的业务向量 ID，用于删除和重传时定位向量',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '切块创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_knowledge_chunks_base_file` (`knowledge_base_id`, `file_id`),
  KEY `idx_knowledge_chunks_vector_id` (`vector_id`),
  CONSTRAINT `fk_knowledge_chunks_base_id` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_knowledge_chunks_file_id` FOREIGN KEY (`file_id`) REFERENCES `knowledge_files` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库切块表';

-- 大模型请求日志表：记录每次调用 OpenAI 兼容接口的请求参数与响应数据，供排查和审计
CREATE TABLE IF NOT EXISTS `llm_request_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志自增主键',
  `model` VARCHAR(100) NOT NULL COMMENT '本次请求使用的模型名称',
  `base_url` VARCHAR(500) DEFAULT NULL COMMENT 'OpenAI 兼容接口基础地址，便于区分不同模型服务来源',
  `request_payload` MEDIUMTEXT NOT NULL COMMENT '完整请求参数 JSON，包含 model、messages、temperature、tools 等',
  `response_payload` MEDIUMTEXT DEFAULT NULL COMMENT '完整响应数据 JSON（model_dump 结果）；请求失败时为空',
  `prompt_tokens` INT UNSIGNED DEFAULT NULL COMMENT '提示词消耗 token 数，取自响应 usage；缺失时为空',
  `completion_tokens` INT UNSIGNED DEFAULT NULL COMMENT '补全消耗 token 数，取自响应 usage；缺失时为空',
  `total_tokens` INT UNSIGNED DEFAULT NULL COMMENT '本次请求总消耗 token 数，取自响应 usage；缺失时为空',
  `latency_ms` INT UNSIGNED DEFAULT NULL COMMENT '请求往返耗时（毫秒）',
  `status` VARCHAR(20) NOT NULL DEFAULT 'success' COMMENT '请求结果：success=成功，error=失败',
  `error_message` VARCHAR(1000) DEFAULT NULL COMMENT '请求失败时的错误摘要；成功时为空',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '日志创建时间（请求发生时间）',
  PRIMARY KEY (`id`),
  KEY `idx_llm_request_logs_model_created` (`model`, `created_at`),
  KEY `idx_llm_request_logs_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大模型请求日志表（记录每次请求参数与响应）';

INSERT INTO `knowledge_bases` (`name`, `description`)
VALUES
  ('订单知识库', '订单查询、订单状态、订单规则相关知识'),
  ('商品知识库', '商品介绍、规格参数、库存说明相关知识'),
  ('售后知识库', '退款、退货、换货、保修相关知识')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

INSERT INTO `managers` (`username`, `password_hash`, `salt`, `nickname`, `status`, `is_admin`)
VALUES ('admin', '8855597499f16994bccfa99612dddfffa2bedf2ea48127c9868497575c11bff4', 'b319b5073f27d2bab5171d9ee7af0262', '管理员', 1, 1)
ON DUPLICATE KEY UPDATE `is_admin` = 1;

-- 演示客户：承载下方演示订单（全新安装时为首行 customers，id=1）；匿名访客由客户端运行时按需创建
INSERT INTO `customers` (`customer_no`, `nickname`, `phone`, `source`, `is_anonymous`, `status`)
VALUES ('CUST-DEMO-0001', '演示客户', '138****0001', 'web', 0, 1)
ON DUPLICATE KEY UPDATE `nickname` = VALUES(`nickname`);

INSERT INTO `user_orders` (
  `customer_id`, `order_no`, `product_name`, `product_sku`, `product_quantity`, `order_amount`, `currency`,
  `order_status`, `paid_at`, `shipped_at`, `receiver_name`, `receiver_phone`, `remark`, `created_at`
)
VALUES
  (1, 'OD202605280001', '智能恒温水杯', 'CUP-THERMO-001', 1, 199.00, 'CNY', 'shipped', '2026-05-28 09:18:00', '2026-05-28 15:30:00', '管理员', '138****0001', '顺丰快递已发货', '2026-05-28 09:12:00'),
  (1, 'OD202605270002', '无线降噪耳机', 'HEADSET-NC-002', 2, 599.00, 'CNY', 'paid', '2026-05-27 20:08:00', NULL, '管理员', '138****0001', '仓库正在准备发货', '2026-05-27 20:05:00'),
  (1, 'OD202605260003', '机械键盘 K8 Pro', 'KB-MECH-003', 1, 349.00, 'CNY', 'completed', '2026-05-26 14:30:00', '2026-05-26 18:00:00', '管理员', '138****0001', '已签收，客户好评', '2026-05-26 14:25:00'),
  (1, 'OD202605250004', '便携蓝牙音箱', 'SPK-BT-001', 1, 159.00, 'CNY', 'completed', '2026-05-25 10:12:00', '2026-05-25 16:45:00', '管理员', '138****0001', NULL, '2026-05-25 10:08:00'),
  (1, 'OD202605290005', 'Type-C 六合一扩展坞', 'HUB-TC-006', 1, 269.00, 'CNY', 'shipped', '2026-05-29 11:20:00', '2026-05-29 17:00:00', '管理员', '138****0001', '中通快递 751234567890', '2026-05-29 11:15:00'),
  (1, 'OD202605300006', '4K 超清显示器 27寸', 'MON-4K-027', 1, 2199.00, 'CNY', 'pending_payment', NULL, NULL, '管理员', '138****0001', NULL, '2026-05-30 08:30:00'),
  (1, 'OD202605300007', '人体工学椅 Pro', 'CHAIR-ERG-PRO', 1, 1499.00, 'CNY', 'pending_payment', NULL, NULL, '管理员', '138****0001', '预约下周配送', '2026-05-30 09:45:00'),
  (1, 'OD202605240008', '无线鼠标 MX Master', 'MOUSE-MX-001', 2, 798.00, 'CNY', 'completed', '2026-05-24 16:00:00', '2026-05-25 09:30:00', '管理员', '138****0001', NULL, '2026-05-24 15:55:00'),
  (1, 'OD202605230009', '手机无线充电板', 'CHG-WL-015', 1, 89.00, 'CNY', 'completed', '2026-05-23 19:30:00', '2026-05-24 11:20:00', '管理员', '138****0001', NULL, '2026-05-23 19:25:00'),
  (1, 'OD202605220010', '氮化镓快充头 65W', 'CHG-GAN-065', 1, 129.00, 'CNY', 'completed', '2026-05-22 12:00:00', '2026-05-22 18:30:00', '管理员', '138****0001', NULL, '2026-05-22 11:55:00'),
  (1, 'OD202605210011', '大容量移动电源 2万mAh', 'BAT-PB-20K', 1, 199.00, 'CNY', 'completed', '2026-05-21 08:45:00', '2026-05-21 15:10:00', '管理员', '138****0001', NULL, '2026-05-21 08:40:00'),
  (1, 'OD202605290012', '智能手表 S3', 'WATCH-S3-001', 1, 899.00, 'CNY', 'paid', '2026-05-29 20:15:00', NULL, '管理员', '138****0001', '预计 6月1日发货', '2026-05-29 20:10:00'),
  (1, 'OD202605200013', '静音桌面风扇', 'FAN-DSK-008', 2, 178.00, 'CNY', 'completed', '2026-05-20 13:30:00', '2026-05-21 10:00:00', '管理员', '138****0001', NULL, '2026-05-20 13:25:00'),
  (1, 'OD202605190014', '护眼台灯 LED', 'LAMP-LED-003', 1, 239.00, 'CNY', 'completed', '2026-05-19 18:20:00', '2026-05-20 14:00:00', '管理员', '138****0001', NULL, '2026-05-19 18:15:00'),
  (1, 'OD202605180015', '高清摄像头 1080P', 'CAM-HD-001', 1, 369.00, 'CNY', 'cancelled', NULL, NULL, '管理员', '138****0001', '用户主动取消', '2026-05-18 22:30:00'),
  (1, 'OD202605300016', 'USB-C 数据线 2米', 'CBL-USB-2M', 3, 87.00, 'CNY', 'paid', '2026-05-30 07:00:00', NULL, '管理员', '138****0001', NULL, '2026-05-30 06:55:00'),
  (1, 'OD202605170017', '笔记本电脑支架', 'STD-LAP-002', 1, 149.00, 'CNY', 'completed', '2026-05-17 09:00:00', '2026-05-17 16:30:00', '管理员', '138****0001', NULL, '2026-05-17 08:55:00'),
  (1, 'OD202605280018', '运动毛巾 速干型', 'TWL-SPD-001', 2, 78.00, 'CNY', 'refunded', '2026-05-28 10:00:00', '2026-05-28 14:00:00', '管理员', '138****0001', '颜色不符，已退货退款', '2026-05-28 09:50:00'),
  (1, 'OD202605160019', '折叠蓝牙键盘', 'KB-FOLD-BT', 1, 199.00, 'CNY', 'completed', '2026-05-16 15:10:00', '2026-05-17 09:30:00', '管理员', '138****0001', NULL, '2026-05-16 15:05:00'),
  (1, 'OD202605300020', '迷你投影仪', 'PROJ-MINI-001', 1, 1299.00, 'CNY', 'pending_payment', NULL, NULL, '管理员', '138****0001', NULL, '2026-05-30 14:20:00'),
  (1, 'OD202605150021', '双肩电脑包 防水款', 'BAG-WP-001', 1, 259.00, 'CNY', 'completed', '2026-05-15 11:25:00', '2026-05-16 10:00:00', '管理员', '138****0001', NULL, '2026-05-15 11:20:00'),
  (1, 'OD202605140022', '多口 USB 充电站 100W', 'CHG-STN-100', 1, 349.00, 'CNY', 'completed', '2026-05-14 17:40:00', '2026-05-15 12:00:00', '管理员', '138****0001', NULL, '2026-05-14 17:35:00')
ON DUPLICATE KEY UPDATE `order_no` = VALUES(`order_no`);

-- 商品种子数据：SKU 与订单种子保持一致，便于商品/订单两个工具交叉印证
INSERT INTO `products` (
  `product_sku`, `name`, `category`, `price`, `currency`, `stock`, `status`, `description`
)
VALUES
  ('CUP-THERMO-001', '智能恒温水杯', '生活家居', 199.00, 'CNY', 320, 'on_sale', '316 不锈钢内胆，支持 APP 温度调节，续航 12 小时。'),
  ('HEADSET-NC-002', '无线降噪耳机', '数码配件', 599.00, 'CNY', 56, 'on_sale', '主动降噪，蓝牙 5.3，单次续航 8 小时，充电盒总续航 30 小时。'),
  ('KB-MECH-003', '机械键盘 K8 Pro', '数码配件', 349.00, 'CNY', 0, 'sold_out', '热插拔轴体，RGB 背光，支持有线/蓝牙双模。'),
  ('SPK-BT-001', '便携蓝牙音箱', '数码配件', 159.00, 'CNY', 210, 'on_sale', 'IPX7 防水，360 度环绕音效，续航 15 小时。'),
  ('HUB-TC-006', 'Type-C 六合一扩展坞', '数码配件', 269.00, 'CNY', 88, 'on_sale', '支持 4K HDMI 输出、PD 100W 快充、USB3.0 数据传输。'),
  ('MON-4K-027', '4K 超清显示器 27寸', '电脑外设', 2199.00, 'CNY', 24, 'on_sale', '27 英寸 4K IPS 屏，95% DCI-P3 广色域，Type-C 一线连。'),
  ('CHAIR-ERG-PRO', '人体工学椅 Pro', '办公家居', 1499.00, 'CNY', 12, 'on_sale', '可调腰托与扶手，网布透气，承重 150kg。'),
  ('MOUSE-MX-001', '无线鼠标 MX Master', '电脑外设', 399.00, 'CNY', 130, 'on_sale', '8000DPI 高精度，支持多设备切换，电磁滚轮。'),
  ('WATCH-S3-001', '智能手表 S3', '数码配件', 899.00, 'CNY', 0, 'off_shelf', '血氧心率监测，AMOLED 屏，50 米防水，已下架待换代。'),
  ('PROJ-MINI-001', '迷你投影仪', '数码配件', 1299.00, 'CNY', 18, 'on_sale', '1080P 物理分辨率，自动对焦梯形校正，内置扬声器。'),
  ('BAG-WP-001', '双肩电脑包 防水款', '生活家居', 259.00, 'CNY', 175, 'on_sale', '防泼水面料，可容纳 16 英寸笔记本，多隔层收纳。'),
  ('CHG-GAN-065', '氮化镓快充头 65W', '数码配件', 129.00, 'CNY', 460, 'on_sale', '氮化镓技术，双 C 口 + 单 A 口，支持笔记本快充。')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- =====================================================================
-- 对外 AI 客服改造（阶段 1A）：已有库升级脚本
-- ---------------------------------------------------------------------
-- 适用范围：仅当数据库已存在「旧结构」（chat_sessions/chat_messages/user_orders
--          仍为 user_id）时使用。全新安装直接 `mysql < schema.sql` 即可，无需本节。
-- 使用方法：上方已 `CREATE TABLE IF NOT EXISTS customers/customer_sessions` 并写入演示客户
--          （id=1）。请将下列语句逐行去掉行首 `-- ` 后，在已有库中按顺序执行。
-- 前提假设：旧库为演示数据，历史会话/订单均属 user_id=1，迁移后统一归到演示客户 id=1；
--          若旧库存在多个用户的历史数据，需先为这些用户补建对应 customers 行，再重建外键。
-- 依赖版本：RENAME COLUMN / RENAME INDEX 需 MySQL 8.0+。
-- =====================================================================
-- ALTER TABLE `user_orders`
--   DROP FOREIGN KEY `fk_user_orders_user_id`;
-- ALTER TABLE `user_orders`
--   RENAME COLUMN `user_id` TO `customer_id`,
--   RENAME INDEX `idx_user_orders_user_created` TO `idx_user_orders_customer_created`,
--   RENAME INDEX `idx_user_orders_user_status`  TO `idx_user_orders_customer_status`,
--   ADD CONSTRAINT `fk_user_orders_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE;
--
-- ALTER TABLE `chat_messages`
--   DROP FOREIGN KEY `fk_chat_messages_user_id`;
-- ALTER TABLE `chat_messages`
--   RENAME COLUMN `user_id` TO `customer_id`,
--   RENAME INDEX `idx_chat_messages_user_id` TO `idx_chat_messages_customer_id`,
--   ADD COLUMN `sender_type` VARCHAR(20) NOT NULL DEFAULT 'customer' COMMENT '消息发送方：customer/bot/agent' AFTER `role`,
--   ADD COLUMN `agent_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '人工消息的坐席用户 ID' AFTER `sender_type`,
--   ADD CONSTRAINT `fk_chat_messages_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
--   ADD CONSTRAINT `fk_chat_messages_agent_id` FOREIGN KEY (`agent_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;
--
-- ALTER TABLE `chat_sessions`
--   DROP FOREIGN KEY `fk_chat_sessions_user_id`;
-- ALTER TABLE `chat_sessions`
--   RENAME COLUMN `user_id` TO `customer_id`,
--   RENAME INDEX `idx_chat_sessions_user_updated` TO `idx_chat_sessions_customer_updated`,
--   ADD COLUMN `mode` VARCHAR(20) NOT NULL DEFAULT 'bot' COMMENT '服务模式：bot/agent' AFTER `remark`,
--   ADD COLUMN `status` VARCHAR(20) NOT NULL DEFAULT 'bot' COMMENT '会话状态：bot/waiting/serving/closed' AFTER `mode`,
--   ADD COLUMN `assigned_agent_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '接管坐席用户 ID' AFTER `status`,
--   ADD COLUMN `last_message_at` DATETIME DEFAULT NULL COMMENT '最近消息时间，用于坐席队列排序' AFTER `assigned_agent_id`,
--   ADD COLUMN `rating` TINYINT DEFAULT NULL COMMENT '客户满意度评分' AFTER `last_message_at`,
--   ADD COLUMN `rating_comment` VARCHAR(500) DEFAULT NULL COMMENT '客户满意度评价文字' AFTER `rating`,
--   ADD KEY `idx_chat_sessions_status_last_msg` (`status`, `last_message_at`),
--   ADD CONSTRAINT `fk_chat_sessions_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
--   ADD CONSTRAINT `fk_chat_sessions_agent_id` FOREIGN KEY (`assigned_agent_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

-- =====================================================================
-- 管理员重命名改造（阶段 1B）：users → managers
-- ---------------------------------------------------------------------
-- 适用范围：仅当数据库已存在旧的 users / user_sessions 表时使用。
--          全新安装直接 `mysql < schema.sql` 即可，无需本节。
-- 使用方法：将下列语句逐行去掉行首 `-- ` 后，在已有库中按顺序执行。
-- 依赖版本：RENAME TABLE / RENAME COLUMN / RENAME INDEX 需 MySQL 8.0+。
-- 说明：`RENAME TABLE users TO managers` 会自动把 chat_sessions / chat_messages
--      指向 users 的外键重定向到 managers，约束名（fk_chat_*_agent_id）保持不变，
--      无需重建；如需让约束名也体现 managers，可自行 DROP/ADD（非必需）。
-- =====================================================================
# -- RENAME TABLE `users` TO `managers`;
# -- ALTER TABLE `managers`
# --   RENAME INDEX `uk_users_username` TO `uk_managers_username`;
# --
-- ALTER TABLE `user_sessions`
--   DROP FOREIGN KEY `fk_user_sessions_user_id`;
-- RENAME TABLE `user_sessions` TO `manager_sessions`;
-- ALTER TABLE `manager_sessions`
--   RENAME COLUMN `user_id` TO `manager_id`,
--   RENAME INDEX `uk_user_sessions_token` TO `uk_manager_sessions_token`,
--   RENAME INDEX `idx_user_sessions_user_id` TO `idx_manager_sessions_manager_id`,
--   RENAME INDEX `idx_user_sessions_expires_at` TO `idx_manager_sessions_expires_at`,
--   ADD CONSTRAINT `fk_manager_sessions_manager_id` FOREIGN KEY (`manager_id`) REFERENCES `managers` (`id`) ON DELETE CASCADE;

-- =====================================================================
-- 客户账号体系（阶段 1）：customers 增加登录账号与登录审计列
-- ---------------------------------------------------------------------
-- 适用范围：仅当数据库已存在 customers 表但缺少 username/avatar/last_login_* 列时使用。
--          全新安装直接 `mysql < schema.sql` 即可，无需本节。
-- 使用方法：将下列语句逐行去掉行首 `-- ` 后，在已有库中执行。
-- 说明：username 唯一索引允许多个 NULL，匿名访客（username 为空）天然兼容、互不冲突。
-- =====================================================================
-- ALTER TABLE `customers`
--   ADD COLUMN `username`      VARCHAR(64)  DEFAULT NULL COMMENT '登录账号，全局唯一；匿名访客为 NULL' AFTER `customer_no`,
--   ADD COLUMN `avatar`        VARCHAR(500) DEFAULT NULL COMMENT '客户头像 URL；为空时前端展示默认头像' AFTER `email`,
--   ADD COLUMN `last_login_at` DATETIME     DEFAULT NULL COMMENT '上次登录时间；匿名访客为空' AFTER `updated_at`,
--   ADD COLUMN `last_login_ip` VARCHAR(64)  DEFAULT NULL COMMENT '上次登录 IP（取 X-Forwarded-For 真实 IP）' AFTER `last_login_at`,
--   ADD UNIQUE KEY `uk_customers_username` (`username`);
