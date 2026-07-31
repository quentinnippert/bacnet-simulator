from types import SimpleNamespace

import pytest
from bacpypes3.basetypes import HostNPort
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.pdu import IPv4Address
from bacpypes3.primitivedata import PropertyIdentifier
from bacpypes3.service.object import read_property_to_result_element

from bacnet_lab.adapters.bacnet.engine import _remove_invalid_fd_bbmd_address


def _make_bac0_instance(fd_bbmd_address: HostNPort):
    network_port = NetworkPortObject(
        IPv4Address("127.0.0.1/24:47808"),
        objectIdentifier=("networkPort", 1),
        objectName="NetworkPort-1",
        fdBBMDAddress=fd_bbmd_address,
    )
    application = SimpleNamespace(
        get_object_name=lambda object_name: (
            network_port if object_name == "NetworkPort-1" else None
        )
    )
    instance = SimpleNamespace(
        this_application=SimpleNamespace(app=application),
    )
    return instance, network_port


@pytest.mark.asyncio
async def test_removes_invalid_fd_bbmd_address():
    instance, network_port = _make_bac0_instance(HostNPort(None))

    with pytest.raises(AttributeError, match="host is a required element"):
        network_port.fdBBMDAddress.encode()

    _remove_invalid_fd_bbmd_address(instance)

    result = await read_property_to_result_element(
        network_port,
        PropertyIdentifier("fdBBMDAddress"),
    )
    error = result.readResult.propertyAccessError
    assert error is not None
    assert str(error.errorClass) == "property"
    assert str(error.errorCode) == "unknown-property"


def test_preserves_valid_fd_bbmd_address():
    instance, network_port = _make_bac0_instance(HostNPort("192.0.2.10:47808"))

    _remove_invalid_fd_bbmd_address(instance)

    assert network_port.fdBBMDAddress.host is not None
    network_port.fdBBMDAddress.encode()
