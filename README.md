# SOG · 离散装配生产作业支援系统

面向**离散型制造装配车间**的现场作业支援（SOG，Standard Operation Guidance）系统，定位为 MOM 体系中与 MES 配套的「生产作业支援子系统」。

技术栈：**Python 3.12 + FastAPI + SQLAlchemy 2（async）+ PostgreSQL 18 + Vue 3 + Element Plus + ECharts**。

> **产品定位、功能详述、数据模型、并发设计、集成方案、实施路径、验收用例、错误码与术语，详见 [SOG系统产品说明书.md](SOG系统产品说明书.md)**。

---

## 目录结构

```
dev/
├── README.md                    # 快速上手（本文档）
├── SOG系统产品说明书.md          # 产品说明书 / 技术方案（完整版）
├── docker-compose.yml           # 容器编排（PG18 + 后端 + Nginx）
├── backend/                     # FastAPI 后端
│   ├── pyproject.toml
│   ├── .env.example             # 环境配置（连接池 / 线程 / 并发 / 跨域）
│   ├── smoke_test.py            # 接口层端到端冒烟测试
│   └── app/
│       ├── main.py              # FastAPI 入口、CORS、异常处理、/health
│       ├── core/                # 基础设施层（config / db / deps / concurrency / response / exceptions）
│       ├── common/              # 枚举、分页、基类
│       ├── modules/             # 业务模块（router → service → repository → models → schemas）
│       │   ├── orders/          # 订单管理
│       │   ├── material/        # 物料管控（主数据 / 库存 / 流水）
│       │   └── production/      # 生产管理（工单 / 进度 / 质量 / 追溯）
│       └── migrations/schema.sql # PostgreSQL 18 DDL（幂等）
└── front/                       # Vue 3 前端（Vite）
    ├── package.json
    ├── vite.config.js           # /api 代理到后端
    └── src/
        ├── api/                 # request、orders、materials、production
        ├── layouts/MainLayout.vue
        ├── router/index.js      # orders / materials / inventory / work-orders / quality / trace
        └── views/               # OrderView / MaterialView / InventoryView / WorkOrderView / QualityView / TraceView
```

后端分层约定：`router`（参数校验 / 响应序列化）→ `service`（业务规则 / 状态机 / 事务）→ `repository`（SQL 与行级锁）→ `models`（ORM 表定义）；请求级会话由 `core.deps.get_db` 注入。业务模块之间不互相 import service，只通过 repository / session 解耦。

---

## 快速启动

### 1. 数据库（PostgreSQL 18）

```bash
# 方式一：本机安装
sudo apt install -y postgresql-18 && sudo pg_ctlcluster 18 main start

# 方式二：容器
docker compose up -d postgres

sudo -u postgres psql -c "CREATE ROLE sog LOGIN PASSWORD 'sog123456';"
sudo -u postgres psql -c "CREATE DATABASE sog OWNER sog;"
```

建表（幂等 `CREATE TABLE IF NOT EXISTS`）：

```bash
psql -h 127.0.0.1 -U sog -d sog -f backend/app/migrations/schema.sql
```

重置 schema：

```bash
psql -h 127.0.0.1 -U sog -d sog -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### 2. 后端

```bash
cd backend
cp .env.example .env                    # 按实际修改 DB 账号密码
uv sync                                 # 安装依赖（Python 3.11~3.12）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 健康检查：GET http://127.0.0.1:8000/health
# 接口文档：http://127.0.0.1:8000/docs
```

高并发部署（多核）：

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app   # worker 数 ≈ CPU×2+1
```

### 3. 前端（Vue 3 + Vite）

前端工程位于 `front/`，`vite.config.js` 将 `/api` 代理到后端（开发模式 5173，生产构建 `dist/` 可由 Nginx 或后端静态托管）：

```bash
cd front
npm install
npm run dev      # http://127.0.0.1:5173
npm run build    # 产物 dist/
```

### 4. 容器化（可选）

```bash
docker compose up -d --build
# 前端 http://localhost:8080 ，API /api ，文档 /docs
```

### 5. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_ENV` / `APP_PORT` | `dev` / `8000` | 运行环境与端口 |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `127.0.0.1` / `5432` / `sog` / `sog` / `sog_pass` | PG18 连接信息 |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `20` / `30` | 单进程连接池上限（20+30=50） |
| `DB_POOL_RECYCLE` / `DB_ECHO` | `1800` / `false` | 连接回收秒数 / SQL 回显 |
| `WORKER_THREADS` | `16` | 阻塞与 CPU 任务线程池大小 |
| `ASYNC_CONCURRENCY` | `32` | 异步协程并发信号量上限 |
| `CORS_ORIGINS` | `http://localhost:5173,…` | 允许的前端来源（逗号分隔） |
| `REDIS_URL` | 空 | 预留：缓存 / 消息队列，留空不启用 |

### 6. 操作人（演示）

当前版本**无登录接口**，操作人通过请求头 `X-Operator` 透传（前端 `localStorage.operator` 默认 `system`）：

```bash
curl -H "X-Operator: operator" http://127.0.0.1:8000/api/production/work-orders
```

前端演示可用角色（供后续 JWT 鉴权落地时复用）：

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| planner | planner123 | 计划员 |
| operator | op123 | 操作工（ST-01） |
| quality | qc123 | 质检员 |

JWT 登录与按钮级权限为规划能力（产品说明书第 2.1、5.1 节）。

---

## 验证

当前仓库提供 `backend/smoke_test.py`（**接口层端到端冒烟，35 项全通过**），也可用在线文档手工自测。

**方式一：冒烟脚本**（推荐，仅依赖标准库 `urllib`）

```bash
cd backend
.venv\Scripts\python.exe smoke_test.py     # Windows
# 覆盖链路：物料建档 → 入库 → 建单 → 释放 → 工单流转 → 逐工序报工（含领料）
#           → 报废 → 末道入库 → 检验 → 质量统计 → 正反向追溯 → 追溯树 → 幂等/超产校验
```

**方式二：在线文档自测** — 打开 `http://127.0.0.1:8000/docs`，按「订单 → 物料 → 生产」顺序调用。最小验收路径：

1. `POST /api/materials` 建成品 + 原料；`POST /api/materials/inbound` 入库（带批次）。
2. `POST /api/orders` 建单 → `PUT /api/orders/{id}?version=1` 验证乐观锁 → `POST /api/orders/{id}/release` 生成工单并看缺料告警。
3. `POST /api/materials/issue`（不传批次验证 FIFO）→ `GET /api/materials/transactions` 看流水。
4. 工单流转 `RELEASED` → `RUNNING` → `GET /{id}/operations` 看工序 → `POST /{id}/report` 逐工序报工（首道带 `materials`）→ 末道报满自动入成品仓。
5. `POST /api/production/inspections` 登记检验 → `GET /api/production/inspections/stats` 看统计。
6. `GET /api/production/trace/forward/{product_batch}`、`/backward/{material_batch}`、`/tree/{product_batch}` 查追溯。

并发验证建议：在手 100 的批次上并发 20 次各领 10，应只有 10 次成功，其余报「可用库存不足」，且在手量不为负（行锁生效）。

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [SOG系统产品说明书.md](SOG系统产品说明书.md) | 产品定位、角色、功能地图与实现状态、业务规则与状态机、功能详述、系统架构、数据模型、ERP/MES/设备集成设计、非功能需求、部署运维、实施路径、验收用例、错误码与术语 |
| `docker-compose.yml` | PostgreSQL 18 单机编排，首启自动执行 `schema.sql` |
| `http://<host>:8000/docs` | 在线 OpenAPI 文档 |

> （注：部分内容由豆包 AI 生成）