from app.integration.adapters.http_base import BaseHttpAdapter
from app.integration.config import SystemConnector


class GenericMesAdapter(BaseHttpAdapter):
    system_name = "MES"

    def __init__(self, connector: SystemConnector):
        super().__init__(connector)