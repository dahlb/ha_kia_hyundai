import logging

from asyncio import sleep
from datetime import timedelta
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import LENGTH_MILES, TEMP_FAHRENHEIT

from kia_hyundai_api import UsKia, AuthError

from .util import convert_last_updated_str_to_datetime, safely_get_json_value
from .vehicle import Vehicle
from .api_cloud import ApiCloud
from .const import (
    INITIAL_STATUS_DELAY_AFTER_COMMAND,
    RECHECK_STATUS_DELAY_AFTER_COMMAND,
    VEHICLE_LOCK_ACTION,
    USA_TEMP_RANGE,
    KIA_US_UNSUPPORTED_INSTRUMENT_KEYS,
    BRAND_KIA,
    REGION_USA,
)

_LOGGER = logging.getLogger(__name__)


def request_with_active_session(func):
    async def request_with_active_session_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AuthError:
            _LOGGER.debug(f"got invalid session, attempting to repair and resend")
            self = args[0]
            vehicle: Vehicle = kwargs["vehicle"]
            await self.login()
            updated_vehicle = await self.get_vehicle(identifier=vehicle.identifier)
            vehicle.key = updated_vehicle.key
            json_body = kwargs.get("json_body", None)
            if json_body is not None and json_body.get("vinKey", None):
                json_body["vinKey"] = [vehicle.key]
            response = await func(*args, **kwargs)
            return response

    return request_with_active_session_wrapper


class ApiCloudUsKia(ApiCloud):
    hvac_on_force_scan_interval: timedelta = timedelta(minutes=5)

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
            username,
            password,
            hass,
            update_interval,
            force_scan_interval,
            no_force_scan_hour_start,
            no_force_scan_hour_finish,
        )
        client_session = async_get_clientsession(hass)
        self.api = UsKia(client_session=client_session)
        self._session_id = None

    async def _get_session_id(self):
        if self._session_id is None:
            await self.login()
        return self._session_id

    async def login(self):
        try:
            self._session_id: str = await self.api.login(self.username, self.password)
        except AuthError as err:
            raise ConfigEntryAuthFailed(err) from err

    @request_with_active_session
    async def get_vehicles(self) -> list[Vehicle]:
        session_id = await self._get_session_id()
        api_vehicles = await self.api.get_vehicles(session_id)
        vehicles = []
        for response_vehicle in api_vehicles["vehicleSummary"]:
            vehicle = Vehicle(
                api_cloud=self,
                identifier=response_vehicle["vehicleIdentifier"],
                api_unsupported_keys=KIA_US_UNSUPPORTED_INSTRUMENT_KEYS,
            )
            vehicle.vin = response_vehicle["vin"]
            vehicle.key = response_vehicle["vehicleKey"]
            vehicle.model = response_vehicle["modelName"]
            vehicle.name = response_vehicle["nickName"]
            vehicles.append(vehicle)
        return vehicles

    @request_with_active_session
    async def update(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        api_vehicle_status = await self.api.get_cached_vehicle_status(
            session_id, vehicle.key
        )
        vehicle.raw_responses = api_vehicle_status
        vehicle_status = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.lastVehicleInfo.vehicleStatusRpt.vehicleStatus",
        )
        target_soc = safely_get_json_value(vehicle_status, "evStatus.targetSOC")
        if target_soc is not None:
            target_soc.sort(key=lambda x: x["plugType"])
        vehicle.last_synced_to_cloud = convert_last_updated_str_to_datetime(
            last_updated_str=vehicle_status["syncDate"]["utc"],
            timezone_of_str=dt_util.UTC,
        )
        vehicle.odometer_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.vehicleConfig.vehicleDetail.vehicle.mileage",
            float,
        )
        vehicle.odometer_unit = LENGTH_MILES

        maintenance_array = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.vehicleConfig.maintenance.maintenanceSchedule",
        )
        if maintenance_array is not None:
            maintenance_array.append(vehicle.odometer_value)
            maintenance_array.sort()
            current_mileage_index = maintenance_array.index(vehicle.odometer_value)
            vehicle.last_service_value = maintenance_array[current_mileage_index - 1]
            vehicle.last_service_unit = LENGTH_MILES
            vehicle.next_service_value = maintenance_array[current_mileage_index + 1]
            vehicle.next_service_unit = LENGTH_MILES

        vehicle.next_service_mile_value = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.vehicleConfig.maintenance.nextServiceMile",
            float,
        )
        vehicle.next_service_mile_unit = LENGTH_MILES

        vehicle.battery_level = safely_get_json_value(
            vehicle_status, "batteryStatus.stateOfCharge", int
        )
        vehicle.engine_on = safely_get_json_value(vehicle_status, "engine", bool)
        vehicle.low_fuel_light_on = safely_get_json_value(
            vehicle_status, "lowFuelLight", bool
        )
        vehicle.doors_locked = safely_get_json_value(vehicle_status, "doorLock", bool)
        vehicle.door_front_left_open = safely_get_json_value(
            vehicle_status, "doorStatus.frontLeft", bool
        )
        vehicle.door_front_right_open = safely_get_json_value(
            vehicle_status, "doorStatus.frontRight", bool
        )
        vehicle.door_back_left_open = safely_get_json_value(
            vehicle_status, "doorStatus.backLeft", bool
        )
        vehicle.door_back_right_open = safely_get_json_value(
            vehicle_status, "doorStatus.backRight", bool
        )
        vehicle.door_trunk_open = safely_get_json_value(
            vehicle_status, "doorStatus.trunk", bool
        )
        vehicle.door_hood_open = safely_get_json_value(
            vehicle_status, "doorStatus.hood", bool
        )
        vehicle.sleep_mode_on = safely_get_json_value(vehicle_status, "sleepMode", bool)
        vehicle.climate_hvac_on = safely_get_json_value(
            vehicle_status, "climate.airCtrl", bool
        )
        vehicle.climate_defrost_on = safely_get_json_value(
            vehicle_status, "climate.defrost", bool
        )

        vehicle.climate_temperature_value = safely_get_json_value(
            vehicle_status, "climate.airTemp.value"
        )
        if vehicle.climate_temperature_value == "0xLOW":
            vehicle.climate_temperature_value = USA_TEMP_RANGE[0]
        elif vehicle.climate_temperature_value == "0xHIGH":
            vehicle.climate_temperature_value = USA_TEMP_RANGE[-1]
        vehicle.climate_temperature_unit = TEMP_FAHRENHEIT

        vehicle.climate_heated_steering_wheel_on = safely_get_json_value(
            vehicle_status, "climate.heatingAccessory.steeringWheel", bool
        )
        vehicle.climate_heated_side_mirror_on = safely_get_json_value(
            vehicle_status, "climate.heatingAccessory.sideMirror", bool
        )
        vehicle.climate_heated_rear_window_on = safely_get_json_value(
            vehicle_status, "climate.heatingAccessory.rearWindow", bool
        )
        vehicle.ev_plugged_in = safely_get_json_value(
            vehicle_status, "evStatus.batteryPlugin", bool
        )
        vehicle.ev_battery_charging = safely_get_json_value(
            vehicle_status, "evStatus.batteryCharge", bool
        )
        ev_battery_level = safely_get_json_value(
            vehicle_status, "evStatus.batteryStatus", int
        )
        if ev_battery_level != 0:
            vehicle.ev_battery_level = ev_battery_level
        vehicle.ev_charge_current_remaining_duration = safely_get_json_value(
            vehicle_status, "evStatus.remainChargeTime.0.timeInterval.value", int
        )
        vehicle.ev_remaining_range_value = safely_get_json_value(
            vehicle_status,
            "evStatus.drvDistance.0.rangeByFuel.evModeRange.value",
            int,
        )
        vehicle.ev_remaining_range_unit = LENGTH_MILES
        vehicle.total_range_value = safely_get_json_value(
            vehicle_status,
            "evStatus.drvDistance.0.rangeByFuel.totalAvailableRange.value",
            int,
        )
        vehicle.total_range_unit = LENGTH_MILES
        hybrid_fuel_range_value = safely_get_json_value(
            vehicle_status,
            "evStatus.drvDistance.0.rangeByFuel.gasModeRange.value",
            float,
        )
        no_ev_fuel_range_value = safely_get_json_value(
            vehicle_status, "distanceToEmpty.value"
        )
        if hybrid_fuel_range_value is not None:
            vehicle.fuel_range_value = hybrid_fuel_range_value
        else:
            vehicle.fuel_range_value = no_ev_fuel_range_value
            vehicle.total_range_value = no_ev_fuel_range_value
        vehicle.fuel_range_unit = LENGTH_MILES

        ev_max_dc_charge_level = safely_get_json_value(
            vehicle_status, "evStatus.targetSOC.0.targetSOClevel", int
        )
        if ev_max_dc_charge_level is not None and ev_max_dc_charge_level <= 100:
            vehicle.ev_max_dc_charge_level = ev_max_dc_charge_level
        ev_max_ac_charge_level = safely_get_json_value(
            vehicle_status, "evStatus.targetSOC.1.targetSOClevel", int
        )
        if ev_max_ac_charge_level is not None and ev_max_ac_charge_level <= 100:
            vehicle.ev_max_ac_charge_level = ev_max_ac_charge_level

        vehicle.tire_all_on = safely_get_json_value(
            vehicle_status, "tirePressure.all", bool
        )

        previous_latitude = vehicle.latitude
        previous_longitude = vehicle.longitude
        vehicle.latitude = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.lastVehicleInfo.location.coord.lat",
            float,
        )
        vehicle.longitude = safely_get_json_value(
            api_vehicle_status,
            "vehicleInfoList.0.lastVehicleInfo.location.coord.lon",
            float,
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

    @request_with_active_session
    async def request_sync(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        await self.api.request_vehicle_data_sync(session_id, vehicle.key)
        await vehicle.update()

    @request_with_active_session
    async def lock(self, vehicle: Vehicle, action: VEHICLE_LOCK_ACTION) -> None:
        session_id = await self._get_session_id()
        self._start_action(f"Lock {action.value}")
        if action == VEHICLE_LOCK_ACTION.LOCK:
            xid = await self.api.lock(session_id, vehicle.key)
        else:
            xid = await self.api.unlock(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

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
        session_id = await self._get_session_id()
        self._start_action(f"Start Climate")
        xid = await self.api.start_climate(
            session_id, vehicle.key, set_temp, defrost, climate, heating
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def stop_climate(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        self._start_action(f"Stop Climate")
        xid = await self.api.stop_climate(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def start_charge(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        self._start_action(f"Start Charge")
        xid = await self.api.start_charge(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def stop_charge(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        self._start_action(f"Stop Charge")
        xid = await self.api.stop_charge(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def set_charge_limits(
        self, vehicle: Vehicle, ac_limit: int, dc_limit: int
    ) -> None:
        session_id = await self._get_session_id()
        self._start_action(f"Set Charge Limits")
        xid = await self.api.set_charge_limits(
            session_id, vehicle.key, ac_limit, dc_limit
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    async def _check_action_completed(self, vehicle: Vehicle) -> None:
        session_id = await self._get_session_id()
        await sleep(INITIAL_STATUS_DELAY_AFTER_COMMAND)
        try:
            completed = await self.api.check_last_action_status(
                session_id, vehicle.key, self._current_action.xid
            )
            while not completed:
                await sleep(RECHECK_STATUS_DELAY_AFTER_COMMAND)
                completed = await self.api.check_last_action_status(
                    session_id, vehicle.key, self._current_action.xid
                )
        finally:
            self._current_action.complete()
            self.publish_updates()
        await vehicle.update()

    @property
    def brand(self) -> str:
        return BRAND_KIA

    @property
    def region(self) -> str:
        return REGION_USA
