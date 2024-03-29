import logging

import voluptuous as vol
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_REGION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from aiohttp.client_exceptions import ClientError
from asyncio import sleep

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_VEHICLE_INSTANCE,
    DATA_CONFIG_UPDATE_LISTENER,
    DATA_VEHICLE_LISTENER,
    DEFAULT_SCAN_INTERVAL,
    CONF_FORCE_SCAN_INTERVAL,
    CONF_NO_FORCE_SCAN_HOUR_FINISH,
    CONF_NO_FORCE_SCAN_HOUR_START,
    CONF_SCAN_INTERVAL,
    CONF_VEHICLE_IDENTIFIER,
    DEFAULT_NO_FORCE_SCAN_HOUR_FINISH,
    DEFAULT_NO_FORCE_SCAN_HOUR_START,
    DEFAULT_FORCE_SCAN_INTERVAL,
    CONF_BRAND,
    CONF_PIN,
    USA_TEMP_RANGE,
    SERVICE_NAME_REQUEST_SYNC,
    SERVICE_NAME_UPDATE,
    SERVICE_NAME_START_CLIMATE,
    SERVICE_NAME_STOP_CLIMATE,
    SERVICE_NAME_START_CHARGE,
    SERVICE_NAME_STOP_CHARGE,
    SERVICE_NAME_SET_CHARGE_LIMITS,
    SERVICE_ATTRIBUTE_TEMPERATURE,
    SERVICE_ATTRIBUTE_DEFROST,
    SERVICE_ATTRIBUTE_CLIMATE,
    SERVICE_ATTRIBUTE_HEATING,
    SERVICE_ATTRIBUTE_AC_LIMIT,
    SERVICE_ATTRIBUTE_DC_LIMIT,
)
from .api_cloud_util import api_cloud_for_region_and_brand
from .vehicle import Vehicle

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config_entry: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})

    def convert_call_to_vehicle(call) -> Vehicle:
        vehicle_identifiers = list(hass.data[DOMAIN].keys())
        if len(vehicle_identifiers) == 1:
            vehicle_identifier = vehicle_identifiers[0]
        else:
            _LOGGER.debug(
                f"multiple vehicles in domain:{vehicle_identifiers}; call.data:{call.data}"
            )
            if ATTR_DEVICE_ID in call.data:
                vehicle_identifier = convert_device_id_to_vehicle_identifier(
                    call.data[ATTR_DEVICE_ID]
                )
            else:
                raise Exception("multiple devices detected, device_id is required.")

        return hass.data[DOMAIN][vehicle_identifier][DATA_VEHICLE_INSTANCE]

    def convert_device_id_to_vehicle_identifier(device_id: str) -> str:
        device_registry = dr.async_get(hass)
        device_entry: dr.DeviceEntry = device_registry.async_get(device_id)
        return list(device_entry.identifiers.copy().pop())[1]

    async def async_handle_request_sync(call):
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.request_sync())

    async def async_handle_update(call):
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.update())

    async def async_handle_start_climate(call):
        set_temp = call.data.get(SERVICE_ATTRIBUTE_TEMPERATURE)
        defrost = call.data.get(SERVICE_ATTRIBUTE_DEFROST)
        climate = call.data.get(SERVICE_ATTRIBUTE_CLIMATE)
        heating = call.data.get(SERVICE_ATTRIBUTE_HEATING)
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(
            hass_vehicle.start_climate(
                set_temp=set_temp,
                defrost=defrost,
                climate=climate,
                heating=heating,
            )
        )

    async def async_handle_stop_climate(call):
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.stop_climate())

    async def async_handle_start_charge(call):
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.start_charge())

    async def async_handle_stop_charge(call):
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.stop_charge())

    async def async_handle_set_charge_limits(call):
        ac_limit = call.data.get(SERVICE_ATTRIBUTE_AC_LIMIT)
        dc_limit = call.data.get(SERVICE_ATTRIBUTE_DC_LIMIT)
        hass_vehicle: Vehicle = convert_call_to_vehicle(call)
        await hass.async_create_task(hass_vehicle.set_charge_limits(ac_limit, dc_limit))

    hass.services.async_register(
        DOMAIN, SERVICE_NAME_REQUEST_SYNC, async_handle_request_sync
    )
    hass.services.async_register(DOMAIN, SERVICE_NAME_UPDATE, async_handle_update)
    climate_schema = {
        vol.Optional(
            SERVICE_ATTRIBUTE_CLIMATE,
        ): vol.Range(1, 10),
        vol.Optional(
            SERVICE_ATTRIBUTE_DEFROST,
        ): cv.boolean,
        vol.Optional(
            SERVICE_ATTRIBUTE_HEATING,
        ): cv.boolean,
        vol.Optional(
            SERVICE_ATTRIBUTE_TEMPERATURE,
        ): vol.All(vol.Coerce(int), vol.In(USA_TEMP_RANGE)),
    }
    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_START_CLIMATE,
        async_handle_start_climate,
        vol.Schema(climate_schema),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NAME_STOP_CLIMATE, async_handle_stop_climate
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NAME_START_CHARGE, async_handle_start_charge
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NAME_STOP_CHARGE, async_handle_stop_charge
    )
    charge_limit_schema = {
        vol.Optional(
            SERVICE_ATTRIBUTE_AC_LIMIT,
        ): vol.All(vol.Coerce(int), vol.In(range(50, 101, 10))),
        vol.Optional(
            SERVICE_ATTRIBUTE_DC_LIMIT,
        ): vol.All(vol.Coerce(int), vol.In(range(50, 101, 10))),
    }
    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_SET_CHARGE_LIMITS,
        async_handle_set_charge_limits,
        vol.Schema(charge_limit_schema),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    vehicle_identifier = config_entry.data[CONF_VEHICLE_IDENTIFIER]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    region = config_entry.data[CONF_REGION]
    brand = config_entry.data[CONF_BRAND]

    no_force_scan_hour_start = config_entry.options.get(
        CONF_NO_FORCE_SCAN_HOUR_START, DEFAULT_NO_FORCE_SCAN_HOUR_START
    )
    no_force_scan_hour_finish = config_entry.options.get(
        CONF_NO_FORCE_SCAN_HOUR_FINISH, DEFAULT_NO_FORCE_SCAN_HOUR_FINISH
    )
    scan_interval = timedelta(
        minutes=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    force_scan_interval = timedelta(
        minutes=config_entry.options.get(
            CONF_FORCE_SCAN_INTERVAL, DEFAULT_FORCE_SCAN_INTERVAL
        )
    )

    api_cloud_class = api_cloud_for_region_and_brand(region=region, brand=brand)
    api_cloud_instance = api_cloud_class(
        username=username,
        password=password,
        hass=hass,
        update_interval=scan_interval,
        force_scan_interval=force_scan_interval,
        no_force_scan_hour_start=no_force_scan_hour_start,
        no_force_scan_hour_finish=no_force_scan_hour_finish,
    )
    if CONF_PIN in config_entry.data and config_entry.data[CONF_PIN] is not None:
        pin = config_entry.data[CONF_PIN]
        api_cloud_instance.pin = pin
    try:
        hass_vehicle: Vehicle = await api_cloud_instance.get_vehicle(
            identifier=vehicle_identifier
        )
    except ClientError as error:
        _LOGGER.warning(
            f"error during setup: {error}, waiting 1 minute and trying again."
        )
        sleep(60)
        hass_vehicle: Vehicle = await api_cloud_instance.get_vehicle(
            identifier=vehicle_identifier
        )

    data = {
        DATA_VEHICLE_INSTANCE: hass_vehicle,
        DATA_VEHICLE_LISTENER: None,
        DATA_CONFIG_UPDATE_LISTENER: None,
    }

    _LOGGER.debug("first update start")
    await hass_vehicle.coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("first update finished")

    async def update(_event_time_utc: datetime):
        try:
            await hass.async_create_task(hass_vehicle.update(interval=True))
        except Exception as ex:
            _LOGGER.error("Exception in interval update : %s", str(ex))

    data[DATA_VEHICLE_LISTENER] = async_track_time_interval(
        hass, update, timedelta(minutes=1)
    )
    hass.data[DOMAIN][vehicle_identifier] = data

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug("unload entry")
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        vehicle_identifier = config_entry.data[CONF_VEHICLE_IDENTIFIER]
        hass_vehicle = hass.data[DOMAIN][vehicle_identifier][DATA_VEHICLE_INSTANCE]
        if hass_vehicle is not None:
            await hass_vehicle.api_cloud.cleanup()

        vehicle_listener = hass.data[DOMAIN][vehicle_identifier][DATA_VEHICLE_LISTENER]
        vehicle_listener()

        config_update_listener = hass.data[DOMAIN][vehicle_identifier][
            DATA_CONFIG_UPDATE_LISTENER
        ]
        config_update_listener()

        hass.data[DOMAIN][vehicle_identifier] = None

    return unload_ok
