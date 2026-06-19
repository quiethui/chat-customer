CREATE DATABASE IF NOT EXISTS `customer_service`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- CREATE USER IF NOT EXISTS 'customer_service'@'%' IDENTIFIED BY 'customer_service';
-- GRANT ALL PRIVILEGES ON `customer_service`.* TO 'customer_service'@'%';

USE `customer_service`;

-- 用户表：存储系统注册用户的基本信息
CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户自增主键',
  `username` VARCHAR(64) NOT NULL COMMENT '用户登录名，全局唯一，用于登录和注册判重',
  `password_hash` CHAR(64) NOT NULL COMMENT '加盐哈希后的密码（SHA-256），不保存明文',
  `salt` VARCHAR(64) NOT NULL COMMENT '生成密码哈希时使用的随机盐值（32位十六进制）',
  `nickname` VARCHAR(64) DEFAULT NULL COMMENT '用户昵称，展示用；为空时回退展示 username',
  `avatar` VARCHAR(500) DEFAULT NULL COMMENT '用户头像 URL 地址；为空时前端展示默认头像',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '用户状态：1=正常可登录，0=禁用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '用户注册时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '用户信息最后更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 用户登录会话表：存储用户的登录 Token 及过期时间
CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '登录会话自增主键',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '会话所属用户 ID，关联 users.id',
  `token` VARCHAR(128) NOT NULL COMMENT '登录凭证 Token，前端以 Bearer 方式携带在 Authorization 头中',
  `expires_at` DATETIME NOT NULL COMMENT 'Token 过期时间（UTC），过期后需重新登录',
  `revoked_at` DATETIME DEFAULT NULL COMMENT 'Token 撤销时间（退出登录时写入）；NULL 表示当前有效',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录会话创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_sessions_token` (`token`),
  KEY `idx_user_sessions_user_id` (`user_id`),
  KEY `idx_user_sessions_expires_at` (`expires_at`),
  CONSTRAINT `fk_user_sessions_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户登录会话表（Token 管理）';

-- 聊天会话表：存储用户的 AI 客服对话会话
CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` VARCHAR(64) NOT NULL COMMENT '会话 ID（UUID hex 字符串），前端用于标识一次对话',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '会话所属用户 ID，用于数据隔离，关联 users.id',
  `session_title` VARCHAR(120) NOT NULL COMMENT '会话标题，通常取用户首个问题的前120个字符',
  `session_content` TEXT DEFAULT NULL COMMENT '会话摘要或用户首轮提问内容，用于会话列表预览',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '会话备注信息，用户或系统可附加的说明',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '会话创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '会话最后更新时间（新消息写入时自动刷新）',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '会话软删除时间；NULL 表示未删除，非空表示已移入回收站',
  PRIMARY KEY (`id`),
  KEY `idx_chat_sessions_user_updated` (`user_id`, `updated_at`),
  CONSTRAINT `fk_chat_sessions_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 客服聊天会话表';

-- 聊天消息表：存储会话中每一轮的用户提问和 AI 回复
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '消息自增主键',
  `session_id` VARCHAR(64) NOT NULL COMMENT '消息所属会话 ID，关联 chat_sessions.id',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '消息所属用户 ID，用于数据隔离，关联 users.id',
  `role` VARCHAR(20) NOT NULL COMMENT '消息角色：user=用户提问，assistant=AI 回复，system=系统消息',
  `content` MEDIUMTEXT NOT NULL COMMENT '消息正文内容',
  `model_name` VARCHAR(100) DEFAULT NULL COMMENT '助手回复使用的模型名称（如 gpt-4o）；用户消息为空',
  `total_tokens` INT NOT NULL DEFAULT 0 COMMENT '本条消息消耗的 token 数；当前未精确统计时为 0',
  `references_text` MEDIUMTEXT DEFAULT NULL COMMENT '助手回答的引用来源，多条引用以换行符拼接；包含知识库检索结果和工具调用结果',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_chat_messages_session_id` (`session_id`, `id`),
  KEY `idx_chat_messages_user_id` (`user_id`),
  CONSTRAINT `fk_chat_messages_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_messages_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 客服聊天消息表';

-- 用户订单表：存储用户的订单信息，供 AI 客服查询
CREATE TABLE IF NOT EXISTS `user_orders` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单自增主键',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT '订单所属用户 ID，用于区分不同用户的订单数据',
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
  KEY `idx_user_orders_user_created` (`user_id`, `created_at`),
  KEY `idx_user_orders_user_status` (`user_id`, `order_status`),
  CONSTRAINT `fk_user_orders_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户订单表（供 AI 客服工具调用查询）';

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

INSERT INTO `knowledge_bases` (`name`, `description`)
VALUES
  ('订单知识库', '订单查询、订单状态、订单规则相关知识'),
  ('商品知识库', '商品介绍、规格参数、库存说明相关知识'),
  ('售后知识库', '退款、退货、换货、保修相关知识')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

INSERT INTO `users` (`username`, `password_hash`, `salt`, `nickname`, `status`)
VALUES ('admin', '8855597499f16994bccfa99612dddfffa2bedf2ea48127c9868497575c11bff4', 'b319b5073f27d2bab5171d9ee7af0262', '管理员', 1)
ON DUPLICATE KEY UPDATE `username` = VALUES(`username`);

INSERT INTO `user_orders` (
  `user_id`, `order_no`, `product_name`, `product_sku`, `product_quantity`, `order_amount`, `currency`,
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
