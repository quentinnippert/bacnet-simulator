"""Explicit BACnet device profile over BACpypes3's local application building blocks."""

from bacpypes3.apdu import (
    ConfirmedServiceChoice,
    UnconfirmedServiceChoice,
    WritePropertyMultipleError,
    confirmed_request_types,
    unconfirmed_request_types,
)
from bacpypes3.app import Application
from bacpypes3.basetypes import (
    ErrorType,
    ObjectPropertyReference,
    ObjectTypesSupported,
    ServicesSupported,
)
from bacpypes3.errors import MissingRequiredParameter, ObjectError, PropertyError
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.primitivedata import ObjectType, PropertyIdentifier

from bacnet_lab.domain.enums import PointType


class ReadOnlyConfiguration:
    async def write_property(self, attr, value, index=None, priority=None):
        attr = PropertyIdentifier(attr).attr
        if attr not in self._elements or getattr(self, attr, None) is None:
            raise PropertyError("unknownProperty")
        raise PropertyError("writeAccessDenied")


class SimulatorDeviceObject(ReadOnlyConfiguration, DeviceObject):
    applicationSoftwareVersion = "0.1.0"

    @property
    def protocolObjectTypesSupported(self):
        return ObjectTypesSupported(
            [
                int(ObjectType(name))
                for name in [p.value for p in PointType] + ["device", "networkPort"]
            ]
        )


class SimulatorNetworkPortObject(ReadOnlyConfiguration, NetworkPortObject):
    """Network configuration is applied at startup, never falsely acknowledged at runtime."""


class SimulatorApplication(Application):
    def get_services_supported(self):
        # 0.0.106 uses ConfirmedServiceChoice for both maps. The namespaces differ.
        supported = ServicesSupported([])
        for choice, requests in (
            (ConfirmedServiceChoice, confirmed_request_types),
            (UnconfirmedServiceChoice, unconfirmed_request_types),
        ):
            for identifier, request in requests.items():
                if hasattr(self, f"do_{request.__name__}"):
                    bit = getattr(supported, choice(identifier).attr)
                    supported[bit] = 1
        return supported

    @staticmethod
    def _default_command_priority(obj, identifier, priority):
        point = getattr(obj, "_point", None)
        if point and point.commandable and identifier == PropertyIdentifier.presentValue:
            return 16 if priority is None else priority
        return priority

    async def do_WritePropertyRequest(self, apdu):
        obj = self.get_object_id(apdu.objectIdentifier)
        if obj is not None and obj.get_property_type(apdu.propertyIdentifier) is None:
            raise PropertyError("unknownProperty")
        # 0.0.106 decodes NULL only when priority is explicit. BACnet defaults to 16.
        apdu.priority = self._default_command_priority(obj, apdu.propertyIdentifier, apdu.priority)
        await super().do_WritePropertyRequest(apdu)

    async def do_WritePropertyMultipleRequest(self, apdu):
        if not apdu.listOfWriteAccessSpecs:
            raise MissingRequiredParameter()
        for specification in apdu.listOfWriteAccessSpecs:
            if not specification.listOfProperties:
                raise MissingRequiredParameter()
            obj = self.get_object_id(specification.objectIdentifier)
            for value in specification.listOfProperties:
                value.priority = self._default_command_priority(
                    obj, value.propertyIdentifier, value.priority
                )
        try:
            await super().do_WritePropertyMultipleRequest(apdu)
        except WritePropertyMultipleError as error:
            # This protocol error inherits BaseException, so the default dispatcher
            # does not send it. Preserve its first-failed-write reference on the wire.
            error.set_context(apdu)
            await self.response(error)
        except ObjectError as error:
            # The all-unknown-object branch also needs this service's error format.
            first = apdu.listOfWriteAccessSpecs[0]
            await self.response(
                WritePropertyMultipleError(
                    errorType=ErrorType(errorClass=error.errorClass, errorCode=error.errorCode),
                    firstFailedWriteAttempt=ObjectPropertyReference(
                        objectIdentifier=first.objectIdentifier,
                        propertyIdentifier=first.listOfProperties[0].propertyIdentifier,
                    ),
                    context=apdu,
                )
            )
