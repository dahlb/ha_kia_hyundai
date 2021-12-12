from enum import Enum
from datetime import timedelta
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_BATTERY_CHARGING,
    DEVICE_CLASS_PLUG,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_POWER,
)
from homeassistant.const import (
    PERCENTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_TIMESTAMP,
    DEVICE_CLASS_TEMPERATURE,
    LENGTH_MILES,
    TIME_MINUTES,
    TEMP_FAHRENHEIT,
    DEVICE_CLASS_DATE,
)

# Configuration Constants
DOMAIN: str = "kia_uvo"
CONF_SCAN_INTERVAL: str = "scan_interval"
CONF_FORCE_SCAN_INTERVAL: str = "force_scan_interval"
CONF_NO_FORCE_SCAN_HOUR_START: str = "no_force_scan_hour_start"
CONF_NO_FORCE_SCAN_HOUR_FINISH: str = "no_force_scan_hour_finish"
CONF_VEHICLES: str = "vehicles"
CONF_VEHICLE_IDENTIFIER: str = "vehicle_identifier"

# I have seen that many people can survive with receiving updates in every 30 minutes. Let's see how KIA will respond
DEFAULT_SCAN_INTERVAL: int = 30
# When vehicle is running/active, it will update its status regularly, so no need to force it. If it has not been running, we will force it every 240 minutes
DEFAULT_FORCE_SCAN_INTERVAL: int = 240
DEFAULT_NO_FORCE_SCAN_HOUR_START: int = 18
DEFAULT_NO_FORCE_SCAN_HOUR_FINISH: int = 6

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 1
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

USA_TEMP_RANGE = range(62, 82)


class VEHICLE_LOCK_ACTION(Enum):
    LOCK = "close"
    UNLOCK = "open"


BINARY_INSTRUMENTS = [
    (
        "Hood",
        "door_hood_open",
        "mdi:car",
        "mdi:car",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Trunk",
        "door_trunk_open",
        "mdi:car-back",
        "mdi:car-back",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Front Left",
        "door_front_left_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Front Right",
        "door_front_right_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Rear Left",
        "door_back_left_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Door - Rear Right",
        "door_back_right_open",
        "mdi:car-door",
        "mdi:car-door",
        DEVICE_CLASS_DOOR,
    ),
    (
        "Engine",
        "engine_on",
        "mdi:engine",
        "mdi:engine-off",
        DEVICE_CLASS_POWER,
    ),
    (
        "Tire Pressure - All",
        "tire_all_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Front Left",
        "tire_front_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Front Right",
        "tire_front_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Rear Left",
        "tire_rear_left_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Tire Pressure - Rear Right",
        "tire_rear_right_on",
        "mdi:car-tire-alert",
        "mdi:tire",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "HVAC",
        "climate_hvac_on",
        "mdi:air-conditioner",
        "mdi:air-conditioner",
        DEVICE_CLASS_POWER,
    ),
    (
        "Defroster",
        "climate_defrost_on",
        "mdi:car-defrost-front",
        "mdi:car-defrost-front",
        DEVICE_CLASS_POWER,
    ),
    (
        "Rear Window Heater",
        "climate_heated_rear_window_on",
        "mdi:car-defrost-rear",
        "mdi:car-defrost-rear",
        DEVICE_CLASS_POWER,
    ),
    (
        "Side Mirror Heater",
        "climate_heated_side_mirror_on",
        "mdi:car-side",
        "mdi:car-side",
        DEVICE_CLASS_POWER,
    ),
    (
        "Steering Wheel Heater",
        "climate_heated_steering_wheel_on",
        "mdi:steering",
        "mdi:steering",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Front Right",
        "climate_heated_seat_front_right_on",
        "mdi:steering",
        "mdi:steering",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Front Left",
        "climate_heated_seat_front_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Rear Right",
        "climate_heated_seat_rear_right_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Seat Heater Rear Left",
        "climate_heated_seat_rear_left_on",
        "mdi:car-seat-heater",
        "mdi:car-seat-heater",
        DEVICE_CLASS_POWER,
    ),
    (
        "Low Fuel Light",
        "low_fuel_light_on",
        "mdi:gas-station-off",
        "mdi:gas-station",
        DEVICE_CLASS_PROBLEM,
    ),
    (
        "Charging",
        "ev_battery_charging",
        "mdi:battery-charging",
        "mdi:battery",
        DEVICE_CLASS_BATTERY_CHARGING,
    ),
    (
        "Plugged In",
        "ev_plugged_in",
        "mdi:power-plug",
        "mdi:power-plug-off",
        DEVICE_CLASS_PLUG,
    ),
]

INSTRUMENTS = [
    (
        "EV Battery",
        "ev_battery_level",
        PERCENTAGE,
        "mdi:car-electric",
        DEVICE_CLASS_BATTERY,
    ),
    (
        "Range by EV",
        "ev_remaining_range_value",
        LENGTH_MILES,
        "mdi:road-variant",
        None,
    ),
    (
        "Range by Fuel",
        "fuel_range_value",
        LENGTH_MILES,
        "mdi:road-variant",
        None,
    ),
    (
        "Range Total",
        "total_range_value",
        LENGTH_MILES,
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
        LENGTH_MILES,
        "mdi:car-electric",
        None,
    ),
    (
        "Target Range of Charge DC",
        "ev_max_range_dc_charge_value",
        LENGTH_MILES,
        "mdi:car-electric",
        None,
    ),
    (
        "Odometer",
        "odometer_value",
        LENGTH_MILES,
        "mdi:speedometer",
        None,
    ),
    (
        "Car Battery",
        "battery_level",
        PERCENTAGE,
        "mdi:car-battery",
        DEVICE_CLASS_BATTERY,
    ),
    (
        "Set Temperature",
        "climate_temperature_value",
        TEMP_FAHRENHEIT,
        None,
        DEVICE_CLASS_TEMPERATURE,
    ),
    (
        "Last Synced To Cloud",
        "last_synced_to_cloud",
        None,
        "mdi:update",
        DEVICE_CLASS_TIMESTAMP,
    ),
    (
        "Sync Age",
        "sync_age",
        TIME_MINUTES,
        "mdi:update",
        DEVICE_CLASS_DATE,
    ),
    (
        "Last Service",
        "last_service_value",
        LENGTH_MILES,
        "mdi:car-wrench",
        None,
    ),
    (
        "Next Service",
        "next_service_value",
        LENGTH_MILES,
        "mdi:car-wrench",
        None,
    ),
]
