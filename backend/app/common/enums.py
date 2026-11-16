"""业务枚举（与数据库 CHECK / 代码默认值保持一致）。"""
import enum


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"              # 草稿
    RELEASED = "RELEASED"        # 已下达
    IN_PROGRESS = "IN_PROGRESS"  # 生产中
    COMPLETED = "COMPLETED"       # 已完工
    CLOSED = "CLOSED"             # 已关闭
    CANCELLED = "CANCELLED"       # 已取消
    LOCKED = "LOCKED"             # 已锁定


class MaterialType(str, enum.Enum):
    RAW = "RAW"          # 原料
    SEMI = "SEMI"        # 半成品
    WIP = "WIP"          # 在制品
    FINISHED = "FINISHED"  # 成品


class StockStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"  # 可用
    RESERVED = "RESERVED"     # 已预留
    QUARANTINE = "QUARANTINE"  # 待检/隔离


class WorkOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    SCRAPPED = "SCRAPPED"


class QualityResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REWORK = "REWORK"


class TraceEventType(str, enum.Enum):
    ISSUE_MATERIAL = "ISSUE_MATERIAL"    # 领料
    WORK_START = "WORK_START"             # 开工
    ASSEMBLE = "ASSEMBLE"                 # 装配
    INSPECT = "INSPECT"                   # 检验
    PACK = "PACK"                         # 包装入库
    SCRAP = "SCRAP"                       # 报废