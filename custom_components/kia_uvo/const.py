import logging

from dateutil import tz
from enum import Enum

from homeassistant.const import LENGTH_KILOMETERS, LENGTH_MILES

# Configuration Constants
DOMAIN: str = "kia_uvo"
CONF_STORED_CREDENTIALS: str = "stored_credentials"
CONF_SCAN_INTERVAL: str = "scan_interval"
CONF_FORCE_SCAN_INTERVAL: str = "force_scan_interval"
CONF_NO_FORCE_SCAN_HOUR_START: str = "no_force_scan_hour_start"
CONF_NO_FORCE_SCAN_HOUR_FINISH: str = "no_force_scan_hour_finish"

# I have seen that many people can survive with receiving updates in every 30 minutes. Let's see how KIA will respond
DEFAULT_SCAN_INTERVAL: int = 30
# When vehicle is running/active, it will update its status regularly, so no need to force it. If it has not been running, we will force it every 240 minutes
DEFAULT_FORCE_SCAN_INTERVAL: int = 240
DEFAULT_NO_FORCE_SCAN_HOUR_START: int = 18
DEFAULT_NO_FORCE_SCAN_HOUR_FINISH: int = 6
TIME_ZONE_EUROPE = tz.gettz("America/New_york")
ACTION_LOCK_TIMEOUT_IN_SECONDS = 5 * 60

# Integration Setting Constants
PARALLEL_UPDATES: int = 1
CONFIG_FLOW_VERSION: int = 1
PLATFORMS = ["binary_sensor", "sensor", "lock"]

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
ACTION_LOCK_TIMEOUT_IN_SECONDS: int = 5 * 60

# Sensor Specific Constants
NOT_APPLICABLE: str = "Not Applicable"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

USA_TEMP_RANGE = range(62, 82)


class VEHICLE_LOCK_ACTION(Enum):
    LOCK = "close"
    UNLOCK = "open"
