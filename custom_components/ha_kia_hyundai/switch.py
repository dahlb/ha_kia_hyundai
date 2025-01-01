from logging import getLogger

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import CalculatedState
from homeassistant.helpers.restore_state import RestoreEntity

from . import VehicleCoordinator
from .const import DOMAIN
from .vehicle_coordinator_base_entity import VehicleCoordinatorBaseEntity

_LOGGER = getLogger(__name__)
PARALLEL_UPDATES: int = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    vehicle_id = config_entry.unique_id
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]

    async_add_entities([
        ClimateDesiredDefrostSwitch(coordinator=coordinator),
        ClimateDesiredHeatingAccSwitch(coordinator=coordinator),
        ChargingSwitch(coordinator=coordinator),
    ], True)


class ClimateDesiredDefrostSwitch(VehicleCoordinatorBaseEntity, SwitchEntity, RestoreEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:car-defrost-front"
    _attr_name = "Climate Desired Defrost"
    _attr_is_on = False

    def __init__(
            self,
            coordinator: VehicleCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{coordinator.vehicle_id}-climate-desired-defrost"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.climate_desired_defrost

    async def async_turn_on(self, **kwargs: any) -> None:
        self.coordinator.climate_desired_defrost = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        self.coordinator.climate_desired_defrost = False
        self.async_write_ha_state()

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
        self.coordinator.climate_desired_defrost = state == STATE_ON


class ClimateDesiredHeatingAccSwitch(VehicleCoordinatorBaseEntity, SwitchEntity, RestoreEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:steering"
    _attr_name = "Climate Desired Heating Acc"

    def __init__(
            self,
            coordinator: VehicleCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{coordinator.vehicle_id}-climate-desired-heating-acc"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.climate_desired_heating_acc

    async def async_turn_on(self, **kwargs: any) -> None:
        self.coordinator.climate_desired_heating_acc = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        self.coordinator.climate_desired_heating_acc = False
        self.async_write_ha_state()

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
        self.coordinator.climate_desired_heating_acc = state == STATE_ON

class ChargingSwitch(VehicleCoordinatorBaseEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:ev-station"
    _attr_name = "Charging"
    _attr_available = False

    def __init__(
            self,
            coordinator: VehicleCoordinator,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{coordinator.vehicle_id}-charging-switch"

    @property
    def available(self) -> bool:
        return super() and self.coordinator.ev_plugged_in

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.ev_battery_charging

    async def async_turn_on(self, **kwargs: any) -> None:
        await self.coordinator.api_connection.start_charge(vehicle_id=self.coordinator.vehicle_id)
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self.coordinator.api_connection.stop_charge(vehicle_id=self.coordinator.vehicle_id)
        self.coordinator.async_update_listeners()
        await self.coordinator.async_request_refresh()
