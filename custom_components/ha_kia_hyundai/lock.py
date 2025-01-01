from logging import getLogger

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import VehicleCoordinator
from .vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity
from .const import (
    DOMAIN,
    CONF_VEHICLE_ID,
)

_LOGGER = getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]
    if coordinator.can_remote_lock:
        async_add_entities([Lock(coordinator)], True)


class Lock(VehicleCoordinatorBaseEntity, LockEntity):
    def __init__(
        self,
        coordinator: VehicleCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{self.coordinator.vehicle_id}-doorLock"
        self._attr_name = f"{self.coordinator.vehicle_name} Door Lock"

    @property
    def is_locked(self) -> bool:
        return self.coordinator.doors_locked

    @property
    def icon(self):
        return "mdi:lock" if self.is_locked else "mdi:lock-open-variant"

    async def async_lock(self, **kwargs: any):
        await self.coordinator.api_connection.lock(vehicle_id=self.coordinator.vehicle_id)
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs: any):
        await self.coordinator.api_connection.unlock(vehicle_id=self.coordinator.vehicle_id)
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()
