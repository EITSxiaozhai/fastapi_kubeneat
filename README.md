# fastapi-kubeneat

`fastapi-kubeneat` 是一个面向 Kubernetes YAML 精简场景的前后端分离项目。

后端基于 `FastAPI + Celery + Redis`，负责接收 YAML、异步调用 `kubectl-neat`、持久化任务元信息，并提供任务查询与结果下载接口。

前端基于 `Ant Design Pro`，提供以下能力：

- 上传 YAML 文件并提交后台任务
- 直接粘贴 Kubernetes YAML 文本并提交后台任务
- 查询单个任务执行状态
- 在仪表盘任务中心查看全部任务的状态、来源和下载链接

## 1. 项目结构

```text
fastapi_kubeneat/
├─ app/
│  ├─ api/                 FastAPI 路由
│  ├─ core/                配置与 Celery 初始化
│  ├─ services/            kubectl-neat 和任务注册表逻辑
│  ├─ workers/             Celery 任务
│  └─ main.py              FastAPI 入口
├─ front-end/              前端项目
├─ runtime_data/           运行期目录，保存上传文件、结果文件、任务注册表
├─ docker-compose.yml      容器编排
├─ Dockerfile              后端镜像构建文件
├─ kubectl-neat            Linux 版 kubectl-neat 二进制
└─ pyproject.toml          后端依赖定义
```

`runtime_data/` 下的几个文件和目录说明如下：

- `uploads/`：保存用户提交的原始 YAML
- `results/`：保存 `kubectl-neat` 处理结果
- `task_registry.jsonl`：保存任务元信息，用于任务总览页

## 2. 运行架构

### 2.1 后端

后端职责如下：

1. 接收 YAML 文件或 YAML 文本
2. 将内容写入本地运行目录
3. 通过 Celery 创建异步任务
4. 调用 `kubectl-neat` 逐个处理 YAML 中的资源对象
5. 返回任务状态和下载链接

### 2.2 前端

前端包含两个主要页面：

- `kubectl-neat YAML cleanup`
  用于提交 YAML 文件或手动粘贴 YAML 文本
- `Dashboard / Task Center`
  用于查看全部任务的执行状态、提交来源、提交时间和结果下载链接

## 3. 环境要求

### 3.1 后端

- Python `3.12+`
- Redis `6.x`
- 可执行的 `kubectl-neat`

### 3.2 前端

- Node.js `20+`
- npm

## 4. 环境变量

项目当前使用以下环境变量：

```env
CELERY_BROKER_URL=redis://:PASSWORD@host:6379/0
CELERY_RESULT_BACKEND=redis://:PASSWORD@host:6379/1
KUBECTL_NEAT_BIN=kubectl-neat
KUBENEAT_RUNTIME_DIR=runtime_data
KUBENEAT_MAX_UPLOAD_BYTES=5242880
```

说明如下：

- `CELERY_BROKER_URL`：Celery broker 地址
- `CELERY_RESULT_BACKEND`：Celery 结果后端地址
- `KUBECTL_NEAT_BIN`：`kubectl-neat` 命令。可以是可执行文件，也可以是一整段命令
- `KUBENEAT_RUNTIME_DIR`：运行期目录
- `KUBENEAT_MAX_UPLOAD_BYTES`：允许提交的最大 YAML 内容大小，默认 `5 MB`

项目根目录提供了两个示例文件：

- [`.env.windows.example`](/D:/fastapi_kubeneat/.env.windows.example)
- [`.env.container.example`](/D:/fastapi_kubeneat/.env.container.example)

## 5. Windows 本地开发

本项目支持在 Windows 上开发，但 `kubectl-neat` 使用的是 Linux 二进制，因此需要通过 WSL 调用。

### 5.1 准备 Redis

当前项目示例使用 Docker 启动 Redis：

```powershell
docker run -d --name my-redis -p 6379:6379 -e REDIS_PASSWORD=KZNkYLt3U3Zmtm7q public.ecr.aws/bitnami/redis:6.2.13-debian-11-r61
```

### 5.2 配置 `.env`

参考 [`.env.windows.example`](/D:/fastapi_kubeneat/.env.windows.example)：

```env
CELERY_BROKER_URL="redis://:KZNkYLt3U3Zmtm7q@localhost:6379/0"
CELERY_RESULT_BACKEND="redis://:KZNkYLt3U3Zmtm7q@localhost:6379/1"
KUBECTL_NEAT_BIN="wsl /mnt/d/fastapi_kubeneat/kubectl-neat"
KUBENEAT_RUNTIME_DIR="runtime_data"
```

这里的关键点是：

- Windows 进程不能直接执行 Linux ELF 二进制
- 需要通过 `wsl /mnt/d/.../kubectl-neat` 间接调用

### 5.3 验证 `kubectl-neat`

在 WSL 中验证时，不要使用：

```bash
bash kubectl-neat
```

正确用法是：

```bash
chmod +x kubectl-neat
./kubectl-neat
```

如果这里执行失败，说明二进制本身有问题，Celery 也不会成功。

### 5.4 启动后端

安装后端依赖：

```powershell
pip install -e .
```

启动 FastAPI：

```powershell
uvicorn app.main:app --reload --port 8002
```

启动 Celery Worker：

```powershell
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

### 5.5 启动前端

进入前端目录：

```powershell
cd front-end
```

安装依赖：

```powershell
npm install
```

启动开发服务器：

```powershell
npm run dev
```

前端默认运行在 `http://localhost:8000`。

## 6. 容器化部署

生产部署建议直接使用 Docker Compose，将 API、Celery 和 Redis 一起编排。

### 6.1 容器运行方式

容器模式下，后端镜像会将项目根目录的 `kubectl-neat` 复制到容器内：

```text
/usr/local/bin/kubectl-neat
```

此时 Celery 直接调用 Linux 容器内的可执行文件，不再经过 WSL。

### 6.2 生产环境变量

参考 [`.env.container.example`](/D:/fastapi_kubeneat/.env.container.example)：

```env
CELERY_BROKER_URL="redis://:KZNkYLt3U3Zmtm7q@redis:6379/0"
CELERY_RESULT_BACKEND="redis://:KZNkYLt3U3Zmtm7q@redis:6379/1"
KUBECTL_NEAT_BIN="/usr/local/bin/kubectl-neat"
KUBENEAT_RUNTIME_DIR="/data/runtime"
```

### 6.3 启动方式

在项目根目录执行：

```powershell
docker compose up --build
```

这会启动以下服务：

- `redis`：Celery broker 和 result backend
- `api`：FastAPI 服务
- `celery`：后台任务处理服务

### 6.4 数据持久化

`docker-compose.yml` 已经为以下数据声明了 volume：

- `redis_data`
- `kubeneat_runtime`

其中 `kubeneat_runtime` 用于持久化：

- 上传的原始 YAML
- 精简后的结果文件
- 任务注册表

这意味着即使 `api` 和 `celery` 容器重启，任务历史和结果文件仍然可见。

## 7. 使用说明

### 7.1 提交 YAML 文件

进入 `kubectl-neat YAML cleanup` 页面后：

1. 切换到 `File upload`
2. 选择或拖拽一个 `.yaml` / `.yml` 文件
3. 点击 `Submit file`
4. 系统创建后台任务并显示任务状态卡片

### 7.2 手动粘贴 YAML

进入 `kubectl-neat YAML cleanup` 页面后：

1. 切换到 `Manual input`
2. 输入结果文件名
3. 粘贴 Kubernetes YAML 内容
4. 点击 `Submit YAML`

### 7.3 查看任务总览

进入 `Dashboard / Task Center` 页面后，可以看到全部任务列表。

当前页面提供以下信息：

- `Task ID`
- `Source file`
- `Submit type`
- `Status`
- `Progress`
- `Created`
- `Download`

其中 `Submit type` 的含义如下：

- `File upload`：通过文件选择器上传
- `Manual paste`：通过手动粘贴 YAML 文本提交

## 8. 后端接口

### 8.1 健康检查

```http
GET /api/health
```

### 8.2 提交 YAML

提交文件：

```http
POST /api/neat/upload
Content-Type: multipart/form-data
```

表单字段：

- `file`

提交文本：

```http
POST /api/neat/upload
Content-Type: multipart/form-data
```

表单字段：

- `content`
- `filename`

### 8.3 查询单个任务

```http
GET /api/neat/tasks/{task_id}
```

### 8.4 查询任务总览

```http
GET /api/neat/tasks
```

### 8.5 下载任务结果

```http
GET /api/neat/tasks/{task_id}/download
```

## 9. 常见问题

### 9.1 Celery 能启动，但任务执行失败，提示找不到 `kubectl-neat`

优先检查以下几项：

1. `KUBECTL_NEAT_BIN` 是否配置正确
2. Windows 模式下是否使用了 `wsl /mnt/.../kubectl-neat`
3. 容器模式下镜像内是否存在 `/usr/local/bin/kubectl-neat`
4. 二进制是否具备执行权限

### 9.2 WSL 中执行 `bash kubectl-neat` 报错 `cannot execute binary file`

这是错误用法。二进制文件不应该通过 `bash` 解释执行。

请使用：

```bash
./kubectl-neat
```

### 9.3 Worker 收到 `unregistered task`

通常是以下原因之一：

1. 任务名称发生了变化，但 Redis 队列中还有旧消息
2. Worker 还没有重启，仍然加载的是旧代码

处理方式通常是：

1. 重启 `uvicorn`
2. 重启 `celery worker`
3. 清理旧消息后重新提交任务