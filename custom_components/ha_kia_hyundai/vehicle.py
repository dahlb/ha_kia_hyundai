from __future__ import annotations

import logging
from datetime import datetime, timedelta
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import (
    LENGTH_MILES,
    LENGTH_KILOMETERS,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
import asyncio
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
from geopy.location import Location
from geopy.exc import GeocoderServiceError

from .const import (
    VEHICLE_LOCK_ACTION,
    REQUEST_TO_SYNC_COOLDOWN,
    INITIAL_STATUS_DELAY_AFTER_COMMAND,
    INSTRUMENTS,
    BINARY_INSTRUMENTS,
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

    fuel_range_value: float = None
    fuel_range_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    total_range_value: float = None
    total_range_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    odometer_value: float = None
    odometer_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
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
    climate_temperature_value: float = None
    climate_temperature_unit: TEMP_CELSIUS | TEMP_FAHRENHEIT = None
    climate_heated_steering_wheel_on: bool = None
    climate_heated_side_mirror_on: bool = None
    climate_heated_rear_window_on: bool = None
    climate_heated_seat_front_right_on: bool = None
    climate_heated_seat_front_left_on: bool = None
    climate_heated_seat_rear_right_on: bool = None
    climate_heated_seat_rear_left_on: bool = None
    ev_plugged_in: bool = None
    ev_battery_charging: bool = None
    ev_battery_level: int = None
    ev_charge_current_remaining_duration: int = None
    ev_charge_fast_duration: int = None
    ev_charge_portable_duration: int = None
    ev_charge_station_duration: int = None
    ev_remaining_range_value: int = None
    ev_remaining_range_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    ev_max_dc_charge_level: int = None
    ev_max_ac_charge_level: int = None
    ev_max_range_ac_charge_value: float = None
    ev_max_range_ac_charge_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    ev_max_range_dc_charge_value: float = None
    ev_max_range_dc_charge_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    tire_all_on: bool = None
    tire_front_left_on: bool = None
    tire_front_right_on: bool = None
    tire_rear_left_on: bool = None
    tire_rear_right_on: bool = None
    last_service_value: float = None
    last_service_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    next_service_value: float = None
    next_service_unit: LENGTH_KILOMETERS | LENGTH_MILES = None
    next_service_mile_value: float = None
    next_service_mile_unit: LENGTH_KILOMETERS | LENGTH_MILES = None

    latitude: float = None
    longitude: float = None
    location_name: str = None

    # usage counters
    calls_today_for_actions = None
    calls_today_for_update = None
    calls_today_for_request_sync = None

    # debug
    raw_responses = None

    def __init__(self, api_cloud, identifier: str, api_unsupported_keys):
        self.api_cloud = api_cloud
        self.identifier = identifier
        self.api_unsupported_keys = api_unsupported_keys

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
            _LOGGER.debug(f"interval update skipping")

        force_scan_interval: timedelta = self.api_cloud.force_scan_interval
        if self.climate_hvac_on:
            _LOGGER.debug(
                f"HVAC on, changing force_scan_interval to api_cloud duration of minutes"
            )
            force_scan_interval = self.api_cloud.hvac_on_force_scan_interval
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
                        _LOGGER.debug(
                            f"sync request skipping, interval sync request failed to be fulfilled by Vehicle, REQUEST_TO_SYNC_COOLDOWN:{REQUEST_TO_SYNC_COOLDOWN}; age_of_last_request_to_sync:{age_of_last_request_to_sync}"
                        )
                        return
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
        if self.calls_today_for_request_sync is not None:
            self.calls_today_for_request_sync.mark_used()
        await self.api_cloud.request_sync(vehicle=self)
        if previous_last_synced_to_cloud == self.last_synced_to_cloud:
            self.api_cloud._session_id = None
            error = RuntimeError(f"sync requested but not completed! {event_time_api}")
            if self.calls_today_for_request_sync is not None:
                self.calls_today_for_request_sync.mark_failed(error=error)
            raise error

    async def lock_action(self, action: VEHICLE_LOCK_ACTION):
        await self.api_cloud.lock(vehicle=self, action=action)
        if self.calls_today_for_actions is not None:
            self.calls_today_for_actions.mark_used()

    async def start_climate(self, set_temp, defrost, climate, heating, duration):
        if set_temp is None:
            set_temp = 76
        if defrost is None:
            defrost = False
        if climate is None:
            climate = True
        if heating is None:
            heating = False
        if duration is None:
            duration = 5
        await self.api_cloud.start_climate(
            vehicle=self,
            set_temp=set_temp,
            defrost=defrost,
            climate=climate,
            heating=heating,
            duration=duration,
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

    def supported_binary_instruments(self):
        supported_binary_instruments = []
        empty_keys = self.empty_keys()
        for binary_instrument in BINARY_INSTRUMENTS:
            binary_instrument_key = binary_instrument[1]
            if binary_instrument_key not in self.api_unsupported_keys:
                if binary_instrument_key not in empty_keys:
                    supported_binary_instruments.append(binary_instrument)
        return supported_binary_instruments

    def supported_instruments(self):
        supported_instruments = []
        empty_keys = self.empty_keys()
        for instrument in INSTRUMENTS:
            instrument_key = instrument[1]
            if instrument_key not in self.api_unsupported_keys:
                if instrument_key not in empty_keys:
                    supported_instruments.append(instrument)
                elif (
                    instrument_key
                    in [
                        "ev_battery_level",
                        "ev_max_dc_charge_level",
                        "ev_max_ac_charge_level",
                    ]
                    and self.ev_plugged_in is not None
                ):
                    supported_instruments.append(instrument)
        return supported_instruments

    def empty_keys(self):
        return [key for key, value in self.__repr__().items() if value is None]

    async def update_location_name(self):
        async with Nominatim(
            user_agent="ha_kia_hyundai",
            adapter_factory=AioHTTPAdapter,
        ) as geolocator:
            try:
                location: Location = await geolocator.reverse(
                    query=(self.latitude, self.longitude)
                )
                self.location_name = location.address
            except GeocoderServiceError as error:
                _LOGGER.warning(f"Location name lookup failed:{error}")

    def __repr__(self):
        return {
            "identifier": self.identifier,
            "vin": self.vin,
            "key": self.key,
            "model": self.model,
            "name": self.name,
            "last_synced_to_cloud": self.last_synced_to_cloud,
            "last_updated_from_cloud": self.last_updated_from_cloud,
            "last_sync_requested": self.last_sync_requested,
            "fuel_range_value": self.fuel_range_value,
            "fuel_range_unit": self.fuel_range_unit,
            "total_range_value": self.total_range_value,
            "total_range_unit": self.total_range_unit,
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
            "climate_heated_seat_front_right_on": self.climate_heated_seat_front_right_on,
            "climate_heated_seat_front_left_on": self.climate_heated_seat_front_left_on,
            "climate_heated_seat_rear_right_on": self.climate_heated_seat_rear_right_on,
            "climate_heated_seat_rear_left_on": self.climate_heated_seat_rear_left_on,
            "ev_plugged_in": self.ev_plugged_in,
            "ev_battery_charging": self.ev_battery_charging,
            "ev_battery_level": self.ev_battery_level,
            "ev_charge_current_remaining_duration": self.ev_charge_current_remaining_duration,
            "ev_charge_fast_duration": self.ev_charge_fast_duration,
            "ev_charge_portable_duration": self.ev_charge_portable_duration,
            "ev_charge_station_duration": self.ev_charge_station_duration,
            "ev_remaining_range_value": self.ev_remaining_range_value,
            "ev_remaining_range_unit": self.ev_remaining_range_unit,
            "ev_max_dc_charge_level": self.ev_max_dc_charge_level,
            "ev_max_ac_charge_level": self.ev_max_ac_charge_level,
            "ev_max_range_ac_charge_value": self.ev_max_range_ac_charge_value,
            "ev_max_range_ac_charge_unit": self.ev_max_range_ac_charge_unit,
            "ev_max_range_dc_charge_value": self.ev_max_range_dc_charge_value,
            "ev_max_range_dc_charge_unit": self.ev_max_range_dc_charge_unit,
            "tire_all_on": self.tire_all_on,
            "tire_front_left_on": self.tire_front_left_on,
            "tire_front_right_on": self.tire_front_right_on,
            "tire_rear_left_on": self.tire_rear_left_on,
            "tire_rear_right_on": self.tire_rear_right_on,
            "last_service_value": self.last_service_value,
            "last_service_unit": self.last_service_unit,
            "next_service_value": self.next_service_value,
            "next_service_unit": self.next_service_unit,
            "next_service_mile_value": self.next_service_mile_value,
            "next_service_mile_unit": self.next_service_mile_unit,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
        }

    def __str__(self):
        return f"{self.__repr__()}"
