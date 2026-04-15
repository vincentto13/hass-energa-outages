from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PLANNED_WINDOW_DAYS,
    CONF_SCAN_INTERVAL,
    CONF_ZONES,
    DEFAULT_PLANNED_WINDOW_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import EnergaOutagesCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = EnergaOutagesCoordinator(
        hass=hass,
        zone_entity_ids=entry.options[CONF_ZONES],
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        planned_window_days=entry.options.get(CONF_PLANNED_WINDOW_DAYS, DEFAULT_PLANNED_WINDOW_DAYS),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
