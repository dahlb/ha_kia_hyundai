import logging
from datetime import datetime
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import asyncio

from .const import (
    VEHICLE_LOCK_ACTION,
    REQUEST_TO_SYNC_COOLDOWN,
    INITIAL_STATUS_DELAY_AFTER_COMMAND,
)

_LOGGER = logging.getLogger(__name__)


class Vehicle:
    identifier: str
    vin: str = None
    key: str = None
    model: str = None
    name: str = None

    # in API based time zone ...
    last_synced_to_cloud: datetime = None
    last_updated_from_cloud: datetime = None
    last_sync_requested: datetime = None

    odometer_value: float = None
    odometer_unit: int = None
    battery_level: int = None
    engine_on: bool = None
    low_fuel_light_on: bool = None
    doors_locked: bool = None
    door_front_left_open: bool = None
    door_front_right_open: bool = None
    door_back_left_open: bool = None
    door_back_right_open: bool = None
    door_trunk_open: bool = None
    door_hood_open: bool = None
    sleep_mode_on: bool = None
    climate_hvac_on: bool = None
    climate_defrost_on: bool = None
    climate_temperature_value: int = None
    climate_temperature_unit: int = None
    climate_heated_steering_wheel_on: bool = None
    climate_heated_side_mirror_on: bool = None
    climate_heated_rear_window_on: bool = None
    ev_plugged_in: bool = None
    ev_battery_charging: bool = None
    ev_battery_level: int = None
    ev_charge_remaining_time: int = None
    ev_remaining_range_value: int = None
    ev_remaining_range_unit: int = None
    ev_max_dc_charge_level: int = None
    ev_max_ac_charge_level: int = None
    tire_all_on: bool = None

    latitude: float = None
    longitude: float = None
    location_name: str = None

    # usage counters
    calls_today_for_actions = None
    calls_today_for_update = None
    calls_today_for_request_sync = None

    def __init__(self, api_cloud, identifier: str):
        self.api_cloud = api_cloud
        self.identifier = identifier

        async def async_update_data():
            if self.calls_today_for_update is not None:
                self.calls_today_for_update.mark_used()
            await self.api_cloud.update(vehicle=self)
            local_timezone = dt_util.UTC
            event_time_local = dt_util.utcnow().astimezone(local_timezone)
            self.last_updated_from_cloud = event_time_local

        self.coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
            api_cloud.hass,
            _LOGGER,
            name=f"Vehicle {identifier}",
            update_method=async_update_data,
        )

    async def update(self, interval: bool = False):
        _LOGGER.debug(f"update starting interval?:{interval}")
        api_timezone = dt_util.UTC
        event_time_api = dt_util.utcnow().astimezone(api_timezone)
        event_time_local = dt_util.as_local(dt_util.utcnow())
        if self.last_updated_from_cloud is None:
            interval = False
        else:
            age_of_last_update_from_cloud = (
                datetime.now(api_timezone) - self.last_updated_from_cloud
            )
        if (
            not interval
            or age_of_last_update_from_cloud > self.api_cloud.update_interval
        ):
            await self.coordinator.async_refresh()
        else:
            _LOGGER.debug(
                f"interval update skipping"
            )

        force_scan_interval = self.api_cloud.force_scan_interval
        if self.climate_hvac_on is not None and self.climate_hvac_on:
            _LOGGER.debug(f"HVAC on, changing force_scan_interval to 5 minutes")
            force_scan_interval = 5
        if (
            self.api_cloud.no_force_scan_hour_start
            > event_time_local.hour
            >= self.api_cloud.no_force_scan_hour_finish
        ):
            age_of_last_sync = datetime.now(api_timezone) - self.last_synced_to_cloud
            if age_of_last_sync > force_scan_interval:
                if self.last_sync_requested is not None and interval:
                    age_of_last_request_to_sync = (
                            datetime.now(api_timezone) - self.last_sync_requested
                    )
                    if age_of_last_request_to_sync < REQUEST_TO_SYNC_COOLDOWN:
                        raise RuntimeError(
                            f"interval sync request failed, waiting for REQUEST_TO_SYNC_COOLDOWN:{REQUEST_TO_SYNC_COOLDOWN}; age_of_last_request_to_sync:{age_of_last_request_to_sync}")
                _LOGGER.debug(
                    f"requesting a sync based on scan interval; age_of_last_sync:{age_of_last_sync}; last synced:{self.last_synced_to_cloud}; now:{event_time_api}"
                )
                await asyncio.sleep(INITIAL_STATUS_DELAY_AFTER_COMMAND)
                await self.request_sync()
            else:
                _LOGGER.debug(
                    f"sync request skipping, a sync within force scan interval: age_of_last_sync:{age_of_last_sync}, force_scan_interval: {force_scan_interval}"
                )
        else:
            _LOGGER.debug(
                f"sync request skipping, no scan settings, setting start:{self.api_cloud.no_force_scan_hour_start}, finish:{self.api_cloud.no_force_scan_hour_finish}; now:{event_time_local.hour}"
            )

    async def request_sync(self):
        api_timezone = dt_util.UTC
        event_time_api = dt_util.utcnow().astimezone(api_timezone)
        self.last_sync_requested = event_time_api
        previous_last_synced_to_cloud = self.last_synced_to_cloud
        if (
            self.calls_today_for_request_sync is not None
            and self.calls_today_for_request_sync.failed_today
        ):
            raise RuntimeError(
                f"sync requested likely over quota skipping until tomorrow {self.calls_today_for_request_sync.failed_error}"
            )
        try:
            if self.calls_today_for_request_sync is not None:
                self.calls_today_for_request_sync.mark_used()
            await self.api_cloud.request_sync(vehicle=self)
        except Exception as error:
            if self.calls_today_for_request_sync is not None:
                self.calls_today_for_request_sync.mark_failed(error)
            raise
        if previous_last_synced_to_cloud == self.last_synced_to_cloud:
            self.api_cloud._session_id = None
            error = RuntimeError("sync requested but not completed!")
            if self.calls_today_for_request_sync is not None:
                self.calls_today_for_request_sync.mark_failed(error=error)
            raise error

    async def lock_action(self, action: VEHICLE_LOCK_ACTION):
        await self.api_cloud.lock(vehicle=self, action=action)
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def start_climate(self, set_temp, defrost, climate, heating):
        if set_temp is None:
            set_temp = 76
        if defrost is None:
            defrost = False
        if climate is None:
            climate = True
        if heating is None:
            heating = False
        await self.api_cloud.start_climate(
            vehicle=self,
            set_temp=set_temp,
            defrost=defrost,
            climate=climate,
            heating=heating,
        )
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def stop_climate(self):
        await self.api_cloud.stop_climate(vehicle=self)
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def start_charge(self):
        await self.api_cloud.start_charge(vehicle=self)
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def stop_charge(self):
        await self.api_cloud.stop_charge(vehicle=self)
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def set_charge_limits(self, ac_limit: int, dc_limit: int):
        if ac_limit is None:
            ac_limit = 90
        if dc_limit is None:
            dc_limit = 90
        await self.api_cloud.set_charge_limits(
            vehicle=self, ac_limit=ac_limit, dc_limit=dc_limit
        )
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    def __repr__(self):
        return {
            "identifier": self.identifier,
            "vin": self.vin,
            "key": self.key,
            "model": self.model,
            "name": self.name,
            "last_updated": self.last_synced_to_cloud,
            "odometer_value": self.odometer_value,
            "odometer_unit": self.odometer_unit,
            "battery_level": self.battery_level,
            "engine_on": self.engine_on,
            "low_fuel_light_on": self.low_fuel_light_on,
            "doors_locked": self.doors_locked,
            "door_front_left_open": self.door_front_left_open,
            "door_front_right_open": self.door_front_right_open,
            "door_back_left_open": self.door_back_left_open,
            "door_back_right_open": self.door_back_right_open,
            "door_trunk_open": self.door_trunk_open,
            "door_hood_open": self.door_hood_open,
            "sleep_mode_on": self.sleep_mode_on,
            "climate_hvac_on": self.climate_hvac_on,
            "climate_defrost_on": self.climate_defrost_on,
            "climate_temperature_value": self.climate_temperature_value,
            "climate_temperature_unit": self.climate_temperature_unit,
            "climate_heated_steering_wheel_on": self.climate_heated_steering_wheel_on,
            "climate_heated_side_mirror_on": self.climate_heated_side_mirror_on,
            "climate_heated_rear_window_on": self.climate_heated_rear_window_on,
            "ev_plugged_in": self.ev_plugged_in,
            "ev_battery_charging": self.ev_battery_charging,
            "ev_battery_level": self.ev_battery_level,
            "ev_charge_remaining_time": self.ev_charge_remaining_time,
            "ev_remaining_range_value": self.ev_remaining_range_value,
            "ev_remaining_range_unit": self.ev_remaining_range_unit,
            "ev_max_dc_charge_level": self.ev_max_dc_charge_level,
            "ev_max_ac_charge_level": self.ev_max_ac_charge_level,
            "tire_all_on": self.tire_all_on,
        }

    def __str__(self):
        return f"{self.__repr__()}"
