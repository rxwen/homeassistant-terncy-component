"""The Terncy integration."""
import asyncio
import logging

import terncy
import terncy.event
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import async_get_platforms

from .utils import get_attr_value
from .const import (
    CONF_DEVID,
    CONF_HOST,
    CONF_IP,
    CONF_PORT,
    DOMAIN,
    HA_CLIENT_ID,
    PROFILE_COLOR_DIMMABLE_LIGHT,
    PROFILE_COLOR_LIGHT,
    PROFILE_COLOR_TEMPERATURE_LIGHT,
    PROFILE_DIMMABLE_COLOR_TEMPERATURE_LIGHT,
    PROFILE_DIMMABLE_LIGHT,
    PROFILE_DIMMABLE_LIGHT2,
    PROFILE_EXTENDED_COLOR_LIGHT,
    PROFILE_EXTENDED_COLOR_LIGHT2,
    PROFILE_ONOFF_LIGHT,
    PROFILE_PLUG,
    PROFILE_PIR,
    PROFILE_DOOR_SENSOR,
    PROFILE_HA_TEMPERATURE_HUMIDITY,
    PROFILE_CURTAIN,
    PROFILE_LOCK,
    TERNCY_EVENT_SVC_ADD,
    TERNCY_EVENT_SVC_REMOVE,
    TERNCY_HUB_ID_PREFIX,
    TERNCY_MANU_NAME,
    ACTION_SINGLE_PRESS,
    ACTION_DOUBLE_PRESS,
    ACTION_LONG_PRESS,
    TerncyHassPlatformData,
)
from .hub_monitor import TerncyHubManager
from .light import (
    SUPPORT_TERNCY_COLOR,
    SUPPORT_TERNCY_CT,
    SUPPORT_TERNCY_DIMMABLE,
    SUPPORT_TERNCY_EXTENDED,
    SUPPORT_TERNCY_ON_OFF,
    TerncyLight,
)
from .switch import (
    TerncySmartPlug,
    TerncySwitch,
)
from .cover import (
    TerncyCurtain,
)
from .binary_sensor import (
    TerncyDoorSensor,
    TerncyMotionSensor,
)
from .sensor import (
    TerncyTemperatureSensor,
)

EVENT_DATA_CLICK_TIMES = "click_times"
DEVID_EXT_TEMP = "_temp"

PLATFORM_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["light", "cover", "switch", "binary_sensor", "sensor"]

_LOGGER = logging.getLogger(__name__)


def find_dev_by_prefix(devices, prefix):
    """Find device with given prefix."""
    result = []
    for dev in devices.values():
        if dev.unique_id.startswith(prefix):
            result.append(dev)
    return result


def terncy_event_handler(tern, ev):
    """Handle event from terncy system."""
    hass = tern.hass_platform_data.hass
    parsed_devices = tern.hass_platform_data.parsed_devices
    if isinstance(ev, terncy.event.Connected):
        _LOGGER.info("got connected event %s", tern.dev_id)
        asyncio.ensure_future(async_refresh_devices(hass, tern))
    if isinstance(ev, terncy.event.Disconnected):
        _LOGGER.info("got disconnected event %s", tern.dev_id)
        for dev in parsed_devices.values():
            dev.is_available = False
            if dev.hass:
                dev.schedule_update_ha_state()
    if isinstance(ev, terncy.event.EventMessage):
        _LOGGER.info("got event message %s %s", tern.dev_id, ev.msg)
        evt_type = ""
        if "type" in ev.msg:
            evt_type = ev.msg["type"]
        if "entities" not in ev.msg:
            return
        ents = ev.msg["entities"]
        if evt_type == "report":
            for ent in ents:
                if "attributes" not in ent:
                    continue
                devid = ent["id"]
                temperature = get_attr_value(ent["attributes"], "temperature")
                if temperature is not None:
                    _LOGGER.info("got temperature")
                    devid = devid + DEVID_EXT_TEMP

                if devid in parsed_devices:
                    dev = parsed_devices[devid]
                    attrs = ent["attributes"]
                    dev.update_state(attrs)
                    if dev.hass:
                        dev.schedule_update_ha_state()
                else:
                    _LOGGER.info("dev %s not found", devid)

        elif evt_type == "keyPressed":
            for ent in ents:
                if "attributes" not in ent:
                    continue
                devid = ent["id"]

                if devid in parsed_devices:
                    dev = parsed_devices[devid]
                    attrs = ent["attributes"]
                    times = attrs[0]["times"]
                    ev_type = ACTION_SINGLE_PRESS
                    if times == 2:
                        ev_type = ACTION_DOUBLE_PRESS
                    event_data = {
                        EVENT_DATA_CLICK_TIMES: times,
                        "source": devid,
                    }
                    _LOGGER.info("fire event to bus %s %d", ev_type, times)
                    _LOGGER.info(event_data)
                    hass.bus.fire(
                        ev_type,
                        event_data,
                    )
        elif evt_type == "entityAvailable":
            for ent in ents:
                devid = ent["id"]
                _LOGGER.info("[%s] %s is available", tern.dev_id, devid)
                hass.async_create_task(update_or_create_entity(ent, tern))
        elif evt_type == "offline":
            for ent in ents:
                devid = ent["id"]
                _LOGGER.info("[%s] %s is offline", tern.dev_id, devid)
                if devid in parsed_devices:
                    dev = parsed_devices[devid]
                    dev.is_available = False
                    if dev.hass:
                        dev.schedule_update_ha_state()
                elif devid.rfind("-") > 0:
                    prefix = devid[0 : devid.rfind("-")]
                    _LOGGER.info(
                        "[%s] %s not found, try find prefix", tern.dev_id, prefix
                    )
                    devs = find_dev_by_prefix(parsed_devices, prefix)
                    for dev in devs:
                        _LOGGER.info("[%s] %s is offline", tern.dev_id, dev.unique_id)
                        dev.is_available = False
                        if dev.hass:
                            dev.schedule_update_ha_state()
        elif evt_type == "entityDeleted":
            platform = None
            for plat in async_get_platforms(hass, DOMAIN):
                if plat.config_entry.unique_id == tern.dev_id:
                    platform = plat
                    break
            if platform is None:
                return
            for ent in ents:
                devid = ent["id"]
                _LOGGER.info("[%s] %s is deleted", tern.dev_id, devid)
                if devid in parsed_devices:
                    dev = parsed_devices[devid]
                    dev.is_available = False
                    if dev.hass:
                        dev.schedule_update_ha_state()
                elif devid.rfind("-") > 0:
                    prefix = devid[0 : devid.rfind("-")]
                    _LOGGER.info(
                        "[%s] %s not found, try find prefix", tern.dev_id, prefix
                    )
                    devs = find_dev_by_prefix(parsed_devices, prefix)
                    for dev in devs:
                        _LOGGER.info("[%s] %s is delete", tern.dev_id, dev.unique_id)
                        hass.async_create_task(
                            platform.async_remove_entity(dev.entity_id)
                        )
                        parsed_devices.pop(dev.unique_id)
        else:
            _LOGGER.info("unsupported event type %s", evt_type)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Terncy component."""
    return True


async def update_or_create_entity(dev, tern):
    """Update or create hass entity for given terncy device."""
    model = dev["model"] if "model" in dev else ""
    version = dev["version"] if "version" in dev else ""
    available = dev["online"] if "online" in dev else False
    if "services" not in dev:
        return []
    _LOGGER.info(dev)
    for svc in dev["services"]:
        isLight = False
        isSwitch = False
        profile = svc["profile"]
        features = -1
        if profile == PROFILE_ONOFF_LIGHT:
            features = SUPPORT_TERNCY_ON_OFF
            isLight = True
        elif profile == PROFILE_COLOR_LIGHT:
            features = SUPPORT_TERNCY_COLOR
            isLight = True
        elif profile == PROFILE_EXTENDED_COLOR_LIGHT:
            features = SUPPORT_TERNCY_EXTENDED
            isLight = True
        elif profile == PROFILE_COLOR_TEMPERATURE_LIGHT:
            features = SUPPORT_TERNCY_CT
            isLight = True
        elif profile == PROFILE_DIMMABLE_COLOR_TEMPERATURE_LIGHT:
            features = SUPPORT_TERNCY_CT
            isLight = True
        elif profile == PROFILE_DIMMABLE_LIGHT:
            features = SUPPORT_TERNCY_DIMMABLE
            isLight = True
        elif profile == PROFILE_DIMMABLE_LIGHT2:
            features = SUPPORT_TERNCY_DIMMABLE
            isLight = True
        elif profile == PROFILE_COLOR_DIMMABLE_LIGHT:
            features = SUPPORT_TERNCY_EXTENDED
            isLight = True
        elif profile == PROFILE_EXTENDED_COLOR_LIGHT2:
            features = SUPPORT_TERNCY_EXTENDED
            isLight = True
        elif profile == PROFILE_PLUG:
            features = SUPPORT_TERNCY_ON_OFF
        elif profile == PROFILE_CURTAIN:
            features = SUPPORT_TERNCY_ON_OFF
        elif profile == PROFILE_DOOR_SENSOR:
            features = SUPPORT_TERNCY_ON_OFF
        elif profile == PROFILE_HA_TEMPERATURE_HUMIDITY:
            features = SUPPORT_TERNCY_ON_OFF
        elif profile == PROFILE_PIR:
            features = SUPPORT_TERNCY_ON_OFF
        else:
            _LOGGER.info("unsupported profile %d", profile)
            continue

        devid = svc["id"]
        devidTemp = devid + DEVID_EXT_TEMP
        if profile == PROFILE_HA_TEMPERATURE_HUMIDITY:
            devid = devidTemp

        disableRelay = get_attr_value(svc["attributes"], "disableRelay")
        if disableRelay is not None and disableRelay == 1:
            _LOGGER.info("%s is disabled, skip it", devid)
            continue
        temperature = get_attr_value(svc["attributes"], "temperature")
        _LOGGER.info(temperature)

        name = svc["name"]
        if name == "":
            name = devid
        device = None
        deviceTemp = None
        if devid in tern.hass_platform_data.parsed_devices:
            device = tern.hass_platform_data.parsed_devices[devid]
            if temperature is not None:
                deviceTemp = tern.hass_platform_data.parsed_devices[devidTemp]
                deviceTemp.update_state(svc["attributes"])
                deviceTemp.is_available = available
        else:
            if model.find("TERNCY-WS") >= 0 or model.find("TERNCY-LF") >= 0:
                isLight = False
                isSwitch = True
                device = TerncySwitch(tern, devid, name, model, version, features)
            elif profile == PROFILE_PLUG:
                device = TerncySmartPlug(tern, devid, name, model, version, features)
            elif profile == PROFILE_CURTAIN:
                device = TerncyCurtain(tern, devid, name, model, version, features)
            elif profile == PROFILE_DOOR_SENSOR:
                device = TerncyDoorSensor(tern, devid, name, model, version, features)
            elif profile == PROFILE_HA_TEMPERATURE_HUMIDITY:
                device = TerncyTemperatureSensor(tern, devid, name + " temperature", model, version, features)
            elif profile == PROFILE_PIR:
                device = TerncyMotionSensor(tern, devid, name, model, version, features)
            else:
                device = TerncyLight(tern, devid, name, model, version, features)

            if profile != PROFILE_HA_TEMPERATURE_HUMIDITY and temperature is not None:
                _LOGGER.info("create temperature sensor")
                deviceTemp = TerncyTemperatureSensor(tern, devidTemp, name + " temperature", model, version, features)
                deviceTemp.update_state(svc["attributes"])
                deviceTemp.is_available = available
                tern.hass_platform_data.parsed_devices[devidTemp] = deviceTemp
        device.update_state(svc["attributes"])
        device.is_available = available
        if devid in tern.hass_platform_data.parsed_devices:
            if device.hass:
                device.schedule_update_ha_state()
        else:
            for platform in async_get_platforms(tern.hass_platform_data.hass, DOMAIN):
                if platform.config_entry.unique_id == tern.dev_id:
                    if profile == PROFILE_PLUG and platform.domain == "switch":
                        await platform.async_add_entities([device])
                        break
                    elif profile == PROFILE_CURTAIN and platform.domain == "cover":
                        await platform.async_add_entities([device])
                        break
                    elif (
                        profile == PROFILE_DOOR_SENSOR
                        and platform.domain == "binary_sensor"
                    ):
                        await platform.async_add_entities([device])
                        break
                    elif profile == PROFILE_PIR and platform.domain == "binary_sensor":
                        await platform.async_add_entities([device])
                        break
                    elif deviceTemp is not None and platform.domain == "sensor":
                        await platform.async_add_entities([deviceTemp])
                        break
                    elif profile == PROFILE_HA_TEMPERATURE_HUMIDITY and platform.domain == "sensor":
                        await platform.async_add_entities([device])
                        break
                    elif isLight and platform.domain == "light":
                        await platform.async_add_entities([device])
                        break
                    elif isSwitch and platform.domain == "switch":
                        await platform.async_add_entities([device])
                        break
            tern.hass_platform_data.parsed_devices[devid] = device


async def async_refresh_devices(hass: HomeAssistant, tern):
    """Get devices from terncy."""
    _LOGGER.info("refresh devices now")
    response = await tern.get_entities("device", True)
    devices = response["rsp"]["entities"]
    pdata = tern.hass_platform_data

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=pdata.hub_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, pdata.mac)},
        identifiers={(DOMAIN, pdata.hub_entry.entry_id)},
        manufacturer=TERNCY_MANU_NAME,
        name=pdata.hub_entry.title,
        model="TERNCY-GW01",
        sw_version=1,
    )

    for dev in devices:
        await update_or_create_entity(dev, tern)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Terncy from a config entry."""
    _LOGGER.info("terncy domain async_setup_entry %s", entry.unique_id)
    dev_id = entry.data["identifier"]
    hass.data[DOMAIN] = {}
    mgr = TerncyHubManager.instance(hass)
    await mgr.start_discovery()

    tern = terncy.Terncy(
        HA_CLIENT_ID,
        dev_id,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data["username"],
        entry.data["token"],
    )

    pdata = TerncyHassPlatformData()

    pdata.hass = hass
    pdata.hub_entry = entry
    pdata.mac = dr.format_mac(entry.unique_id.replace(TERNCY_HUB_ID_PREFIX, ""))
    tern.hass_platform_data = pdata
    hass.data[DOMAIN][entry.entry_id] = tern

    async def setup_terncy_loop():
        asyncio.create_task(tern.start())

    async def on_hass_stop(event):
        """Stop push updates when hass stops."""
        _LOGGER.info("terncy domain stop")
        await tern.stop()

    async def on_terncy_svc_add(event):
        """Stop push updates when hass stops."""
        dev_id = event.data[CONF_DEVID]
        _LOGGER.info("found terncy service: %s %s", dev_id, event.data)
        ip = event.data[CONF_IP]
        if dev_id == tern.dev_id and not tern.is_connected():
            tern.ip = ip
            _LOGGER.info("start connection to %s %s", dev_id, tern.ip)

            hass.async_create_task(setup_terncy_loop())

    async def on_terncy_svc_remove(event):
        """Stop push updates when hass stops."""
        dev_id = event.data[CONF_DEVID]
        _LOGGER.info("terncy svc remove %s", dev_id)
        if not tern.is_connected():
            await tern.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, on_hass_stop)
    hass.bus.async_listen(TERNCY_EVENT_SVC_ADD, on_terncy_svc_add)
    hass.bus.async_listen(TERNCY_EVENT_SVC_REMOVE, on_terncy_svc_remove)

    manager = TerncyHubManager.instance(hass)
    if dev_id in manager.hubs:
        if not tern.is_connected():
            tern.ip = manager.hubs[dev_id][CONF_IP]
            _LOGGER.info("start connection to %s %s", dev_id, tern.ip)
            hass.async_create_task(setup_terncy_loop())

    tern.register_event_handler(terncy_event_handler)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(pdata.hub_entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
