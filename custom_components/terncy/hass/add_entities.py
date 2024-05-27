import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .entity import TerncyEntity
from .entity_descriptions import TerncyEntityDescription
from ..const import DOMAIN
from ..types import AttrValue

if TYPE_CHECKING:
    from ..core.gateway import TerncyGateway

_LOGGER = logging.getLogger(__name__)


def create_entity(
    gateway: "TerncyGateway",
    eid: str,
    description: TerncyEntityDescription,
    init_states: list[AttrValue],  # 初始状态，用于判断设备支持多少特性。
) -> TerncyEntity:
    domain = str(description.PLATFORM)
    cls = (  # fmt: off
        TerncyEntity.NEW.get(f"{domain}.key.{description.key}")
        or TerncyEntity.NEW.get(domain)
    )
    return cls(gateway, eid, description, init_states)


def ha_add_entity(hass: HomeAssistant, config_entry: ConfigEntry, entity: TerncyEntity):
    """Add entity to HA"""
    domain = str(entity.entity_description.PLATFORM)
    config_entry_id = config_entry.entry_id
    registry = er.async_get(hass)
    if entity_id := registry.async_get_entity_id(domain, DOMAIN, entity.unique_id):
        if entity_entry := registry.async_get(entity_id):
            if entity_entry.config_entry_id != config_entry_id:
                _LOGGER.debug(
                    "[%s] entity %s already exists, skip",
                    entity.gateway.unique_id,
                    entity.unique_id,
                )
                return
    _LOGGER.debug("[%s] created entity %s", entity.gateway.unique_id, entity.unique_id)
    async_add_entities = TerncyEntity.ADD[f"{config_entry_id}.{domain}"]
    async_add_entities([entity], update_before_add=False)
