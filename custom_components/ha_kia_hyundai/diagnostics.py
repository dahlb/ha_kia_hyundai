from __future__ import annotations
from typing import Any

import attr
import logging

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, DATA_VEHICLE_INSTANCE, CONF_VEHICLE_IDENTIFIER
from .vehicle import Vehicle

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_UNIQUE_ID, "vehicle_identifier"}
TO_REDACT_MAPPED = {
    "identifier",
    "vin",
    "key",
    "latitude",
    "longitude",
    "location_name",
}
TO_REDACT_RAW = {
    "vehicle_identifier",
    "vinKey",
    "vin",
    "meid",
    "mdn",
    "iccid",
    "preferredDealer",
    "lat",
    "lon",
    "invDealerCode",
}
TO_REDACT_DEVICE = {"identifiers"}
TO_REDACT_ENTITIES = {"latitude", "longitude"}

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    vehicle: Vehicle = hass.data[DOMAIN][config_entry.data[CONF_VEHICLE_IDENTIFIER]][
        DATA_VEHICLE_INSTANCE
    ]
    data = {
        "entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "vehicle_mapped_data": async_redact_data(vehicle.__repr__(), TO_REDACT_MAPPED),
        "vehicle_raw_response": async_redact_data(vehicle.raw_responses, TO_REDACT_RAW),
    }

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    hass_device = device_registry.async_get_device(
        identifiers={(DOMAIN, str(vehicle.identifier))}
    )
    if not hass_device:
        return data

    data["device"] = {
        **async_redact_data(attr.asdict(hass_device), TO_REDACT_DEVICE),
        "entities": {},
    }

    hass_entities = er.async_entries_for_device(
        entity_registry,
        device_id=hass_device.id,
        include_disabled_entities=True,
    )

    for entity_entry in hass_entities:
        state = hass.states.get(entity_entry.entity_id)
        state_dict = None
        if state:
            state_dict = dict(state.as_dict())
            # The entity_id is already provided at root level.
            state_dict.pop("entity_id", None)
            # The context doesn't provide useful information in this case.
            state_dict.pop("context", None)

        data["device"]["entities"][entity_entry.entity_id] = {
            **async_redact_data(
                attr.asdict(
                    entity_entry, filter=lambda attr, value: attr.name != "entity_id"
                ),
                TO_REDACT_ENTITIES,
            ),
            "state": state_dict,
        }

    return data
