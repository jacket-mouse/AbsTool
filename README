# AbsTool

## 快速启动

1. 创建并激活虚拟环境：

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 创建 `.env` 文件：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@localhost:3306/数据库名
SECRET_KEY=请替换为随机安全字符串

MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_ACCESS_KEY=你的 MinIO Access Key
MINIO_SECRET_KEY=你的 MinIO Secret Key
MINIO_SECURE=false
```

4. 确认 MySQL 数据库和 MinIO 服务已启动，并已准备好项目所需的数据表。

5. 启动服务：

```bash
python main.py
```

默认服务地址：

```text
http://localhost:8080
```

FastAPI 文档地址：

```text
http://localhost:8080/docs
```

## 配置说明

| 变量名 | 说明 | 示例 |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy 数据库连接字符串 | `mysql+pymysql://root:password@localhost:3306/abs_tool_db` |
| `SECRET_KEY` | JWT 签名密钥 | `replace-with-random-secret` |
| `MINIO_ENDPOINT` | MinIO 服务地址 | `http://127.0.0.1:9000` |
| `MINIO_ACCESS_KEY` | MinIO 访问 Key | `admin` |
| `MINIO_SECRET_KEY` | MinIO 密钥 | `password` |
| `MINIO_SECURE` | 是否使用 HTTPS | `false` |

请不要把真实生产密钥提交到代码仓库。

## 使用 Docker 配置 MinIO

1. 拉取 MinIO 镜像：

```bash
docker pull minio/minio
```

2. 启动 MinIO 容器：

```bash
docker run -d 
  --name abs-minio 
  -p 9000:9000 
  -p 9001:9001 
  -e MINIO_ROOT_USER=admin ^
  -e MINIO_ROOT_PASSWORD=password123 ^
  -v abs-minio-data:/data ^
  minio/minio server /data --console-address ":9001"
```

PowerShell 也可以使用单行命令：

```powershell
docker run -d --name abs-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=password123 -v abs-minio-data:/data minio/minio server /data --console-address ":9001"
```

3. 打开 MinIO 控制台：

```text
http://127.0.0.1:9001
```

登录账号：

```text
用户名：admin
密码：password123
```

4. 在 `.env` 中配置 MinIO：

```env
MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
MINIO_SECURE=false
```

项目启动后会自动检查并创建 `abs-scripts` bucket。
