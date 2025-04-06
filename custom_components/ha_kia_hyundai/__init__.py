import logging

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from kia_hyundai_api import UsKia, AuthError

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_VEHICLE_ID,
    DEFAULT_SCAN_INTERVAL,
    CONFIG_FLOW_VERSION,
)
from .services import async_setup_services, async_unload_services
from .vehicle_coordinator import VehicleCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating configuration from version %s.%s", config_entry.version, config_entry.minor_version)

    if config_entry.version > CONFIG_FLOW_VERSION:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 2:
        _LOGGER.debug(f"old config data:{config_entry.data}")
        new_data = {
            CONF_USERNAME: config_entry.data[CONF_USERNAME],
            CONF_PASSWORD: config_entry.data[CONF_PASSWORD],
            CONF_VEHICLE_ID: config_entry.data["vehicle_identifier"],
        }
        hass.config_entries.async_update_entry(config_entry, data=new_data, minor_version=1, version=CONFIG_FLOW_VERSION)

    _LOGGER.debug("Migration to configuration version %s.%s successful", config_entry.version, config_entry.minor_version)

    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    async_setup_services(hass)

    vehicle_id = config_entry.data[CONF_VEHICLE_ID]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    scan_interval = timedelta(
        minutes=config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
    )

    client_session = async_get_clientsession(hass)
    api_connection = UsKia(
        username=username,
        password=password,
        client_session=client_session,
    )
    try:
        await api_connection.get_vehicles()
    except AuthError as err:
        raise ConfigEntryAuthFailed(err) from err
    coordinator: VehicleCoordinator | None = None
    for vehicle in api_connection.vehicles:
        if vehicle_id == vehicle["vehicleIdentifier"]:
            coordinator = VehicleCoordinator(
                hass=hass,
                vehicle_id=vehicle["vehicleIdentifier"],
                vehicle_name=vehicle["nickName"],
                vehicle_model=vehicle["modelName"],
                api_connection=api_connection,
                scan_interval=scan_interval,
            )
    if coordinator is None:
        raise ConfigEntryError("vehicle not found")
    _LOGGER.debug("first update start")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("first update finished")

    hass.data[DOMAIN][vehicle_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True

async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    if unload_ok :=  await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        vehicle_id = config_entry.unique_id
        await hass.data[DOMAIN][vehicle_id].api_connection.api_session.close()
        del hass.data[DOMAIN][vehicle_id]
    if not hass.data[DOMAIN]:
        async_unload_services(hass)
    return unload_ok
