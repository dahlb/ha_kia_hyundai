import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant import config_entries
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from kia_hyundai_api import UsKia

from .const import (
    DOMAIN,
    CONFIG_FLOW_VERSION,
    CONF_VEHICLE_ID,
    DEFAULT_SCAN_INTERVAL,
    CONFIG_FLOW_TEMP_VEHICLES,
)

_LOGGER = logging.getLogger(__name__)


class KiaUvoOptionFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
            }
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class KiaUvoConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    data: dict[str, Any] | None = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KiaUvoOptionFlowHandler(config_entry)

    def __init__(self):
        pass

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                client_session = async_get_clientsession(self.hass)
                api_connection = UsKia(
                    username=username,
                    password=password,
                    client_session=client_session,
                )
                await api_connection.login()
                self.data.update(user_input)
                await api_connection.get_vehicles()
                self.data[CONFIG_FLOW_TEMP_VEHICLES] = api_connection.vehicles
                return await self.async_step_pick_vehicle()
            except ConfigEntryAuthFailed:
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_pick_vehicle(
        self, user_input: dict[str, Any] | None = None
    ):
        vehicle_map = {}
        for vehicle in self.data[CONFIG_FLOW_TEMP_VEHICLES]:
            vehicle_map[vehicle["vehicleIdentifier"]] = f"{vehicle["nickName"]} ({vehicle["modelName"]})"

        errors: dict[str, str] = {}
        data_schema = {
            vol.Required(
                CONF_VEHICLE_ID,
            ): vol.In(vehicle_map),
        }
        if len(self.data[CONFIG_FLOW_TEMP_VEHICLES]) == 1:
            user_input = {
                CONF_VEHICLE_ID: list(vehicle_map.keys())[0]
            }
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_VEHICLE_ID])
            self._abort_if_unique_id_configured()
            del self.data[CONFIG_FLOW_TEMP_VEHICLES]
            self.data[CONF_VEHICLE_ID] = user_input[CONF_VEHICLE_ID]
            return self.async_create_entry(
                title=vehicle_map[user_input[CONF_VEHICLE_ID]],
                data=self.data,
            )
        else:
            return self.async_show_form(
                step_id="pick_vehicle",
                data_schema=vol.Schema(data_schema),
                errors=errors,
            )
