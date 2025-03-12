"""Select entity for seats."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from custom_components.ha_kia_hyundai import VehicleCoordinator
from custom_components.ha_kia_hyundai.vehicle_coordinator_base_entity import (
    VehicleCoordinatorBaseEntity,
)

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_VEHICLE_ID, DOMAIN, SEAT_STATUS, STR_TO_NUMBER

OFF = ["Off"]
HEAT_OPTIONS = {
    3: ["High Heat", "Medium Heat", "Low Heat"],
    2: ["High Heat", "Low Heat"],
}
COOL_OPTIONS = {
    3: ["High Cool", "Medium Cool", "Low Cool"],
    2: ["High Cool", "Low Cool"],
}

HEAT_TYPE = "heatVentType"
STEPS = "heatVentStep"


@dataclass(frozen=True, kw_only=True)
class KiaSelectEntityDescription(SelectEntityDescription):
    """Class for Kia select entities."""

    exists_fn: Callable[[VehicleCoordinatorBaseEntity], bool] = lambda _: True
    value_fn: Callable[[VehicleCoordinatorBaseEntity], str | None]
    options_fn: Callable[[VehicleCoordinatorBaseEntity], int | None]
    icon = "mdi:car-seat"


SEAT_SELECTIONS: Final[tuple[KiaSelectEntityDescription, ...]] = (
    KiaSelectEntityDescription(
        key="desired_driver_seat_comfort",
        name="Seat-Driver with Climate",
        exists_fn=lambda seat: bool(seat.front_seat_options[HEAT_TYPE]),
        value_fn=lambda seat: SEAT_STATUS[seat.climate_driver_seat],
        options_fn=lambda seat: seat.front_seat_options,
    ),
    KiaSelectEntityDescription(
        key="desired_passenger_seat_comfort",
        name="Seat-Passenger with Climate",
        exists_fn=lambda seat: bool(seat.front_seat_options[HEAT_TYPE]),
        value_fn=lambda seat: SEAT_STATUS[seat.climate_passenger_seat],
        options_fn=lambda seat: seat.front_seat_options,
    ),
    KiaSelectEntityDescription(
        key="desired_left_rear_seat_comfort",
        name="Seat-Left Rear with Climate",
        exists_fn=lambda seat: bool(seat.rear_seat_options[HEAT_TYPE]),
        value_fn=lambda seat: SEAT_STATUS[seat.climate_left_rear_seat],
        options_fn=lambda seat: seat.rear_seat_options,
    ),
    KiaSelectEntityDescription(
        key="desired_right_rear_seat_comfort",
        name="Seat-Right Rear with Climate",
        exists_fn=lambda seat: bool(seat.rear_seat_options[HEAT_TYPE]),
        value_fn=lambda seat: SEAT_STATUS[seat.climate_right_rear_seat],
        options_fn=lambda seat: seat.rear_seat_options,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the entity."""
    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    coordinator: VehicleCoordinator = hass.data[DOMAIN][vehicle_id]

    async_add_entities(
        SeatSelect(coordinator, select_description)
        for select_description in SEAT_SELECTIONS
        if coordinator.has_climate_seats
        if select_description.exists_fn(coordinator)
    )


class SeatSelect(VehicleCoordinatorBaseEntity, SelectEntity, RestoreEntity):
    """Class for seat select entities."""

    entity_description: KiaSelectEntityDescription

    @property
    def options(self) -> list[str]:
        """Return the available options."""
        # Making the assumption that any seat that offers cooling offers heat as well.
        installed_options = self.entity_description.options_fn(self.coordinator)
        if installed_options[HEAT_TYPE] == 3:
            return (
                OFF
                + HEAT_OPTIONS[installed_options[STEPS]]
                + COOL_OPTIONS[installed_options[STEPS]]
            )
        if installed_options[HEAT_TYPE] == 2:
            return OFF + COOL_OPTIONS[installed_options[STEPS]]
        return OFF + HEAT_OPTIONS[installed_options[STEPS]]

    @property
    def available(self) -> bool:
        """Return if the selector is available."""
        return super().available

    async def async_select_option(self, option: str) -> None:
        """Change the select option."""
        setattr(self.coordinator, self.entity_description.key, STR_TO_NUMBER[option])
        self._attr_current_option = option
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore preivous state when added to Hass."""
        previous_state = await self.async_get_last_state()
        if previous_state is not None and previous_state.state not in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            self._attr_current_option = previous_state.state
        else:
            self._attr_current_option = self.entity_description.value_fn(
                self.coordinator
            )

        setattr(
            self.coordinator,
            self.entity_description.key,
            STR_TO_NUMBER[self._attr_current_option],
        )
