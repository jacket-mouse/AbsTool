## 进度

### 数据库

- [ ] 数据库设计
- [ ] 绘制图像
- [ ] 代码建表



## 数据库设计

### 用户信息表（user_info）

| 字段名  | 类型        | 约束       | 说明        |
| ------- | ----------- | ---------- | ----------- |
| user_id | VARCHAR(32) | 主键，非空 | 用户唯一 ID |
|         |             |            |             |
|         |             |            |             |
|         |             |            |             |
|         |             |            |             |
|         |             |            |             |
|         |             |            |             |
|         |             |            |             |

### 脚本信息表（script_info）

| 字段名         | 类型         | 约束            | 说明                                  |
| -------------- | ------------ | --------------- | ------------------------------------- |
| script_id      | VARCHAR(32)  | 主键，非空      | 脚本唯一 ID（如 SC123）               |
| name           | VARCHAR(100) | 非空            | 脚本名称（如 “微信操作模拟”）         |
| type           | VARCHAR(20)  | 非空            | 类型（GENERAL：通用；CUSTOM：定制）   |
| content        | TEXT         | 非空            | 脚本内容（JSON 格式，存储节点与流程） |
| status         | VARCHAR(10)  | 非空            | 状态（ENABLED：启用；DISABLED：禁用） |
| creator        | VARCHAR(32)  | 外键（用户 ID） | 创建人 ID                             |
| create_time    | DATETIME     | 非空            | 创建时间                              |
| latest_version | VARCHAR(20)  | 非空            | 最新版本号（如 V3）                   |

### 脚本版本表（script_version）

| 字段名      | 类型         | 约束            | 说明                          |
| ----------- | ------------ | --------------- | ----------------------------- |
| version_id  | VARCHAR(32)  | 主键，非空      | 版本 ID                       |
| script_id   | VARCHAR(32)  | 外键，非空      | 关联脚本 ID                   |
| version     | VARCHAR(20)  | 非空            | 版本号（如 V2）               |
| content     | TEXT         | 非空            | 该版本脚本内容                |
| modifier    | VARCHAR(32)  | 外键（用户 ID） | 修改人 ID                     |
| modify_time | DATETIME     | 非空            | 修改时间                      |
| change_log  | VARCHAR(500) | nullable        | 变更日志（如 “新增滑动节点”） |

### 模版信息表（template_info）

| 字段名      | 类型        | 约束       | 说明        |
| ----------- | ----------- | ---------- | ----------- |
| template_id | VARCHAR(32) | 主键，非空 | 模版唯一 ID |
|             |             |            |             |
|             |             |            |             |
|             |             |            |             |
|             |             |            |             |
|             |             |            |             |
|             |             |            |             |
|             |             |            |             |

### 脚本 - 模板关联表（script_template_rel）

脚本和模版多对多关系

| 字段名      | 类型        | 主键 / 外键 | 约束                     | 说明                                          |
| ----------- | ----------- | ----------- | ------------------------ | --------------------------------------------- |
| id          | BIGINT      | 主键        | NOT NULL, AUTO_INCREMENT | 关联记录 ID（自增）                           |
| template_id | VARCHAR(32) | 外键        | NOT NULL                 | 关联模板 ID（关联 template_info.template_id） |
| script_id   | VARCHAR(32) | 外键        | NOT NULL                 | 关联脚本 ID（关联 script_info.script_id）     |
| is_default  | TINYINT     | -           | NOT NULL                 | 是否为模板默认脚本（1 = 是，0 = 否）          |
| sort_order  | INT         | -           | NOT NULL                 | 脚本执行顺序（数字越小越先执行）              |
| create_time | DATETIME    | -           | NOT NULL                 | 关联创建时间                                  |

### 脚本执行日志表（script_exec_log）

| 字段名    | 类型         | 约束       | 说明                              |
| --------- | ------------ | ---------- | --------------------------------- |
| log_id    | VARCHAR(32)  | 主键，非空 | 日志 ID                           |
| script_id | VARCHAR(32)  | 外键，非空 | 脚本 ID                           |
| task_id   | VARCHAR(32)  | 外键，非空 | 关联任务 ID                       |
| step_name | VARCHAR(100) | 非空       | 执行步骤名称（如 “点击登录按钮”） |
| status    | VARCHAR(10)  | 非空       | 步骤状态（SUCCESS/FAIL）          |
| error_msg | TEXT         | nullable   | 错误信息（失败时填写）            |
| exec_time | DATETIME     | 非空       | 执行时间                          |
| duration  | INT          | 非空       | 步骤耗时（毫秒）                  |

 当你启动一个基于特定模板的任务时，数据流转如下：

1. **查询阶段**：系统根据 `template_id` 从 `script_template_rel` 找到所有相关的 `script_id` 及其 `sort_order`。
2. **执行阶段**：程序按顺序调用脚本逻辑。
3. **持久化阶段**：
   - 每执行一步，程序向 `script_exec_log` 插入一条记录。
   - **关键关联**：日志表中的 `script_id` 确保了你可以追溯到这条日志是属于哪个脚本的；而 `task_id` 则是这一批次执行的全局唯一标识（特定任务的所有执行日志）。





### 数据库表结构说明

#### 1. 用户信息表 (`sys_user`)

用于存储系统的用户信息，包括创建者、修改者等。

| 字段名        | 类型           | 约束 / 默认值             | 说明        |
| :------------ | :------------- | :------------------------ | :---------- |
| `user_id`     | `varchar(32)`  | **PRIMARY KEY**, NOT NULL | 用户唯一 ID |
| `username`    | `varchar(50)`  | NOT NULL                  | 用户名      |
| `password`    | `varchar(100)` | NOT NULL                  | 密码        |
| `nickname`    | `varchar(50)`  | DEFAULT NULL              | 昵称        |
| `create_time` | `datetime`     | NOT NULL                  | 创建时间    |

------

#### 2. 脚本模板表 (`script_template`)

用于定义脚本的集合（模板），支持将多个脚本编排为一个工作流。

| 字段名        | 类型           | 约束 / 默认值             | 说明     |
| :------------ | :------------- | :------------------------ | :------- |
| `template_id` | `varchar(32)`  | **PRIMARY KEY**, NOT NULL | 模板 ID  |
| `name`        | `varchar(100)` | NOT NULL                  | 模板名称 |
| `description` | `varchar(500)` | DEFAULT NULL              | 模板描述 |
| `creator`     | `varchar(32)`  | FK -> `sys_user(user_id)` | 创建人   |
| `create_time` | `datetime`     | NOT NULL                  | 创建时间 |

------

#### 3. 脚本信息表 (`script_info`)

存储脚本的基本元数据和当前状态。

| 字段名           | 类型           | 约束 / 默认值             | 说明        |
| :--------------- | :------------- | :------------------------ | :---------- |
| `script_id`      | `varchar(32)`  | **PRIMARY KEY**, NOT NULL | 脚本唯一 ID |
| `name`           | `varchar(100)` | NOT NULL                  | 脚本名称    |
| `type`           | `varchar(20)`  | NOT NULL                  | 类型        |
| `content`        | `text`         | NOT NULL                  | 脚本内容    |
| `status`         | `varchar(10)`  | NOT NULL                  | 状态        |
| `creator`        | `varchar(32)`  | FK -> `sys_user(user_id)` | 创建人 ID   |
| `create_time`    | `datetime`     | NOT NULL                  | 创建时间    |
| `latest_version` | `varchar(20)`  | NOT NULL                  | 最新版本号  |

------

#### 4. 脚本版本表 (`script_version`)

用于脚本的版本控制，记录脚本的历史变更。

| 字段名        | 类型           | 约束 / 默认值                            | 说明           |
| :------------ | :------------- | :--------------------------------------- | :------------- |
| `version_id`  | `varchar(32)`  | **PRIMARY KEY**, NOT NULL                | 版本 ID        |
| `script_id`   | `varchar(32)`  | NOT NULL, FK -> `script_info(script_id)` | 关联脚本 ID    |
| `version`     | `varchar(20)`  | NOT NULL                                 | 版本号         |
| `content`     | `text`         | NOT NULL                                 | 该版本脚本内容 |
| `modifier`    | `varchar(32)`  | FK -> `sys_user(user_id)`                | 修改人 ID      |
| `modify_time` | `datetime`     | NOT NULL                                 | 修改时间       |
| `change_log`  | `varchar(500)` | DEFAULT NULL                             | 变更日志       |

------

#### 5. 脚本-模板关联表 (`script_template_rel`)

连接脚本与模板，定义模板中包含哪些脚本以及它们的执行顺序。

| 字段名        | 类型          | 约束 / 默认值                                  | 说明               |
| :------------ | :------------ | :--------------------------------------------- | :----------------- |
| `id`          | `bigint(20)`  | **PRIMARY KEY**, AUTO_INCREMENT                | 关联记录 ID        |
| `template_id` | `varchar(32)` | NOT NULL, FK -> `script_template(template_id)` | 关联模板 ID        |
| `script_id`   | `varchar(32)` | NOT NULL, FK -> `script_info(script_id)`       | 关联脚本 ID        |
| `is_default`  | `tinyint(4)`  | NOT NULL                                       | 是否为模板默认脚本 |
| `sort_order`  | `int(11)`     | NOT NULL                                       | 脚本执行顺序       |
| `create_time` | `datetime`    | NOT NULL                                       | 关联创建时间       |

------

#### 6. 任务信息表 (`task_info`)

记录每一次执行实例（无论是单脚本执行还是模板执行）。

| 字段名         | 类型           | 约束 / 默认值             | 说明                             |
| :------------- | :------------- | :------------------------ | :------------------------------- |
| `task_id`      | `varchar(32)`  | **PRIMARY KEY**, NOT NULL | 任务 ID                          |
| `name`         | `varchar(100)` | NOT NULL                  | 任务名称                         |
| `script_id`    | `varchar(32)`  | DEFAULT NULL              | 关联脚本ID (单脚本任务)          |
| `template_id`  | `varchar(32)`  | DEFAULT NULL              | 关联模板ID (模板任务)            |
| `trigger_type` | `varchar(20)`  | NOT NULL                  | 触发方式 (e.g. MANUAL, SCHEDULE) |
| `status`       | `varchar(20)`  | NOT NULL                  | 任务整体状态                     |
| `create_time`  | `datetime`     | NOT NULL                  | 创建时间                         |
| `start_time`   | `datetime`     | DEFAULT NULL              | 开始执行时间                     |
| `end_time`     | `datetime`     | DEFAULT NULL              | 结束时间                         |
| `creator`      | `varchar(32)`  | FK -> `sys_user(user_id)` | 执行人                           |

------

#### 7. 脚本执行日志表 (`script_exec_log`)

记录任务中每一个执行步骤的详细日志。

| 字段名      | 类型           | 约束 / 默认值                            | 说明          |
| :---------- | :------------- | :--------------------------------------- | :------------ |
| `log_id`    | `varchar(32)`  | **PRIMARY KEY**, NOT NULL                | 日志 ID       |
| `script_id` | `varchar(32)`  | NOT NULL, FK -> `script_info(script_id)` | 脚本 ID       |
| `task_id`   | `varchar(32)`  | NOT NULL, FK -> `task_info(task_id)`     | 关联任务 ID   |
| `step_name` | `varchar(100)` | NOT NULL                                 | 执行步骤名称  |
| `status`    | `varchar(10)`  | NOT NULL                                 | 步骤状态      |
| `error_msg` | `text`         | DEFAULT NULL                             | 错误信息      |
| `exec_time` | `datetime`     | NOT NULL                                 | 执行时间      |
| `duration`  | `int(11)`      | NOT NULL                                 | 步骤耗时 (ms) |

