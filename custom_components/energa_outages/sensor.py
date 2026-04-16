from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from energa_outages_api import OutageMatch

from .const import DOMAIN
from .coordinator import EnergaOutagesCoordinator, ZoneStatus

STATE_ACTIVE = "active"
STATE_PLANNED = "planned"
STATE_NONE = "none"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergaOutagesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EnergaOutagesSensor(coordinator, entry, zone_entity_id)
        for zone_entity_id in coordinator.zone_entity_ids
    )


class EnergaOutagesSensor(CoordinatorEntity[EnergaOutagesCoordinator], SensorEntity):
    """Enum sensor exposing outage status for a zone: active / planned / none."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_ACTIVE, STATE_PLANNED, STATE_NONE]
    _attr_has_entity_name = True

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
    def native_value(self) -> str:
        status = self._status
        if status.active:
            return STATE_ACTIVE
        if status.planned:
            return STATE_PLANNED
        return STATE_NONE

    @property
    def icon(self) -> str:
        state = self.native_value
        if state == STATE_ACTIVE:
            return "mdi:flash-alert"
        if state == STATE_PLANNED:
            return "mdi:flash-triangle"
        return "mdi:flash"

    @property
    def extra_state_attributes(self) -> dict:
        status = self._status
        now = datetime.now(timezone.utc)
        attrs: dict = {}

        # Primary match — active takes priority, otherwise soonest planned
        primary: OutageMatch | None = status.active or (status.planned[0] if status.planned else None)

        if primary:
            s = primary.shutdown
            attrs["confidence"] = round(primary.confidence, 4)
            attrs["is_inside"] = primary.is_inside
            attrs["distance_to_boundary_m"] = round(primary.distance_to_boundary_m, 1)
            attrs["outage_guid"] = primary.guid
            attrs["shutdown_type"] = s.shutdown_type_label
            attrs["start_date"] = s.start_date.isoformat()
            attrs["end_date"] = s.end_date.isoformat()
            attrs["region"] = s.region_name
            attrs["department"] = s.dept_name
            attrs["message"] = s.message
            next_start = s.next_start(now)
            if next_start:
                attrs["next_outage_start"] = next_start.isoformat()
            elif status.active:
                # Currently active — next_start is the start of the active window
                attrs["next_outage_start"] = s.start_date.isoformat()

        # Full planned list — always present (even during active outage)
        attrs["planned_outages"] = [
            {
                "guid": m.guid,
                "start_date": m.shutdown.start_date.isoformat(),
                "end_date": m.shutdown.end_date.isoformat(),
                "next_outage_start": (
                    ns.isoformat() if (ns := m.shutdown.next_start(now)) else None
                ),
                "confidence": round(m.confidence, 4),
                "is_inside": m.is_inside,
                "shutdown_type": m.shutdown.shutdown_type_label,
                "region": m.shutdown.region_name,
                "message": m.shutdown.message,
            }
            for m in status.planned
        ]

        return attrs
