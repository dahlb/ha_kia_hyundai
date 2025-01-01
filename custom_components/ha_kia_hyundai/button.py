from logging import getLogger

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import VehicleCoordinator
from .const import (
    DOMAIN,
    CONF_VEHICLE_ID,
)
from .vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity

_LOGGER = getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]

    async_add_entities([
        RequestUpdateFromCarButton(coordinator=coordinator),
    ], True)


class RequestUpdateFromCarButton(VehicleCoordinatorBaseEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.UPDATE

    def __init__(
            self,
            coordinator: VehicleCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{coordinator.vehicle_id}-request-update-from-car-button"
        self._attr_name = f"{coordinator.vehicle_name} Request Wake Up from Car (hurts 12v battery)"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api_connection.request_vehicle_data_sync(vehicle_id=self.coordinator.vehicle_id)
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()
