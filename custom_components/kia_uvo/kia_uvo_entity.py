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
            "manufacturer": "Kia",
            "model": self._vehicle.model,
            "via_device": (DOMAIN, self._vehicle.identifier),
        }


class KiaUvoEntity(CoordinatorEntity[Vehicle], DeviceInfoMixin, Entity):
    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle.coordinator)
        self._vehicle = vehicle

    async def async_update(self) -> None:
        """
        disable generic update method ...
        """
        pass
