# Devices

BACnet Lab simulates 8 HVAC devices with 80 BACnet points. Default devices use separate UDP ports and directed discovery.

## Device Overview

| Device | ID | UDP Port | Points | Location |
|--------|----|----------|--------|----------|
| AHU-01 | 1001 | 47808 | 26 | Supply Air Handling Unit |
| FCU-01 | 2001 | 47810 | 7 | Zone 1 (Office North) |
| FCU-02 | 2002 | 47811 | 7 | Zone 2 (Office South) |
| TSTAT-01 | 3001 | 47813 | 6 | Lobby |
| ZC-01 | 4001 | 47814 | 7 | Open Plan Area |
| OAT-01 | 5001 | 47812 | 2 | Outdoor |
| CO2-01 | 5002 | 47809 | 3 | Conference Room |
| SF-01 | 6001 | 47815 | 22 | Supply Ventilation |

## AHU-01 — Air Handling Unit

| Point Name | Object Type | Description | Default | Units |
|------------|-------------|-------------|---------|-------|
| AHU-01/SupplyAirTemp | analogInput | Supply air temperature | 22.5 | degreesCelsius |
| AHU-01/ElectricalPower | analogInput | Estimated supply fan electrical power (fan-only) | 4.22 | kilowatts |
| AHU-01/FilterDifferentialPressure | analogInput | Filter differential pressure (FI-01) | 75.0 | pascals |
| AHU-01/FanSpeedFeedback | analogInput | Supply fan VFD speed feedback | 75.0 | percent |
| AHU-01/CoolingValve | analogOutput | Cooling coil valve position | 45.0 | percent |
| AHU-01/HeatingValve | analogOutput | Heating coil valve position | 0.0 | percent |
| AHU-01/FanSpeed | analogOutput | Supply fan VFD speed command | 75.0 | percent |
| AHU-01/OutdoorAirDamper | analogOutput | Modulating outdoor air damper command | 100.0 | percent |
| AHU-01/SupplyAirTempSetpoint | analogValue | Supply air temperature setpoint | 22.0 | degreesCelsius |
| AHU-01/FanRunStatus | binaryInput | Supply fan run status feedback | true | — |
| AHU-01/FanFault | binaryInput | Supply fan fault status | false | — |
| AHU-01/FireAlarmStatus | binaryInput | Fire alarm interlock status | false | — |
| AHU-01/SupplyFanEnable | binaryOutput | Supply fan enable command | true | — |
| AHU-01/ReturnWaterTemp | analogInput | Heating coil return water temperature | 20.0 | degreesCelsius |
| AHU-01/IntakeAirflow | analogInput | Intake airflow as a percentage of design flow | 0.0 | percent |
| AHU-01/HeatingPower | analogInput | Estimated heating power from the energy meter model | 0.0 | kilowatts |
| AHU-01/HeatingEnergy | analogInput | Accumulated estimated heating energy | 0.0 | kilowattHours |
| AHU-01/ReturnWaterTempSetpoint | analogValue | Heating coil return temperature target while stopped | 20.0 | degreesCelsius |
| AHU-01/ReturnWaterMinimumSetpoint | analogValue | Minimum heating coil return temperature while operating | 12.0 | degreesCelsius |
| AHU-01/ServiceSwitch | binaryInput | Service switch status | false | — |
| AHU-01/ExternalStop | binaryInput | External stop signal | false | — |
| AHU-01/HeatingPumpFault | binaryInput | Heating circulation pump fault status | false | — |
| AHU-01/FreezeProtectionAlarm | binaryInput | Latched heating coil frost protection alarm | false | — |
| AHU-01/ReturnWaterControlActive | binaryInput | Return water temperature controller override active | false | — |
| AHU-01/HeatingPumpRunStatus | binaryInput | Heating circulation pump run feedback | false | — |
| AHU-01/HeatingPumpEnable | binaryOutput | Heating circulation pump command | false | — |

The bundled AHU inventory contains only unit-related points shared by the `cleanroom_ahu` and `seal_ahu` scenarios. External room pressure and outdoor humidity sensors are not part of AHU-01; it also has no return-air or mixed-air sensor. Intake airflow, the intake damper, and safety interlocks remain part of the unit. `ElectricalPower` is an estimate updated by the HVAC Day/Night and Supply AHU Control scenarios using `rated_power × (fan_speed / 100)^3`. Both assume a 10 kW rated supply fan by default; change `fan_rated_power_kw` to use another rating. This is fan-only power, not total AHU or plant energy, and is not a measured value.

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

## SF-01 - Supply Fan Controller

Device instance **6001**, default UDP port **47815**. The file
`config/devices/zone_supply_fan_01.yaml` sorts after the existing inventory,
preserving all seven existing port assignments. Like other default devices, it
uses the configured BACnet IP and sequential port allocation from `port_start`.

Each row below represents one point, prefixed with `SF-01/Supply`
(for example, `SF-01/SupplyFanSpeed`). There are no exhaust points.

| Point suffix | Object type | Default | Units |
|---|---|---|---|
| FanSpeed | analogOutput | 60 | percent |
| DamperPosition | analogOutput | 100 | percent |
| FanEnable | binaryOutput | true | - |
| FanFaultReset | binaryOutput | false | - |
| FanSpeedFeedback | analogInput | 60 | percent |
| Airflow | analogInput | 1200 | cubicFeetPerMinute |
| DuctPressure | analogInput | 250 | pascals |
| FanCurrent | analogInput | 4.5 | amperes |
| FanElectricalPower | analogInput | 2.16 | kilowatts |
| FanElectricalEnergy | analogInput | 0 | kilowattHours |
| FanRuntime | analogInput | 0 | hours |
| FanRunStatus | binaryInput | true | - |
| FanFault | binaryInput | false | - |
| AirflowProof | binaryInput | true | - |
| DamperOpenStatus | binaryInput | true | - |
| FanLocalOverride | binaryInput | false | - |
| DuctPressureSetpoint | analogValue | 250 | pascals |
| AirflowSetpoint | analogValue | 1200 | cubicFeetPerMinute |

Controller-wide points use the `SF-01/` prefix:

| Point | Object type | Default | States |
|---|---|---|---|
| Mode | multiStateValue | 2 | 1=Off, 2=SupplyOnly |
| FireAlarmStatus | binaryInput | false | - |
| ExternalStop | binaryInput | false | - |
| ServiceSwitch | binaryInput | false | - |

All points expose the standard simulator BACnet properties, including descriptions,
status flags and Out_Of_Service. Analog points include units and COV increments;
commandable outputs/values include priority arrays and relinquish defaults.
These are independently controllable simulated points, not an automatic fan
sequence: enable, reset, mode and interlock writes do not drive feedback, alarms,
energy or runtime. Use HTTP point writes or manual overrides to set simulated
feedback; native BACnet input writes require Out_Of_Service.

## Custom devices

Add a YAML file in `config/devices/`, then restart:

```yaml
device_id: 7001
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
