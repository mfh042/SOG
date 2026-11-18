"""DELV-SOG 后端入口。

启动：uvicorn app.main:app --loop selector --host 0.0.0.0 --port 8000
高并发部署：gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.common.base import Base
from app.core.config import settings
from app.core.concurrency import shutdown_threadpool
from app.core.db import AsyncSessionLocal, engine
from app.core.exceptions import register_exception_handlers
from app.core.response import Resp
from app.integration.router import router as integration_router
from app.modules.auth.crypto import hash_password
from app.modules.auth.models import AppUser
from app.modules.auth.router import router as auth_router
from app.modules.audit.router import router as audit_router
from app.modules.bom.router import router as bom_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.device.router import router as device_router
from app.modules.material.models import Material
from app.modules.material.router import router as material_router
from app.modules.orders.models import OrderItem, SalesOrder
from app.modules.orders.router import router as order_router
from app.modules.production.router import router as production_router
from app.modules.quality.router import router as quality_router
from app.modules.sop.models import Sop, SopTemplate
from app.modules.sop.router import router as sop_router

logger = logging.getLogger("delv-sog")


async def _init_db():
    """自动建表 + 种子数据（幂等，可反复执行）。"""
    import app.integration.models  # noqa: F401
    import app.modules.auth.models  # noqa: F401  让 Base.metadata 注册
    import app.modules.bom.models  # noqa: F401
    import app.modules.material.models  # noqa: F401
    import app.modules.orders.models  # noqa: F401
    import app.modules.production.models  # noqa: F401
    import app.modules.quality.models  # noqa: F401
    import app.modules.sop.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ 数据库表已就绪")

    async with AsyncSessionLocal() as session:
        result = await session.scalar(select(AppUser).limit(1))
        if result is None:
            _seed_users(session)
            _seed_materials(session)
            await session.commit()
            logger.info("✓ 基础种子数据已写入")

        sop_count = await session.scalar(select(Sop).limit(1))
        if sop_count is None:
            _seed_sops(session)
            await session.commit()
            logger.info("✓ SOP 种子数据已写入")

        tpl_count = await session.scalar(select(SopTemplate).limit(1))
        if tpl_count is None:
            _seed_sop_templates(session)
            await session.commit()
            logger.info("✓ SOP 模板种子已写入")

        from app.modules.auth.models import RolePermission
        perm_count = await session.scalar(select(RolePermission).limit(1))
        if perm_count is None:
            _seed_role_permissions(session)
            await session.commit()
            logger.info("✓ 角色权限种子已写入")


def _seed_role_permissions(session):
    from app.core.permissions import ROLE_PERMISSIONS
    from app.modules.auth.models import RolePermission
    for role, perms in ROLE_PERMISSIONS.items():
        for p in perms:
            if p == "*":
                continue
            session.add(RolePermission(role=role, permission=p))


def _seed_users(session):
    users = [
        ("admin",    "Admin",    "admin123",   "ADMIN"),
        ("planner",  "Planner",  "planner123", "PLANNER"),
        ("operator", "Operator", "op123",      "OPERATOR"),
        ("quality",  "Quality",  "qc123",      "QUALITY"),
    ]
    for username, display, pwd, role in users:
        session.add(
            AppUser(
                username=username,
                display_name=display,
                password_hash=hash_password(pwd),
                role=role,
                is_active=True,
            )
        )


def _seed_materials(session):
    materials = [
        ("GB-100", "减速机 GB-100",   "台", "FINISHED"),
        ("GB-200", "减速机 GB-200",   "台", "FINISHED"),
        ("M-001",  "电机总成 A 型",    "个", "WIP"),
        ("M-002",  "齿轮箱外壳",       "件", "WIP"),
        ("R-001",  "轴承 6205-2RS",    "个", "RAW"),
        ("R-002",  "O 型密封圈 Ø45",   "个", "RAW"),
    ]
    for code, name, unit, type_ in materials:
        session.add(
            Material(
                code=code,
                name=name,
                spec="",
                unit=unit,
                type=type_,
            )
        )


def _seed_sops(session):
    sops = [
        Sop(product_code="GB-100", operation_seq=10, operation_name="外壳加工",
            title="GB-100 减速机 — 外壳 CNC 加工",
            content=(
                "## 🎯 工序目标\n"
                "加工 GB-100 铸铁外壳，保证形位公差与表面粗糙度。\n\n"
                "## 📋 前置条件\n"
                "- 来料：HT250 铸铁毛坯（已检验合格）\n"
                "- 设备：FANUC α-D14MiA5 立式加工中心\n"
                "- 刀具：φ12 硬质合金立铣刀 / φ8 钻头 / M10 丝锥\n\n"
                "## 🔧 作业步骤\n"
                "1. **装夹**：以底面 A 为基准，使用 4 爪卡盘找正，跳动 ≤ 0.02mm\n"
                "2. **粗铣**：铣削上表面及四侧面，留 0.3mm 精铣余量\n"
                "3. **精铣**：精铣各面至尺寸，表面粗糙度 Ra ≤ 3.2μm\n"
                "4. **钻孔攻丝**：按图纸钻 8×M10 安装孔，攻丝后清理铁屑\n"
                "5. **去毛刺**：使用毛刷及砂纸清除各锐边毛刺\n\n"
                "## ✅ 检验要点\n"
                "- 外形尺寸 240×180×120 ±0.1mm\n"
                "- 各面垂直度 ≤ 0.05mm\n"
                "- 安装孔位置度 ≤ 0.1mm\n\n"
                "## ⚠️ 注意事项\n"
                "- 加工前确认毛坯无砂眼、裂纹\n"
                "- 精铣阶段禁止中途停机，防止接刀痕"
            ),
            content_url="https://a0ai.marscode.cn/api/ide/v1/text_to_image?prompt=CNC%20machining%20center%20processing%20cast%20iron%20gearbox%20housing%2C%20industrial%20factory%20scene%2C%20blue%20tech%20lighting&image_size=landscape_16_9",
            version="V2"),
        Sop(product_code="GB-100", operation_seq=20, operation_name="轴承压装",
            title="GB-100 减速机 — 轴承热压装配",
            content=(
                "## 🎯 工序目标\n"
                "将 6205-2RS 轴承正确压入外壳轴承孔。\n\n"
                "## 📋 物料清单\n"
                "- 外壳（上工序完工）× 1\n"
                "- 轴承 6205-2RS × 2（GB/T 276）\n"
                "- O 型密封圈 Ø45 × 2\n"
                "- 锂基润滑脂 ZL-3\n\n"
                "## 🔧 作业步骤\n"
                "1. **加热轴承**：使用感应加热器将轴承内圈加热至 80-100℃\n"
                "2. **清洁配合面**：用酒精棉擦拭轴承孔及轴颈，涂抹薄薄一层润滑脂\n"
                "3. **压装轴承**：使用专用压套，压力均匀缓慢（≤ 5kN），严禁敲击\n"
                "4. **安装密封圈**：检查 O 圈无划痕后，用安装工具推入槽内\n"
                "5. **注脂**：每轴承注 ZL-3 脂 8-10g，转动轴承确认无异响\n\n"
                "## ✅ 检验要点\n"
                "- 轴承端面到外壳端面距离 2.0 ± 0.1mm\n"
                "- 轴承转动灵活，无卡滞、无异响\n"
                "- 密封圈无翻边、无扭曲"
            ),
            content_url="https://a0ai.marscode.cn/api/ide/v1/text_to_image?prompt=bearing%20press%20fitting%20assembly%20in%20gearbox%2C%20industrial%20workshop%2C%20precision%20assembly%20process&image_size=landscape_16_9",
            version="V1"),
        Sop(product_code="GB-100", operation_seq=30, operation_name="齿轮组装",
            title="GB-100 减速机 — 齿轮轴组装",
            content=(
                "## 🎯 工序目标\n"
                "完成高速轴、中间轴、低速轴齿轮组装，保证啮合间隙。\n\n"
                "## 🔧 作业步骤\n"
                "1. 依序将齿轮、隔套、锁紧螺母装配到对应轴上\n"
                "2. 使用扭矩扳手锁紧螺母：预紧力矩 25 N·m\n"
                "3. 齿轮啮合侧隙：0.08-0.15mm（用铅丝压测）\n"
                "4. 齿面接触斑点 ≥ 70%（涂色法检验）\n\n"
                "## ⚠️ 注意事项\n"
                "- 组装前所有零件用汽油清洗并吹干\n"
                "- 禁止用铁锤直接敲击齿轮端面"
            ),
            version="V1"),
        Sop(product_code="GB-100", operation_seq=40, operation_name="总装试车",
            title="GB-100 减速机 — 总装与空载试车",
            content=(
                "## 🎯 工序目标\n"
                "完成减速机总装并通过空载试车验证。\n\n"
                "## 🔧 作业步骤\n"
                "1. 将齿轮轴组整体装入外壳，对准轴承位置\n"
                "2. 安装端盖、密封件，螺栓按对角顺序拧紧（15 N·m）\n"
                "3. 注入 46# 抗磨液压油至油标中线\n"
                "4. 联轴器对接电机，手动盘车 3 圈确认无卡滞\n"
                "5. 通电空载运行 30 分钟，温升 ≤ 40K，噪声 ≤ 65dB\n\n"
                "## ✅ 检验记录\n"
                "- 空载电流 ≤ 额定电流 30%\n"
                "- 输出轴径向跳动 ≤ 0.03mm\n"
                "- 密封处无渗漏"
            ),
            content_url="https://a0ai.marscode.cn/api/ide/v1/text_to_image?prompt=gearbox%20final%20assembly%20testing%2C%20electric%20motor%20coupling%2C%20industrial%20quality%20control&image_size=landscape_16_9",
            version="V3"),
        Sop(product_code="GB-200", operation_seq=10, operation_name="外壳铸造后处理",
            title="GB-200 减速机 — 铸后清砂与时效",
            content=(
                "## 🎯 工序目标\n"
                "消除 GB-200 外壳铸造应力，为机加做准备。\n\n"
                "## 🔧 作业步骤\n"
                "1. 振动落砂机清砂，内腔残留砂粒清理干净\n"
                "2. 抛丸处理表面，Sa2.5 级\n"
                "3. 去应力退火：550℃ × 4h，随炉冷却\n"
                "4. 检验毛坯无裂纹、无缩孔（超声波探伤）"
            ),
            version="V1"),
        Sop(product_code="GB-200", operation_seq=20, operation_name="精加工",
            title="GB-200 减速机 — 数控精加工",
            content=(
                "## 🎯 工序目标\n"
                "CNC 精加工至成品尺寸。\n\n"
                "## 🔧 作业步骤\n"
                "1. 精镗轴承孔至 H7 公差，Ra ≤ 1.6μm\n"
                "2. 精铣接合面，平面度 ≤ 0.03mm/100mm\n"
                "3. 钻攻全部螺纹孔，通止规检验\n\n"
                "## ✅ 检验要点\n"
                "- 轴承孔圆柱度 ≤ 0.005mm\n"
                "- 孔系位置度 ≤ 0.08mm"
            ),
            version="V1"),
        Sop(product_code="GB-200", operation_seq=30, operation_name="总成装配",
            title="GB-200 减速机 — 总成装配线作业",
            content=(
                "## 🎯 工序目标\n"
                "在总装线上完成 GB-200 全套装配。\n\n"
                "## 🔧 作业步骤\n"
                "1. 轴承热压（100℃），压装速度 2mm/s\n"
                "2. 齿轮组预组装 → 涂色检验啮合斑点\n"
                "3. 箱内注脂 + 封盖 → 螺栓按扭矩对角拧紧\n"
                "4. 空载跑合 2h → 油温 ≤ 60℃ → 换油\n\n"
                "## 📋 BOM 关键件\n"
                "- 轴承 6306-2RS × 4\n"
                "- 油封 TG 45×72×7 × 2\n"
                "- 齿轮 Z=32/φ120 × 1"
            ),
            content_url="https://a0ai.marscode.cn/api/ide/v1/text_to_image?prompt=gearbox%20assembly%20line%20production%2C%20multiple%20workers%20on%20assembly%20line%2C%20blue%20industrial%20lighting&image_size=landscape_16_9",
            version="V2"),
        Sop(product_code="M-001", operation_seq=10, operation_name="定子绕线",
            title="电机总成 A 型 — 定子绕组绕制",
            content=(
                "## 🎯 工序目标\n"
                "完成三相异步电机定子绕组绕制。\n\n"
                "## 🔧 作业步骤\n"
                "1. 槽内放置聚酰亚胺绝缘纸（厚度 0.25mm）\n"
                "2. 自动绕线机绕制，漆包线规格 Ø0.8mm，匝数 126\n"
                "3. 三相绕组 Y 形连接，引出线 UVW + PE\n"
                "4. 浸漆处理：F 级绝缘漆，真空压力浸渍\n\n"
                "## ✅ 检验要点\n"
                "- 绕组直流电阻不平衡度 ≤ 2%\n"
                "- 绝缘电阻 ≥ 100 MΩ（500V 摇表）\n"
                "- 匝间耐压 1800V/5s 无击穿"
            ),
            content_url="https://a0ai.marscode.cn/api/ide/v1/text_to_image?prompt=electric%20motor%20stator%20winding%20machine%2C%20copper%20wire%20coils%2C%20electrical%20assembly%20workshop&image_size=landscape_16_9",
            version="V1"),
        Sop(product_code="M-001", operation_seq=20, operation_name="转子动平衡",
            title="电机总成 A 型 — 转子动平衡校正",
            content=(
                "## 🎯 工序目标\n"
                "转子动平衡精度 G2.5 级。\n\n"
                "## 🔧 作业步骤\n"
                "1. 动平衡机转速 3000 rpm\n"
                "2. 测量两侧不平衡量，铣削去重（去重深度 ≤ 2mm）\n"
                "3. 复测至剩余不平衡量 ≤ 1.6 g·mm\n"
                "4. 热套风扇（加热至 120℃）"
            ),
            version="V1"),
        Sop(product_code="M-001", operation_seq=30, operation_name="电机总装测试",
            title="电机总成 A 型 — 总装与出厂测试",
            content=(
                "## 🎯 工序目标\n"
                "完成电机总装并通过出厂试验。\n\n"
                "## 🔧 作业步骤\n"
                "1. 定子-转子合装 → 端盖安装 → 轴承注脂\n"
                "2. 空载试验：电压 380V/50Hz，空载电流 ≤ 2.5A\n"
                "3. 负载试验：堵转力矩 12 N·m\n"
                "4. 温升试验：额定负载运行 2h，绕组温度 ≤ 105℃\n"
                "5. 噪声振动：噪声 ≤ 55dB，振动 ≤ 1.8 mm/s"
            ),
            version="V2"),
        Sop(product_code="M-002", operation_seq=10, operation_name="铸造毛坯",
            title="齿轮箱外壳 — 球墨铸铁铸造",
            content=(
                "## 🎯 工序目标\n"
                "生产球墨铸铁 QT450-10 外壳毛坯。\n\n"
                "## 🔧 作业步骤\n"
                "1. 中频炉熔炼，出炉温度 1500℃\n"
                "2. 冲入法球化处理（Mg-Si 合金 1.2%）\n"
                "3. 湿型砂浇注，浇注温度 1420℃\n"
                "4. 冷却 24h 后落砂\n\n"
                "## ✅ 金相检验\n"
                "- 球化率 ≥ 85%\n"
                "- 石墨大小 6-7 级"
            ),
            version="V1"),
        Sop(product_code="M-002", operation_seq=20, operation_name="CNC 镗铣",
            title="齿轮箱外壳 — CNC 镗铣加工",
            content=(
                "## 🎯 工序目标\n"
                "加工中心一次装夹完成全部关键面加工。\n\n"
                "## 🔧 作业步骤\n"
                "1. 卧式加工中心 TH65100，一次装夹四面加工\n"
                "2. 主轴孔镗至 H7，Ra ≤ 1.6μm\n"
                "3. 接合面铣削，平面度 ≤ 0.04mm\n"
                "4. 深孔钻油道孔 Ø6×80"
            ),
            version="V1"),
    ]
    for s in sops:
        session.add(s)


def _seed_sop_templates(session):
    templates = [
        SopTemplate(
            name="CNC 机加工通用模板",
            category="CNC",
            description="适用于立式/卧式加工中心的典型机加工工序，包含装夹、粗铣、精铣、检验全流程",
            title_template="{product} — {operation_name}",
            operation_name_default="CNC 机加工",
            content=(
                "## 🎯 工序目标\n"
                "完成 {product} 的 CNC 加工，保证尺寸精度与表面质量。\n\n"
                "## 📋 前置条件\n"
                "- 来料检验合格\n"
                "- 设备：立式加工中心（FANUC / 三菱 / 西门子系统）\n"
                "- 刀具清单：按工艺卡准备\n\n"
                "## 🔧 作业步骤\n"
                "1. **装夹找正**：以基准面定位，使用寻边器/对刀仪设定工件坐标系\n"
                "2. **程序校验**：空运行确认刀具路径，无干涉\n"
                "3. **首件试切**：执行首件加工，尺寸检验合格后方可批量\n"
                "4. **批量加工**：按程序连续加工，中途监控切削参数\n"
                "5. **完工送检**：加工件放置周转架，送检质检员\n\n"
                "## ✅ 检验要点\n"
                "- 关键尺寸公差按图纸要求\n"
                "- 表面粗糙度 Ra 按工艺规定\n"
                "- 无碰刀、无振纹\n\n"
                "## ⚠️ 安全注意\n"
                "- 加工中禁止打开防护门\n"
                "- 铁屑清理使用钩子，严禁用手"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="热压装配通用模板",
            category="装配",
            description="轴承、衬套等过盈配合零件的热压装配作业指导",
            title_template="{product} — {operation_name}",
            operation_name_default="热压装配",
            content=(
                "## 🎯 工序目标\n"
                "完成 {product} 的过盈配合装配，保证配合精度。\n\n"
                "## 📋 物料清单\n"
                "- 配合件（内圈加热 / 外圈冷却）\n"
                "- 专用压套、压杆\n"
                "- 润滑脂 / 防锈油\n\n"
                "## 🔧 作业步骤\n"
                "1. **加热/冷却**：感应加热器至 80-120℃ 或干冰冷却至 -30℃\n"
                "2. **清洁配合面**：酒精棉擦拭，检查无毛刺、无锈蚀\n"
                "3. **快速装配**：热胀冷缩窗口期内（<30s）一次对准压入\n"
                "4. **冷却固定**：自然冷却 5 分钟，禁止浇水急冷\n"
                "5. **复检转动**：装配后零件应转动灵活，无卡滞\n\n"
                "## ✅ 检验要点\n"
                "- 压入到位标记对齐\n"
                "- 轴向间隙 / 径向跳动符合要求\n"
                "- 配合面无烧伤、无压痕"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="总成装配线模板",
            category="装配",
            description="流水线式多工位总成装配，适合减速机、电机等机电产品",
            title_template="{product} — {operation_name}",
            operation_name_default="总成装配",
            content=(
                "## 🎯 工序目标\n"
                "在装配线上完成 {product} 的全套装配作业。\n\n"
                "## 📋 工位节拍\n"
                "- 节拍时间：按线体节拍执行\n"
                "- 工位器具：定位工装 / 扭矩扳手 / 量具\n\n"
                "## 🔧 作业步骤\n"
                "1. **上料**：上工序半成品到位，扫码确认\n"
                "2. **预装**：按工艺卡顺序预装各子部件\n"
                "3. **扭矩紧固**：按扭矩表顺序（对角 / 十字）拧紧，记录力矩\n"
                "4. **密封 / 注液**：密封圈安装 → 注润滑脂 / 液压油\n"
                "5. **下线送检**：扫码完工 → 流转下一工位 / 终检\n\n"
                "## ✅ 在线检验\n"
                "- 扭矩扳手数据自动上传\n"
                "- 气密测试 / 绝缘测试（如适用）\n"
                "- 视觉防错（Poka-Yoke）"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="出厂检验测试模板",
            category="检验",
            description="成品出厂前的功能性测试、耐久性测试",
            title_template="{product} — {operation_name}",
            operation_name_default="出厂测试",
            content=(
                "## 🎯 工序目标\n"
                "完成 {product} 的出厂前性能测试。\n\n"
                "## 🔧 测试项目\n"
                "1. **外观检查**：无划痕、无锈蚀、铭牌正确\n"
                "2. **空载测试**：电压/气压额定值下空载运行 30 分钟\n"
                "3. **负载测试**：额定负载运行，记录电流/扭矩/转速\n"
                "4. **温升测试**：额定工况 2h，测温升 ≤ 规定值\n"
                "5. **噪声振动**：dB / mm/s ≤ 标准值\n\n"
                "## 📋 测试记录\n"
                "所有数据录入测试系统，合格标识粘贴后放行。\n\n"
                "## ❌ 不合格处理\n"
                "不合格品隔离 → 开不合格报告 → 返修/报废"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="铸件后处理模板",
            category="铸造",
            description="铸铁/铸钢件的落砂、清砂、时效处理",
            title_template="{product} — {operation_name}",
            operation_name_default="铸件后处理",
            content=(
                "## 🎯 工序目标\n"
                "消除 {product} 铸造应力，获得合格毛坯。\n\n"
                "## 🔧 作业步骤\n"
                "1. **振动落砂**：振动落砂机 3-5 分钟\n"
                "2. **抛丸清理**：抛丸机 Sa2.5 级，表面氧化皮完全清除\n"
                "3. **去应力退火**：550-600℃ × 4-6h，随炉冷却\n"
                "4. **缺陷检查**：外观 + 超声波探伤（重要件）\n\n"
                "## ✅ 检验要点\n"
                "- 表面无粘砂、无裂纹\n"
                "- 关键部位 UT 探伤无超标缺陷\n"
                "- 硬度 / 金相组织符合材料标准"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="绕线浸渍模板",
            category="电气",
            description="电机定子绕组绕制与真空压力浸渍工艺",
            title_template="{product} — {operation_name}",
            operation_name_default="绕线与浸渍",
            content=(
                "## 🎯 工序目标\n"
                "完成 {product} 定子绕组绕制与绝缘浸渍。\n\n"
                "## 🔧 作业步骤\n"
                "1. **槽绝缘**：放置聚酰亚胺 / 聚酯薄膜槽衬\n"
                "2. **绕线**：自动绕线机按匝数绕制，漆包线规格按工艺\n"
                "3. **端部处理**：绑扎 → 引出线焊接 → 绝缘包扎\n"
                "4. **VPI 浸渍**：真空 → 浸漆 → 加压 → 固化\n"
                "5. **性能测试**：直流电阻 / 绝缘电阻 / 匝间耐压\n\n"
                "## ✅ 检验要点\n"
                "- 三相电阻不平衡度 ≤ 2%\n"
                "- 绝缘电阻 ≥ 100 MΩ（500V）\n"
                "- 匝间耐压 1800V/5s 无击穿"
            ),
            is_builtin=True,
        ),
        SopTemplate(
            name="通用作业指导模板",
            category="通用",
            description="通用型模板，涵盖目标、物料、步骤、检验、注意事项五大板块",
            title_template="{product} — {operation_name}",
            operation_name_default="标准作业",
            content=(
                "## 🎯 工序目标\n"
                "完成 {product} 的 {operation_name} 作业。\n\n"
                "## 📋 物料与工具\n"
                "- 来料/上工序半成品\n"
                "- 本工序所需物料清单\n"
                "- 专用工具、量具\n\n"
                "## 🔧 作业步骤\n"
                "1. 按工艺卡执行第 1 步操作\n"
                "2. 按工艺卡执行第 2 步操作\n"
                "3. 按工艺卡执行第 3 步操作\n\n"
                "## ✅ 检验要点\n"
                "- 首件必检\n"
                "- 过程抽检\n"
                "- 完工全检关键项\n\n"
                "## ⚠️ 注意事项\n"
                "- 安全防护用品佩戴\n"
                "- 设备参数不得随意更改\n"
                "- 异常立即停机上报"
            ),
            is_builtin=False,
        ),
    ]
    for t in templates:
        session.add(t)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _init_db()
    yield
    shutdown_threadpool()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(bom_router)
app.include_router(dashboard_router)
app.include_router(device_router)
app.include_router(integration_router)
app.include_router(quality_router)
app.include_router(order_router)
app.include_router(material_router)
app.include_router(production_router)
app.include_router(sop_router)

_upload_root = Path(os.environ.get("SOP_UPLOAD_DIR", Path(__file__).resolve().parent.parent.parent / "backend" / "uploads"))
_upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_root)), name="uploads")


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return Resp.ok({"status": "up", "env": settings.app_env})