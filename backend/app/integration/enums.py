import enum


class ExternalSystem(str, enum.Enum):
    LOCAL = "LOCAL"
    ERP = "ERP"
    MES = "MES"
    PLM = "PLM"
    WMS = "WMS"


class SyncStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class DataType(str, enum.Enum):
    ORDERS = "ORDERS"
    MATERIALS = "MATERIALS"
    BOM = "BOM"
    INVENTORY = "INVENTORY"
    CUSTOMERS = "CUSTOMERS"