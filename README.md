# Energa Outages — Home Assistant Integration

A custom Home Assistant integration that monitors [Energa Operator](https://energa-operator.pl) power outages for your configured zones.

## Features

- Monitors one or more HA zones for scheduled or unplanned power outages
- Uses zone GPS coordinates and radius as the search area
- **Binary sensor** per zone: `ON` = active outage right now, `OFF` = no current outage
- **Timestamp sensor** per zone: shows when the next outage starts (active or planned)
- Detects **planned outages** up to N days ahead (default 7 days) via `planned_outages` attribute
- Configurable polling interval (default: 5 minutes)
- Backed by [energa-outages-api](https://github.com/vincentto13/energa-outages-api) PyPI package

---

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/vincentto13/hass-energa-outages` as type **Integration**
3. Install "Energa Outages" → restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → Energa Outages**

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

For each configured zone the integration creates two entities.

### Binary sensor — `binary_sensor.energa_outages_<zone>`

| State | Meaning |
|---|---|
| `on` | Active outage affecting the zone right now |
| `off` | No current outage (check `planned_outages` for upcoming ones) |

**Attributes when `on` (active outage):**

| Attribute | Description |
|---|---|
| `outage_status` | `"active"` |
| `confidence` | `1.0` = zone centre inside polygon; `<1.0` = within zone radius of boundary |
| `is_inside` | `true` if zone centre is inside the outage polygon |
| `distance_to_boundary_m` | Distance to nearest polygon edge in metres (0 if inside) |
| `outage_guid` | Unique outage identifier |
| `start_date` / `end_date` | Outage time window (ISO 8601, UTC) |
| `region` / `department` | Energa region and department |
| `shutdown_type` | `"planned"` or `"emergency"` |
| `message` | Raw affected address list from Energa |

**Attribute always present when upcoming outages exist:**

| Attribute | Description |
|---|---|
| `planned_outages` | List of upcoming outages within the look-ahead window (see example below) |

---

### Timestamp sensor — `sensor.energa_outages_<zone>_next_outage`

Shows the start time of the next outage (active or planned). Useful for automations like "notify me 1 hour before a planned outage".

| State | Meaning |
|---|---|
| ISO 8601 datetime | Start time of next outage |
| `unavailable` | No outage in the look-ahead window |

**Attributes:**

| Attribute | Description |
|---|---|
| `outage_status` | `"active"` or `"planned"` |
| `end_date` | When the outage ends |
| `shutdown_type` | `"planned"` or `"emergency"` |
| `message` | Raw affected address list |
| `planned_count` | Total number of planned outages in the window (only when `planned`) |

---

## Example

Zone `qwe` centred at `53.6336 N, 17.4372 E` with radius 500 m, no active outage but one upcoming:

**`binary_sensor.energa_outages_qwe`** — `off`
```yaml
planned_outages:
  - guid: 9e379372-ea6a-4aa4-ab82-aa4dda854223
    start_date: "2026-04-15T06:30:00+00:00"
    end_date: "2026-04-15T11:30:00+00:00"
    confidence: 1.0
    is_inside: true
    shutdown_type: emergency
    region: Człuchów
    message: >-
      Jęczniki Wielkie ulica Makowa 8, 11, 23/13 1, 1a, 2, 2/A, 3, od 7 do 9,
      9/A, od 10 do 12, 12/A, 14, 14A, 40, 23/12, 23/15, 23/20, 23/23, 23/26,
      23/28, Jęczniki Wielkie-107/1 (GPO) (MDZ), Jęczniki Wielkie-36/3 (GPO)
      (MDZ), Jęczniki-23/1 (GPO), Jęczniki-37/4 (GPO).
device_class: power
```

**`sensor.energa_outages_qwe_next_outage`** — `2026-04-15T06:30:00+00:00`
```yaml
outage_status: planned
end_date: "2026-04-15T11:30:00+00:00"
shutdown_type: emergency
planned_count: 1
message: >-
  Jęczniki Wielkie ulica Makowa 8, 11, 23/13 1, 1a, 2, 2/A, 3, od 7 do 9,
  9/A, od 10 do 12, 12/A, 14, 14A, 40, 23/12, 23/15, 23/20, 23/23, 23/26,
  23/28, Jęczniki Wielkie-107/1 (GPO) (MDZ), Jęczniki Wielkie-36/3 (GPO)
  (MDZ), Jęczniki-23/1 (GPO), Jęczniki-37/4 (GPO).
device_class: timestamp
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
3. It checks whether the zone is affected by any **currently active** outage (point-in-polygon + margin)
4. It also scans for **upcoming outages** within the configured look-ahead window
5. Binary sensor turns `on` only for active outages; planned outages appear in `planned_outages` attribute
6. Timestamp sensor always points to the nearest outage start, active or planned

---

## Automations

Example — notify 30 minutes before a planned outage:

```yaml
automation:
  trigger:
    - platform: template
      value_template: >
        {{ states('sensor.energa_outages_home_next_outage') != 'unavailable'
           and state_attr('sensor.energa_outages_home_next_outage', 'outage_status') == 'planned'
           and (as_timestamp(states('sensor.energa_outages_home_next_outage')) - as_timestamp(now())) < 1800 }}
  action:
    - service: notify.mobile_app
      data:
        title: "Planned power outage soon"
        message: >
          Outage starts at {{ states('sensor.energa_outages_home_next_outage') }}.
          {{ state_attr('sensor.energa_outages_home_next_outage', 'message') }}
```

---

## Requirements

- Home Assistant 2024.1+
- Python package `energa-outages-api>=0.2.0` (installed automatically)

---

## Coverage

Energa Operator serves northern and central Poland: Gdańsk, Gdynia, Sopot, Toruń, Bydgoszcz, Olsztyn, Płock, Włocławek, Kalisz, Konin and surrounding areas. Wrocław and southern Poland are served by Tauron — those areas will return no results.
