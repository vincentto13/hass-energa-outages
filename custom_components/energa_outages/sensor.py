from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnergaOutagesCoordinator, ZoneStatus


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EnergaOutagesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EnergaOutagesNextSensor(coordinator, entry, zone_entity_id)
        for zone_entity_id in coordinator.zone_entity_ids
    )


class EnergaOutagesNextSensor(CoordinatorEntity[EnergaOutagesCoordinator], SensorEntity):
    """Timestamp sensor showing when the next outage starts for a zone."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
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
        self._attr_name = f"{zone_name} Next Outage"
        self._attr_unique_id = f"{entry.entry_id}_{zone_entity_id}_next"
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
    def native_value(self) -> datetime | None:
        status = self._status
        # If currently active, return the active outage start
        if status.active:
            return status.active.shutdown.start_date
        # Otherwise return the soonest planned outage start
        if status.planned:
            return status.planned[0].shutdown.start_date
        return None

    @property
    def extra_state_attributes(self) -> dict:
        status = self._status
        if status.active:
            m = status.active
            return {
                "outage_status": "active",
                "end_date": m.shutdown.end_date.isoformat(),
                "shutdown_type": m.shutdown.shutdown_type_label,
                "message": m.shutdown.message,
            }
        if status.planned:
            m = status.planned[0]
            return {
                "outage_status": "planned",
                "end_date": m.shutdown.end_date.isoformat(),
                "shutdown_type": m.shutdown.shutdown_type_label,
                "message": m.shutdown.message,
                "planned_count": len(status.planned),
            }
        return {}
