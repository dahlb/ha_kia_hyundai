import logging
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .vehicle import Vehicle

_LOGGER = logging.getLogger(__name__)


class DeviceInfoMixin:
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vehicle.identifier)},
            "name": self._vehicle.name,
            "manufacturer": f"{self._vehicle.api_cloud.region} {self._vehicle.api_cloud.brand}",
            "model": self._vehicle.model,
            "via_device": (DOMAIN, self._vehicle.identifier),
        }


class BaseEntity(CoordinatorEntity[Vehicle], DeviceInfoMixin, Entity):
    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle.coordinator)
        self._vehicle: Vehicle = vehicle

    async def async_update(self) -> None:
        """
        disable generic update method ...
        """
        pass
