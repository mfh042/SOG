"""设备直连 REST 路由 — 骨架，后续按协议实现。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.permissions import require_perm
from app.core.response import Resp
from app.modules.device.schemas import DeviceRegister, DeviceStatus, DeviceType, Protocol

router = APIRouter(prefix="/api/devices", tags=["设备直连"])


@router.get("", summary="已注册设备列表")
async def list_devices(
    _: dict = Depends(require_perm("device:read")),
):
    return Resp.ok({
        "devices": [
            {
                "id": 1,
                "code": "PLC-01",
                "name": "主产线 PLC",
                "device_type": DeviceType.PLC.value,
                "protocol": Protocol.OPCUA.value,
                "endpoint": "opc.tcp://192.168.1.10:4840",
                "status": DeviceStatus.OFFLINE.value,
                "note": "骨架占位，后续接 OPC-UA 实际扫描",
            },
            {
                "id": 2,
                "code": "AGV-01",
                "name": "物料搬运 AGV",
                "device_type": DeviceType.AGV.value,
                "protocol": Protocol.MQTT.value,
                "endpoint": "mqtt://mqtt.broker.local:1883",
                "status": DeviceStatus.OFFLINE.value,
                "note": "骨架占位，后续接 MQTT 订阅",
            },
        ],
        "protocol_stub": {
            "opcua_client": "opcua python package (pip install opcua)",
            "mqtt_client": "paho-mqtt (pip install paho-mqtt)",
            "poller_interval_sec": 5,
            "telemetry_push": "forward to dashboard WIP / trace",
        },
    })


@router.post("", summary="注册新设备（骨架）")
async def register_device(
    payload: DeviceRegister,
    _: dict = Depends(require_perm("device:create")),
):
    return Resp.ok({
        "code": 201,
        "device": payload.model_dump(),
        "note": "已接收，待 DB + 实际连接池实现",
    }, message="设备注册请求已接收")


@router.get("/protocols", summary="支持的协议类型")
async def list_protocols(
    _: dict = Depends(require_perm("device:read")),
):
    return Resp.ok({
        "device_types": [e.value for e in DeviceType],
        "protocols": [e.value for e in Protocol],
        "sample_nodes": [
            {"code": "production_rate", "node_id": "ns=2;s=ProductionRate", "type": "Float", "unit": "pcs/hour"},
            {"code": "current_count", "node_id": "ns=2;s=CurrentCount", "type": "Int32"},
            {"code": "status_word", "node_id": "ns=2;s=StatusWord", "type": "UInt16"},
        ],
        "sample_mqtt": [
            {"topic": "device/+/telemetry/#", "qos": 1},
            {"topic": "device/+/event/#", "qos": 2},
        ],
    })