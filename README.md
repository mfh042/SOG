# SOG · 离散装配生产作业支援系统

面向**离散型制造装配车间**的现场作业支援（SOG，Standard Operation Guidance）系统，定位为 MOM 体系中与 MES 配套的「生产作业支援子系统」：**轻工单、重现场资料与异常协同**，同时补齐**订单 → 物料 → 生产**三域闭环。

| 模块 | 能力（✅ 已实现 / ◐ 部分 / ○ 规划） |
|---|---|
| 订单管理 | ✅ 创建/列表/详情、草稿编辑乐观锁、状态机流转　○ BOM 齐套校验、释放生成工单 |
| 物料管控 | ✅ 三态库存、批次、入库/预留/释放/领料、流水、安全库存预警　○ BOM 维护、齐套检查接口、库存调整 |
| 生产管理 | ✅ 工单创建与状态流转、工单级报工、报废、进度　○ 工序路由、逐工序报工、幂等键、批量/并行报工、末道自动入库 |
| 质量管理 | ✅ 检验登记（PASS/FAIL/REWORK）、质量统计与不良 Top　◐ 不良代码字段　○ 不良代码库与处置图册、首检/过程检/终检细分 |
| SOP 作业指导 | ○ 按「产品 + 工序 + 版本」下发、步骤/检查点/扭矩要求、阅读确认与改版提醒 |
| 生产追溯 | ✅ 正反向批次查询（trace_record 事件流）　○ 树形链路与深度展开 |
| 生产总览看板 | ○ 订单/工单/产出/合格率/低库存 KPI、7 天趋势、状态分布、不良 Top |
| 集成 | ○ ERP 订单与过账、MES 事件、PLC/拧紧/焊接/扫码设备接入（契约已在产品说明书中定义） |

技术栈：**Python 3.12 + FastAPI + SQLAlchemy 2（async）+ PostgreSQL 18 + Vue 3 + Element Plus + ECharts**。

> 完整产品说明、功能详述、数据模型、并发设计、集成方案、实施路径、验收用例、错误码与术语，详见 [SOG系统产品说明书.md](SOG系统产品说明书.md)。

---

## 1. 与 MES 的差异

| 对比项 | MES | 本 SOG 系统 |
|---|---|---|
| 重心 | 排产、工单执行、报工采集、产量统计 | 现场作业指引 + 物料齐套 + 进度/质量/追溯闭环 |
| 数据粒度 | 工单 / 产线 | **批次（batch）+ 工序（operation）** |
| 现场价值 | 计划达成 | 操作工不用翻纸质图纸，扫码即看 SOP、报工即入账、异常可追溯 |

边界一句话：**ERP 管钱和单，MES 管计划和产，SOG 管工位怎么干、干得对不对、出了事查得到。**

---

## 2. 目录结构

```
dev/
├── README.md                    # 快速上手（本文档）
├── SOG系统产品说明书.md          # 产品说明书 / 技术方案（完整版，含实现状态标注）
├── docker-compose.yml           # 容器编排（PG18 + 后端 + Nginx）
├── backend/                     # FastAPI 后端（当前实现）
│   ├── pyproject.toml
│   ├── .env.example             # 环境配置（连接池 / 线程 / 并发 / 跨域）
│   └── app/
│       ├── main.py              # FastAPI 入口、CORS、异常处理、/health
│       ├── core/                # 基础设施层
│       │   ├── config.py        # Settings：连接池 / 线程池 / 并发限流
│       │   ├── db.py            # async engine、AsyncSessionLocal、get_session
│       │   ├── deps.py          # 请求会话、分页、操作人（X-Operator，JWT 预留）
│       │   ├── concurrency.py   # run_in_threadpool、gather_limited、parallel_map
│       │   ├── response.py      # 统一 Resp / PageData 包装
│       │   └── exceptions.py    # BizException 体系 + 全局异常处理
│       ├── common/              # 枚举 enums、分页 pagination、基类 base
│       ├── modules/             # 业务模块（router → service → repository → models → schemas）
│       │   ├── orders/          # 订单管理
│       │   ├── material/        # 物料管控（主数据 / 库存 / 流水）
│       │   └── production/      # 生产管理（工单 / 进度 / 质量 / 追溯）
│       ├── migrations/schema.sql # PostgreSQL 18 DDL（9 表 + 1 视图 + 索引）
│       └── jobs/                # 后台 / 定时任务预留
└── front/                       # Vue 3 前端工程（Vite，已实现 6 个页面）
    ├── package.json
    ├── vite.config.js           # /api 代理到后端
    └── src/
        ├── api/                 # request（统一解包 Resp + X-Operator）、orders、materials、production
        ├── layouts/MainLayout.vue
        ├── router/index.js      # orders / materials / inventory / work-orders / quality / trace
        └── views/               # OrderView / MaterialView / InventoryView / WorkOrderView / QualityView / TraceView
```

后端分层约定：`router`（参数校验 / 响应序列化）→ `service`（业务规则 / 状态机 / 事务）→ `repository`（SQL 与行级锁）→ `models`（ORM 表定义）；请求级会话由 `core.deps.get_db` 注入。业务模块之间不互相 import service，只通过 repository / session 解耦。

---

## 3. 快速启动

### 3.1 数据库（PostgreSQL 18）

```bash
# 方式一：本机安装
sudo apt install -y postgresql-18 && sudo pg_ctlcluster 18 main start

# 方式二：容器
docker compose up -d postgres

sudo -u postgres psql -c "CREATE ROLE sog LOGIN PASSWORD 'sog123456';"
sudo -u postgres psql -c "CREATE DATABASE sog OWNER sog;"
```

建表可用 `backend/app/migrations/schema.sql`（幂等 `CREATE TABLE IF NOT EXISTS`）：

```bash
psql -h 127.0.0.1 -U sog -d sog -f backend/app/migrations/schema.sql
```

### 3.2 后端

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

重置 schema：

```bash
psql -h 127.0.0.1 -U sog -d sog -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### 3.3 前端（Vue 3 + Vite）

前端工程位于 `front/`，`vite.config.js` 将 `/api` 代理到后端（开发模式 5173，生产构建 `dist/` 可由 Nginx 或后端静态托管）：

```bash
cd front
npm install
npm run dev      # http://127.0.0.1:5173
npm run build    # 产物 dist/
```

### 3.4 容器化（可选）

```bash
docker compose up -d --build
# 前端 http://localhost:8080 ，API /api（目标形态 /api/v1），文档 /docs
```

### 3.5 环境变量

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

### 3.6 操作人（演示）

当前版本**无登录接口**，操作人通过请求头 `X-Operator` 透传（前端 `localStorage.operator` 默认 `system`）：

```bash
curl -H "X-Operator: operator" http://127.0.0.1:8000/api/production/work-orders
```

前端演示可用角色（供后续 JWT 鉴权落地时复用）：admin / planner / operator（ST-01）/ quality。JWT 登录与按钮级权限为规划能力（产品说明书第 2.1、5.1 节）。

---

## 4. 核心业务流（当前实现可跑通的部分）

```
创建销售订单（草稿） → 编辑（乐观锁） → 状态流转至 RELEASED / IN_PROGRESS
物料入库（原料/半成品，批次 + 库位） → 预留 → 领料出库（原料仓 → 在制品仓，行级锁）
创建工单 → PLANNED → RELEASED → RUNNING → 报工（合格/不良）→ 报废登记 → DONE / SCRAPPED
报工进度记录查询 → 质量检验登记（检验项 + 不良代码）→ 质量统计（判定分布 + 不良 Top）
正/反向批次追溯（trace_record 事件流）
```

规划形态（○，需按产品说明书第 11 章补齐）：订单释放自动生成工单 + BOM 齐套校验、逐工序报工、末道自动入成品仓、SOP 下发、看板、ERP/MES/设备集成。

演示数据口径（目标形态）：客户「天津精工机械有限公司」订单 50 台；五道工序 OP10 上料 / OP20 装配 / OP30 拧紧 / OP40 检验 / OP50 包装入库；BOM 用量 1/1/4；SOP（OP20 装配，扭矩 25N·m）。

---

## 5. 接口速查（前缀 `/api`）

| 模块 | 方法与路径 | 说明 |
|---|---|---|
| 订单 | `POST /api/orders`、`GET /api/orders`、`GET /api/orders/{id}`、`PUT /api/orders/{id}?version=`、`POST /api/orders/{id}/transition?target=` | 状态机 DRAFT→RELEASED→IN_PROGRESS→COMPLETED→CLOSED，编辑走乐观锁 |
| 物料 | `POST /api/materials`、`GET /api/materials` | 物料主数据（RAW / WIP / FINISHED） |
| 库存 | `POST /api/materials/inbound`、`/reserve`、`/release`、`/issue`、`GET /api/materials/inventory`、`/transactions`、`/low-stock` | 行级锁扣减、流水留痕、低库存预警 |
| 工单 | `POST /api/production/work-orders`、`GET /api/production/work-orders`、`GET /{id}`、`POST /{id}/transition`、`POST /{id}/report`、`POST /{id}/scrap` | 工单状态机与报工 / 报废 |
| 进度 | `GET /api/production/progress` | 报工进度记录 |
| 质量 | `POST /api/production/inspections`、`GET /api/production/inspections`、`GET /api/production/quality-stats` | 检验登记与合格率 / 不良 Top |
| 追溯 | `GET /api/production/trace/forward?product_batch=`、`GET /api/production/trace/backward?material_batch=` | 正向扩散 / 反向回溯 |
| 系统 | `GET /health`、`GET /docs`、`GET /openapi.json` | 探活与在线接口文档 |

统一响应包装：`{"code": 0, "message": "ok", "data": ...}`；分页为 `data.items / total / page / size`。

---

## 6. 并发与性能设计（速览）

| 层次 | 手段 | 说明 |
|---|---|---|
| 连接层 | asyncpg / psycopg3 异步连接池 `pool_size=20, max_overflow=30` | 单进程最多 50 连接，`pool_pre_ping` + `pool_recycle=1800` |
| 事务层 | `SELECT ... FOR UPDATE`（`with_for_update(of=...)`） | 库存余额行锁串行化，防超扣；**必须带 `of=`** |
| 乐观锁 | 订单 / 工单 `version` 字段 | 编辑前比对版本，冲突返回 409 |
| 状态机 | `TRANSITIONS` / `WO_TRANSITIONS` 白名单 | 非法流转直接拒绝 |
| 并行层 | `asyncio.gather` + `gather_limited(limit)` / `parallel_map` | 多工单、多物料查询与批量处理并发受限 |
| 线程层 | `run_in_threadpool`（`WORKER_THREADS=16`） | 阻塞 IO 与 CPU 计算不阻塞事件循环 |

> 完整并发方案（幂等键、显式提交换取写后读一致、实测数据、横向扩展建议）见产品说明书第 6.4 节。

---

## 7. 验证

当前仓库**未提供自动化测试脚本**，推荐以下两种验证方式：

**方式一：在线文档自测** — 打开 `http://127.0.0.1:8000/docs`，按「订单 → 物料 → 生产」顺序调用。最小验收路径：

1. `POST /api/materials` 建 1 个成品 + 2 个原料物料；`POST /api/materials/inbound` 入库（带批次）。
2. `POST /api/orders` 建单 → `PUT /api/orders/{id}?version=1` 验证乐观锁 → `POST /api/orders/{id}/transition?target=RELEASED`。
3. `POST /api/materials/reserve` → `/issue`，验证库存扣减与 `GET /api/materials/transactions` 流水。
4. `POST /api/production/work-orders` 建工单 → 流转 `RELEASED` → `RUNNING` → `POST /{id}/report` 报工 → `GET /api/production/progress`。
5. `POST /api/production/inspections` 登记检验 → `GET /api/production/quality-stats` 看统计。
6. `GET /api/production/trace/forward` 与 `/backward` 查追溯事件。

**方式二：curl 冒烟** — 见 `docker-compose.yml` 起库 + `uv run uvicorn` 起服务后，逐条调用上述接口。

并发验证建议：在手 100 的批次上并发 20 次各领 10，应只有 10 次 200，其余 409「可用库存不足」，且在手量不为负（行锁生效）。更完整的用例清单见产品说明书第 12 章。

---

## 8. 已知限制

- **代码现状**：`backend/` 为「订单 / 物料 / 生产（工单 · 进度 · 质量 · 追溯）」三模块 9 表 1 视图，REST 前缀 `/api`；报工为**工单级**（只累加合格/报废数量并写进度与追溯事件），**不联动库存**；工单无 PUT 修改接口；无 BOM 表。
- **前端现状**：`front/` 已实现订单、物料、库存、工单、质量、追溯 6 个页面与统一请求封装，无登录页与看板页。
- **文档规划态**：订单释放生成工单、BOM 齐套、工序路由与逐工序报工、报工幂等键、末道自动入库、SOP、看板、JWT 鉴权、`/api/v1` 37 个接口为**目标形态**，标 ○ / ◐ 者未实现。
- **鉴权**：无登录接口，操作人由 `X-Operator` 头透传，未接入企业 SSO 与按钮级权限矩阵。
- **迁移**：未引入 Alembic，表结构由 `schema.sql` 建立，生产升级需人工脚本。
- **集成**：设备直连（OPC UA / 拧紧 / 焊接 / 扫码）与 ERP / MES 对接仅完成接口契约设计，未实现驱动与适配层。
- **一致性**：写端点为请求级会话，提交发生在响应之后（`yield session` → `commit`），高并发写需按产品说明书 6.4.3 改为显式 commit。

---

## 9. 文档索引

| 文档 | 内容 |
|---|---|
| [SOG系统产品说明书.md](SOG系统产品说明书.md) | 产品定位、角色、功能地图与实现状态、业务规则与状态机、功能详述、系统架构、数据模型、ERP/MES/设备集成设计、非功能需求、部署运维、实施路径、验收用例、错误码与术语（原 `architecture.md` 与《技术方案》内容已全部并入） |
| `docker-compose.yml` | PostgreSQL 18 单机编排，首启自动执行 `schema.sql` |
| `http://<host>:8000/docs` | 在线 OpenAPI 文档 |

> （注：部分内容由豆包 AI 生成）