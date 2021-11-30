from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .vehicle import Vehicle


class KiaUvoEntity(Entity):
    _attr_should_poll = False

    def __init__(self, vehicle: Vehicle):
        self._vehicle = vehicle

    async def async_added_to_hass(self) -> None:
        self._vehicle.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._vehicle.remove_callback(self.async_write_ha_state)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._vehicle.identifier)},
            "name": self._vehicle.name,
            "manufacturer": "Kia",
            "model": self._vehicle.model,
            "via_device": (DOMAIN, self._vehicle.identifier),
        }

    @property
    def available(self) -> bool:
        return self._vehicle.battery_level is not None
