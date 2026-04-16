# Energa Outages — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/vincentto13/hass-energa-outages.svg)](https://github.com/vincentto13/hass-energa-outages/releases)
[![HACS Validation](https://github.com/vincentto13/hass-energa-outages/actions/workflows/validate.yaml/badge.svg)](https://github.com/vincentto13/hass-energa-outages/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/vincentto13/hass-energa-outages/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/vincentto13/hass-energa-outages/actions/workflows/hassfest.yaml)

A custom Home Assistant integration that monitors [Energa Operator](https://energa-operator.pl) power outages for your configured zones.

## Features

- Monitors one or more HA zones for scheduled or unplanned power outages
- Uses zone GPS coordinates and radius as the search area
- **Enum sensor** per zone with states: `active` / `planned` / `none`
- Detects **planned outages** up to N days ahead (default 7 days)
- Configurable polling interval (default: 5 minutes)
- Backed by [energa-outages-api](https://github.com/vincentto13/energa-outages-api) PyPI package

---

## Installation

### HACS (recommended)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=vincentto13&repository=hass-energa-outages&category=integration)

1. Click the button above or open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/vincentto13/hass-energa-outages` as type **Integration**
3. Install "Energa Outages" → restart Home Assistant
4. Then add the integration:

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=energa_outages)

### Manual

Copy `custom_components/energa_outages/` into your `<config>/custom_components/` directory and restart.

---

## Configuration

1. **Settings → Devices & Services → Add Integration → search "Energa Outages"**
2. Select one or more HA zones to monitor
3. Set the polling interval (60–3600 seconds, default 300)
4. Set the planned outage look-ahead window (1–14 days, default 7)

To update zones or settings later: **Settings → Devices & Services → Energa Outages → Configure**

---

## Entities

For each configured zone the integration creates one entity.

### Sensor — `sensor.energa_outages_<zone>`

| State | Icon | Meaning |
|---|---|---|
| `active` | `mdi:flash-alert` | Outage is happening right now |
| `planned` | `mdi:flash-triangle` | Outage planned within the look-ahead window |
| `none` | `mdi:flash` | No outage detected |

**Attributes (present when state is `active` or `planned`):**

| Attribute | Description |
|---|---|
| `confidence` | `1.0` = zone centre inside polygon; `<1.0` = within zone radius of boundary |
| `is_inside` | `true` if zone centre is inside the outage polygon |
| `distance_to_boundary_m` | Distance to nearest polygon edge in metres (0 if inside) |
| `outage_guid` | Unique outage identifier |
| `shutdown_type` | `"planned"` or `"emergency"` |
| `start_date` / `end_date` | Outage time window (ISO 8601, UTC) |
| `next_outage_start` | Start of the next outage time window (ISO 8601, UTC) |
| `region` / `department` | Energa region and department |
| `message` | Raw affected address list from Energa |

**Always present:**

| Attribute | Description |
|---|---|
| `planned_outages` | Full list of upcoming outages within look-ahead window (empty list if none) |

---

## Example

Zone `qwe` centred at `53.6336 N, 17.4372 E` with radius 500 m, no active outage but one upcoming:

**`sensor.energa_outages_qwe`** — `planned`
```yaml
confidence: 1.0
is_inside: true
distance_to_boundary_m: 0
outage_guid: 9e379372-ea6a-4aa4-ab82-aa4dda854223
shutdown_type: emergency
start_date: "2026-04-15T06:30:00+00:00"
end_date: "2026-04-15T11:30:00+00:00"
next_outage_start: "2026-04-15T06:30:00+00:00"
region: Człuchów
department: Słupsk
message: >-
  Jęczniki Wielkie ulica Makowa 8, 11, 23/13 1, 1a, 2, 2/A, 3, od 7 do 9,
  9/A, od 10 do 12, 12/A, 14, 14A, 40, 23/12, 23/15, 23/20, 23/23, 23/26,
  23/28, Jęczniki Wielkie-107/1 (GPO) (MDZ), Jęczniki Wielkie-36/3 (GPO)
  (MDZ), Jęczniki-23/1 (GPO), Jęczniki-37/4 (GPO).
planned_outages:
  - guid: 9e379372-ea6a-4aa4-ab82-aa4dda854223
    start_date: "2026-04-15T06:30:00+00:00"
    end_date: "2026-04-15T11:30:00+00:00"
    next_outage_start: "2026-04-15T06:30:00+00:00"
    confidence: 1.0
    is_inside: true
    shutdown_type: emergency
    region: Człuchów
    message: Jęczniki Wielkie ulica Makowa 8, 11 ...
device_class: enum
```

**`zone.qwe`** (source zone):
```yaml
latitude: 53.63361221037351
longitude: 17.437167263309025
radius: 500
```

---

## How It Works

1. On each poll cycle the integration fetches the Energa Operator outage feed (one HTTP request, result cached)
2. For each configured zone it reads `latitude`, `longitude`, and `radius` from HA zone state
3. It checks whether the zone is affected by any **currently active** outage (point-in-polygon + margin) → state `active`
4. It also scans for **upcoming outages** within the configured look-ahead window → state `planned`
5. If neither matches → state `none`
6. The `planned_outages` attribute is always populated with the full list of upcoming matches

---

## Automations

Example — notify 30 minutes before a planned outage:

```yaml
automation:
  trigger:
    - platform: template
      value_template: >
        {{ states('sensor.energa_outages_home') == 'planned'
           and state_attr('sensor.energa_outages_home', 'next_outage_start') is not none
           and (as_timestamp(state_attr('sensor.energa_outages_home', 'next_outage_start')) - as_timestamp(now())) < 1800 }}
  action:
    - service: notify.mobile_app
      data:
        title: "Planned power outage soon"
        message: >
          Outage starts at {{ state_attr('sensor.energa_outages_home', 'next_outage_start') }}.
          {{ state_attr('sensor.energa_outages_home', 'message') }}
```

---

## Requirements

- Home Assistant 2024.1+
- Python package `energa-outages-api>=0.2.0` (installed automatically)

---

## Coverage

Energa Operator serves northern and central Poland: Gdańsk, Gdynia, Sopot, Toruń, Bydgoszcz, Olsztyn, Płock, Włocławek, Kalisz, Konin and surrounding areas. Wrocław and southern Poland are served by Tauron — those areas will return no results.
