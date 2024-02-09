import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DATA_VEHICLE_INSTANCE, CONF_VEHICLE_IDENTIFIER
from .vehicle import Vehicle
from .base_entity import BaseEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigType, async_add_entities
):
    vehicle: Vehicle = hass.data[DOMAIN][config_entry.data[CONF_VEHICLE_IDENTIFIER]][
        DATA_VEHICLE_INSTANCE
    ]
    async_add_entities([LocationTracker(vehicle)], True)


class LocationTracker(BaseEntity, TrackerEntity):
    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{vehicle.identifier}-location"
        self._attr_name = f"{vehicle.name} Location"
        self._attr_icon = "mdi:map-marker-outline"

    @property
    def source_type(self):
        return SourceType.GPS

    @property
    def latitude(self):
        return self._vehicle.latitude

    @property
    def longitude(self):
        return self._vehicle.longitude

    @property
    def location_name(self):
        return self._vehicle.location_name

    @property
    def available(self) -> bool:
        return super() and self.latitude is not None and self.longitude is not None
