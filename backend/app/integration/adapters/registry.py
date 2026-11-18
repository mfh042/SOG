import logging
from typing import Type

from app.integration.adapters.base import ExternalSystemAdapter
from app.integration.config import SystemConnector

logger = logging.getLogger("delv-sog.integration")


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, Type[ExternalSystemAdapter]] = {}
        self._instances: dict[str, ExternalSystemAdapter] = {}

    def register(self, adapter_class: Type[ExternalSystemAdapter]):
        name = adapter_class.system_name.upper()
        self._adapters[name] = adapter_class
        logger.info("Adapter registered: %s", name)
        return adapter_class

    def get(self, system_name: str, connector: SystemConnector | None = None) -> ExternalSystemAdapter | None:
        key = system_name.upper()
        if key not in self._adapters:
            return None
        if key not in self._instances:
            cls = self._adapters[key]
            self._instances[key] = cls(connector=connector) if connector else cls()
        return self._instances[key]

    def available(self) -> list[str]:
        return list(self._adapters.keys())

    def clear(self):
        self._instances.clear()


registry = AdapterRegistry()