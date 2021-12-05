import logging
from typing import Dict, Optional, Any

import voluptuous as vol
import traceback

from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    CONF_FORCE_SCAN_INTERVAL,
    DEFAULT_FORCE_SCAN_INTERVAL,
    CONF_NO_FORCE_SCAN_HOUR_START,
    DEFAULT_NO_FORCE_SCAN_HOUR_START,
    CONF_NO_FORCE_SCAN_HOUR_FINISH,
    DEFAULT_NO_FORCE_SCAN_HOUR_FINISH,
    DOMAIN,
    CONFIG_FLOW_VERSION,
    CONF_VEHICLES,
    CONF_VEHICLE_IDENTIFIER,
)
from .api_cloud import ApiCloud

_LOGGER = logging.getLogger(__name__)


class KiaUvoOptionFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
                vol.Optional(
                    CONF_FORCE_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_FORCE_SCAN_INTERVAL, DEFAULT_FORCE_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
                vol.Optional(
                    CONF_NO_FORCE_SCAN_HOUR_START,
                    default=self.config_entry.options.get(
                        CONF_NO_FORCE_SCAN_HOUR_START, DEFAULT_NO_FORCE_SCAN_HOUR_START
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=23)),
                vol.Optional(
                    CONF_NO_FORCE_SCAN_HOUR_FINISH,
                    default=self.config_entry.options.get(
                        CONF_NO_FORCE_SCAN_HOUR_FINISH,
                        DEFAULT_NO_FORCE_SCAN_HOUR_FINISH,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=23)),
            }
        )

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        if user_input is not None:
            _LOGGER.debug(f"user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class KiaUvoConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    data: Optional[Dict[str, Any]]

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KiaUvoOptionFlowHandler(config_entry)

    def __init__(self):
        pass

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        errors: Dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                api_cloud = ApiCloud(
                    username=username, password=password, hass=self.hass
                )
                await api_cloud.login()
                self.data = user_input
                self.data[CONF_VEHICLES] = await api_cloud.get_vehicles()
                await api_cloud.cleanup()
                return await self.async_step_pick_vehicle()
            except Exception as ex:
                _LOGGER.error(
                    f"Exception in kia_uvo login : %s - traceback: %s",
                    ex,
                    traceback.format_exc(),
                )
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_pick_vehicle(
        self, user_input: Optional[Dict[str, Any]] = None
    ):
        vehicle_map = {}
        for vehicle in self.data[CONF_VEHICLES]:
            vehicle_map[vehicle.identifier] = f"{vehicle.name} ({vehicle.model})"

        errors: Dict[str, str] = {}
        data_schema = {
            vol.Required(
                CONF_VEHICLE_IDENTIFIER,
            ): vol.In(vehicle_map),
        }
        if len(self.data[CONF_VEHICLES]) == 1:
            user_input = {
                CONF_VEHICLE_IDENTIFIER: self.data[CONF_VEHICLES][0].identifier
            }
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_VEHICLE_IDENTIFIER])
            self._abort_if_unique_id_configured()
            del self.data[CONF_VEHICLES]
            self.data[CONF_VEHICLE_IDENTIFIER] = user_input[CONF_VEHICLE_IDENTIFIER]
            return self.async_create_entry(
                title=vehicle_map[user_input[CONF_VEHICLE_IDENTIFIER]],
                data=self.data,
            )
        else:
            return self.async_show_form(
                step_id="pick_vehicle",
                data_schema=vol.Schema(data_schema),
                errors=errors,
            )
