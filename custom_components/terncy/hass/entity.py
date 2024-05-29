from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity_descriptions import TerncyEntityDescription
from ..const import DOMAIN
from ..types import AttrValue

if TYPE_CHECKING:
    from ..core.gateway import TerncyGateway


class TerncyEntity(Entity):
    """Base class for Terncy entities."""

    ADD: dict[str, AddEntitiesCallback] = {}  # key: config_entry_id.domain
    NEW: dict[
        str,
        Callable[
            ["TerncyGateway", str, TerncyEntityDescription, list[AttrValue]],
            "TerncyEntity",
        ],
    ] = {}  # key: domain.key or domain

    entity_description: TerncyEntityDescription
    _attr_should_poll: bool = False

    def __init__(
        self,
        gateway: "TerncyGateway",
        eid: str,
        description: TerncyEntityDescription,
        init_states: list[AttrValue],
    ):
        self.gateway = gateway
        self.eid = eid
        """和小燕网关通信用的id，在那边叫entityId，一般是'序列号-01'这样的形式"""
        self.entity_description = description

        unique_id = self.eid
        if description.sub_key:
            unique_id = f"{unique_id}_{description.sub_key}"
        if description.unique_id_prefix:
            unique_id = f"{description.unique_id_prefix}_{unique_id}"
        self._attr_unique_id = unique_id

        # migrate from old entity_id
        self._migrate_from_old_entity(gateway.hass, description)

    @property
    def api(self):
        return self.gateway

    def update_state(self, attrs: list[AttrValue]):
        raise NotImplementedError

    def set_available(self, available):
        self._attr_available = available
        if self.hass:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.gateway.add_listener(self.eid, self.update_state))

    def _migrate_from_old_entity(self, hass, description: TerncyEntityDescription):
        """Migrate from old entity_id"""
        if not description.old_unique_id_suffix:
            return

        entity_registry = er.async_get(hass)
        # noinspection PyTypeChecker
        if old_entity_id := entity_registry.async_get_entity_id(
            description.PLATFORM,
            DOMAIN,
            f"{self.eid}{description.old_unique_id_suffix}",
        ):
            self.gateway.logger.debug("Migrate from old entity_id %s", old_entity_id)
            entity_registry.async_update_entity(
                old_entity_id,
                new_unique_id=self._attr_unique_id,
            )
