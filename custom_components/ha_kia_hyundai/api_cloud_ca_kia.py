from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from kia_hyundai_api import CaKia

from .api_cloud_ca import ApiCloudCa
from .const import BRAND_KIA


class ApiCloudCaKia(ApiCloudCa):
    def __init__(
        self,
        username: str,
        password: str,
        hass: HomeAssistant,
        update_interval: timedelta = None,
        force_scan_interval: timedelta = None,
        no_force_scan_hour_start: int = None,
        no_force_scan_hour_finish: int = None,
    ):
        super().__init__(
            username=username,
            password=password,
            hass=hass,
            update_interval=update_interval,
            force_scan_interval=force_scan_interval,
            no_force_scan_hour_start=no_force_scan_hour_start,
            no_force_scan_hour_finish=no_force_scan_hour_finish,
        )
        client_session = async_get_clientsession(hass)
        self.api = CaKia(client_session=client_session)

    @property
    def brand(self) -> str:
        return BRAND_KIA
