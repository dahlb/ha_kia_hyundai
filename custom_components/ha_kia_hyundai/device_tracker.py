from logging import getLogger

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import VehicleCoordinator
from .const import DOMAIN, CONF_VEHICLE_ID
from .vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity

_LOGGER = getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]

    async_add_entities([LocationTracker(coordinator)], True)


class LocationTracker(VehicleCoordinatorBaseEntity, TrackerEntity):
    def __init__(self, coordinator: VehicleCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{coordinator.vehicle_id}-location"
        self._attr_name = f"{coordinator.vehicle_name} Location"
        self._attr_icon = "mdi:map-marker-outline"

    @property
    def source_type(self):
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.coordinator.latitude

    @property
    def longitude(self) -> float | None:
        return self.coordinator.longitude

    @property
    def available(self) -> bool:
        return super().available and self.latitude is not None and self.longitude is not None
