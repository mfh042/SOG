"""设备直连模块 — OPC-UA / MQTT 接口骨架。

当前阶段：定义接口 + 数据模型 + REST 路由占位，便于后续真实接入。
"""
from datetime import datetime
from decimal import Decimal
from typing import Any
from enum import Enum

from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"


class DeviceType(str, Enum):
    PLC = "PLC"
    ROBOT = "ROBOT"
    SENSOR = "SENSOR"
    AGV = "AGV"
    SCANNER = "SCANNER"
    WEIGH_SCALE = "WEIGH_SCALE"


class Protocol(str, Enum):
    OPCUA = "OPC-UA"
    MQTT = "MQTT"
    MODBUS = "MODBUS"
    HTTP = "HTTP"


class DeviceRegister(BaseModel):
    code: str = Field(..., max_length=64, description="设备编号")
    name: str = Field(..., max_length=128, description="设备名称")
    device_type: DeviceType
    protocol: Protocol
    endpoint: str = Field(..., description="OPC-UA endpoint / MQTT broker / IP")
    node_prefix: str | None = Field(None, description="OPC-UA node 前缀 / MQTT topic 前缀")
    username: str | None = None
    password: str | None = None
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class DeviceOut(DeviceRegister):
    id: int
    status: DeviceStatus
    last_seen_at: datetime | None = None
    current_values: dict[str, Any] = Field(default_factory=dict)


class TagDataPoint(BaseModel):
    tag: str
    value: Any
    quality: str = "GOOD"
    timestamp: datetime | None = None


class DeviceTelemetryIn(BaseModel):
    device_code: str
    values: list[TagDataPoint]


class OpcUaNode:
    """OPC-UA 节点定义（接入阶段直接映射变量）。"""
    code: str
    node_id: str
    data_type: str
    unit: str | None = None

    def __init__(self, code: str, node_id: str, data_type: str = "Float", unit: str | None = None):
        self.code = code
        self.node_id = node_id
        self.data_type = data_type
        self.unit = unit


class MqttTopic:
    """MQTT 订阅主题。"""
    topic: str
    qos: int = 1
    decode: str = "json"

    def __init__(self, topic: str, qos: int = 1, decode: str = "json"):
        self.topic = topic
        self.qos = qos
        self.decode = decode


DEFAULT_OPCUA_NODES = [
    OpcUaNode("production_rate", "ns=2;s=ProductionRate", "Float", "pcs/hour"),
    OpcUaNode("current_count", "ns=2;s=CurrentCount", "Int32"),
    OpcUaNode("temperature", "ns=2;s=Temp", "Float", "°C"),
    OpcUaNode("humidity", "ns=2;s=Humidity", "Float", "%"),
    OpcUaNode("status_word", "ns=2;s=StatusWord", "UInt16"),
]

DEFAULT_MQTT_TOPICS = [
    MqttTopic("device/+/telemetry/#", qos=1),
    MqttTopic("device/+/event/#", qos=2),
]