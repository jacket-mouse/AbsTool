/*
 Navicat Premium Dump SQL

 Source Server         : leeson
 Source Server Type    : MySQL
 Source Server Version : 80405 (8.4.5)
 Source Host           : localhost:3306
 Source Schema         : abs_tool_db

 Target Server Type    : MySQL
 Target Server Version : 80405 (8.4.5)
 File Encoding         : 65001

 Date: 19/03/2026 19:12:22
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for script_exec_log
-- ----------------------------
DROP TABLE IF EXISTS `script_exec_log`;
CREATE TABLE `script_exec_log` (
  `log_id` varchar(32) NOT NULL COMMENT '日志 ID',
  `task_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '关联任务 ID',
  `template_id` varchar(32) DEFAULT NULL COMMENT '关联模板 ID',
  `device_id` varchar(255) NOT NULL COMMENT '设备 ID',
  `exec_status` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '执行结果: SUCCESS, FAILED, ERROR',
  `log_file_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'MinIO中完整的日志文件路径',
  `start_time` datetime NOT NULL COMMENT '开始时间',
  `end_time` datetime NOT NULL COMMENT '结束时间',
  PRIMARY KEY (`log_id`),
  KEY `task_id` (`task_id`),
  KEY `idx_template_time` (`template_id`,`start_time` DESC) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='脚本执行日志表';

-- ----------------------------
-- Table structure for script_info
-- ----------------------------
DROP TABLE IF EXISTS `script_info`;
CREATE TABLE `script_info` (
  `script_id` varchar(32) NOT NULL COMMENT '脚本唯一 ID',
  `name` varchar(100) NOT NULL COMMENT '脚本名称',
  `type` varchar(20) NOT NULL COMMENT '类型',
  `content` text NOT NULL COMMENT '脚本内容(MinIO路径)',
  `status` varchar(10) NOT NULL COMMENT '状态',
  `creator` varchar(32) DEFAULT NULL COMMENT '创建人 ID',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `latest_version` varchar(20) NOT NULL COMMENT '最新版本号',
  PRIMARY KEY (`script_id`),
  KEY `creator` (`creator`),
  CONSTRAINT `script_info_ibfk_1` FOREIGN KEY (`creator`) REFERENCES `sys_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='脚本信息表';

-- ----------------------------
-- Table structure for script_template
-- ----------------------------
DROP TABLE IF EXISTS `script_template`;
CREATE TABLE `script_template` (
  `template_id` varchar(32) NOT NULL COMMENT '模板 ID',
  `name` varchar(100) NOT NULL COMMENT '模板名称',
  `description` varchar(500) DEFAULT NULL COMMENT '模板描述',
  `creator` varchar(32) DEFAULT NULL COMMENT '创建人',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`template_id`),
  KEY `creator` (`creator`),
  CONSTRAINT `script_template_ibfk_1` FOREIGN KEY (`creator`) REFERENCES `sys_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='脚本模板表';

-- ----------------------------
-- Table structure for script_template_rel
-- ----------------------------
DROP TABLE IF EXISTS `script_template_rel`;
CREATE TABLE `script_template_rel` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '关联记录 ID',
  `template_id` varchar(32) NOT NULL COMMENT '关联模板 ID',
  `script_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '关联脚本 ID',
  `is_default` tinyint NOT NULL COMMENT '是否为模板默认脚本',
  `sort_order` int NOT NULL COMMENT '脚本执行顺序',
  `create_time` datetime NOT NULL COMMENT '关联创建时间',
  PRIMARY KEY (`id`),
  KEY `template_id` (`template_id`),
  KEY `script_info` (`script_id`),
  CONSTRAINT `script_info` FOREIGN KEY (`script_id`) REFERENCES `script_info` (`script_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `script_template_rel_ibfk_1` FOREIGN KEY (`template_id`) REFERENCES `script_template` (`template_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='脚本-模板关联表';

-- ----------------------------
-- Table structure for script_version
-- ----------------------------
DROP TABLE IF EXISTS `script_version`;
CREATE TABLE `script_version` (
  `version_id` varchar(32) NOT NULL COMMENT '版本 ID',
  `script_id` varchar(32) NOT NULL COMMENT '关联脚本 ID',
  `version` varchar(20) NOT NULL COMMENT '版本号',
  `content` text NOT NULL COMMENT '该版本脚本内容(MinIO路径)',
  `modifier` varchar(32) DEFAULT NULL COMMENT '修改人 ID',
  `modify_time` datetime NOT NULL COMMENT '修改时间',
  `change_log` varchar(500) DEFAULT NULL COMMENT '变更日志',
  PRIMARY KEY (`version_id`),
  KEY `script_id` (`script_id`),
  KEY `modifier` (`modifier`),
  CONSTRAINT `script_version_ibfk_1` FOREIGN KEY (`script_id`) REFERENCES `script_info` (`script_id`),
  CONSTRAINT `script_version_ibfk_2` FOREIGN KEY (`modifier`) REFERENCES `sys_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='脚本版本表';

-- ----------------------------
-- Table structure for sys_user
-- ----------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `user_id` varchar(32) NOT NULL COMMENT '用户唯一 ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(100) NOT NULL COMMENT '密码',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户信息表';

-- ----------------------------
-- Table structure for task_info
-- ----------------------------
DROP TABLE IF EXISTS `task_info`;
CREATE TABLE `task_info` (
  `task_id` varchar(32) NOT NULL COMMENT '任务 ID',
  `name` varchar(100) NOT NULL COMMENT '任务名称',
  `template_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '关联模板ID',
  `creator` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '执行人',
  `cron_expression` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Cron定时表达式',
  `device_id` varchar(255) NOT NULL COMMENT '设备 ID',
  `status` varchar(32) NOT NULL COMMENT '任务状态: ENABLE,DISABLE',
  PRIMARY KEY (`task_id`),
  KEY `creator` (`creator`),
  KEY `script_template` (`template_id`),
  CONSTRAINT `script_template` FOREIGN KEY (`template_id`) REFERENCES `script_template` (`template_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务信息表';

SET FOREIGN_KEY_CHECKS = 1;
