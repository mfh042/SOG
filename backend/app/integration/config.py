from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemConnector(BaseModel):
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    username: str = ""
    password: str = ""
    timeout_seconds: int = 30
    sync_interval_minutes: int = 60
    extra: dict[str, str] = Field(default_factory=dict)


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    integration_mode: str = "LOCAL"

    erp_enabled: bool = False
    erp_base_url: str = ""
    erp_api_key: str = ""
    erp_sync_interval: int = 60

    mes_enabled: bool = False
    mes_base_url: str = ""
    mes_api_key: str = ""
    mes_sync_interval: int = 60

    plm_enabled: bool = False
    plm_base_url: str = ""
    plm_api_key: str = ""
    plm_sync_interval: int = 60

    wms_enabled: bool = False
    wms_base_url: str = ""
    wms_api_key: str = ""
    wms_sync_interval: int = 60

    sap_enabled: bool = False
    sap_base_url: str = ""
    sap_username: str = ""
    sap_password: str = ""
    sap_api_key: str = ""
    sap_sync_interval: int = 60

    kingdee_enabled: bool = False
    kingdee_base_url: str = ""
    kingdee_api_key: str = ""
    kingdee_username: str = ""
    kingdee_password: str = ""
    kingdee_acct_id: str = ""
    kingdee_x_acgw_identity: str = ""
    kingdee_sync_interval: int = 60

    yonyou_enabled: bool = False
    yonyou_base_url: str = ""
    yonyou_app_key: str = ""
    yonyou_app_secret: str = ""
    yonyou_tenant_id: str = ""
    yonyou_api_key: str = ""
    yonyou_sync_interval: int = 60

    @property
    def local_mode(self) -> bool:
        return self.integration_mode.upper() == "LOCAL" or not any([
            self.erp_enabled, self.mes_enabled, self.plm_enabled, self.wms_enabled,
            self.sap_enabled, self.kingdee_enabled, self.yonyou_enabled,
        ])

    @property
    def erp(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.erp_enabled,
            base_url=self.erp_base_url,
            api_key=self.erp_api_key,
            sync_interval_minutes=self.erp_sync_interval,
        )

    @property
    def mes(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.mes_enabled,
            base_url=self.mes_base_url,
            api_key=self.mes_api_key,
            sync_interval_minutes=self.mes_sync_interval,
        )

    @property
    def plm(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.plm_enabled,
            base_url=self.plm_base_url,
            api_key=self.plm_api_key,
            sync_interval_minutes=self.plm_sync_interval,
        )

    @property
    def wms(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.wms_enabled,
            base_url=self.wms_base_url,
            api_key=self.wms_api_key,
            sync_interval_minutes=self.wms_sync_interval,
        )

    @property
    def sap(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.sap_enabled,
            base_url=self.sap_base_url,
            username=self.sap_username,
            password=self.sap_password,
            api_key=self.sap_api_key,
            sync_interval_minutes=self.sap_sync_interval,
        )

    @property
    def kingdee(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.kingdee_enabled,
            base_url=self.kingdee_base_url,
            api_key=self.kingdee_api_key,
            username=self.kingdee_username,
            password=self.kingdee_password,
            sync_interval_minutes=self.kingdee_sync_interval,
            extra={
                "acct_id": self.kingdee_acct_id,
                "x_acgw_identity": self.kingdee_x_acgw_identity,
            },
        )

    @property
    def yonyou(self) -> SystemConnector:
        return SystemConnector(
            enabled=self.yonyou_enabled,
            base_url=self.yonyou_base_url,
            api_key=self.yonyou_api_key,
            username=self.yonyou_app_key,
            password=self.yonyou_app_secret,
            sync_interval_minutes=self.yonyou_sync_interval,
            extra={
                "app_key": self.yonyou_app_key,
                "app_secret": self.yonyou_app_secret,
                "tenant_id": self.yonyou_tenant_id,
            },
        )

    def enabled_systems(self) -> list[tuple[str, SystemConnector]]:
        result: list[tuple[str, SystemConnector]] = []
        for name in ["erp", "mes", "plm", "wms", "sap", "kingdee", "yonyou"]:
            connector = getattr(self, name)
            if connector.enabled:
                result.append((name.upper(), connector))
        return result


@lru_cache
def get_integration_settings() -> IntegrationSettings:
    return IntegrationSettings()


integration_settings = get_integration_settings()