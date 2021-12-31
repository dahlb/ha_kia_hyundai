from __future__ import annotations

import logging

from kia_hyundai_api import UsHyundai, AuthError, RateError
from homeassistant.const import TEMP_FAHRENHEIT, LENGTH_MILES
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from datetime import timedelta, datetime

from .api_cloud import ApiCloud
from .vehicle import Vehicle
from .const import (
    VEHICLE_LOCK_ACTION,
    USA_TEMP_RANGE,
    BRAND_HYUNDAI,
    REGION_USA,
)
from .util import (
    convert_last_updated_str_to_datetime,
    safely_get_json_value,
    convert_api_unit_to_ha_unit_of_distance,
)

_LOGGER = logging.getLogger(__name__)


class ApiCloudUsHyundai(ApiCloud):
    pin: str = None
    api: UsHyundai = None
    _access_token: str = None

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
        super().__init__(
            username=username,
            password=password,
            hass=hass,
            update_interval=update_interval,
            force_scan_interval=force_scan_interval,
            no_force_scan_hour_start=no_force_scan_hour_start,
            no_force_scan_hour_finish=no_force_scan_hour_finish,
        )
        client_session = async_get_clientsession(hass)
        self.api: UsHyundai = UsHyundai(client_session=client_session)
        self.hvac_on_force_scan_interval: timedelta = force_scan_interval
        self.last_loc_timestamp = datetime.now() - timedelta(hours=3)

    async def _get_access_token(self):
        if self._access_token is None:
            await self.login()
        return self._access_token

    async def login(self):
        try:
            self._access_token, _, _ = await self.api.login(
                self.username, self.password, self.pin
            )
        except AuthError as err:
            raise ConfigEntryAuthFailed(err) from err

    async def get_vehicles(self) -> list[Vehicle]:
        access_token = await self._get_access_token()
        api_vehicles = await self.api.get_vehicles(
            username=self.username, pin=self.pin, access_token=access_token
        )
        vehicles = []
        for response_vehicle in api_vehicles["enrolledVehicleDetails"]:
            vehicle = Vehicle(
                api_cloud=self,
                identifier=safely_get_json_value(
                    response_vehicle, "vehicleDetails.vin"
                ),
                api_unsupported_keys=[],
            )
            vehicle.vin = safely_get_json_value(response_vehicle, "vehicleDetails.vin")
            vehicle.key = safely_get_json_value(
                response_vehicle, "vehicleDetails.regid"
            )
            vehicle.model = safely_get_json_value(
                response_vehicle, "vehicleDetails.modelCode"
            )
            vehicle.name = safely_get_json_value(
                response_vehicle, "vehicleDetails.nickName"
            )
            vehicle.odometer_value = safely_get_json_value(
                response_vehicle, "vehicleDetails.odometer"
            )
            vehicles.append(vehicle)
        return vehicles

    async def update(self, vehicle: Vehicle) -> None:
        access_token = await self._get_access_token()
        api_vehicle_status = await self.api.get_cached_vehicle_status(
            username=self.username,
            pin=self.pin,
            access_token=access_token,
            vehicle_vin=vehicle.vin,
        )
        vehicle.raw_responses = {
            "status": api_vehicle_status
        }

        updated_vehicle = await self.get_vehicle(identifier=vehicle.identifier)

        vehicle.last_synced_to_cloud = convert_last_updated_str_to_datetime(
            last_updated_str=api_vehicle_status["vehicleStatus"]["dateTime"]
            .replace("-", "")
            .replace("T", "")
            .replace(":", "")
            .replace("Z", ""),
            timezone_of_str=dt_util.UTC,
        )
        previous_odometer_value = vehicle.odometer_value
        vehicle.odometer_value = updated_vehicle.odometer_value
        vehicle.odometer_unit = LENGTH_MILES

        vehicle.tire_all_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.tirePressureLamp.tirePressureWarningLampAll",
            bool,
        )
        vehicle.tire_front_right_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.tirePressureLamp.tirePressureWarningLampFrontRight",
            bool,
        )
        vehicle.tire_front_left_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.tirePressureLamp.tirePressureWarningLampFrontLeft",
            bool,
        )
        vehicle.tire_rear_right_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.tirePressureLamp.tirePressureWarningLampRearRight",
            bool,
        )
        vehicle.tire_rear_left_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.tirePressureLamp.tirePressureWarningLampRearLeft",
            bool,
        )
        vehicle.doors_locked = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.doorLockStatus", bool
        )

        target_soc = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.targetSOC"
        )
        if target_soc is not None:
            target_soc.sort(key=lambda x: x["plugType"])

        vehicle.door_hood_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.hoodOpen", bool
        )
        vehicle.door_trunk_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.trunkOpen", bool
        )
        vehicle.door_front_left_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.doorOpen.frontLeft", bool
        )
        vehicle.door_front_right_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.doorOpen.frontRight", bool
        )
        vehicle.door_back_left_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.doorOpen.backLeft", bool
        )
        vehicle.door_back_right_open = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.doorOpen.backRight", bool
        )
        vehicle.engine_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.engine", bool
        )
        vehicle.climate_hvac_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.airCtrlOn", bool
        )
        vehicle.climate_defrost_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.defrost", bool
        )
        vehicle.climate_heated_rear_window_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.sideBackWindowHeat", bool
        )
        vehicle.climate_heated_side_mirror_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.sideMirrorHeat", bool
        )
        vehicle.climate_heated_steering_wheel_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.steerWheelHeat", bool
        )
        vehicle.climate_heated_seat_front_right_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.seatHeaterVentState.frSeatHeatState",
            bool,
        )
        vehicle.climate_heated_seat_front_left_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.seatHeaterVentState.flSeatHeatState",
            bool,
        )
        vehicle.climate_heated_seat_rear_right_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.seatHeaterVentState.rrSeatHeatState",
            bool,
        )
        vehicle.climate_heated_seat_rear_left_on = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.seatHeaterVentState.rlSeatHeatState",
            bool,
        )
        vehicle.low_fuel_light_on = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.lowFuelLight", bool
        )
        vehicle.ev_battery_charging = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.batteryCharge", bool
        )
        vehicle.ev_plugged_in = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.batteryPlugin", bool
        )

        ev_battery_level = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.batteryStatus", int
        )
        if ev_battery_level != 0:
            vehicle.ev_battery_level = ev_battery_level
        vehicle.ev_remaining_range_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.evModeRange.value",
            float,
        )
        vehicle.ev_remaining_range_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.evModeRange.unit",
                int,
            )
        )
        vehicle.total_range_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.total_range_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.ev_charge_current_remaining_duration = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.remainTime2.atc.value", int
        )
        vehicle.ev_charge_fast_duration = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.remainTime2.etc1.value", int
        )
        vehicle.ev_charge_portable_duration = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.remainTime2.etc2.value", int
        )
        vehicle.ev_charge_station_duration = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.remainTime2.etc3.value", int
        )
        ev_max_dc_charge_level = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.targetSOC.0.targetSOClevel", int
        )
        if ev_max_dc_charge_level is not None and ev_max_dc_charge_level <= 100:
            vehicle.ev_max_dc_charge_level = ev_max_dc_charge_level
        ev_max_ac_charge_level = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.evStatus.targetSOC.1.targetSOClevel", int
        )
        if ev_max_ac_charge_level is not None and ev_max_ac_charge_level <= 100:
            vehicle.ev_max_ac_charge_level = ev_max_ac_charge_level
        vehicle.ev_max_range_dc_charge_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.evStatus.targetSOC.0.dte.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.ev_max_range_dc_charge_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "vehicleStatus.evStatus.targetSOC.0.dte.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.ev_max_range_ac_charge_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleStatus.evStatus.targetSOC.1.dte.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.ev_max_range_ac_charge_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "vehicleStatus.evStatus.targetSOC.1.dte.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.battery_level = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.battery.batSoc", int
        )

        temp_value = safely_get_json_value(api_vehicle_status, "vehicleStatus.airTemp.value")
        if temp_value is not None:
            if temp_value == "LO":
                vehicle.climate_temperature_value = USA_TEMP_RANGE[0]
            elif temp_value == "HI":
                vehicle.climate_temperature_value = USA_TEMP_RANGE[-1]
            else:
                temp_value = temp_value.replace("H", "")
                vehicle.climate_temperature_value = USA_TEMP_RANGE[int(temp_value, 16)]
        vehicle.climate_temperature_unit = TEMP_FAHRENHEIT

        non_ev_fuel_distance = safely_get_json_value(
            api_vehicle_status, "vehicleStatus.dte.value", float
        )
        if non_ev_fuel_distance is not None:
            vehicle.fuel_range_value = safely_get_json_value(
                api_vehicle_status, "vehicleStatus.dte.value", float
            )
            vehicle.fuel_range_unit = convert_api_unit_to_ha_unit_of_distance(
                safely_get_json_value(api_vehicle_status, "vehicleStatus.dte.unit", int)
            )
        else:
            vehicle.fuel_range_value = safely_get_json_value(
                api_vehicle_status,
                "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.gasModeRange.value",
                float,
            )
            vehicle.fuel_range_unit = convert_api_unit_to_ha_unit_of_distance(
                safely_get_json_value(
                    api_vehicle_status,
                    "vehicleStatus.evStatus.drvDistance.0.rangeByFuel.gasModeRange.unit",
                    int,
                )
            )

        if (
            previous_odometer_value is None
            or previous_odometer_value > vehicle.odometer_value
            and (self.last_loc_timestamp < datetime.now() - timedelta(hours=1))
        ):
            try:
                previous_latitude = vehicle.latitude
                previous_longitude = vehicle.longitude
                api_vehicle_location = await self.api.get_location(
                    username=self.username,
                    pin=self.pin,
                    access_token=access_token,
                    vehicle_vin=vehicle.vin,
                )
                vehicle.raw_responses["location"] = api_vehicle_location

                vehicle.latitude = safely_get_json_value(
                    api_vehicle_location, "coord.lat", float
                )
                vehicle.longitude = safely_get_json_value(
                    api_vehicle_location, "coord.lon", float
                )
                if (
                        (
                                vehicle.latitude != previous_latitude
                                or vehicle.longitude != previous_longitude
                        )
                        and vehicle.latitude is not None
                        and vehicle.longitude is not None
                ):
                    await vehicle.update_location_name()
            except RateError:
                self.last_loc_timestamp = datetime.now() + timedelta(hours=11)
                _LOGGER.warning(
                    f"get vehicle location rate limit exceeded.  Location will not be fetched until at least {self.last_loc_timestamp + timedelta(hours=1)}"
                )

    async def request_sync(self, vehicle: Vehicle) -> None:
        raise NotImplemented(f"request_sync not implemented, api sniffing needed for this feature")

    async def lock(self, vehicle: Vehicle, action: VEHICLE_LOCK_ACTION) -> None:
        access_token = await self._get_access_token()
        if action == VEHICLE_LOCK_ACTION.LOCK:
            await self.api.lock(
                username=self.username,
                pin=self.pin,
                access_token=access_token,
                vehicle_vin=vehicle.vin,
                vehicle_regid=vehicle.key,
            )
        else:
            await self.api.unlock(
                username=self.username,
                pin=self.pin,
                access_token=access_token,
                vehicle_vin=vehicle.vin,
                vehicle_regid=vehicle.key,
            )

    async def start_climate(
        self,
        vehicle: Vehicle,
        set_temp: int,
        defrost: bool,
        climate: bool,
        heating: bool,
        duration: int,
    ) -> None:
        access_token = await self._get_access_token()
        await self.api.start_climate(
            username=self.username,
            pin=self.pin,
            access_token=access_token,
            vehicle_vin=vehicle.vin,
            vehicle_regid=vehicle.key,
            set_temp=set_temp,
            defrost=defrost,
            climate=climate,
            heating=heating,
            duration=duration,
        )

    async def stop_climate(self, vehicle: Vehicle) -> None:
        access_token = await self._get_access_token()
        await self.api.stop_climate(
            username=self.username,
            pin=self.pin,
            access_token=access_token,
            vehicle_vin=vehicle.vin,
            vehicle_regid=vehicle.key,
        )

    async def start_charge(self, vehicle: Vehicle) -> None:
        raise NotImplemented("Not yet implemented")

    async def stop_charge(self, vehicle: Vehicle) -> None:
        raise NotImplemented("Not yet implemented")

    async def set_charge_limits(
        self, vehicle: Vehicle, ac_limit: int, dc_limit: int
    ) -> None:
        raise NotImplemented("Not yet implemented")

    @property
    def region(self) -> str:
        return REGION_USA

    @property
    def brand(self) -> str:
        return BRAND_HYUNDAI
