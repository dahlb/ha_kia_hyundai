import asyncio
import logging
from sqlite3 import DataError
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry, OptionsFlow
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
    CONF_DEVICE_ID,
    CONF_OTP_CODE,
    CONF_OTP_TYPE,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    CONFIG_FLOW_VERSION,
    CONF_VEHICLE_ID,
    DEFAULT_SCAN_INTERVAL,
    CONFIG_FLOW_TEMP_VEHICLES,
)

_LOGGER = logging.getLogger(__name__)

class OneTimePasswordStarted(Exception):
    pass


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

    data: dict[str, Any] = {}
    otp_key: str | None = None
    api_connection: UsKia | None = None
    last_action: dict[str, Any] | None = None
    notify_type: str | None = None


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KiaUvoOptionFlowHandler(config_entry)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        _LOGGER.debug(f"Reauth with input: {user_input}")
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        _LOGGER.debug(f"User step with input: {user_input}")
        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_OTP_TYPE, default="SMS"): vol.In(["EMAIL", "SMS"]),
        }
        errors: dict[str, str] = {}

        if user_input is not None and CONF_OTP_TYPE in user_input:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            otp_type = user_input[CONF_OTP_TYPE]
            async def otp_callback(context: dict[str, Any]):
                if context["stage"] == "choose_destination":
                    _LOGGER.debug(f"OTP context: {context}")
                    return { "notify_type": otp_type }
                if context["stage"] == "input_code":
                    loop_counter = 0
                    while loop_counter < 120:
                        _LOGGER.debug(f"data: {self.data}")
                        if CONF_OTP_CODE in self.data:
                            _LOGGER.debug(f"OTP code: {self.data[CONF_OTP_CODE]}")
                            return { "otp_code": self.data[CONF_OTP_CODE] }
                        loop_counter += 1
                        _LOGGER.debug(f"Waiting for OTP {loop_counter}")
                        _LOGGER.debug(f"data: {self.data}")
                        await asyncio.sleep(1)
                    raise ConfigEntryAuthFailed("2 minute timeout waiting for OTP")

            try:
                client_session = async_get_clientsession(self.hass)
                self.api_connection = UsKia(
                    username=username,
                    password=password,
                    otp_callback=otp_callback,
                    client_session=client_session,
                )
                self.data.update(user_input)
#                try:
                self.otp_task = self.hass.loop.create_task(self.api_connection.login())
#                except OneTimePasswordStarted:
#                    _LOGGER.debug("OTP code required")
                return await self.async_step_otp_code()
            except ConfigEntryAuthFailed:
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_otp_code(
        self, user_input: dict[str, Any] | None = None
    ):
        _LOGGER.debug(f"OTP code step with input: {user_input}")
        data_schema = {
            vol.Required(CONF_OTP_CODE): str,
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data.update(user_input)
            try:
                await self.otp_task
            except DataError:
                raise ConfigEntryAuthFailed("Invalid OTP code")
            if self.api_connection is None:
                raise ConfigEntryAuthFailed("API connection not established")
            await self.api_connection.get_vehicles()
            self.data[CONFIG_FLOW_TEMP_VEHICLES] = self.api_connection.vehicles
            return await self.async_step_pick_vehicle()
        return self.async_show_form(
            step_id="otp_code", data_schema=vol.Schema(data_schema), errors=errors
        )


    async def async_step_pick_vehicle(
        self, user_input: dict[str, Any] | None = None
    ):
        _LOGGER.debug(f"Pick vehicle step with input: {user_input}")
        vehicle_map = {}
        for vehicle in self.data[CONFIG_FLOW_TEMP_VEHICLES]:
            vehicle_map[vehicle["vehicleIdentifier"]] = f"{vehicle['nickName']} ({vehicle['modelName']})"

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
            del self.data[CONFIG_FLOW_TEMP_VEHICLES]
            self.data[CONF_VEHICLE_ID] = user_input[CONF_VEHICLE_ID]
            if self.api_connection is None:
                raise ConfigEntryAuthFailed("API connection not established")
            self.data[CONF_REFRESH_TOKEN] = self.api_connection.refresh_token
            self.data[CONF_DEVICE_ID] = self.api_connection.device_id
            if self.source == SOURCE_REAUTH:
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=self.data,
                )
            self._abort_if_unique_id_configured()
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
