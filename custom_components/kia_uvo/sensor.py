import logging

from homeassistant.const import (
    PERCENTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_TIMESTAMP,
    DEVICE_CLASS_TEMPERATURE,
    LENGTH_MILES,
    TIME_MINUTES,
    TEMP_FAHRENHEIT,
    DEVICE_CLASS_DATE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util
from datetime import datetime

from .vehicle import Vehicle
from .kia_uvo_entity import KiaUvoEntity
from .const import (
    DOMAIN,
    DATA_VEHICLE_INSTANCE,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, _config_entry: ConfigType, async_add_entities
):
    vehicle: Vehicle = hass.data[DOMAIN][DATA_VEHICLE_INSTANCE]

    instruments = [
        (
            "EV Battery",
            "ev_battery_level",
            PERCENTAGE,
            "mdi:car-electric",
            DEVICE_CLASS_BATTERY,
        ),
        (
            "Range by EV",
            "ev_remaining_range_value",
            LENGTH_MILES,
            "mdi:road-variant",
            None,
        ),
        (
            "Estimated Current Charge Duration",
            "ev_charge_remaining_time",
            TIME_MINUTES,
            "mdi:ev-station",
            None,
        ),
        (
            "Target Capacity of Charge AC",
            "ev_max_ac_charge_level",
            PERCENTAGE,
            "mdi:car-electric",
            None,
        ),
        (
            "Target Capacity of Charge DC",
            "ev_max_dc_charge_level",
            PERCENTAGE,
            "mdi:car-electric",
            None,
        ),
        (
            "Odometer",
            "odometer_value",
            LENGTH_MILES,
            "mdi:speedometer",
            None,
        ),
        (
            "Car Battery",
            "battery_level",
            PERCENTAGE,
            "mdi:car-battery",
            DEVICE_CLASS_BATTERY,
        ),
        (
            "Set Temperature",
            "climate_temperature_value",
            TEMP_FAHRENHEIT,
            None,
            DEVICE_CLASS_TEMPERATURE,
        ),
        (
            "Last Update",
            "last_updated",
            None,
            "mdi:update",
            DEVICE_CLASS_TIMESTAMP,
        ),
        (
            "Sync Age",
            "sync_age",
            TIME_MINUTES,
            "mdi:update",
            DEVICE_CLASS_DATE,
        ),
    ]

    sensors = []

    for description, key, unit, icon, device_class in instruments:
        sensors.append(
            InstrumentSensor(
                vehicle,
                description,
                key,
                unit,
                icon,
                device_class,
            )
        )

    async_add_entities(sensors, True)


class InstrumentSensor(KiaUvoEntity):
    def __init__(
        self,
        vehicle: Vehicle,
        description,
        key,
        unit,
        icon,
        device_class,
    ):
        super().__init__(vehicle)
        self._attr_unique_id = f"{DOMAIN}-{vehicle.identifier}-{key}"
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unit_of_measurement = unit
        self._attr_name = f"{vehicle.name} {description}"

        self._key = key

    @property
    def state(self):
        if self._key == "last_updated":
            return dt_util.as_local(self._vehicle.last_updated).isoformat()
        if self._key == "sync_age":
            local_timezone = dt_util.UTC
            age_of_last_sync = datetime.now(local_timezone) - self._vehicle.last_updated
            _LOGGER.debug(f"Sync Age, {datetime.now(local_timezone)} - {self._vehicle.last_updated} = {age_of_last_sync}")
            return int(age_of_last_sync.total_seconds() / 60)

        value = getattr(self._vehicle, self._key)
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        key_to_check = self._key
        if self._key == "sync_age":
            key_to_check = "last_updated"
        return super() and getattr(self._vehicle, key_to_check) is not None
