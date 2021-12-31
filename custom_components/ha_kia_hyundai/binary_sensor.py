import logging
import json
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_LOCK,
    DEVICE_CLASS_CONNECTIVITY,
)

from .vehicle import Vehicle
from .base_entity import BaseEntity, DeviceInfoMixin
from .const import (
    CONF_VEHICLE_IDENTIFIER,
    DATA_VEHICLE_INSTANCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigType, async_add_entities
):
    vehicle: Vehicle = hass.data[DOMAIN][config_entry.data[CONF_VEHICLE_IDENTIFIER]][
        DATA_VEHICLE_INSTANCE
    ]

    binary_sensors = []

    for (
        description,
        key,
        on_icon,
        off_icon,
        device_class,
    ) in vehicle.supported_binary_instruments():
        binary_sensors.append(
            InstrumentSensor(
                vehicle,
                description,
                key,
                on_icon,
                off_icon,
                device_class,
            )
        )

    async_add_entities(binary_sensors, True)
    async_add_entities([DebugRawEntity(vehicle)], True)
    async_add_entities([DebugMappedEntity(vehicle)], True)
    async_add_entities([APIActionInProgress(vehicle)], True)


class InstrumentSensor(BaseEntity):
    def __init__(
        self,
        vehicle: Vehicle,
        description,
        key,
        on_icon,
        off_icon,
        device_class,
    ):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{vehicle.identifier}-{key}"
        self._attr_device_class = device_class
        self._attr_name = f"{vehicle.name} {description}"

        self._key = key
        self._on_icon = on_icon
        self._off_icon = off_icon

    @property
    def icon(self):
        return self._on_icon if self.is_on else self._off_icon

    @property
    def is_on(self) -> bool:
        return getattr(self._vehicle, self._key)

    @property
    def state(self):
        if self._attr_device_class == DEVICE_CLASS_LOCK:
            return "off" if self.is_on else "on"
        return "on" if self.is_on else "off"

    @property
    def available(self) -> bool:
        return super() and getattr(self._vehicle, self._key) is not None


class DebugRawEntity(BaseEntity):
    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{vehicle.identifier}-all-data-raw"
        self._attr_name = f"{vehicle.name} DEBUG DATA RAW"

    @property
    def state(self):
        return "on"

    @property
    def is_on(self) -> bool:
        return True

    @property
    def state_attributes(self):
        return {
            "raw_responses": json.dumps(self._vehicle.raw_responses)
        }


class DebugMappedEntity(BaseEntity):
    def __init__(self, vehicle: Vehicle):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{vehicle.identifier}-all-data-mapped"
        self._attr_name = f"{vehicle.name} DEBUG DATA MAPPED"

    @property
    def state(self):
        return "on"

    @property
    def is_on(self) -> bool:
        return True

    @property
    def state_attributes(self):
        return self._vehicle.__repr__()


class APIActionInProgress(DeviceInfoMixin, Entity):
    _attr_should_poll = False

    def __init__(self, vehicle: Vehicle):
        self._vehicle = vehicle
        self._attr_unique_id = f"{DOMAIN}-API-action-in-progress"
        self._attr_device_class = DEVICE_CLASS_CONNECTIVITY
        self._attr_available = False
        self._attr_name = None

        self._is_on = False

    async def async_added_to_hass(self) -> None:
        self._vehicle.api_cloud.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._vehicle.api_cloud.remove_callback(self.async_write_ha_state)

    @property
    def name(self) -> str:
        return f"API Action ({self._vehicle.api_cloud.current_action_name()})"

    @property
    def available(self) -> bool:
        return not not self._vehicle

    @property
    def icon(self):
        return "mdi:api" if self.is_on else "mdi:api-off"

    @property
    def state(self):
        return "on" if self.is_on else "off"

    @property
    def is_on(self) -> bool:
        return not not self._vehicle and self._vehicle.api_cloud.action_in_progress()
