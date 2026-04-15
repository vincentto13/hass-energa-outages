from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from energa_outages_api import OutageMatch

from .const import DOMAIN
from .coordinator import EnergaOutagesCoordinator, ZoneStatus


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergaOutagesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EnergaOutagesBinarySensor(coordinator, entry, zone_entity_id)
        for zone_entity_id in coordinator.zone_entity_ids
    )


class EnergaOutagesBinarySensor(CoordinatorEntity[EnergaOutagesCoordinator], BinarySensorEntity):
    """Binary sensor — ON when an active outage affects the zone."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_has_entity_name = True

    @property
    def icon(self) -> str:
        return "mdi:flash-alert" if self.is_on else "mdi:flash"

    def __init__(
        self,
        coordinator: EnergaOutagesCoordinator,
        entry: ConfigEntry,
        zone_entity_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_entity_id = zone_entity_id
        zone_name = zone_entity_id.split(".")[-1].replace("_", " ").title()
        self._attr_name = zone_name
        self._attr_unique_id = f"{entry.entry_id}_{zone_entity_id}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energa Outages",
            manufacturer="Energa Operator",
        )

    @property
    def _status(self) -> ZoneStatus:
        if self.coordinator.data is None:
            return ZoneStatus()
        return self.coordinator.data.get(self._zone_entity_id, ZoneStatus())

    @property
    def is_on(self) -> bool:
        return self._status.active is not None

    @property
    def extra_state_attributes(self) -> dict:
        status = self._status
        attrs: dict = {}

        if status.active:
            match = status.active
            attrs["outage_status"] = "active"
            attrs["confidence"] = match.confidence
            attrs["is_inside"] = match.is_inside
            attrs["distance_to_boundary_m"] = match.distance_to_boundary_m
            attrs["outage_guid"] = match.guid
            s = match.shutdown
            if s.start_date:
                attrs["start_date"] = s.start_date.isoformat()
            if s.end_date:
                attrs["end_date"] = s.end_date.isoformat()
            if s.region_name:
                attrs["region"] = s.region_name
            if s.dept_name:
                attrs["department"] = s.dept_name
            attrs["shutdown_type"] = s.shutdown_type_label
            attrs["message"] = s.message

        if status.planned:
            attrs["planned_outages"] = [
                {
                    "guid": m.guid,
                    "start_date": m.shutdown.start_date.isoformat(),
                    "end_date": m.shutdown.end_date.isoformat(),
                    "confidence": round(m.confidence, 4),
                    "is_inside": m.is_inside,
                    "shutdown_type": m.shutdown.shutdown_type_label,
                    "message": m.shutdown.message,
                    "region": m.shutdown.region_name,
                }
                for m in status.planned
            ]

        return attrs
