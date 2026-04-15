from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.components.zone import DOMAIN as ZONE_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from energa_outages_api import EnergaOutagesClient, EnergaOutagesError, OutageMatch

from .const import CONF_PLANNED_WINDOW_DAYS, DEFAULT_PLANNED_WINDOW_DAYS, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneStatus:
    """Outage status for a single zone."""
    active: OutageMatch | None = None
    planned: list[OutageMatch] = field(default_factory=list)


class EnergaOutagesCoordinator(DataUpdateCoordinator[dict[str, ZoneStatus]]):
    """Fetch outage data for all configured zones."""

    def __init__(
        self,
        hass: HomeAssistant,
        zone_entity_ids: list[str],
        scan_interval: int,
        planned_window_days: int = DEFAULT_PLANNED_WINDOW_DAYS,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.zone_entity_ids = zone_entity_ids
        self._planned_window_hours = planned_window_days * 24
        self._client = EnergaOutagesClient(
            session=async_get_clientsession(hass),
            cache_ttl_seconds=scan_interval,
        )
        self._client._owns_session = False

    async def _async_update_data(self) -> dict[str, ZoneStatus]:
        try:
            await self._client.get_shutdowns(force=True)
        except EnergaOutagesError as err:
            raise UpdateFailed(f"Error fetching outage data: {err}") from err

        results: dict[str, ZoneStatus] = {}

        for entity_id in self.zone_entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning("Zone %s not found, skipping", entity_id)
                results[entity_id] = ZoneStatus()
                continue

            try:
                lat = float(state.attributes["latitude"])
                lon = float(state.attributes["longitude"])
                radius = float(state.attributes.get("radius", 100))
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.warning("Zone %s has invalid attributes: %s", entity_id, err)
                results[entity_id] = ZoneStatus()
                continue

            try:
                active = await self._client.check_location(
                    lat=lat, lon=lon, margin_m=radius, force=False,
                )
                planned = await self._client.check_location_planned(
                    lat=lat, lon=lon, margin_m=radius,
                    window_hours=self._planned_window_hours, force=False,
                )
            except EnergaOutagesError as err:
                _LOGGER.error("Error checking location for zone %s: %s", entity_id, err)
                results[entity_id] = ZoneStatus()
                continue

            results[entity_id] = ZoneStatus(active=active, planned=planned)

        return results
