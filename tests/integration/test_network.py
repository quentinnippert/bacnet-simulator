"""Real UDP interoperability. Run explicitly with BACNET_LAB_NETWORK_TESTS=1."""

import asyncio
import os
import socket
from contextlib import asynccontextmanager

import pytest
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.pdu import Address, IPv4Address
from bacpypes3.primitivedata import ObjectIdentifier

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.bacnet.engine import BACnetEngine
from bacnet_lab.domain.enums import PointType

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.getenv("BACNET_LAB_NETWORK_TESTS") != "1",
        reason="Opt in to local UDP tests with BACNET_LAB_NETWORK_TESTS=1",
    ),
]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def network():
    engine = BACnetEngine("127.0.0.1", prefix=32)
    devices = load_all_devices("config/devices")
    client = None
    try:
        for device in devices:
            await engine.start_device(device, free_port())
        client = Application.from_object_list(
            [
                DeviceObject(
                    objectIdentifier=("device", 999999),
                    objectName="Test client",
                    vendorIdentifier=999,
                ),
                NetworkPortObject(
                    IPv4Address(f"127.0.0.1/32:{free_port()}"),
                    objectIdentifier=("networkPort", 1),
                    objectName="client network",
                ),
            ]
        )
        await asyncio.gather(
            *(task for link in client.link_layers.values() for task in link.server._transport_tasks)
        )
        yield engine, devices, client
    finally:
        if client:
            client.close()
        await engine.stop_all()


@pytest.mark.asyncio
async def test_all_devices_discovery_reads_writes_priorities_and_independent_restart():
    async with network() as (engine, devices, client):
        for device in devices:
            address = Address(str(device.address))
            found = await client.who_is(address=address, timeout=0.15)
            assert [int(r.iAmDeviceIdentifier[1]) for r in found] == [device.device_id]
            first = device.points[0]
            value = await asyncio.wait_for(
                client.read_property(address, first.object_identifier, "presentValue"), 2
            )
            assert value == first.present_value
        target = devices[0]
        address = Address(str(target.address))
        await client.write_property(address, "analogOutput,1", "presentValue", 88, priority=8)
        await engine.write_point_value(1001, PointType.ANALOG_OUTPUT, 1, 55)
        assert await engine.read_point_value(1001, PointType.ANALOG_OUTPUT, 1) == 88
        await engine.write_point_value(1001, PointType.ANALOG_OUTPUT, 1, None, priority=8)
        assert await client.read_property(address, "analogOutput,1", "presentValue") == 55
        result = await client.read_property_multiple(
            address, ["analogInput,1", ["presentValue", "covIncrement"]]
        )
        assert len(result) == 2 and result[1][3] == 0.5
        with pytest.raises(ErrorRejectAbortNack):
            await client.write_property(address, "analogOutput,1", "presentValue", 101)
        for _ in range(2):
            await engine.stop_device(target.device_id)
            assert await client.who_is(address=address, timeout=0.1) == []
            other = devices[1]
            assert (
                await client.read_property(
                    str(other.address), other.points[0].object_identifier, "presentValue"
                )
                == other.points[0].present_value
            )
            await engine.start_device(target, target.address.port)
            assert await client.read_property(address, "analogOutput,1", "presentValue") == 55
        thermostat = next(d for d in devices if d.device_id == 3001)
        assert (
            await client.read_property(
                str(thermostat.address), "multiStateValue,1", "numberOfStates"
            )
            == 4
        )


@pytest.mark.asyncio
async def test_cov_threshold_binary_and_multistate_notifications():
    async with network() as (engine, devices, client):
        address = Address(str(devices[0].address))
        async with client.change_of_value(
            address, ObjectIdentifier("analogInput,1"), lifetime=30
        ) as subscription:

            async def next_value():
                while True:
                    prop, value = await subscription.get_value()
                    if str(prop) == "present-value":
                        return value

            assert await asyncio.wait_for(next_value(), 1) == 22.5
            await engine.write_point_value(1001, PointType.ANALOG_INPUT, 1, 22.6)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(next_value(), 0.1)
            await engine.write_point_value(1001, PointType.ANALOG_INPUT, 1, 23.1)
            assert await asyncio.wait_for(next_value(), 1) == pytest.approx(23.1)
        thermostat = next(d for d in devices if d.device_id == 3001)
        async with client.change_of_value(
            Address(str(thermostat.address)), ObjectIdentifier("multiStateValue,1"), lifetime=30
        ) as subscription:

            async def next_state():
                while True:
                    prop, value = await subscription.get_value()
                    if str(prop) == "present-value":
                        return value

            assert await asyncio.wait_for(next_state(), 1) == 4
            await engine.write_point_value(3001, PointType.MULTI_STATE_VALUE, 1, 2)
            assert await asyncio.wait_for(next_state(), 1) == 2
        async with client.change_of_value(
            address, ObjectIdentifier("binaryOutput,1"), lifetime=30
        ) as subscription:

            async def next_binary():
                while True:
                    prop, value = await subscription.get_value()
                    if str(prop) == "present-value":
                        return int(value)

            initial = await asyncio.wait_for(next_binary(), 1)
            await engine.write_point_value(1001, PointType.BINARY_OUTPUT, 1, not bool(initial))
            assert await asyncio.wait_for(next_binary(), 1) == 1 - initial


@pytest.mark.asyncio
async def test_wire_profile_rejections_default_null_and_device_metadata():
    from bacpypes3.apdu import WritePropertyRequest
    from bacpypes3.constructeddata import Any
    from bacpypes3.primitivedata import CharacterString, Null, Real

    async with network() as (engine, devices, client):
        address = Address(str(devices[0].address))
        types = await client.read_property(address, "device,1001", "protocolObjectTypesSupported")
        assert types[0] and types[19] and types[56] and not types[17]
        objects = await client.read_property(address, "device,1001", "objectList")
        assert len(objects) == len(devices[0].points) + 2
        for prop, value, priority, index, code in [
            ("presentValue", Real(80), 6, None, "write-access-denied"),
            ("presentValue", Real(80), 8, 1, "property-is-not-an-array"),
            ("presentValue", Real(80), 0, None, "value-out-of-range"),
            ("relinquishDefault", Real(101), None, None, "value-out-of-range"),
            ("objectName", CharacterString("changed"), None, None, "write-access-denied"),
            (512, Real(1), None, None, "unknown-property"),
        ]:
            request = WritePropertyRequest(
                objectIdentifier=("analogOutput", 1),
                propertyIdentifier=prop,
                propertyValue=Any(value),
                destination=address,
            )
            if priority is not None:
                request.priority = priority
            if index is not None:
                request.propertyArrayIndex = index
            with pytest.raises(ErrorRejectAbortNack) as caught:
                await asyncio.wait_for(client.request(request), 2)
            assert str(caught.value.errorCode) == code
        await client.write_property(address, "analogOutput,1", "presentValue", 60)
        request = WritePropertyRequest(
            objectIdentifier=("analogOutput", 1),
            propertyIdentifier="presentValue",
            propertyValue=Any(Null(())),
            destination=address,
        )
        await asyncio.wait_for(client.request(request), 2)
        assert await client.read_property(address, "analogOutput,1", "presentValue") == 45


@pytest.mark.asyncio
async def test_out_of_service_emits_status_cov_and_isolates_sensor_updates():
    async with network() as (engine, devices, client):
        address = Address(str(devices[0].address))
        with pytest.raises(ErrorRejectAbortNack):
            await client.write_property(address, "analogInput,1", "presentValue", 66)
        async with client.change_of_value(
            address, ObjectIdentifier("analogInput,1"), lifetime=30
        ) as subscription:

            async def next_flags():
                while True:
                    prop, value = await subscription.get_value()
                    if str(prop) == "status-flags":
                        return list(value)

            assert await asyncio.wait_for(next_flags(), 1) == [0, 0, 0, 0]
            await client.write_property(address, "analogInput,1", "outOfService", True)
            assert await asyncio.wait_for(next_flags(), 1) == [0, 0, 0, 1]
            await client.write_property(address, "analogInput,1", "presentValue", 66)
            await engine.write_point_value(1001, PointType.ANALOG_INPUT, 1, 18)
            assert await client.read_property(address, "analogInput,1", "presentValue") == 66
            await client.write_property(address, "analogInput,1", "outOfService", False)
            assert await client.read_property(address, "analogInput,1", "presentValue") == 18
            assert list(await client.read_property(address, "analogInput,1", "statusFlags")) == [
                0,
                0,
                0,
                0,
            ]


@pytest.mark.asyncio
async def test_read_property_with_independently_encoded_udp_frame():
    """A fixed wire exchange avoids sharing the server's codec with the test client."""
    async with network() as (_, devices, __):
        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.setblocking(False)
            # BVLC unicast, NPDU expecting reply, confirmed ReadProperty, AI:1/PV.
            request = bytes.fromhex("810a0011010400054d0c0c000000011955")
            await loop.sock_sendto(sock, request, (devices[0].address.ip, devices[0].address.port))
            response, peer = await asyncio.wait_for(loop.sock_recvfrom(sock, 2048), 2)
            assert peer[1] == devices[0].address.port
            assert response[:2] == bytes.fromhex("810a")
            assert int.from_bytes(response[2:4], "big") == len(response)
            # Complex ACK; REAL 22.5 encoded as IEEE754 0x41b40000.
            assert response[4:] == bytes.fromhex("0100304d0c0c0000000119553e4441b400003f")


@pytest.mark.asyncio
async def test_native_writes_change_slot_revision_even_when_effective_value_does_not_change():
    async with network() as (engine, devices, client):
        address = Address(str(devices[0].address))
        revision = await engine.write_point_value(1001, PointType.ANALOG_OUTPUT, 1, 80, 8)
        await client.write_property(address, "analogOutput,1", "presentValue", 80, priority=8)
        value, newer_revision = await engine.read_control_state(1001, PointType.ANALOG_OUTPUT, 1, 8)
        assert value == 80 and newer_revision > revision
        await client.write_property(address, "analogOutput,1", "presentValue", 90, priority=4)
        assert await engine.read_control_state(1001, PointType.ANALOG_OUTPUT, 1, 8) == (
            80,
            newer_revision,
        )
        services = await client.read_property(address, "device,1001", "protocolServicesSupported")
        for name in [
            "whoIs",
            "whoHas",
            "iAm",
            "iHave",
            "readProperty",
            "writeProperty",
            "subscribeCOV",
        ]:
            assert services[getattr(services, name)] == 1
        for name in [
            "acknowledgeAlarm",
            "confirmedEventNotification",
            "atomicWriteFile",
            "addListElement",
        ]:
            assert services[getattr(services, name)] == 0


@pytest.mark.asyncio
async def test_write_property_multiple_preserves_order_and_default_relinquish():
    from bacpypes3.apdu import WritePropertyMultipleRequest
    from bacpypes3.basetypes import PropertyValue, WriteAccessSpecification
    from bacpypes3.constructeddata import Any
    from bacpypes3.primitivedata import Null, Real

    async with network() as (_, devices, client):
        address = Address(str(devices[0].address))

        async def write_many(values, identifier=("analogOutput", 1)):
            request = WritePropertyMultipleRequest(
                listOfWriteAccessSpecs=[
                    WriteAccessSpecification(
                        objectIdentifier=identifier,
                        listOfProperties=values,
                    )
                ],
                destination=address,
            )
            await asyncio.wait_for(client.request(request), 2)

        await write_many([PropertyValue(propertyIdentifier="presentValue", value=Any(Real(60)))])
        await write_many([PropertyValue(propertyIdentifier="presentValue", value=Any(Null(())))])
        assert await client.read_property(address, "analogOutput,1", "presentValue") == 45
        with pytest.raises(ErrorRejectAbortNack) as caught:
            await write_many(
                [
                    PropertyValue(propertyIdentifier="presentValue", value=Any(Real(70))),
                    PropertyValue(
                        propertyIdentifier="presentValue", value=Any(Real(80)), priority=6
                    ),
                ]
            )
        assert str(caught.value.errorType.errorCode) == "write-access-denied"
        # WPM executes in order; it is not an all-or-nothing transaction.
        assert await client.read_property(address, "analogOutput,1", "presentValue") == 70

        with pytest.raises(ErrorRejectAbortNack) as caught:
            await write_many(
                [PropertyValue(propertyIdentifier="presentValue", value=Any(Real(60)))],
                identifier=("analogOutput", 999),
            )
        assert str(caught.value.errorType.errorCode) == "unknown-object"
