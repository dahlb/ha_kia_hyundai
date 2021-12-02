import logging

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .vehicle import Vehicle
from .kia_uvo_entity import KiaUvoEntity
from .const import (
    DOMAIN,
    DATA_VEHICLE_INSTANCE,
    VEHICLE_LOCK_ACTION,
    PARALLEL_UPDATES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, _config_entry: ConfigType, async_add_entities
):
    vehicle: Vehicle = hass.data[DOMAIN][DATA_VEHICLE_INSTANCE]
    async_add_entities([Lock(vehicle)], True)


class Lock(KiaUvoEntity, LockEntity):
    def __init__(
        self,
        vehicle: Vehicle,
    ):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{self._vehicle.identifier}-doorLock"
        self._attr_name = f"{self._vehicle.name} Door Lock"

    @property
    def is_locked(self):
        return self._vehicle.doors_locked

    @property
    def icon(self):
        return "mdi:lock" if self.is_locked else "mdi:lock-open-variant"

    async def async_lock(self):
        await self.hass.async_create_task(
            self._vehicle.lock_action(VEHICLE_LOCK_ACTION.LOCK)
        )

    async def async_unlock(self):
        await self.hass.async_create_task(
            self._vehicle.lock_action(VEHICLE_LOCK_ACTION.UNLOCK)
        )
