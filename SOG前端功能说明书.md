# SOG 系统 · 前端功能说明书

| 项目 | 内容 |
|---|---|
| 技术栈 | Vue 3 + Vite + Pinia + Element Plus + Axios |
| 源码路径 | `E:\999-Dev\04-SOG\dev\front` |
| 页面数量 | 26 个视图组件（含子目录） |
| API 封装 | 13 个模块（`src/api/`） |
| 文档版本 | V2.0（2026-11-17） |

---

## 一、整体架构

```
front/src/
├── App.vue                      根组件（全局样式 / 路由出口）
├── main.js                      入口（Vue + Pinia + Router + ElementPlus）
├── router/index.js              路由表 + 路由守卫（鉴权 + 权限校验）
├── stores/auth.js               Pinia 用户/Token/权限（5 角色 × 35 权限）
├── api/
│   ├── request.js               Axios 封装（拦截器 / 401 跳转 / 错误提示）
│   ├── auth.js                  login / register / getMe
│   ├── materials.js             物料 CRUD + CSV 导入 + 入出库 + 盘点 + **流水查询**
│   ├── boms.js                  BOM 头/行 CRUD + CSV 导入 + 齐套检查
│   ├── orders.js                订单 CRUD + CSV 导入 + 释放 + **批量释放** + **调整**
│   ├── production.js            工单 / 工序 / 报工 / 报废 / 追溯四路
│   ├── inspectTypes.js          检验类型字典 CRUD
│   ├── defectCodes.js           不良代码字典 CRUD
│   ├── quality.js               质量检验登记 + 统计
│   ├── sops.js                  SOP CRUD + 媒体上传 + 模板管理 + 动态 SOP
│   ├── devices.js               设备注册 + 协议模板查询
│   ├── auditLogs.js             审计日志列表 + 动作枚举
│   ├── roles.js                 listRoles / getCatalog / saveRolePermissions
│   └── dashboard.js             看板聚合 KPI
├── layouts/MainLayout.vue       主布局（侧边栏菜单 + 顶栏 + 内容区）
├── components/
│   └── AnnotationEditor.vue     SOP 图片交互式标注（Canvas 2D）
└── views/
    ├── LoginView.vue            登录页
    ├── DashboardView.vue        运营看板
    ├── MaterialView.vue         物料主数据
    ├── BomView.vue              BOM 清单
    ├── InspectTypeView.vue      检验类型字典（已移至主数据管理）
    ├── DefectCodeView.vue       不良代码字典（已移至主数据管理）
    ├── QualityView.vue          质量检验
    ├── SopView.vue              SOP 作业指导（动态 SOP + 模板管理 + 标注）
    ├── TraceView.vue            批次追溯（正/反/树/BFS 四路）
    ├── DeviceView.vue           设备直连
    ├── orders/                  生产订单子目录
    │   ├── OrderWorkView.vue        生产工单（多 props：work / release / adjust / monitor）
    │   └── ...
    ├── inventory/               物资管理子目录（四大中心）
    │   ├── InventoryHub.vue         物料管理中心 / 消耗品管理中心（通过 stockType props 切换）
    │   ├── WipHub.vue               在制品管理中心（WIP 看板 + 龄期 + 瓶颈）
    │   └── StockTxnView.vue         批次与流水（异动全链路追踪）
    └── system/                  系统子目录（User / Roles / Logs）
```

---

## 二、登录与鉴权

### 2.1 登录页 `/login`

| 功能 | 说明 |
|---|---|
| 账号密码登录 | 调 `POST /api/auth/login`，返回 JWT `access_token` |
| Token 持久化 | `localStorage.sog_token` + `localStorage.sog_user` |
| 登录后刷新 | 自动调 `GET /api/auth/me` 拿真实用户信息（含 role） |
| 登录页跳转 | 已登录访问 `/login` → 跳 `/dashboard`；未登录访问受限页 → 跳 `/login?redirect=原路径` |

### 2.2 路由守卫

```
router.beforeEach(async (to) => {
  1. 路由 meta.public → 直接放行
  2. localStorage 无 token → 跳登录
  3. auth.user 未初始化 → 调 refreshUser()（失败跳登录）
  4. meta.perm 存在 → auth.hasPerm(perm) 校验，无权限跳 dashboard
})
```

### 2.3 权限矩阵（前端硬编码 + 后端实时可配）

| 角色 | 权限数 | 典型权限 |
|---|---|---|
| **ADMIN** | `*`（全部） | 系统管理 + 全部业务 |
| **MANAGER** | 26 | 物料/BOM/订单/生产/质量/SOP/看板/追溯/审计 |
| **PLANNER** | 19 | 订单 + BOM + 物料 + 生产发布 + SOP |
| **QUALITY** | 11 | 质量 + 不良代码 + 追溯 + 看板 |
| **OPERATOR** | 9 | 报工 + 领料 + SOP + WIP + 看板 |

权限按模块分组：material / bom / orders / production / quality / defect / sop / inventory / wip / device / trace / dashboard / admin。

---

## 三、主布局 · 侧边栏菜单

`layouts/MainLayout.vue` 根据登录角色动态渲染菜单项（无权限菜单不显示）：

```
📊 运营看板                         → /dashboard

🔐 系统管理
   ├── 用户管理                     → /system/users
   ├── 角色授权                     → /system/roles
   └── 审计日志                     → /system/logs

📋 主数据管理
   ├── 物料主数据                   → /materials
   ├── BOM 清单                     → /boms
   ├── 检验类型字典                  → /inspect-types
   └── 不良代码字典                  → /defect-codes

📦 物资管理
   ├── 物料管理中心                  → /inventory/hub          (InventoryHub.vue, stockType='RAW')
   ├── 消耗品管理中心                → /consumables/hub         (InventoryHub.vue, stockType='CONSUMABLE')
   ├── 在制品管理中心                → /wip/hub                (WipHub.vue)
   └── 批次与流水                    → /stock/txn              (StockTxnView.vue)

📝 生产订单
   ├── 生产工单                      → /orders/work            (OrderWorkView.vue)
   ├── 生产发布                      → /orders/release         (OrderWorkView.vue, focusRelease=true)
   └── 订单调整                      → /orders/adjust          (OrderWorkView.vue)

⚙️ 生产管理
   ├── 生产执行监控                  → /orders/monitor         (OrderWorkView.vue)
   ├── 质量检验                      → /quality
   ├── SOP 作业指导                  → /sops
   └── 批次追溯                      → /trace

💻 设备管理
   └── 设备直连                      → /devices
```

顶栏显示：当前用户（display_name + role 标签）+ 登出按钮。

---

## 四、各页面功能详述

### 4.1 运营看板 `/dashboard` — `DashboardView.vue`

| 功能 | 实现 |
|---|---|
| KPI 卡片 | 订单总数 / 进行中工单 / 今日检验数 / 低库存告警（调 `/api/dashboard` 聚合） |
| 工单状态分布图 | ECharts 饼图（PLANNED / RELEASED / RUNNING / DONE） |
| 近 7 天报工趋势 | ECharts 折线图（日合格 + 日报废） |
| 齐套告警列表 | 最近 10 条缺料告警 |
| 权限 | `dashboard:read` |

---

### 4.2 用户管理 `/system/users` — `UserView.vue`

| 功能 | 实现 |
|---|---|
| 用户列表 | username / display_name / role / is_active |
| 新建用户 | username + password + display_name + role 下拉 |
| 启停账号 | 行内开关（toggleActive） |
| 权限 | `admin:*` |

### 4.3 角色授权 `/system/roles` — `RolesView.vue`

| 功能 | 实现 |
|---|---|
| **可视化权限矩阵** | 行=权限项（13 模块分组），列=5 个角色，勾选框表示是否拥有 |
| **ADMIN 锁定** | ADMIN 角色永远全部勾选，禁用编辑（灰色不可点） |
| **单角色保存** | 每列头有 💾 保存按钮，仅保存该角色的变更 |
| **批量保存** | 顶部 `💾 批量保存全部变更` → 确认弹窗 → 一次性提交所有变更角色 |
| **脏标记** | 有变更未保存的角色列头显示 `*` |
| 数据来源 | `GET /api/auth/roles` + `GET /api/auth/permissions/catalog`，保存 `PUT /api/auth/roles/{role}/permissions` |
| 实时生效 | 保存后后端清缓存，`require_perm` 立即生效 |
| 权限 | `admin:*` |

### 4.4 审计日志 `/system/logs` — `LogsView.vue`

| 功能 | 实现 |
|---|---|
| 真实 API 接入 | 调 `GET /api/audit-logs`（无硬编码假数据） |
| 多条件过滤 | action 下拉 + actor 输入 + target 输入 + 时间范围 |
| 分页 | 服务端分页（page / size） |
| 动作标签着色 | 绿色=成功 / 红色=失败 / 蓝色=变更 / 灰色=读取 |
| 权限 | `admin:audit` |

---

### 4.5 物料主数据 `/materials` — `MaterialView.vue`

| 功能 | 实现 |
|---|---|
| 列表 | 分页表格，显示 code / name / type / unit / safety_stock / status |
| 搜索 | 按编码/名称模糊过滤，按 type 下拉过滤 |
| 新建 | `+ 新建物料` 弹窗，表单校验必填项 |
| 编辑 | 行内「编辑」按钮 → 弹窗修改 |
| 删除 | 行内「删除」→ 二次确认 → `DELETE /api/materials/{id}`（后端校验库存引用） |
| **CSV 批量导入** | `📥 CSV 导入` → `POST /api/materials/import`；UTF-8-sig/GBK/UTF-8 自动兼容；已存在编码跳过（幂等） |
| 模板下载 | `📄 下载模板` 提供空 CSV 模板 |
| 低库存标红 | 当前库存 < safety_stock 的行自动高亮 |
| 权限 | `material:read` / `material:create` / `material:update` |

**CSV 模板列**：`code, name, type, spec, unit, safety_stock, status`

---

### 4.6 BOM 清单 `/boms` — `BomView.vue`

| 功能 | 实现 |
|---|---|
| BOM 头列表 | 产品编码 / 版本 / 是否激活 / 状态 |
| BOM 详情 | 点击行 → 右侧面板显示组件明细 |
| 新建 BOM | 选成品物料 + 填版本 + 行内添加组件 |
| 激活版本切换 | 行内「激活」→ 停用旧版、启用新版 |
| 删除 | 停用状态下可删 |
| **CSV 批量导入** | `📥 CSV 导入` → 一行一个组件行，自动关联 material 编码 |
| **齐套检查** | 行内「🔍 齐套」→ 弹窗输入订单数量 → `GET /api/boms/shortage/{bom_id}?qty=N` → 显示缺料清单（组件/需求/可用/缺口/齐套率） |
| 权限 | `bom:read` / `bom:create` / `bom:update` / `bom:delete` |

**CSV 模板列**：`product_code, component_code, version, qty_per, loss_rate, seq`

---

### 4.7 检验类型字典 `/inspect-types` — `InspectTypeView.vue`

| 功能 | 实现 |
|---|---|
| 列表 | code / name / category / sampling_strategy / is_active |
| 新建 / 编辑 | category 下拉（7 选 1：IQC/IPQC/PQC/FQC/OQC/SPQC/CUSTOM）；sampling_strategy 下拉（4 选 1：100%/AQL/FIXED/RANDOM） |
| 启停切换 | 行内开关 |
| 删除 | 停用状态下可删 |
| 权限 | `quality:read` |

### 4.8 不良代码字典 `/defect-codes` — `DefectCodeView.vue`

| 功能 | 实现 |
|---|---|
| 列表 | code / name / category / severity / is_active |
| 过滤 | 按 category / severity 下拉过滤 |
| 新建 / 编辑 | code（唯一）/ name / category / severity / **disposal_guide（处置指引）** |
| 启停切换 | 行内开关 |
| 权限 | `defect:read` / `defect:create` / `defect:update` |

---

### 4.9 物料管理中心 `/inventory/hub` — `InventoryHub.vue`（stockType=RAW）

Tab 四合一操作台：

| Tab | 功能 | API |
|---|---|---|
| **📊 库存查询** | 批次级台账（material / batch / qty_on_hand / qty_reserved / available）；低库存过滤；多维度搜索 | `GET /api/materials/` + `GET /api/materials/low-stock` |
| **📥 入库登记** | 选物料 → 输入数量 / 批次号（可自动生成）/ 库位 → 确认入库 | `POST /api/materials/inbound` |
| **📤 出库操作** | 选物料 → 系统 FIFO 自动选最早批次 → 填数量 + 关联工单（可选）→ 确认出库 | `POST /api/materials/issue` |
| **📋 盘库管理** | 打印盘点单 → 现场清点 → 录入差异数量 → 系统自动盘盈盘亏调账（同时写流水） | `POST /api/materials/adjust`（调差）+ `POST /api/materials/scrap`（报废） |

每次入库/出库/调整/报废 → **自动写入 `stock_transaction` 流水表**。

权限：`inventory:all`

### 4.10 消耗品管理中心 `/consumables/hub` — `InventoryHub.vue`（stockType=CONSUMABLE）

与物料管理中心复用 `InventoryHub.vue` 组件，通过 `props.stockType='CONSUMABLE'` 切换过滤条件。独立库位，领用绑定工单（成本归集）。

权限：`inventory:all`

### 4.11 在制品管理中心 `/wip/hub` — `WipHub.vue`

| 功能 | 实现 |
|---|---|
| WIP 看板 | 实时展示各工序在制数量堆叠柱图 |
| 龄期分析 | 按在制品停留时间分桶（0-4h / 4-8h / 8-24h / >24h）→ 热力图 |
| 瓶颈识别 | 对比前后工序速率 → 高亮瓶颈工序 |
| 批次追踪 | 点击 WIP → 关联追溯模块查上游原料批次 |
| 过滤 | 按车间 / 产线 / 产品下拉 |
| 超期预警 | 超 24h 在制品自动标红 |
| 权限 | `wip:read` |

### 4.12 批次与流水 `/stock/txn` — `StockTxnView.vue`

**所有出入库操作自动写入流水表，前端页面专门展示和查询：**

| 功能 | 实现 |
|---|---|
| 流水列表 | 全量 `stock_transaction` 记录（批次号 / 物料 / 操作类型 / 数量 / 结存 / 关联单据 / 操作人 / 时间） |
| 7 种类型 | 入库（绿）/ 出库（红）/ 预留（橙）/ 释放（蓝）/ 报废（红）/ 盘盈（绿）/ 盘亏（红） |
| 多维度过滤 | 操作类型下拉 + 批次号输入 + 关键词搜索（操作人/备注/关联单号） |
| 数量颜色 | 绿正 / 红负，结存蓝底高亮 |
| 关联追溯 | 点击批次号 → 可跳转到追溯模块查全链路 |
| 权限 | `inventory:all` |

---

### 4.13 生产工单 `/orders/work` — `OrderWorkView.vue`

**多 props 复用组件：**

| 路由 | props | 行为差异 |
|---|---|---|
| `/orders/work` | 默认 | 全部订单展示 |
| `/orders/release` | `focusRelease=true` | 自动筛选状态=DRAFT（草稿待下达），方便直接操作下达按钮 |
| `/orders/adjust` | — | 显示拆分 / 排产 / 调数量 / 锁定解锁按钮 |
| `/orders/monitor` | — | 6 KPI 卡 + 状态分布图 + 逾期标红 + 快捷状态推进 |

**通用功能：**

| 功能 | 实现 |
|---|---|
| 工单列表 | order_no / 产品 / 客户 / 计划量 / 优先级(P1-P5) / 状态 / 计划日期 |
| CSV 导入 | `POST /api/orders/import`，幂等防重 |
| 新建 | 弹窗：客户 + 产品 + 数量 + 优先级 + 计划日期 |
| **生产发布（下达）** | 单条：`POST /api/orders/{id}/release` → 后端齐套检查 → 通过则状态→RELEASED 并自动生成工单；缺料则弹清单。支持批量：`POST /api/orders/batch-release` |
| **齐套检查** | `GET /api/orders/{id}/kit-check` → 下达前弹出 |
| **订单调整** | 单项：拆分 / 调数量 / 锁定解锁；批量：批量发布 / 批量锁定；状态保护：已锁定/取消/完工的禁用编辑 |
| 状态机 | DRAFT → RELEASED → RUNNING → DONE → CLOSED |
| 权限 | `orders:read` / `orders:update` |

---

### 4.14 生产执行监控 `/orders/monitor` — `OrderWorkView.vue`

| 功能 | 实现 |
|---|---|
| 6 KPI 卡 | 总订单 / 已下达 / 生产中 / 已完工 / 逾期 / 完工率 |
| 状态分布 | 条图 + 饼图 |
| 逾期标红 | 计划日期已过且未完工的订单自动标红 |
| 优先级列 | P1-P2 紧急订单独立展示 |
| 快捷推进 | 每行按钮：下达 → 投产 → 完工 → 关闭 |
| 权限 | `orders:read` |

---

### 4.15 质量检验 `/quality` — `QualityView.vue`

| 功能 | 实现 |
|---|---|
| 检验列表 | 工单 / 产品 / **检验类型** / 工序 / 结果 / 不良代码 / 检验人 / 时间 |
| **录入检验** | 弹窗：工单（下拉）/ **检验类型（动态从 `/api/inspect-types` 加载）** / 工序序号 / 样本数 / 判定（PASS/FAIL/REWORK）/ 不良代码（FAIL 时必填，从 `/api/defect-codes` 加载） |
| 自动联动 | 检验类型选中后自动填充 category / sampling_strategy；抽样数自动计算 |
| 权限 | `quality:read` / `quality:create` / `quality:update` |

### 4.16 SOP 作业指导 `/sops` — `SopView.vue`

**三个 Tab + 一个弹窗体系：**

#### Tab 1：动态 SOP（工位扫码即看）

| 功能 | 实现 |
|---|---|
| 产品选择 | 下拉选产品编码 |
| 工艺路线展示 | 5 道工序步骤条（可自定义） |
| 工序内容 | 左/右切换，显示 title + content + 媒体预览 |
| BOM 关联 | 底部显示该产品激活 BOM 组件清单 |
| 接口 | `GET /api/sops/dynamic/{product_code}` |

#### Tab 2：静态 SOP 管理

| 功能 | 实现 |
|---|---|
| 搜索 | 产品编码 / 工序序号 / 版本 / 状态 |
| **新建 SOP** | 1000px 宽弹窗：左表单 + 右图片标注区 |
| **媒体上传** | JPG/PNG/GIF/PDF/MP4/WebM，≤ 50MB，UUID 重命名 |
| **交互式图片标注**（`AnnotationEditor.vue`） | Canvas 2D：箭头 / 矩形框 / 圆形 / 文字；8 色；Ctrl+Z 撤销 / Ctrl+Shift+Z 重做；Delete 删除；滚轮缩放 + 拖拽平移；**归一化坐标存储**（任意缩放不失真） |
| 编辑 / 停用 | 修改内容 / 替换媒体 / 调整标注；新版发布自动停用旧版 |

#### Tab 3：SOP 模板管理

| 功能 | 实现 |
|---|---|
| 内置模板 | 系统默认 7 套（装配 / 检验 / 包装 / 通用等） |
| 自定义模板 | 支持 `{product}` `{code}` `{operation}` `{seq}` 占位符一键填充 |

权限：`sop:read` / `sop:create` / `sop:update` / `sop:upload`

---

### 4.17 批次追溯 `/trace` — `TraceView.vue`

四路追溯（Tab 切换）：

| 路径 | 输入 | 接口 | 回答的问题 |
|---|---|---|---|
| **正向 Forward** | 成品批次号 | `GET /api/production/trace/forward/{product_batch}` | 这批成品用了哪些原料、哪个工单生产的 |
| **反向 Backward** | 原料批次号 | `GET /api/production/trace/backward/{material_batch}` | 这批原料被用在了哪些工单、最终成品批号 |
| **树形 Tree** | 成品批次号 | `GET /api/production/trace/tree/{product_batch}` | 成品 → WIP → 原料的层级展开 |
| **BFS 广度优先** | 成品批次号 + 最大深度 | `GET /api/production/trace/bfs/{product_batch}?max_depth=N` | 限制深度的批量追溯 |

每行事件：event_type / product_batch / material_batch / qty / wo_no / logged_at。

权限：`trace:read`

---

### 4.18 设备直连 `/devices` — `DeviceView.vue`

卡片式 UI（**骨架页面，预留后续扩展**）：

| 协议 | 默认地址格式 | 默认节点/主题 | 典型用途 |
|---|---|---|---|
| **OPC-UA** | `opc.tcp://host:4840` | `ns=3;s=ProductionLine1.Tag1` | PLC 实时点位采集 |
| **MQTT** | `mqtt://host:1883` | `sog/{line}/telemetry` | 设备遥测上报 |

支持：添加新设备（协议 + endpoint + config JSONB）/ 启用 / 停用。

权限：`device:read`

---

## 五、公共组件与交互规范

### 5.1 统一交互模式

所有列表页遵循 Element Plus 布局模式：

```
┌─ 过滤区 ───────────────────────────────┐
│ 搜索框 + 下拉过滤器 + 操作按钮组          │
└────────────────────────────────────────┘
┌─ 表格区 ───────────────────────────────┐
│ el-table（stripe + border + height）     │
│ 行内操作：详情 / 编辑 / 删除 / 状态切换   │
├────────────────────────────────────────┤
│ 分页：page-size-selector + total + 跳转  │
└────────────────────────────────────────┘
┌─ 弹窗区（el-dialog） ───────────────────┐
│ 新建 / 编辑表单（el-form + 校验规则）     │
└────────────────────────────────────────┘
```

### 5.2 统一请求规范

- **Axios BaseURL**：`/api`（Vite dev proxy 到 `localhost:8000`）
- **鉴权头**：`Authorization: Bearer {token}` 自动注入
- **统一成功**：`code=0` 视为成功；其他为业务失败 → `ElMessage.error`
- **401 自动处理**：Token 过期 → 清 localStorage → 跳 `/login?redirect=原路径`
- **乐观锁冲突**：409 → `ElMessage.warning('数据已被他人修改，请刷新后重试')`

### 5.3 统一 CSV 导入规范

| 页面 | API | 模板列 | 幂等逻辑 |
|---|---|---|---|
| 物料 | `POST /api/materials/import` | code, name, type, spec, unit, safety_stock, status | 已存在 code → skipped |
| BOM | `POST /api/boms/import` | product_code, component_code, version, qty_per, loss_rate, seq | 已存在 product_code + version → 更新 component 行 |
| 订单 | `POST /api/orders/import` | order_no, customer_name, product_model, priority, planned_date | 已存在 order_no → skipped |

### 5.4 AnnotationEditor 组件（SOP 图片标注）

| 工具 | 快捷键 | 说明 |
|---|---|---|
| 箭头 | — | 绘制带箭头的指示线 |
| 矩形框 | — | 框选指定区域 |
| 圆形 | — | 圈出特定点位 |
| 文字 | — | 添加文字说明 |
| 撤销 | Ctrl+Z | 撤销最近一次操作 |
| 重做 | Ctrl+Shift+Z | 重做 |
| 删除 | Delete | 删除当前选中标注 |
| 缩放 | 滚轮 | 放大缩小图片 |
| 平移 | 拖拽 | 移动视图 |

**数据格式**（归一化坐标，存 `sop.annotations` JSONB）：
```json
{
  "shapes": [
    { "type": "arrow", "x1": 0.3, "y1": 0.4, "x2": 0.7, "y2": 0.8, "color": "#ff0000" },
    { "type": "rect", "x": 0.2, "y": 0.3, "w": 0.5, "h": 0.4, "color": "#00aa00" },
    { "type": "text", "x": 0.5, "y": 0.1, "text": "注意扭矩 25N·m", "color": "#0000ff" }
  ]
}
```

---

## 六、API 模块与后端对应关系

| 前端 API 文件 | 后端路由前缀 | 主要端点 |
|---|---|---|
| `auth.js` | `/api/auth` | POST login / POST register / GET me |
| `materials.js` | `/api/materials` | CRUD + POST import + POST inbound + POST issue + POST scrap + POST adjust + POST reserve + POST release + **GET transactions** + GET low-stock |
| `boms.js` | `/api/boms` | CRUD + POST import + GET shortage/{bom_id}?qty=N |
| `orders.js` | `/api/orders` | CRUD + POST import + **POST batch-release** + **GET {id}/kit-check** + **POST {id}/adjust** + POST {id}/transition |
| `production.js` | `/api/production` | 工单 CRUD + POST {id}/transition + POST {id}/report + POST {id}/scrap + GET trace/{forward,backward,tree,bfs} |
| `inspectTypes.js` | `/api/inspect-types` | CRUD |
| `defectCodes.js` | `/api/defect-codes` | CRUD |
| `quality.js` | `/api/production/inspections` | POST create + GET list + GET stats |
| `sops.js` | `/api/sops` + `/api/auth/sop-templates` | CRUD + POST upload + GET dynamic/{product_code} + GET templates |
| `devices.js` | `/api/devices` | GET list + POST create + GET protocols |
| `auditLogs.js` | `/api/audit-logs` | GET list + GET actions |
| `roles.js` | `/api/auth` | GET roles + GET permissions/catalog + PUT roles/{role}/permissions |
| `dashboard.js` | `/api/dashboard` | GET overview + GET shortage-alerts |

---

## 七、开发调试

| 操作 | 命令 |
|---|---|
| 安装依赖 | `cd front && npm install` |
| 启动开发服务器 | `npm run dev`（默认 `http://localhost:5174`） |
| 构建生产版本 | `npm run build`（输出到 `front/dist`） |
| Vite Proxy | `/api` → `http://localhost:8000`，`/uploads` → `http://localhost:8000/uploads` |

### 典型调试路径

1. 浏览器 DevTools → Network 面板查看所有 API 请求是否 200
2. Console 面板查看 Vue 组件渲染错误
3. Elements 面板直接修改 `localStorage.sog_token` / `sog_user` 切换角色
4. 后端 Swagger `http://localhost:8000/docs` 独立测试单个端点