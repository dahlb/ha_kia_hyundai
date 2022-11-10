from __future__ import annotations

import re
from datetime import datetime, tzinfo
from homeassistant.const import (
    LENGTH_MILES,
    LENGTH_KILOMETERS,
    UnitOfTemperature,
)


def convert_last_updated_str_to_datetime(
    last_updated_str: str, timezone_of_str: tzinfo
):
    m = re.match(
        r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})",
        last_updated_str,
    )
    return datetime(
        year=int(m.group(1)),
        month=int(m.group(2)),
        day=int(m.group(3)),
        hour=int(m.group(4)),
        minute=int(m.group(5)),
        second=int(m.group(6)),
        tzinfo=timezone_of_str,
    )


def convert_api_unit_to_ha_unit_of_distance(
    api_unit: int,
) -> LENGTH_MILES | LENGTH_KILOMETERS | None:
    if api_unit == 1:
        return LENGTH_KILOMETERS
    if api_unit == 3:
        return LENGTH_MILES


def convert_api_unit_to_ha_unit_of_temperature(
    api_unit: int,
) -> UnitOfTemperature:
    if api_unit == 0:
        return UnitOfTemperature.CELSIUS
    if api_unit == 1:
        return UnitOfTemperature.FAHRENHEIT


def safely_get_json_value(json, key, callable_to_cast=None):
    value = json
    for x in key.split("."):
        if value is not None:
            try:
                value = value[x]
            except (TypeError, KeyError):
                try:
                    value = value[int(x)]
                except (TypeError, KeyError, ValueError):
                    value = None
    if callable_to_cast is not None and value is not None:
        value = callable_to_cast(value)
    return value
