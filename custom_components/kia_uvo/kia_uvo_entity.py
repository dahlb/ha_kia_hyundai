from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .vehicle import Vehicle


class KiaUvoEntity(CoordinatorEntity[Vehicle], Entity):
    _attr_should_poll = False

    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle.coordinator)
        self._vehicle = vehicle

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vehicle.identifier)},
            "name": self._vehicle.name,
            "manufacturer": "Kia",
            "model": self._vehicle.model,
            "via_device": (DOMAIN, self._vehicle.identifier),
        }
