from logging import getLogger
from typing import Final

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, STATE_UNAVAILABLE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.ha_kia_hyundai import DOMAIN, CONF_VEHICLE_ID, VehicleCoordinator
from custom_components.ha_kia_hyundai.vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity

_LOGGER = getLogger(__name__)

AC_CHARGING_LIMIT_KEY = "ev_charge_limits_ac"
DC_CHARGING_LIMIT_KEY = "ev_charge_limits_dc"

NUMBER_DESCRIPTIONS: Final[tuple[NumberEntityDescription, ...]] = (
    NumberEntityDescription(
        key=AC_CHARGING_LIMIT_KEY,
        name="AC Charging Limit",
        icon="mdi:ev-plug-type1",
        native_min_value=50,
        native_max_value=100,
        native_step=10,
        native_unit_of_measurement=PERCENTAGE,
    ),
    NumberEntityDescription(
        key=DC_CHARGING_LIMIT_KEY,
        name="DC Charging Limit",
        icon="mdi:ev-plug-ccs1",
        native_min_value=50,
        native_max_value=100,
        native_step=10,
        native_unit_of_measurement=PERCENTAGE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]

    entities = []
    for description in NUMBER_DESCRIPTIONS:
        if getattr(coordinator, description.key, None) is not None:
            entities.append(
                ChargeLimitNumber(coordinator, description)
            )

    async_add_entities(entities)


class ChargeLimitNumber(VehicleCoordinatorBaseEntity, NumberEntity, RestoreEntity):
    def __init__(
        self,
        coordinator: VehicleCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        self._key = self._description.key
        self._attr_unique_id = f"{DOMAIN}_{coordinator.vehicle_id}_{self._key}"
        self._attr_icon = self._description.icon
        self._attr_mode = NumberMode.SLIDER
        self._attr_name = f"{coordinator.vehicle_name} {self._description.name}"
        self._attr_device_class = self._description.device_class
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = self._description.native_min_value
        self._attr_native_max_value = self._description.native_max_value
        self._attr_native_step = self._description.native_step

    @property
    def native_value(self) -> float | None:
        """Return the entity value to represent the entity state."""
        value = getattr(self.coordinator, self._key)
        if value is None or value == 0:
            _LOGGER.debug(f"invalid value found for {self._key} = {value}, returning stored value of {self._attr_native_value})")
            return self._attr_native_value
        else:
            self._attr_native_value = value
            return value

    async def async_set_native_value(self, value: float) -> None:
        """Set new charging limit."""
        _LOGGER.debug(f"Setting charging limit to {value} for {self._description.key}")
        if (
            self._description.key == AC_CHARGING_LIMIT_KEY
            and self.coordinator.ev_charge_limits_ac == int(value)
        ):
            return
        if (
            self._description.key == DC_CHARGING_LIMIT_KEY
            and self.coordinator.ev_charge_limits_dc == int(value)
        ):
            return

        # set new limits
        if self._description.key == AC_CHARGING_LIMIT_KEY:
            ac_limit = int(value)
            dc_limit = self.coordinator.ev_charge_limits_dc
        else:
            ac_limit = self.coordinator.ev_charge_limits_ac
            dc_limit = int(value)
        await self.coordinator.api_connection.set_charge_limits(
            vehicle_id=self.coordinator.vehicle_id,
            ac_limit=ac_limit,
            dc_limit=dc_limit,
        )
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()


    async def async_internal_added_to_hass(self) -> None:
        """Call when the button is added to hass."""
        await super().async_internal_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state not in (STATE_UNAVAILABLE, None):
            self.__set_state(state.state)

    def __set_state(self, state: str | None) -> None:
        """Set the entity state."""
        # Invalidate the cache of the cached property
        self.__dict__.pop("state", None)
        self._attr_native_value = state
