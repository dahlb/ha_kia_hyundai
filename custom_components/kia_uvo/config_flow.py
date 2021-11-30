import logging

import voluptuous as vol
import traceback

from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback

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
)
from .api_cloud import ApiCloud

_LOGGER = logging.getLogger(__name__)


class KiaUvoOptionFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
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

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            _LOGGER.debug(f"user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


class KiaUvoConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KiaUvoOptionFlowHandler(config_entry)

    def __init__(self):
        self.schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = None

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                await ApiCloud(username=username, password=password).login()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )
            except Exception as ex:
                _LOGGER.error(
                    f"Exception in kia_uvo login : %s - traceback: %s",
                    ex,
                    traceback.format_exc(),
                )
                errors = {"base": "auth"}

        return self.async_show_form(
            step_id="user", data_schema=self.schema, errors=errors
        )
