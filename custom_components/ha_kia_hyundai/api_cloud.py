from __future__ import annotations

import logging

from abc import ABC, abstractmethod
from datetime import timedelta
from homeassistant.core import HomeAssistant

from .vehicle import Vehicle
from .api_action_status import ApiActionStatus
from .callbacks import CallbacksMixin
from .const import (
    VEHICLE_LOCK_ACTION,
)

_LOGGER = logging.getLogger(__name__)


class ApiCloud(CallbacksMixin, ABC):
    _current_action: ApiActionStatus | None = None
    hvac_on_force_scan_interval: timedelta = timedelta(minutes=10)

    def __init__(
        self,
        username: str,
        password: str,
        hass: HomeAssistant,
        update_interval: timedelta = None,
        force_scan_interval: timedelta = None,
        no_force_scan_hour_start: int = None,
        no_force_scan_hour_finish: int = None,
    ):
        self.hass: HomeAssistant = hass
        self.update_interval: timedelta = update_interval
        self.force_scan_interval: timedelta = force_scan_interval
        self.no_force_scan_hour_start: int = no_force_scan_hour_start
        self.no_force_scan_hour_finish: int = no_force_scan_hour_finish
        self.username: str = username
        self.password: str = password

    async def cleanup(self):
        pass

    @abstractmethod
    async def login(self):
        pass

    async def get_vehicle(self, identifier: str) -> Vehicle:
        vehicles = await self.get_vehicles()
        for vehicle in vehicles:
            if vehicle.identifier == identifier:
                return vehicle
        raise RuntimeError(f"vehicle with identifier:{identifier} missing")

    @abstractmethod
    async def get_vehicles(self) -> list[Vehicle]:
        pass

    @abstractmethod
    async def update(self, vehicle: Vehicle) -> None:
        pass

    @abstractmethod
    async def request_sync(self, vehicle: Vehicle) -> None:
        pass

    @abstractmethod
    async def lock(self, vehicle: Vehicle, action: VEHICLE_LOCK_ACTION) -> None:
        pass

    @abstractmethod
    async def start_climate(
        self,
        vehicle: Vehicle,
        set_temp: int,
        defrost: bool,
        climate: bool,
        heating: bool,
        duration: int,
    ) -> None:
        pass

    @abstractmethod
    async def stop_climate(self, vehicle: Vehicle) -> None:
        pass

    @abstractmethod
    async def start_charge(self, vehicle: Vehicle) -> None:
        pass

    @abstractmethod
    async def stop_charge(self, vehicle: Vehicle) -> None:
        pass

    @abstractmethod
    async def set_charge_limits(
        self, vehicle: Vehicle, ac_limit: int, dc_limit: int
    ) -> None:
        pass

    def _start_action(self, name: str) -> None:
        if self.action_in_progress():
            raise RuntimeError(
                f"Existing Action in progress: {self._current_action.name}; started at {self._current_action.start_time}"
            )
        else:
            self._current_action = ApiActionStatus(name)
            self.publish_updates()

    def action_in_progress(self) -> bool:
        return not (
            self._current_action is None
            or self._current_action.completed()
            or self._current_action.expired()
        )

    def current_action_name(self) -> str:
        if self.action_in_progress():
            return self._current_action.name
        else:
            "None"

    @property
    @abstractmethod
    def region(self) -> str:
        pass

    @property
    @abstractmethod
    def brand(self) -> str:
        pass
