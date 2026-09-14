# BACnet profile

Laboratory profile on **BACpypes3 0.0.106**; not a PICS or BTL certification.

## Protocol contract

| Area | Support / rule |
|---|---|
| Network | BACnet/IP over IPv4; independent address/application per device |
| Discovery | Who-Is/I-Am, Who-Has/I-Have; default ports require directed discovery |
| Inventory | Object_List, Property_List, supported object types and services |
| Objects | Analog/binary/multistate Input, Output and Value; Device; Network Port |
| Properties | ReadProperty, ReadPropertyMultiple, WriteProperty, WritePropertyMultiple |
| Commands | Outputs/values: 16 slots; default priority 16; 6 reserved; NULL releases a slot |
| Relinquish_Default | Writable within range; recalculates value without overriding commands |
| COV | Analog thresholds, discrete changes and status changes |
| Multiple writes | Applied in order; first error reported; preceding writes remain applied |

### Writable properties

| Property | Permission |
|---|---|
| Present_Value | Outputs/values: commandable; inputs: only with Out_Of_Service=true |
| Out_Of_Service | Writable on points |
| Relinquish_Default | Commandable points only |
| Other configured properties | Read-only, including Device/Network Port configuration |
| Absent property | UNKNOWN_PROPERTY |

```text
Input in service:      simulated source ──► Present_Value
Input out of service:  simulated source     Present_Value ◄── BACnet test write
Back in service:       latest source ─────► Present_Value
```

HTTP/scenarios update the simulated source. [ASHRAE reference](https://bacnet.org/wp-content/uploads/sites/4/2022/08/Add-135-2016bl.pdf).

- Analog values/COV thresholds: finite 32-bit Real; multistate: `1..Number_Of_States`.
- Percent range `0..100` is a **simulator policy**, not a universal BACnet rule.
- Overrides restore only when no later command replaced their slot, including same-value writes. Internal write revisions are not BACnet properties. [Scenario rules](scenarios.md).

## BACpypes3 compatibility

No dependency fork. These application adaptations must be rechecked before upgrading:

| Gap in 0.0.106 | Adapter responsibility |
|---|---|
| Permissive local objects | Enforce this profile's permissions/ranges; retain native priority arbitration |
| Empty supported-object bitmap | Announce supported object types |
| Wrong namespace for unconfirmed-service bits | Compute confirmed/unconfirmed capabilities separately |
| NULL decoded only with explicit priority | Resolve omitted command priority to 16 |
| Multiple-write errors not sent / wrong format | Send the structured error with request context and failed-write reference, including unknown objects |
| Computed Status_Flags not independently monitored | Track Out_Of_Service and refresh COV flags |
| No public async readiness/complete close | Isolated `_transport_tasks` and subscription cleanup in the engine |

Upstream service/decoding fixes and public `ready()/aclose()` APIs would remove the corresponding adaptations.

## Scope and verification

| Boundary | What to expect |
|---|---|
| Default discovery | Ports 47808–47814; broadcasts do not cross ports |
| Same-port LAN discovery | Provision distinct host IPs and correct subnet; no alias creation or broadcast relay. [Setup](configuration.md#network-topology) |
| Not implemented | Runtime network reconfiguration, DeviceCommunicationControl, ReinitializeDevice, native alarms/events, schedules, trends, routing/BBMD, BACnet/SC |
| Vendor ID 999 | Reserved ASHRAE sample identity, **not assigned to this project**. [Official list](https://bacnet.org/assigned-vendor-ids/) |
| Verified | UDP reads/writes/errors, priorities, NULL, ordered multiple writes, COV, independent restarts; one independently encoded ReadProperty frame |
| Still required for deployment | Target-LAN and third-party BMS testing; tests do not establish [BACnet conformance](https://bacnet.org/conformance-pics/) |

Keep this profile on a lab network. Application alarms are webhook/application events, not BACnet intrinsic reporting.
