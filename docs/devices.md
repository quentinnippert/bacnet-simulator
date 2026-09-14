# Devices

BACnet Lab simulates 7 HVAC devices with 44 BACnet points. Default devices use separate UDP ports and directed discovery.

## Device Overview

| Device | ID | UDP Port | Points | Location |
|--------|----|----------|--------|----------|
| AHU-01 | 1001 | 47808 | 12 | Main Building |
| FCU-01 | 2001 | 47810 | 7 | Zone 1 (Office North) |
| FCU-02 | 2002 | 47811 | 7 | Zone 2 (Office South) |
| TSTAT-01 | 3001 | 47813 | 6 | Lobby |
| ZC-01 | 4001 | 47814 | 7 | Open Plan Area |
| OAT-01 | 5001 | 47812 | 2 | Outdoor |
| CO2-01 | 5002 | 47809 | 3 | Conference Room |

## AHU-01 — Air Handling Unit

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| AHU-01/SupplyAirTemp | analogInput | Supply air temperature | 22.5 | degreesCelsius |
| AHU-01/ReturnAirTemp | analogInput | Return air temperature | 24.0 | degreesCelsius |
| AHU-01/MixedAirTemp | analogInput | Mixed air temperature | 20.0 | degreesCelsius |
| AHU-01/DuctStaticPressure | analogInput | Duct static pressure | 250.0 | pascals |
| AHU-01/CoolingValve | analogOutput | Cooling coil valve position | 45.0 | percent |
| AHU-01/HeatingValve | analogOutput | Heating coil valve position | 0.0 | percent |
| AHU-01/FanSpeed | analogOutput | Supply fan speed | 75.0 | percent |
| AHU-01/SupplyAirTempSetpoint | analogValue | Supply air temperature setpoint | 22.0 | degreesCelsius |
| AHU-01/DuctPressureSetpoint | analogValue | Duct pressure setpoint | 250.0 | pascals |
| AHU-01/FilterDirty | binaryInput | Filter dirty alarm | false | — |
| AHU-01/SupplyFanEnable | binaryOutput | Supply fan enable command | true | — |
| AHU-01/ReturnFanEnable | binaryOutput | Return fan enable command | true | — |

## FCU-01 — Fan Coil Unit Zone 1

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| FCU-01/RoomTemp | analogInput | Room temperature | 23.0 | degreesCelsius |
| FCU-01/CoolingValve | analogOutput | Cooling valve position | 30.0 | percent |
| FCU-01/HeatingValve | analogOutput | Heating valve position | 0.0 | percent |
| FCU-01/FanSpeed | analogOutput | Fan speed | 50.0 | percent |
| FCU-01/RoomTempSetpoint | analogValue | Room temperature setpoint | 22.0 | degreesCelsius |
| FCU-01/OccupancySensor | binaryInput | Room occupancy | true | — |
| FCU-01/FanEnable | binaryOutput | Fan enable command | true | — |

## FCU-02 — Fan Coil Unit Zone 2

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| FCU-02/RoomTemp | analogInput | Room temperature | 24.0 | degreesCelsius |
| FCU-02/CoolingValve | analogOutput | Cooling valve position | 55.0 | percent |
| FCU-02/HeatingValve | analogOutput | Heating valve position | 0.0 | percent |
| FCU-02/FanSpeed | analogOutput | Fan speed | 60.0 | percent |
| FCU-02/RoomTempSetpoint | analogValue | Room temperature setpoint | 23.0 | degreesCelsius |
| FCU-02/OccupancySensor | binaryInput | Room occupancy | true | — |
| FCU-02/FanEnable | binaryOutput | Fan enable command | true | — |

## TSTAT-01 — Thermostat

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| TSTAT-01/SpaceTemp | analogInput | Space temperature | 22.0 | degreesCelsius |
| TSTAT-01/SpaceHumidity | analogInput | Space relative humidity | 45.0 | percentRelativeHumidity |
| TSTAT-01/CoolingSetpoint | analogValue | Cooling setpoint | 24.0 | degreesCelsius |
| TSTAT-01/HeatingSetpoint | analogValue | Heating setpoint | 21.0 | degreesCelsius |
| TSTAT-01/Mode | multiStateValue | Operating mode (1=Off, 2=Cool, 3=Heat, 4=Auto) | 4 | — |
| TSTAT-01/Occupancy | binaryInput | Space occupancy | true | — |

## ZC-01 — Zone Controller

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| ZC-01/ZoneTemp | analogInput | Zone average temperature | 22.5 | degreesCelsius |
| ZC-01/AirflowRate | analogInput | Zone airflow rate | 500.0 | cubicFeetPerMinute |
| ZC-01/DamperPosition | analogOutput | VAV damper position | 65.0 | percent |
| ZC-01/ReheatValve | analogOutput | Reheat valve position | 0.0 | percent |
| ZC-01/ZoneTempSetpoint | analogValue | Zone temperature setpoint | 22.0 | degreesCelsius |
| ZC-01/MinAirflow | analogValue | Minimum airflow setpoint | 200.0 | cubicFeetPerMinute |
| ZC-01/OccupancySensor | binaryInput | Zone occupancy | true | — |

## OAT-01 — Outdoor Temperature Sensor

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| OAT-01/OutdoorTemp | analogInput | Outdoor air temperature | 15.0 | degreesCelsius |
| OAT-01/OutdoorHumidity | analogInput | Outdoor relative humidity | 60.0 | percentRelativeHumidity |

## CO2-01 — CO2 Sensor

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| CO2-01/CO2Level | analogInput | CO2 concentration | 450.0 | partsPerMillion |
| CO2-01/CO2Setpoint | analogValue | CO2 setpoint for demand ventilation | 800.0 | partsPerMillion |
| CO2-01/HighCO2Alarm | binaryValue | High CO2 alarm | false | — |

## Custom devices

Add a YAML file in `config/devices/`, then restart:

```yaml
device_id: 6001
name: "MY-DEVICE-01"
description: "My custom device"
points:
  - object_type: analogInput
    object_instance: 1
    object_name: "MY-DEVICE-01/Temp"
    description: "Temperature"
    present_value: 22.0
    units: "degreesCelsius"
    cov_increment: 0.5
```

| Family | Input | Output | Value | YAML value |
|---|---|---|---|---|
| Analog | `analogInput` (AI) | `analogOutput` (AO) | `analogValue` (AV) | Finite 32-bit Real; percentages 0–100 |
| Binary | `binaryInput` (BI) | `binaryOutput` (BO) | `binaryValue` (BV) | `true` / `false` |
| Multistate | `multiStateInput` (MSI) | `multiStateOutput` (MSO) | `multiStateValue` (MSV) | Integer `1..len(state_text)` |

Multistate example fields:

```yaml
state_text: ["Off", "Cool", "Heat", "Auto"]
present_value: 4
```

| Configuration rule | Requirement |
|---|---|
| Identity | Unique device IDs/names; unique point names and type/instance pairs within a device; unique effective addresses |
| Instances | 0..4194302 |
| Naming / units | Prefer `DeviceName/PointName`; use BACnet engineering-unit names |
| COV | Optional `cov_increment` sets the real analog object's reporting threshold |
| Default ports | Sequential from 47808, in filename order; [explicit addresses](configuration.md#network-topology) avoid reassignment |
| Restart | YAML replaces inventory/initial values; stale devices/points are removed from SQLite |
| Writes | Outputs/values use priorities; native input writes require Out_Of_Service; HTTP drives the simulated source |

The API returns effective values. Defaults are loopback-only; broadcasts do not cross ports. [Full protocol rules](bacnet-profile.md).
