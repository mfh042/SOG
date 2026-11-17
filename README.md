# SOG · 离散装配生产作业支援系统（DELV-SOG）

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
│   ├── run.py                   # Windows 启动脚本（自动启用 SelectorEventLoop）
│   ├── pyproject.toml
│   ├── .env.example             # 环境配置（连接池 / 线程 / 并发 / 跨域）
│   ├── uploads/sop/             # SOP 媒体文件存储（自动创建）
│   ├── scripts/csv_import.py    # 离线 CSV 批量导入脚本（orders / materials / boms）
│   ├── smoke_test.py            # 接口层端到端冒烟测试
│   └── app/
│       ├── main.py              # FastAPI 入口、CORS、异常处理、/health、静态文件挂载、种子初始化
│       ├── core/                # 基础设施层（config / db / deps / concurrency / response / exceptions / permissions）
│       ├── common/              # 枚举、分页、基类
│       ├── modules/             # 业务模块（router → service → repository → models → schemas）
│       │   ├── auth/            # JWT 鉴权 + RBAC 角色权限持久化（纯标准库 HS256 + PBKDF2 + role_permission 表）
│       │   ├── audit/           # 审计日志（关键操作自动记录）
│       │   ├── orders/          # 订单管理（含释放生成工单、CSV 批量导入）
│       │   ├── material/        # 物料管控（主数据 CRUD + CSV 导入 / 库存 / 流水 / FIFO）
│       │   ├── bom/             # BOM 头/行 CRUD + 激活版本切换 + CSV 导入 + 齐套检查
│       │   ├── production/      # 生产管理（工单 / 工序 / 报工 / 追溯 / BFS 树形）
│       │   ├── quality/         # 检验类型字典 + 检验登记 + 不良代码独立字典
│       │   ├── device/          # 设备直连骨架（OPC-UA / MQTT 协议模板）
│       │   ├── sop/             # SOP 作业指导（产品+工序+版本 + 媒体上传 + 图片标注）
│       │   ├── dashboard/       # 看板聚合（概览 KPI / 齐套告警）
│       │   └── migrations/schema.sql # PostgreSQL 18 DDL（幂等）
└── front/                       # Vue 3 前端（Vite）
    ├── package.json
    ├── vite.config.js           # /api 和 /uploads 代理到后端
    └── src/
        ├── api/                 # axios 封装 + 各模块接口（auth / materials / boms / orders / production / quality / sop / devices / auditLogs / inspectTypes / roles）
        ├── components/
        │   └── AnnotationEditor.vue  # 独立的 Canvas 图片标注编辑器（箭头/矩形/圆形/文字）
        ├── layouts/MainLayout.vue
        ├── router/index.js       # 路由守卫 + Pinia 权限校验
        ├── stores/auth.js       # Pinia JWT + 真实 RBAC 权限（从 /api/auth/me 获取）
        └── views/
            ├── LoginView.vue        # 登录界面
            ├── DashboardView.vue    # 运营看板
            ├── MaterialView.vue     # 物料主数据（CRUD + CSV 导入）
            ├── BomView.vue          # BOM 清单（CRUD + CSV 导入 + 齐套检查）
            ├── WorkOrderView.vue    # 生产工单
            ├── QualityView.vue      # 质量检验（检验类型动态加载）
            ├── InspectTypeView.vue  # 检验类型字典（7 种分类 × 4 种抽样策略）
            ├── DefectCodeView.vue   # 不良代码字典
            ├── DeviceView.vue       # 设备直连骨架（OPC-UA / MQTT）
            ├── SopView.vue          # SOP 作业指导（含上传/标注/多类型媒体预览）
            ├── TraceView.vue        # 批次追溯
            ├── InventoryView.vue    # 库存总览
            ├── inventory/           # 物料/消耗品/在制品管理中心
            ├── orders/              # 订单生产 / 订单调整 / 订单监控
            └── system/              # 用户管理 / 角色授权（RBAC 可编辑矩阵） / 操作日志（真实 API 接入）
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

sudo -u postgres psql -c "CREATE ROLE sog LOGIN PASSWORD 'sog_pass';"
sudo -u postgres psql -c "CREATE DATABASE sog OWNER sog;"
```

后端首次启动会**自动建表 + 写入种子数据**（4 个演示用户、6 个物料、12 个 SOP、7 个 SOP 模板），无需手动执行 DDL。

### 2. 后端

```bash
cd backend
cp .env.example .env                    # 按实际修改 DB 账号密码
uv sync                                 # 安装依赖（Python 3.11~3.12）

# macOS / Linux
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Windows（psycopg 需要 SelectorEventLoop）
uv run python run.py
# 或手动指定 loop：uv run uvicorn app.main:app --loop selector --host 0.0.0.0 --port 8000

# 健康检查：GET http://127.0.0.1:8000/health
# 接口文档：http://127.0.0.1:8000/docs
```

> ⚠️ **Windows 注意**：psycopg3 异步驱动不能用 ProactorEventLoop，必须用 `--loop selector` 或 `run.py`。

高并发部署（多核）：

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app   # worker 数 ≈ CPU×2+1
```

### 3. 前端（Vue 3 + Vite）

前端工程位于 `front/`，`vite.config.js` 将 `/api` 和 `/uploads` 代理到后端：

```bash
cd front
npm install
npm run dev      # http://127.0.0.1:5173  （或 5174 若 5173 被占用）
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
| `SOP_UPLOAD_DIR` | `backend/uploads` | SOP 媒体文件存储根目录 |
| `JWT_SECRET` | `change-me-in-production-please` | JWT 签名密钥，**生产必须更换**（32+ 字符随机串） |
| `JWT_ALGORITHM` | `HS256` | 签名算法 |
| `JWT_ACCESS_EXPIRE_MINUTES` | `120` | Access Token 有效期（分钟） |

### 6. 鉴权（JWT）

系统已落地 **JWT Bearer 鉴权**，密码哈希使用 **PBKDF2-HMAC-SHA256**。

```bash
# 登录 → 获取 Token
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# → {"code":0, "data":{"access_token":"eyJhbGciOi...","token_type":"bearer","expires_in":7200}}

# 带 Token 调业务接口
curl -H "Authorization: Bearer eyJhbGciOi..." http://127.0.0.1:8000/api/production/work-orders
```

**前端演示账号：**

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| planner | planner123 | 计划员 |
| operator | op123 | 操作工 |
| quality | qc123 | 质检员 |

> 用户注册入口已移至 **系统管理 → 用户管理**（前端界面），登录页仅保留登录功能。

---

## SOP 媒体上传与图片标注（最新）

SOP 模块已扩展支持**图片/PDF/视频**三种媒体类型上传，以及在图片上进行**交互式标注**：

### 后端接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/sops/upload` | 上传媒体文件（JPG/PNG/GIF/WebP/BMP / PDF / MP4/WebM/OGG/MOV，≤50MB），返回 `url` + `media_type` |
| GET | `/api/sops/files/{filename}` | 下载/预览已上传文件 |
| GET | `/api/sops/dynamic/{product_code}` | **动态 SOP**：完整工艺路线（含 BOM 指引 + 多类型媒体） |

新增字段（`sop` 表）：`media_type`（image/pdf/video）、`media_url`、`annotations`（JSONB 存储标注数据）。

### 前端 AnnotationEditor 组件

- **4 种标注工具**：箭头 → 、矩形框 ⬜、圆形 ⭕、文字 T
- **8 种颜色可选**
- **拖拽移动 / 角点调整大小**
- **撤销/重做**（Ctrl+Z / Ctrl+Shift+Z）、Delete 删除
- **归一化坐标存储**，不同尺寸图片标注位置一致
- **适配 Retina 屏**（devicePixelRatio）

---

## 验证

后端 `openapi.json` 已注册 **70+ 条路径**（auth / users / roles / materials / boms / orders / production / inspections / defect-codes / sops / devices / audit-logs / dashboard / health）。

**新增关键端点（近期实现）：**

| 方法 | 路径 | 说明 |
|---|---|---|
| PUT / DELETE | `/api/materials/{id}` | 物料主数据编辑 / 删除（删除前校验无库存台账） |
| POST | `/api/materials/import` | 物料 CSV 批量导入（幂等：已存在编码自动跳过） |
| POST | `/api/boms/import` | BOM CSV 批量导入（自动关联物料编码、支持多版本） |
| GET | `/api/boms/shortage/{bom_id}?qty=N` | BOM 齐套检查（需求展开 × 损耗率 × 订单量 vs 现有库存） |
| GET | `/api/auth/roles` | 角色权限列表（从 DB + 硬编码种子初始化） |
| GET | `/api/auth/permissions/catalog` | 可选权限清单（35 项） |
| PUT | `/api/auth/roles/{role}/permissions` | 保存角色权限（全量替换、写时清缓存） |
| GET | `/api/inspect-types` | 检验类型字典（7 种分类 × 4 种抽样策略） |
| GET | `/api/devices` | 设备直连骨架（OPC-UA / MQTT 协议模板） |
| GET | `/api/audit-logs` | 审计日志（关键操作自动记录） |

**CSV 编码自动兼容：** UTF-8-sig（Excel 默认导出）→ GBK（兼容中文系统），UTF-8 直读。

**在线文档自测** — 打开 `http://127.0.0.1:8000/docs`，按「鉴权 → 订单 → 物料 → 生产」顺序调用。最小验收路径：

1. **鉴权**：`POST /api/auth/login` 拿 Token → `GET /api/auth/users` 查列表。
2. **物料**：`POST /api/materials` 建成品 + 原料 → `POST /api/materials/inbound` 入库（带批次）。
3. **物料 CSV 导入**：前端 MaterialView 点击「📥 CSV 导入」→ 上传模板文件 → 后端自动解析、幂等创建。
4. **BOM CSV 导入**：前端 BomView 点击「📥 CSV 导入」→ 上传后自动关联物料编码。
5. **BOM 齐套**：`GET /api/boms/shortage/{bom_id}?qty=10` 展开 BOM 算缺料明细。
6. **订单**：`POST /api/orders` 建单 → `PUT /api/orders/{id}?version=1` 验证乐观锁 → `POST /api/orders/{id}/release` 生成工单并看缺料告警。
7. **领料**：`POST /api/materials/issue`（不传批次验证 FIFO）→ `GET /api/materials/transactions` 看流水。
8. **生产**：工单流转 `RELEASED` → `RUNNING` → `GET /{id}/operations` 看工序 → `POST /{id}/report` 逐工序报工（首道带 `materials`）→ 末道报满自动入成品仓。
9. **质量**：`POST /api/defect-codes` 建不良代码 → `POST /api/production/inspections` 登记检验 → `GET /api/production/inspections/stats` 看统计。
10. **检验类型**：`GET /api/inspect-types` 拿 7 种分类 + 4 种抽样策略 → QualityView 下拉动态加载。
11. **SOP 动态**：`GET /api/sops/dynamic/GB-100` 拿到完整工艺路线 + BOM + 各工序内容。
12. **SOP 上传 & 标注**：`POST /api/sops/upload` 上传图片 → 在 SopView 中使用 AnnotationEditor 标注 → `PUT /api/sops/{id}` 保存 annotations。
13. **追溯**：`GET /api/production/trace/forward/{product_batch}`、`/backward/{material_batch}`、`/tree/{product_batch}`、`/bfs/{product_batch}?max_depth=4` 查四条路径。
14. **RBAC 角色权限**：系统管理 → 角色授权 → 勾选权限矩阵 → 保存后权限立即生效（`require_perm` 实时查 DB）。
15. **审计日志**：系统管理 → 操作日志 → 真实 API 接入，多条件过滤、分页。

---

## 文档索引

| 文档 | 内容 |
|---|---|
| [SOG系统产品说明书.md](SOG系统产品说明书.md) | 完整版：产品定位、角色、功能地图、业务规则、系统架构、数据模型、集成设计、验收用例 |
| [SOG系统产品说明书_简约版.md](SOG系统产品说明书_简约版.md) | 对外客户版：核心痛点、功能亮点、技术架构、实施路径 |
| [SOG前端功能说明书.md](SOG前端功能说明书.md) | 开发版：页面路由、组件结构、权限矩阵、API 模块对应关系 |
| [build_ppt.py](ppt/build_ppt.py) | PPT 生成脚本（浅蓝色科技感主题，34 页，真实系统截图） |
| [take_screenshots.py](ppt/take_screenshots.py) | Playwright 自动截图脚本（连接本地 Chrome，截取 22 张真实界面） |
| `http://<host>:8000/docs` | 在线 OpenAPI 文档（70+ 接口） |