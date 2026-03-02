CREATE TABLE IF NOT EXISTS `sys_user` (
  `user_id` varchar(32) NOT NULL COMMENT '用户唯一 ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(100) NOT NULL COMMENT '密码',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

CREATE TABLE IF NOT EXISTS `script_template` (
  `template_id` varchar(32) NOT NULL COMMENT '模板 ID',
  `name` varchar(100) NOT NULL COMMENT '模板名称',
  `description` varchar(500) DEFAULT NULL COMMENT '模板描述',
  `creator` varchar(32) DEFAULT NULL COMMENT '创建人',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`template_id`),
  FOREIGN KEY (`creator`)
  REFERENCES sys_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本模板表';

CREATE TABLE IF NOT EXISTS `script_info` (
  `script_id` varchar(32) NOT NULL COMMENT '脚本唯一 ID',
  `name` varchar(100) NOT NULL COMMENT '脚本名称',
  `type` varchar(20) NOT NULL COMMENT '类型',
  `content` text NOT NULL COMMENT '脚本内容(MinIO路径)',
  `status` varchar(10) NOT NULL COMMENT '状态',
  `creator` varchar(32) DEFAULT NULL COMMENT '创建人 ID',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `latest_version` varchar(20) NOT NULL COMMENT '最新版本号',
  PRIMARY KEY (`script_id`),
  FOREIGN KEY (`creator`)
  REFERENCES sys_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本信息表';

CREATE TABLE IF NOT EXISTS `script_version` (
  `version_id` varchar(32) NOT NULL COMMENT '版本 ID',
  `script_id` varchar(32) NOT NULL COMMENT '关联脚本 ID',
  `version` varchar(20) NOT NULL COMMENT '版本号',
  `content` text NOT NULL COMMENT '该版本脚本内容(MinIO路径)',
  `modifier` varchar(32) NULL COMMENT '修改人 ID',
  `modify_time` datetime NOT NULL COMMENT '修改时间',
  `change_log` varchar(500) DEFAULT NULL COMMENT '变更日志',
  PRIMARY KEY (`version_id`),
  FOREIGN KEY (`script_id`)
  REFERENCES script_info(script_id),
  FOREIGN KEY (`modifier`)
  REFERENCES sys_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本版本表';

CREATE TABLE IF NOT EXISTS `script_template_rel` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '关联记录 ID',
  `template_id` varchar(32) NOT NULL COMMENT '关联模板 ID',
  `script_id` varchar(32) NOT NULL COMMENT '关联脚本 ID',
  `is_default` tinyint(4) NOT NULL COMMENT '是否为模板默认脚本',
  `sort_order` int(11) NOT NULL COMMENT '脚本执行顺序',
  `create_time` datetime NOT NULL COMMENT '关联创建时间',
  PRIMARY KEY (`id`),
  FOREIGN KEY (`template_id`)
  REFERENCES script_template(template_id),
  FOREIGN KEY (`script_id`)
  REFERENCES script_info(script_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本-模板关联表';

CREATE TABLE IF NOT EXISTS `task_info` (
  `task_id` varchar(32) NOT NULL COMMENT '任务 ID',
  `name` varchar(100) NOT NULL COMMENT '任务名称',
  `script_id` varchar(32) DEFAULT NULL COMMENT '关联脚本ID',
  `template_id` varchar(32) DEFAULT NULL COMMENT '关联模板ID',
  `trigger_type` varchar(20) NOT NULL COMMENT '触发方式',
  `status` varchar(20) NOT NULL COMMENT '任务整体状态',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `start_time` datetime DEFAULT NULL COMMENT '开始执行时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `creator` varchar(32) DEFAULT NULL COMMENT '执行人',
  PRIMARY KEY (`task_id`),
  FOREIGN KEY (`creator`) REFERENCES sys_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务信息表';

CREATE TABLE IF NOT EXISTS `script_exec_log` (
  `log_id` varchar(32) NOT NULL COMMENT '日志 ID',
  `script_id` varchar(32) NOT NULL COMMENT '脚本 ID',
  `task_id` varchar(32) NOT NULL COMMENT '关联任务 ID',
  `step_name` varchar(100) NOT NULL COMMENT '执行步骤名称',
  `status` varchar(10) NOT NULL COMMENT '步骤状态',
  `error_msg` text DEFAULT NULL COMMENT '错误信息',
  `exec_time` datetime NOT NULL COMMENT '执行时间',
  `duration` int(11) NOT NULL COMMENT '步骤耗时',
  PRIMARY KEY (`log_id`),
  FOREIGN KEY (`script_id`)
  REFERENCES script_info(script_id),
  FOREIGN KEY (`task_id`)
  REFERENCES task_info(task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脚本执行日志表';
