from __future__ import annotations

import voluptuous as vol

from homeassistant.components.zone import DOMAIN as ZONE_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_PLANNED_WINDOW_DAYS,
    CONF_SCAN_INTERVAL,
    CONF_ZONES,
    DEFAULT_PLANNED_WINDOW_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_PLANNED_WINDOW_DAYS,
    MAX_SCAN_INTERVAL,
    MIN_PLANNED_WINDOW_DAYS,
    MIN_SCAN_INTERVAL,
)


def _schema(
    default_zones: list[str],
    default_interval: int,
    default_window: int,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_ZONES, default=default_zones): selector.selector(
                {"entity": {"domain": ZONE_DOMAIN, "multiple": True}}
            ),
            vol.Optional(CONF_SCAN_INTERVAL, default=default_interval): vol.All(
                selector.selector({
                    "number": {
                        "min": MIN_SCAN_INTERVAL,
                        "max": MAX_SCAN_INTERVAL,
                        "unit_of_measurement": "s",
                        "mode": "box",
                    }
                }),
                vol.Coerce(int),
            ),
            vol.Optional(CONF_PLANNED_WINDOW_DAYS, default=default_window): vol.All(
                selector.selector({
                    "number": {
                        "min": MIN_PLANNED_WINDOW_DAYS,
                        "max": MAX_PLANNED_WINDOW_DAYS,
                        "unit_of_measurement": "days",
                        "mode": "slider",
                    }
                }),
                vol.Coerce(int),
            ),
        }
    )


class EnergaOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Energa Outages."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            zones = user_input[CONF_ZONES]
            if not zones:
                errors[CONF_ZONES] = "no_zones_selected"
            else:
                unique_id = "|".join(sorted(zones))
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(zones),
                    data={},
                    options={
                        CONF_ZONES: zones,
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        CONF_PLANNED_WINDOW_DAYS: user_input.get(CONF_PLANNED_WINDOW_DAYS, DEFAULT_PLANNED_WINDOW_DAYS),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema([], DEFAULT_SCAN_INTERVAL, DEFAULT_PLANNED_WINDOW_DAYS),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EnergaOutagesOptionsFlow(config_entry)


class EnergaOutagesOptionsFlow(OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        current = self._config_entry.options

        if user_input is not None:
            zones = user_input[CONF_ZONES]
            if not zones:
                errors[CONF_ZONES] = "no_zones_selected"
            else:
                return self.async_create_entry(
                    data={
                        CONF_ZONES: zones,
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        CONF_PLANNED_WINDOW_DAYS: user_input.get(CONF_PLANNED_WINDOW_DAYS, DEFAULT_PLANNED_WINDOW_DAYS),
                    }
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                current.get(CONF_ZONES, []),
                current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                current.get(CONF_PLANNED_WINDOW_DAYS, DEFAULT_PLANNED_WINDOW_DAYS),
            ),
            errors=errors,
        )


def _entry_title(zone_entity_ids: list[str]) -> str:
    names = [eid.split(".")[-1].replace("_", " ").title() for eid in zone_entity_ids]
    return "Energa Outages: " + ", ".join(names)
