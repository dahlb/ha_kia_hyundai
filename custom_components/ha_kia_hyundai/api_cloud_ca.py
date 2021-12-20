from __future__ import annotations

import logging

from asyncio import sleep
from kia_hyundai_api import CaKia, CaHyundai, AuthError
from homeassistant.const import TEMP_CELSIUS
from homeassistant.util import dt as dt_util
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
from geopy.location import Location
from geopy.exc import GeocoderServiceError
from datetime import timedelta

from .api_cloud import ApiCloud
from .vehicle import Vehicle
from .const import (
    VEHICLE_LOCK_ACTION,
    INITIAL_STATUS_DELAY_AFTER_COMMAND,
    RECHECK_STATUS_DELAY_AFTER_COMMAND,
    CA_TEMP_RANGE,
)
from .util import (
    convert_last_updated_str_to_datetime,
    safely_get_json_value,
    convert_api_unit_to_ha_unit_of_distance,
)

_LOGGER = logging.getLogger(__name__)


def request_with_active_session(func):
    async def request_with_active_session_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AuthError:
            _LOGGER.debug(f"got invalid session, attempting to repair and resend")
            self = args[0]
            await self.login()
            response = await func(*args, **kwargs)
            return response

    return request_with_active_session_wrapper


class ApiCloudCa(ApiCloud):
    pin: str = None
    api: CaKia | CaHyundai = None
    _access_token: str = None

    async def _get_access_token(self):
        if self._access_token is None:
            await self.login()
        return self._access_token

    async def login(self):
        self._access_token, _ = self.api.login(self.username, self.password)

    @request_with_active_session
    async def get_vehicles(self) -> list[Vehicle]:
        access_token = await self._get_access_token()
        api_vehicles = await self.api.get_vehicles(access_token=access_token)
        vehicles = []
        for response_vehicle in api_vehicles["vehicles"]:
            vehicle = Vehicle(
                api_cloud=self,
                identifier=response_vehicle["vehicleId"],
                api_unsupported_keys=[],  # KIA_US_UNSUPPORTED_INSTRUMENT_KEYS, TODO
            )
            # vehicle.vin = response_vehicle["vin"]
            # vehicle.key = response_vehicle["vehicleKey"]
            # vehicle.model = response_vehicle["modelName"]
            vehicle.name = response_vehicle["nickName"]
            # if bool(response_vehicle["enrollmentStatus"]):
            #     vehicles.append(vehicle)
        return vehicles

    @request_with_active_session
    async def update(self, vehicle: Vehicle) -> None:
        access_token = await self._get_access_token()
        # TODO these could be done in parallel
        api_vehicle_status = await self.api.get_cached_vehicle_status(
            access_token=access_token, vehicle_id=vehicle.identifier
        )
        api_vehicle_next_service = await self.api.get_next_service_status(
            access_token=access_token, vehicle_id=vehicle.identifier
        )

        vehicle.last_synced_to_cloud = convert_last_updated_str_to_datetime(
            last_updated_str=api_vehicle_status["status"]["lastStatusDate"],
            timezone_of_str=dt_util.UTC,
        )

        target_soc = safely_get_json_value(
            api_vehicle_status, "status.evStatus.targetSOC"
        )
        if target_soc is not None:
            target_soc.sort(key=lambda x: x["plugType"])

        vehicle.doors_locked = safely_get_json_value(
            api_vehicle_status, "status.doorLock", bool
        )
        vehicle.door_hood_open = safely_get_json_value(
            api_vehicle_status, "status.hoodOpen", bool
        )
        vehicle.door_trunk_open = safely_get_json_value(
            api_vehicle_status, "status.trunkOpen", bool
        )
        vehicle.door_front_left_open = safely_get_json_value(
            api_vehicle_status, "status.doorOpen.frontLeft", bool
        )
        vehicle.door_front_right_open = safely_get_json_value(
            api_vehicle_status, "status.doorOpen.frontRight", bool
        )
        vehicle.door_back_left_open = safely_get_json_value(
            api_vehicle_status, "status.doorOpen.backLeft", bool
        )
        vehicle.door_back_right_open = safely_get_json_value(
            api_vehicle_status, "status.doorOpen.backRight", bool
        )
        vehicle.engine_on = safely_get_json_value(
            api_vehicle_status, "status.engine", bool
        )
        vehicle.tire_all_on = safely_get_json_value(
            api_vehicle_status, "status.tirePressureLamp.tirePressureLampAll", bool
        )
        vehicle.tire_front_left_on = safely_get_json_value(
            api_vehicle_status, "status.tirePressureLamp.tirePressureLampFL", bool
        )
        vehicle.tire_front_right_on = safely_get_json_value(
            api_vehicle_status, "status.tirePressureLamp.tirePressureLampFR", bool
        )
        vehicle.tire_rear_left_on = safely_get_json_value(
            api_vehicle_status, "status.tirePressureLamp.tirePressureLampRL", bool
        )
        vehicle.tire_rear_right_on = safely_get_json_value(
            api_vehicle_status, "status.tirePressureLamp.tirePressureLampRR", bool
        )
        vehicle.climate_hvac_on = safely_get_json_value(
            api_vehicle_status, "status.airCtrlOn", bool
        )
        vehicle.climate_defrost_on = safely_get_json_value(
            api_vehicle_status, "status.defrost", bool
        )
        vehicle.climate_heated_rear_window_on = safely_get_json_value(
            api_vehicle_status, "status.sideBackWindowHeat", bool
        )
        vehicle.climate_heated_side_mirror_on = safely_get_json_value(
            api_vehicle_status, "status.sideMirrorHeat", bool
        )
        vehicle.climate_heated_steering_wheel_on = safely_get_json_value(
            api_vehicle_status, "status.steerWheelHeat", bool
        )
        vehicle.climate_heated_seat_front_right_on = safely_get_json_value(
            api_vehicle_status, "status.seatHeaterVentState.frSeatHeatState", bool
        )
        vehicle.climate_heated_seat_front_left_on = safely_get_json_value(
            api_vehicle_status, "status.seatHeaterVentState.flSeatHeatState", bool
        )
        vehicle.climate_heated_seat_rear_right_on = safely_get_json_value(
            api_vehicle_status, "status.seatHeaterVentState.rrSeatHeatState", bool
        )
        vehicle.climate_heated_seat_rear_left_on = safely_get_json_value(
            api_vehicle_status, "status.seatHeaterVentState.rlSeatHeatState", bool
        )
        vehicle.low_fuel_light_on = safely_get_json_value(
            api_vehicle_status, "status.lowFuelLight", bool
        )
        vehicle.ev_battery_charging = safely_get_json_value(
            api_vehicle_status, "status.evStatus.batteryCharge", bool
        )
        vehicle.ev_plugged_in = safely_get_json_value(
            api_vehicle_status, "status.evStatus.batteryPlugin", bool
        )

        ev_battery_level = safely_get_json_value(
            api_vehicle_status, "status.evStatus.batteryStatus", int
        )
        if ev_battery_level != 0:
            vehicle.ev_battery_level = ev_battery_level
        vehicle.ev_remaining_range_value = safely_get_json_value(
            api_vehicle_status,
            "status.evStatus.drvDistance.0.rangeByFuel.evModeRange.value",
            float,
        )
        vehicle.ev_remaining_range_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "status.evStatus.drvDistance.0.rangeByFuel.evModeRange.unit",
                int,
            )
        )
        vehicle.total_range_value = safely_get_json_value(
            api_vehicle_status,
            "status.evStatus.drvDistance.0.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.total_range_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "status.evStatus.drvDistance.0.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.ev_charge_current_remaining_duration = safely_get_json_value(
            api_vehicle_status, "status.evStatus.remainTime2.atc.value", int
        )
        vehicle.ev_charge_fast_duration = safely_get_json_value(
            api_vehicle_status, "status.evStatus.remainTime2.etc1.value", int
        )
        vehicle.ev_charge_portable_duration = safely_get_json_value(
            api_vehicle_status, "status.evStatus.remainTime2.etc2.value", int
        )
        vehicle.ev_charge_station_duration = safely_get_json_value(
            api_vehicle_status, "status.evStatus.remainTime2.etc3.value", int
        )
        vehicle.ev_max_dc_charge_level = safely_get_json_value(
            api_vehicle_status, "status.evStatus.targetSOC.0.targetSOClevel", int
        )
        vehicle.ev_max_ac_charge_level = safely_get_json_value(
            api_vehicle_status, "status.evStatus.targetSOC.1.targetSOClevel", int
        )
        vehicle.ev_max_range_dc_charge_value = safely_get_json_value(
            api_vehicle_status,
            "status.evStatus.targetSOC.0.dte.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.ev_max_range_dc_charge_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "status.evStatus.targetSOC.0.dte.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.ev_max_range_ac_charge_value = safely_get_json_value(
            api_vehicle_status,
            "status.evStatus.targetSOC.1.dte.rangeByFuel.totalAvailableRange.value",
            float,
        )
        vehicle.ev_max_range_ac_charge_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_status,
                "status.evStatus.targetSOC.1.dte.rangeByFuel.totalAvailableRange.unit",
                int,
            )
        )
        vehicle.battery_level = safely_get_json_value(
            api_vehicle_status, "status.battery.batSoc", int
        )

        temp_value = (
            safely_get_json_value(api_vehicle_status, "status.airTemp.value", float)
            .replace("H", "")
            .replace("C", "")
        )
        temp_value = "0x" + temp_value
        vehicle.climate_temperature_value = CA_TEMP_RANGE[int(temp_value, 16)]
        vehicle.climate_temperature_unit = TEMP_CELSIUS

        non_ev_fuel_distance = safely_get_json_value(
            api_vehicle_status, "status.dte.value", float
        )
        if non_ev_fuel_distance is not None:
            vehicle.fuel_range_value = safely_get_json_value(
                api_vehicle_status, "status.dte.value", float
            )
            vehicle.fuel_range_unit = convert_api_unit_to_ha_unit_of_distance(
                safely_get_json_value(api_vehicle_status, "status.dte.unit", int)
            )
        else:
            vehicle.fuel_range_value = safely_get_json_value(
                api_vehicle_status,
                "status.evStatus.drvDistance.0.rangeByFuel.gasModeRange.value",
                float,
            )
            vehicle.fuel_range_unit = convert_api_unit_to_ha_unit_of_distance(
                safely_get_json_value(
                    api_vehicle_status,
                    "status.evStatus.drvDistance.0.rangeByFuel.gasModeRange.unit",
                    int,
                )
            )

        previous_odometer_value = vehicle.odometer_value
        vehicle.odometer_value = safely_get_json_value(
            api_vehicle_next_service, "maintenanceInfo.currentOdometer", float
        )
        vehicle.odometer_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_next_service, "maintenanceInfo.currentOdometerUnit", int
            )
        )

        vehicle.next_service_value = safely_get_json_value(
            api_vehicle_next_service, "maintenanceInfo.imatServiceOdometer", float
        )
        vehicle.next_service_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_next_service, "maintenanceInfo.imatServiceOdometerUnit", int
            )
        )

        vehicle.last_service_value = safely_get_json_value(
            api_vehicle_next_service, "maintenanceInfo.msopServiceOdometer", float
        )
        vehicle.last_service_unit = convert_api_unit_to_ha_unit_of_distance(
            safely_get_json_value(
                api_vehicle_next_service, "maintenanceInfo.msopServiceOdometerUnit", int
            )
        )

        if previous_odometer_value != vehicle.odometer_value:
            pin_token = await self.api.get_pin_token(
                access_token=access_token, pin=self.pin
            )
            api_vehicle_location = await self.api.get_location(
                access_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
            )
            previous_latitude = vehicle.latitude
            previous_longitude = vehicle.longitude
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
                async with Nominatim(
                    user_agent="ha_kia_hyundai",
                    adapter_factory=AioHTTPAdapter,
                ) as geolocator:
                    try:
                        location: Location = await geolocator.reverse(
                            query=(vehicle.latitude, vehicle.longitude)
                        )
                        vehicle.location_name = location.address
                    except GeocoderServiceError as error:
                        _LOGGER.warning(f"Location name lookup failed:{error}")

    @request_with_active_session
    async def request_sync(self, vehicle: Vehicle) -> None:
        access_token = await self._get_access_token()
        await self.api.request_vehicle_data_sync(
            access_token=access_token, vehicle_id=vehicle.identifier
        )
        await vehicle.update()

    @request_with_active_session
    async def lock(self, vehicle: Vehicle, action: VEHICLE_LOCK_ACTION) -> None:
        self._start_action(f"Lock {action.value}")
        access_token = await self._get_access_token()
        pin_token = await self.api.get_pin_token(
            access_token=access_token, pin=self.pin
        )
        if action == VEHICLE_LOCK_ACTION.LOCK:
            xid = await self.api.lock(
                access_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
            )
        else:
            xid = await self.api.unlock(
                saccess_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
            )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle, pin_token=pin_token)

    @request_with_active_session
    async def start_climate(
        self,
        vehicle: Vehicle,
        set_temp: int,
        defrost: bool,
        climate: bool,
        heating: bool,
        duration: int,
    ) -> None:
        self._start_action(f"Start Climate")
        access_token = await self._get_access_token()
        pin_token = await self.api.get_pin_token(
            access_token=access_token, pin=self.pin
        )
        if vehicle.ev_plugged_in is None:
            xid = await self.api.start_climate(
                saccess_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
                set_temp=set_temp,
                defrost=defrost,
                climate=climate,
                heating=heating,
                duration=duration,
            )
        else:
            xid = await self.api.start_climate_ev(
                saccess_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
                set_temp=set_temp,
                defrost=defrost,
                climate=climate,
                heating=heating,
                duration=duration,
            )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle, pin_token=pin_token)
        self.hvac_on_force_scan_interval = timedelta(minutes=int(duration) + 1)

    @request_with_active_session
    async def stop_climate(self, vehicle: Vehicle) -> None:
        self._start_action(f"Stop Climate")
        access_token = await self._get_access_token()
        pin_token = await self.api.get_pin_token(
            access_token=access_token, pin=self.pin
        )
        if vehicle.ev_plugged_in is None:
            xid = await self.api.stop_climate(
                saccess_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
            )
        else:
            xid = await self.api.stop_climate_ev(
                saccess_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                pin_token=pin_token,
            )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle, pin_token=pin_token)

    @request_with_active_session
    async def start_charge(self, vehicle: Vehicle) -> None:
        self._start_action(f"Start Charge")
        access_token = await self._get_access_token()
        pin_token = await self.api.get_pin_token(
            access_token=access_token, pin=self.pin
        )
        xid = await self.api.start_charge(
            saccess_token=access_token,
            vehicle_id=vehicle.identifier,
            pin=self.pin,
            pin_token=pin_token,
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle, pin_token=pin_token)

    @request_with_active_session
    async def stop_charge(self, vehicle: Vehicle) -> None:
        self._start_action(f"Stop Charge")
        access_token = await self._get_access_token()
        pin_token = await self.api.get_pin_token(
            access_token=access_token, pin=self.pin
        )
        xid = await self.api.stop_charge(
            saccess_token=access_token,
            vehicle_id=vehicle.identifier,
            pin=self.pin,
            pin_token=pin_token,
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle, pin_token=pin_token)

    @request_with_active_session
    async def set_charge_limits(
        self, vehicle: Vehicle, ac_limit: int, dc_limit: int
    ) -> None:
        raise NotImplemented("Not yet implemented")

    async def _check_action_completed(self, vehicle: Vehicle, pin_token: str) -> None:
        access_token = await self._get_access_token()
        await sleep(INITIAL_STATUS_DELAY_AFTER_COMMAND)
        try:
            completed = await self.api.check_last_action_status(
                access_token=access_token,
                vehicle_id=vehicle.identifier,
                pin=self.pin,
                xid=self._current_action.xid,
                pin_token=pin_token,
            )
            while not completed:
                await sleep(RECHECK_STATUS_DELAY_AFTER_COMMAND)
                completed = await self.api.check_last_action_status(
                    access_token=access_token,
                    vehicle_id=vehicle.identifier,
                    pin=self.pin,
                    xid=self._current_action.xid,
                    pin_token=pin_token,
                )
        finally:
            self._current_action.complete()
            self.publish_updates()
        await vehicle.update()
