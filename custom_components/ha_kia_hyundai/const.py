# Configuration Constants
from kia_hyundai_api.const import SeatSettings

from homeassistant.const import Platform

DOMAIN: str = "ha_kia_hyundai"
CONF_VEHICLE_ID: str = "vehicle_id"
CONFIG_FLOW_TEMP_VEHICLES: str = "vehicles"

DEFAULT_SCAN_INTERVAL: int = 10
DELAY_BETWEEN_ACTION_IN_PROGRESS_CHECKING: int = 20
TEMPERATURE_MIN = 62
TEMPERATURE_MAX = 82

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 3
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Sensor Specific Constants
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

SEAT_STATUS = {
    (0, 1): "Off",
    (1, 4): "High Heat",
    (1, 3): "Medium Heat",
    (1, 2): "Low Heat",
    (2, 4): "High Cool",
    (2, 3): "Medium Cool",
    (2, 2): "Low Cool",
}

STR_TO_ENUM = {
    "Off": SeatSettings.NONE,
    "High Heat": SeatSettings.HeatHigh,
    "Medium Heat": SeatSettings.HeatMedium,
    "Low Heat": SeatSettings.HeatLow,
    "High Cool": SeatSettings.CoolHigh,
    "Medium Cool": SeatSettings.CoolMedium,
    "Low Cool": SeatSettings.CoolLow,
}
