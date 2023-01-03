from enum import Enum
from datetime import timedelta
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    TIME_MINUTES,
)

# Configuration Constants
DOMAIN: str = "ha_kia_hyundai"
CONF_SCAN_INTERVAL: str = "scan_interval"
CONF_FORCE_SCAN_INTERVAL: str = "force_scan_interval"
CONF_NO_FORCE_SCAN_HOUR_START: str = "no_force_scan_hour_start"
CONF_NO_FORCE_SCAN_HOUR_FINISH: str = "no_force_scan_hour_finish"
CONF_VEHICLES: str = "vehicles"
CONF_VEHICLE_IDENTIFIER: str = "vehicle_identifier"
CONF_BRAND: str = "brand"
CONF_PIN: str = "pin"

# I have seen that many people can survive with receiving updates in every 30 minutes. Let's see how KIA will respond
DEFAULT_SCAN_INTERVAL: int = 30
# When vehicle is running/active, it will update its status regularly, so no need to force it. If it has not been running, we will force it every 240 minutes
DEFAULT_FORCE_SCAN_INTERVAL: int = 240
DEFAULT_NO_FORCE_SCAN_HOUR_START: int = 18
DEFAULT_NO_FORCE_SCAN_HOUR_FINISH: int = 6

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
PLATFORMS = ["binary_sensor", "device_tracker", "sensor", "lock"]

# Home Assistant Data Storage Constants
DATA_VEHICLE_INSTANCE: str = "vehicle"  # Vehicle Instance
DATA_VEHICLE_LISTENER: str = (
    "vehicle_listener"  # Vehicle Topic Update Listener Unsubscribe Caller
)
DATA_CONFIG_UPDATE_LISTENER: str = (
    "config_update_listener"  # Config Options Update Listener Unsubscribe Caller
)

# action status delay constants
INITIAL_STATUS_DELAY_AFTER_COMMAND: int = 15
RECHECK_STATUS_DELAY_AFTER_COMMAND: int = 10
ACTION_LOCK_TIMEOUT_IN_SECONDS: int = 5 * 604
REQUEST_TO_SYNC_COOLDOWN: timedelta = timedelta(minutes=15)

# Sensor Specific Constants
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

DYNAMIC_UNIT: str = "dynamic_unit"

CA_TEMP_RANGE = [x * 0.5 for x in range(32, 64)]
USA_TEMP_RANGE = range(62, 82)

REGION_CANADA = "Canada"
REGION_USA = "USA"
REGIONS = [REGION_USA, REGION_CANADA]

BRAND_KIA = "Kia"
BRAND_HYUNDAI = "Hyundai"
BRANDS = [BRAND_KIA, BRAND_HYUNDAI]


class VEHICLE_LOCK_ACTION(Enum):
    LOCK = "close"
    UNLOCK = "open"


BINARY_INSTRUMENTS = [
    (
        "Hood",
        "door_hood_open",
        "mdi:car",
        "mdi:car",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Trunk",
        "door_trunk_open",
        "mdi:car-back",
        "mdi:car-back",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Door - Front Left",
        "door_front_left_open",
        "mdi:car-door",
        "mdi:car-door",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Door - Front Right",
        "door_front_right_open",
        "mdi:car-door",
        "mdi:car-door",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Door - Rear Left",
        "door_back_left_open",
        "mdi:car-door",
        "mdi:car-door",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Door - Rear Right",
        "door_back_right_open",
        "mdi:car-door",
        "mdi:car-door",
        BinarySensorDeviceClass.DOOR,
    ),
    (
        "Engine",
        "engine_on",
        "mdi:engine",
        "mdi:engine-off",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Tire Pressure - All",
        "tire_all_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "Tire Pressure - Front Left",
        "tire_front_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "Tire Pressure - Front Right",
        "tire_front_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "Tire Pressure - Rear Left",
        "tire_rear_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "Tire Pressure - Rear Right",
        "tire_rear_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "HVAC",
        "climate_hvac_on",
        "mdi:air-conditioner",
        "mdi:air-conditioner",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Defroster",
        "climate_defrost_on",
        "mdi:car-defrost-front",
        "mdi:car-defrost-front",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Rear Window Heater",
        "climate_heated_rear_window_on",
        "mdi:car-defrost-rear",
        "mdi:car-defrost-rear",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Side Mirror Heater",
        "climate_heated_side_mirror_on",
        "mdi:car-side",
        "mdi:car-side",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Steering Wheel Heater",
        "climate_heated_steering_wheel_on",
        "mdi:steering",
        "mdi:steering",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Seat Heater Front Right",
        "climate_heated_seat_front_right_on",
        "mdi:steering",
        "mdi:steering",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Seat Heater Front Left",
        "climate_heated_seat_front_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Seat Heater Rear Right",
        "climate_heated_seat_rear_right_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Seat Heater Rear Left",
        "climate_heated_seat_rear_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        BinarySensorDeviceClass.POWER,
    ),
    (
        "Low Fuel Light",
        "low_fuel_light_on",
        "mdi:gas-station-off",
        "mdi:gas-station",
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "Charging",
        "ev_battery_charging",
        "mdi:battery-charging",
        "mdi:battery",
        BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    (
        "Plugged In",
        "ev_plugged_in",
        "mdi:power-plug",
        "mdi:power-plug-off",
        BinarySensorDeviceClass.PLUG,
    ),
]

INSTRUMENTS = [
    (
        "EV Battery",
        "ev_battery_level",
        PERCENTAGE,
        "mdi:car-electric",
        SensorDeviceClass.BATTERY,
    ),
    (
        "Range by EV",
        "ev_remaining_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Range by Fuel",
        "fuel_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Range Total",
        "total_range_value",
        DYNAMIC_UNIT,
        "mdi:road-variant",
        None,
    ),
    (
        "Estimated Current Charge Duration",
        "ev_charge_current_remaining_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Fast Charge Duration",
        "ev_charge_fast_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Portable Charge Duration",
        "ev_charge_portable_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Estimated Station Charge Duration",
        "ev_charge_station_duration",
        TIME_MINUTES,
        "mdi:ev-station",
        None,
    ),
    (
        "Target Capacity of Charge AC",
        "ev_max_ac_charge_level",
        PERCENTAGE,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Capacity of Charge DC",
        "ev_max_dc_charge_level",
        PERCENTAGE,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Range of Charge AC",
        "ev_max_range_ac_charge_value",
        DYNAMIC_UNIT,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Range of Charge DC",
        "ev_max_range_dc_charge_value",
        DYNAMIC_UNIT,
        "mdi:car-electric",
        None,
    ),
    (
        "Odometer",
        "odometer_value",
        DYNAMIC_UNIT,
        "mdi:speedometer",
        None,
    ),
    (
        "Car Battery",
        "battery_level",
        PERCENTAGE,
        "mdi:car-battery",
        SensorDeviceClass.BATTERY,
    ),
    (
        "Set Temperature",
        "climate_temperature_value",
        DYNAMIC_UNIT,
        None,
        SensorDeviceClass.TEMPERATURE,
    ),
    (
        "Last Synced To Cloud",
        "last_synced_to_cloud",
        None,
        "mdi:update",
        SensorDeviceClass.TIMESTAMP,
    ),
    (
        "Sync Age",
        "sync_age",
        TIME_MINUTES,
        "mdi:update",
        SensorDeviceClass.DATE,
    ),
    (
        "Last Service",
        "last_service_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
    (
        "Next Service",
        "next_service_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
    (
        "Miles Until Next Service",
        "next_service_mile_value",
        DYNAMIC_UNIT,
        "mdi:car-wrench",
        None,
    ),
]

KIA_US_UNSUPPORTED_INSTRUMENT_KEYS = [
    "ev_max_range_ac_charge_value",
    "ev_max_range_dc_charge_value",
    "ev_charge_fast_duration",
    "ev_charge_portable_duration",
    "ev_charge_station_duration",
    "climate_heated_seat_front_right_on",
    "climate_heated_seat_front_left_on",
    "climate_heated_seat_rear_right_on",
    "climate_heated_seat_rear_left_on",
    "tire_front_right_on",
    "tire_front_left_on",
    "tire_rear_right_on",
    "tire_rear_left_on",
]

SERVICE_NAME_REQUEST_SYNC = "request_sync"
SERVICE_NAME_UPDATE = "update"
SERVICE_NAME_START_CLIMATE = "start_climate"
SERVICE_NAME_STOP_CLIMATE = "stop_climate"
SERVICE_NAME_START_CHARGE = "start_charge"
SERVICE_NAME_STOP_CHARGE = "stop_charge"
SERVICE_NAME_SET_CHARGE_LIMITS = "set_charge_limits"

SERVICE_ATTRIBUTE_TEMPERATURE = "temperature"
SERVICE_ATTRIBUTE_DEFROST = "defrost"
SERVICE_ATTRIBUTE_CLIMATE = "climate"
SERVICE_ATTRIBUTE_HEATING = "heating"
SERVICE_ATTRIBUTE_DURATION = "duration"
SERVICE_ATTRIBUTE_AC_LIMIT = "ac_limit"
SERVICE_ATTRIBUTE_DC_LIMIT = "dc_limit"
