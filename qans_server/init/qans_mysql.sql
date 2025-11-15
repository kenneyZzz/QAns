
-- ============================================
-- 1. 知识库表
-- ============================================
DROP TABLE IF EXISTS `t_knowledge_base`;
CREATE TABLE `t_knowledge_base` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `name` VARCHAR(200) NOT NULL COMMENT '知识库名称',
    `description` TEXT COMMENT '知识库描述',
    `document_count` INT(11) NOT NULL DEFAULT 0 COMMENT '文档数量',
    `total_size` BIGINT(20) NOT NULL DEFAULT 0 COMMENT '总大小（字节）',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_name` (`name`),
    INDEX `idx_create_time` (`create_time`)
)  COMMENT='知识库表';

-- ============================================
-- 2. 文档表
-- ============================================
DROP TABLE IF EXISTS `t_document`;
CREATE TABLE `t_document` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `knowledge_base_id` INT(11) NOT NULL COMMENT '所属知识库ID',
    `file_name` VARCHAR(255) NOT NULL COMMENT '文件名',
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    `file_size` BIGINT(20) NOT NULL COMMENT '文件大小（字节）',
    `file_type` VARCHAR(50) NOT NULL COMMENT '文件类型（扩展名）',
    `chunk_count` INT(11) NOT NULL DEFAULT 0 COMMENT '分块数量',
    `status` VARCHAR(20) NOT NULL DEFAULT 'uploaded' COMMENT '状态：uploaded/processing/chunked/completed/failed',
    `error_message` VARCHAR(1000) DEFAULT NULL COMMENT '错误信息',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_kb_id` (`knowledge_base_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_create_time` (`create_time`),
    CONSTRAINT `fk_document_knowledge_base` FOREIGN KEY (`knowledge_base_id`) 
        REFERENCES `t_knowledge_base` (`id`) ON DELETE CASCADE
)  COMMENT='文档表';

-- ============================================
-- 3. 文档分块表
-- ============================================
DROP TABLE IF EXISTS `t_document_chunk`;
CREATE TABLE `t_document_chunk` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `document_id` INT(11) NOT NULL COMMENT '文档ID',
    `knowledge_base_id` INT(11) NOT NULL COMMENT '知识库ID',
    `chunk_index` INT(11) NOT NULL COMMENT '分块序号',
    `content` MEDIUMTEXT NOT NULL COMMENT '分块内容',
    `metadata` TEXT DEFAULT NULL COMMENT '元数据(JSON)',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_document_id` (`document_id`),
    INDEX `idx_kb_id` (`knowledge_base_id`),
    CONSTRAINT `fk_document_chunk_document` FOREIGN KEY (`document_id`)
        REFERENCES `t_document` (`id`) ON DELETE CASCADE
)  COMMENT='文档分块表';

-- ============================================
-- 4. 聊天会话表
-- ============================================
DROP TABLE IF EXISTS `t_chat_session`;
CREATE TABLE `t_chat_session` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `title` VARCHAR(200) DEFAULT NULL COMMENT '会话标题',
    `knowledge_base_ids` TEXT COMMENT '选中的知识库ID列表（JSON格式）',
    `message_count` INT(11) NOT NULL DEFAULT 0 COMMENT '消息数量',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_create_time` (`create_time`)
)  COMMENT='聊天会话表';

-- ============================================
-- 5. 聊天消息表
-- ============================================
DROP TABLE IF EXISTS `t_chat_message`;
CREATE TABLE `t_chat_message` (
    `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `session_id` INT(11) NOT NULL COMMENT '会话ID',
    `role` VARCHAR(20) NOT NULL COMMENT '角色：user/assistant',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `sources` TEXT DEFAULT NULL COMMENT '引用来源（JSON格式，仅assistant消息）',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_create_time` (`create_time`),
    CONSTRAINT `fk_chat_message_session` FOREIGN KEY (`session_id`) 
        REFERENCES `t_chat_session` (`id`) ON DELETE CASCADE
)  COMMENT='聊天消息表';



