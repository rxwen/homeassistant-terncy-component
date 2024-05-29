"""The Terncy integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceEntry

from .const import (
    CONF_EXPORT_DEVICE_GROUPS,
    CONF_EXPORT_SCENES,
    DOMAIN,
    HAS_EVENT_PLATFORM,
    TERNCY_MANU_NAME,
)
from .core.gateway import TerncyGateway
from .hub_monitor import TerncyHubManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    # Platform.EVENT,  # >=2023.8
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]
if HAS_EVENT_PLATFORM:
    PLATFORMS.append(Platform.EVENT)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Terncy integration."""
    # _LOGGER.debug("async_setup %s", config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terncy from a config entry."""
    _LOGGER.debug("async_setup_entry %s, %s", entry.unique_id, entry.options)
    hass.data.setdefault(DOMAIN, {})

    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    hub_manager = TerncyHubManager.instance(hass)
    await hub_manager.start_discovery()

    gateway = TerncyGateway(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = gateway

    # first create gateway device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(CONNECTION_NETWORK_MAC, gateway.mac)},
        identifiers={(DOMAIN, gateway.unique_id)},
        manufacturer=TERNCY_MANU_NAME,
        name=gateway.name,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    gateway.start()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry %s", entry.unique_id)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if gateway := hass.data[DOMAIN].get(entry.entry_id):
            gateway.api.retry = False
            await gateway.api.stop()
            hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    # reference: https://developers.home-assistant.io/docs/device_registry_index/#removing-devices
    _LOGGER.debug(
        "async_remove_config_entry_device entry.unique_id:%s device_id:%s",
        config_entry.unique_id,
        device_entry.id,
    )
    return True


async def entry_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    # https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
    _LOGGER.debug("[%s] Options updated: %s", entry.unique_id, entry.options)
    gateway: TerncyGateway = hass.data[DOMAIN][entry.entry_id]
    if (
        entry.options.get(CONF_EXPORT_DEVICE_GROUPS, True)
        != gateway.export_device_groups
        or entry.options.get(CONF_EXPORT_SCENES, False) != gateway.export_scenes
    ):
        await hass.config_entries.async_reload(entry.entry_id)
