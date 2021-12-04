import logging

from datetime import timedelta
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
import asyncio

from .util import convert_last_updated_str_to_datetime
from .api.KiaUvoApiUSA import KiaUvoApiUSA, AuthError
from .vehicle import Vehicle
from .api_action_status import ApiActionStatus
from .callbacks import CallbacksMixin
from .const import (
    INITIAL_STATUS_DELAY_AFTER_COMMAND,
    RECHECK_STATUS_DELAY_AFTER_COMMAND,
    VEHICLE_LOCK_ACTION,
    USA_TEMP_RANGE,
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
            vehicles = await self.get_vehicles()
            for updated_vehicle in vehicles:
                if updated_vehicle.identifier == vehicle.identifier:
                    _LOGGER.debug(
                        f"updating vehicle old key:{vehicle.key}; new key:{updated_vehicle.key}"
                    )
                    vehicle.key = updated_vehicle.key
            json_body = kwargs.get("json_body", None)
            if json_body is not None and json_body.get("vinKey", None):
                json_body["vinKey"] = [vehicle.key]
            response = await func(*args, **kwargs)
            return response

    return request_with_active_session_wrapper


class ApiCloud(CallbacksMixin):
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
        self.hass = hass
        self.update_interval: timedelta = update_interval
        self.force_scan_interval = force_scan_interval
        self.no_force_scan_hour_start = no_force_scan_hour_start
        self.no_force_scan_hour_finish = no_force_scan_hour_finish
        self.username: str = username
        self.password: str = password

        self.api = KiaUvoApiUSA()
        self._session_id = None
        self._current_action: ApiActionStatus = None

    async def cleanup(self):
        await self.api.close()

    async def get_session_id(self):
        if self._session_id is None:
            await self.login()
        return self._session_id

    async def login(self):
        self._session_id: str = await self.api.login(self.username, self.password)

    async def get_vehicle(self) -> Vehicle:
        vehicles = await self.get_vehicles()
        return vehicles[0]

    @request_with_active_session
    async def get_vehicles(self):
        session_id = await self.get_session_id()
        api_vehicles = await self.api.get_vehicles(session_id)
        vehicles = []
        for response_vehicle in api_vehicles["vehicleSummary"]:
            vehicle = Vehicle(
                api_cloud=self, identifier=response_vehicle["vehicleIdentifier"]
            )
            vehicle.vin = response_vehicle["vin"]
            vehicle.key = response_vehicle["vehicleKey"]
            vehicle.model = response_vehicle["modelName"]
            vehicle.name = response_vehicle["nickName"]
            vehicles.append(vehicle)
        return vehicles

    @request_with_active_session
    async def update(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        api_vehicle_status = await self.api.get_cached_vehicle_status(
            session_id, vehicle.key
        )
        vehicle_status = api_vehicle_status["vehicleInfoList"][0]["lastVehicleInfo"][
            "vehicleStatusRpt"
        ]["vehicleStatus"]
        climate_data = vehicle_status["climate"]
        ev_status = vehicle_status["evStatus"]
        ev_status["targetSOC"].sort(key=lambda x: x["plugType"])
        vehicle.last_synced_to_cloud = convert_last_updated_str_to_datetime(
            last_updated_str=vehicle_status["syncDate"]["utc"],
            timezone_of_str=dt_util.UTC,
        )
        vehicle.odometer_value = float(
            api_vehicle_status["vehicleInfoList"][0]["vehicleConfig"]["vehicleDetail"][
                "vehicle"
            ]["mileage"]
        )
        vehicle.odometer_unit = 3
        vehicle.battery_level = vehicle_status["batteryStatus"]["stateOfCharge"]
        vehicle.engine_on = bool(vehicle_status["engine"])
        vehicle.low_fuel_light_on = bool(vehicle_status["lowFuelLight"])
        vehicle.doors_locked = bool(vehicle_status["doorLock"])
        vehicle.door_front_left_open = bool(vehicle_status["doorStatus"]["frontLeft"])
        vehicle.door_front_right_open = bool(vehicle_status["doorStatus"]["frontRight"])
        vehicle.door_back_left_open = bool(vehicle_status["doorStatus"]["backLeft"])
        vehicle.door_back_right_open = bool(vehicle_status["doorStatus"]["backRight"])
        vehicle.door_trunk_open = bool(vehicle_status["doorStatus"]["trunk"])
        vehicle.door_hood_open = bool(vehicle_status["doorStatus"]["hood"])
        vehicle.sleep_mode_on = bool(vehicle_status["sleepMode"])
        vehicle.climate_hvac_on = bool(climate_data["airCtrl"])
        vehicle.climate_defrost_on = bool(climate_data["defrost"])
        vehicle.climate_temperature_value = int(climate_data["airTemp"]["value"])
        if vehicle.climate_temperature_value == "0xLOW":
            vehicle.climate_temperature_value = USA_TEMP_RANGE[0]
        elif vehicle.climate_temperature_value == "0xHIGH":
            vehicle.climate_temperature_value = USA_TEMP_RANGE[-1]

        vehicle.climate_temperature_unit = climate_data["airTemp"]["unit"]
        vehicle.climate_heated_steering_wheel_on = bool(
            climate_data["heatingAccessory"]["steeringWheel"]
        )
        vehicle.climate_heated_side_mirror_on = bool(
            climate_data["heatingAccessory"]["sideMirror"]
        )
        vehicle.climate_heated_rear_window_on = bool(
            climate_data["heatingAccessory"]["rearWindow"]
        )
        vehicle.ev_plugged_in = bool(ev_status["batteryPlugin"])
        vehicle.ev_battery_charging = bool(ev_status["batteryCharge"])
        vehicle.ev_battery_level = ev_status["batteryStatus"]
        vehicle.ev_charge_remaining_time = ev_status["remainChargeTime"][0][
            "timeInterval"
        ]["value"]
        vehicle.ev_remaining_range_value = ev_status["drvDistance"][0]["rangeByFuel"][
            "totalAvailableRange"
        ]["value"]
        vehicle.ev_remaining_range_unit = ev_status["drvDistance"][0]["rangeByFuel"][
            "totalAvailableRange"
        ]["unit"]
        vehicle.ev_max_dc_charge_level = ev_status["targetSOC"][0]["targetSOClevel"]
        vehicle.ev_max_ac_charge_level = ev_status["targetSOC"][1]["targetSOClevel"]
        vehicle.tire_all_on = bool(vehicle_status["tirePressure"]["all"])
        return vehicle

    @request_with_active_session
    async def request_sync(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        await self.api.request_vehicle_data_sync(session_id, vehicle.key)
        await vehicle.update()

    @request_with_active_session
    async def lock(self, vehicle: Vehicle, action: VEHICLE_LOCK_ACTION):
        session_id = await self.get_session_id()
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
    ):
        session_id = await self.get_session_id()
        self._start_action(f"Start Climate")
        xid = await self.api.start_climate(
            session_id, vehicle.key, set_temp, defrost, climate, heating
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def stop_climate(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        self._start_action(f"Stop Climate")
        xid = await self.api.stop_climate(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def start_charge(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        self._start_action(f"Start Charge")
        xid = await self.api.start_charge(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def stop_charge(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        self._start_action(f"Stop Charge")
        xid = await self.api.stop_charge(session_id, vehicle.key)
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    @request_with_active_session
    async def set_charge_limits(self, vehicle: Vehicle, ac_limit: int, dc_limit: int):
        session_id = await self.get_session_id()
        self._start_action(f"Set Charge Limits")
        xid = await self.api.set_charge_limits(
            session_id, vehicle.key, ac_limit, dc_limit
        )
        self._current_action.set_xid(xid)
        await self._check_action_completed(vehicle=vehicle)

    def _start_action(self, name: str):
        if self.action_in_progress():
            raise RuntimeError(
                f"Existing Action in progress: {self._current_action.name}"
            )
        else:
            self._current_action = ApiActionStatus(name)
            self.publish_updates()

    async def _check_action_completed(self, vehicle: Vehicle):
        session_id = await self.get_session_id()
        await asyncio.sleep(INITIAL_STATUS_DELAY_AFTER_COMMAND)
        try:
            completed = await self.api.check_last_action_status(
                session_id, vehicle.key, self._current_action.xid
            )
            while not completed:
                await asyncio.sleep(RECHECK_STATUS_DELAY_AFTER_COMMAND)
                completed = await self.api.check_last_action_status(
                    session_id, vehicle.key, self._current_action.xid
                )
        finally:
            self._current_action.complete()
            self.publish_updates()
        await vehicle.update()

    def action_in_progress(self):
        return not (
            self._current_action is None
            or self._current_action.completed()
            or self._current_action.expired()
        )

    def current_action_name(self):
        if self.action_in_progress():
            return self._current_action.name
        else:
            "None"
