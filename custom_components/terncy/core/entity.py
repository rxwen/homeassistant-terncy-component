import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN, TerncyEntityDescription
from ..types import AttrValue

if TYPE_CHECKING:
    from .gateway import TerncyGateway
    from .device import TerncyDevice


_LOGGER = logging.getLogger(__name__)


class TerncyEntity(Entity):
    """Base class for Terncy entities."""

    entity_description: TerncyEntityDescription
    _attr_should_poll: bool = False

    def __init__(
        self,
        gateway: "TerncyGateway",
        device: "TerncyDevice",
        description: TerncyEntityDescription,
    ):
        self.gateway = gateway
        self.device = device
        self.entity_description = description

        self.serial_number = device.serial_number  # svc["id"]
        """和小燕网关通信用的key"""

        unique_id = self.serial_number
        if description.sub_key:
            unique_id = f"{unique_id}_{description.sub_key}"
        if description.unique_id_prefix:
            unique_id = f"{description.unique_id_prefix}_{unique_id}"
        self._attr_unique_id = unique_id

        # migrate from old entity_id
        self._migrate_from_old_entity(gateway.hass, description)

        self._attr_device_info = DeviceInfo(
            identifiers=device.identifiers,
        )

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
        self.async_on_remove(
            self.gateway.add_listener(self.serial_number, self.update_state)
        )

    def _migrate_from_old_entity(self, hass, description: TerncyEntityDescription):
        """Migrate from old entity_id"""
        if not description.old_unique_id_suffix:
            return

        entity_registry = er.async_get(hass)
        # noinspection PyTypeChecker
        if old_entity_id := entity_registry.async_get_entity_id(
            description.PLATFORM,
            DOMAIN,
            f"{self.serial_number}{description.old_unique_id_suffix}",
        ):
            _LOGGER.debug("Migrate from old entity_id %s", old_entity_id)
            entity_registry.async_update_entity(
                old_entity_id,
                new_unique_id=self._attr_unique_id,
            )


def create_entity_setup(
    async_add_entities: AddEntitiesCallback,
    new_entity: Callable[
        ["TerncyGateway", "TerncyDevice", TerncyEntityDescription], TerncyEntity
    ],
):
    def setup_entity(
        gateway: "TerncyGateway",
        device: "TerncyDevice",
        descriptions: list[TerncyEntityDescription],
    ) -> list[TerncyEntity]:
        entities = []
        for description in descriptions:
            entity = new_entity(gateway, device, description)
            entities.append(entity)
        async_add_entities(entities)
        return entities

    return setup_entity
