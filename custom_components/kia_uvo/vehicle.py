import logging
from datetime import datetime
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import VEHICLE_LOCK_ACTION

_LOGGER = logging.getLogger(__name__)


class Vehicle:
    identifier: str
    vin: str = None
    key: str = None
    model: str = None
    name: str = None

    last_updated: datetime = None
    last_refreshed: datetime = None  # in local time zone
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

    def __init__(self, api_cloud, identifier: str):
        self.api_cloud = api_cloud
        self.identifier = identifier

        async def async_update_data():
            await self.api_cloud.refresh(vehicle=self)
            local_timezone = dt_util.UTC
            event_time_local = dt_util.utcnow().astimezone(local_timezone)
            self.last_refreshed = event_time_local

        self.coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
            api_cloud.hass,
            _LOGGER,
            name=f"Vehicle {identifier}",
            update_method=async_update_data,
        )

    async def refresh(self, interval: bool = False):
        _LOGGER.debug(f"Vehicle:{self.__repr__()}")
        old_vehicle_status: dict = self.__repr__()
        local_timezone = dt_util.UTC
        event_time_local = dt_util.utcnow().astimezone(local_timezone)
        if self.last_updated is None:
            _LOGGER.debug(f"last updated is None!")
            interval = False
        else:
            age_of_last_refresh = datetime.now(local_timezone) - self.last_refreshed
            _LOGGER.debug(
                f"age_of_last_refresh:{age_of_last_refresh}; last refreshed:{self.last_refreshed}; now:{event_time_local}"
            )  # 5 hours ahead of local
        force_scan_internal = self.api_cloud.force_scan_interval
        if not interval or age_of_last_refresh > self.api_cloud.update_interval:
            await self.coordinator.async_refresh()
        else:
            _LOGGER.debug(f"refresh happened within update_interval, skipping refresh")
        age_of_last_sync = datetime.now(local_timezone) - self.last_updated
        _LOGGER.debug(
            f"age_of_last_sync:{age_of_last_sync}; last updated:{self.last_updated}; now:{event_time_local}"
        )

        if self.climate_hvac_on is not None and self.climate_hvac_on:
            _LOGGER.debug(f"HVAC on, changing staleness max age to 5 minutes")
            force_scan_internal = 5
        call_force_update = False
        if (
            not self.engine_on
            and old_vehicle_status["engine_on"] is not None
            and not old_vehicle_status["engine_on"]
            and self.ev_battery_level == 0
            and old_vehicle_status["ev_battery_level"] != 0
        ):
            _LOGGER.debug(
                f"zero battery api error, force_update started to correct data"
            )
            call_force_update = True
        elif (
            self.ev_max_dc_charge_level is not None
            and self.ev_max_dc_charge_level > 100
        ) or (
            self.ev_max_ac_charge_level is not None
            and self.ev_max_ac_charge_level > 100
        ):
            _LOGGER.debug(
                f"max charge levels api error, force_update started to correct data"
            )
            call_force_update = True
        elif (
            self.api_cloud.no_force_scan_hour_start
            > event_time_local.hour
            >= self.api_cloud.no_force_scan_hour_finish
        ):
            if age_of_last_sync > force_scan_internal:
                _LOGGER.debug(f"data stale, requesting a sync based on scan interval")
                call_force_update = True

        if call_force_update:
            _LOGGER.debug(f"requesting data sync and refresh")
            await self.api_cloud.request_sync(vehicle=self)
            await self.coordinator.async_refresh()
        else:
            _LOGGER.debug(f"no request for data sync deemed needed")

    async def request_sync(self):
        local_timezone = dt_util.UTC
        event_time_local = dt_util.utcnow().astimezone(local_timezone)
        self.last_sync_requested = event_time_local
        previous_syn_datetime = self.last_refreshed
        await self.api_cloud.request_sync(vehicle=self)
        if previous_syn_datetime == self.last_refreshed:
            raise RuntimeError("sync requested but not completed!")

    async def lock_action(self, action: VEHICLE_LOCK_ACTION):
        await self.api_cloud.lock(vehicle=self, action=action)

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

    async def stop_climate(self):
        await self.api_cloud.stop_climate(vehicle=self)

    async def start_charge(self):
        await self.api_cloud.start_charge(vehicle=self)

    async def stop_charge(self):
        await self.api_cloud.stop_charge(vehicle=self)

    async def set_charge_limits(self, ac_limit: int, dc_limit: int):
        if ac_limit is None:
            ac_limit = 90
        if dc_limit is None:
            dc_limit = 90
        await self.api_cloud.set_charge_limits(
            vehicle=self, ac_limit=ac_limit, dc_limit=dc_limit
        )

    def __repr__(self):
        return {
            "identifier": self.identifier,
            "vin": self.vin,
            "key": self.key,
            "model": self.model,
            "name": self.name,
            "last_updated": self.last_updated,
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
