import logging

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from typing import Any

from .vehicle import Vehicle
from .base_entity import BaseEntity
from .const import (
    DOMAIN,
    DATA_VEHICLE_INSTANCE,
    VEHICLE_LOCK_ACTION,
    CONF_VEHICLE_IDENTIFIER,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigType, async_add_entities
):
    vehicle_identifier = config_entry.data[CONF_VEHICLE_IDENTIFIER]
    vehicle: Vehicle = hass.data[DOMAIN][vehicle_identifier][DATA_VEHICLE_INSTANCE]
    async_add_entities([Lock(vehicle)], True)


class Lock(BaseEntity, LockEntity):
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

    async def async_lock(self, **kwargs: Any):
        await self.hass.async_create_task(
            self._vehicle.lock_action(VEHICLE_LOCK_ACTION.LOCK)
        )

    async def async_unlock(self, **kwargs: Any):
        await self.hass.async_create_task(
            self._vehicle.lock_action(VEHICLE_LOCK_ACTION.UNLOCK)
        )
