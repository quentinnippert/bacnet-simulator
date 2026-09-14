"""Construct independent BACpypes3 objects; no process-wide factory registry."""

from __future__ import annotations

from bacpypes3.errors import PropertyError
from bacpypes3.local.analog import AnalogInputObject, AnalogOutputObject, AnalogValueObject
from bacpypes3.local.binary import BinaryInputObject, BinaryOutputObject, BinaryValueObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.cov import COVIncrementCriteria, GenericCriteria
from bacpypes3.local.multistate import (
    MultiStateInputObject,
    MultiStateOutputObject,
    MultiStateValueObject,
)
from bacpypes3.primitivedata import Null, PropertyIdentifier

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.errors import ValidationError
from bacnet_lab.domain.models.device import Point


class StatusFlagsCOV:
    def send_cov_notifications(self, subscription=None):
        # Computed flags are not a stored property; refresh the criteria snapshot.
        self.statusFlags = self.obj.statusFlags
        super().send_cov_notifications(subscription)


class AnalogCOV(StatusFlagsCOV, COVIncrementCriteria):
    # statusFlags is computed by BACpypes; track its mutable source as well.
    properties_tracked = COVIncrementCriteria.properties_tracked + ("outOfService",)


class DiscreteCOV(StatusFlagsCOV, GenericCriteria):
    properties_tracked = GenericCriteria.properties_tracked + ("outOfService",)


class ValidatedObject:
    """The writable-property contract of this simulator's point objects.

    BACpypes supplies encoding, priority arbitration and COV. This profile owns
    permissions, engineering ranges and the boundary with simulated sensors.
    Configuration/identity properties stay defined by YAML for the whole run.
    """

    async def write_property(self, attr, value, index=None, priority=None):
        attr = PropertyIdentifier(attr).attr
        if attr not in self._elements or getattr(self, attr, None) is None:
            raise PropertyError("unknownProperty")
        writable = {"presentValue", "outOfService"}
        if self._point.commandable:
            writable.add("relinquishDefault")
        if attr not in writable:
            raise PropertyError("writeAccessDenied")
        if index is not None:
            raise PropertyError("propertyIsNotAnArray")
        if priority is not None and not 1 <= priority <= 16:
            raise PropertyError("valueOutOfRange")
        if attr == "presentValue" and self._point.commandable and priority == 6:
            raise PropertyError("writeAccessDenied")
        if attr == "presentValue" and not self._point.commandable and not self.outOfService:
            raise PropertyError("writeAccessDenied")
        if isinstance(value, Null):
            if attr != "presentValue" or not self._point.commandable:
                raise PropertyError("invalidDataType")
        elif attr in {"presentValue", "relinquishDefault"}:
            kind = self._point.object_type.value
            raw = int(value) if kind.startswith(("binary", "multiState")) else float(value)
            if kind.startswith("binary"):
                if raw not in (0, 1):
                    raise PropertyError("valueOutOfRange")
                raw = bool(raw)
            try:
                self._point.validate_value(raw)
            except ValidationError as exc:
                raise PropertyError("valueOutOfRange") from exc
        if attr == "outOfService":
            # Use the local setter so COV monitors see this status transition.
            self.outOfService = value
            if not value and not self._point.commandable:
                self.presentValue = self._sensor_value
        elif attr == "relinquishDefault":
            self.relinquishDefault = value
            self.recalculating()
        else:
            await super().write_property(attr, value, index, priority)
            if self._point.commandable:
                slot = 16 if priority is None else priority
                self._write_revisions[slot] = self._write_revisions.get(slot, 0) + 1

    def update_sensor(self, value):
        """Physical input changes continue while OOS, but are not exposed until rejoined."""
        self._sensor_value = value
        self._sensor_revision += 1
        if not self.outOfService:
            self.presentValue = value


class AnalogInput(ValidatedObject, AnalogInputObject):
    _cov_criteria = AnalogCOV


class BinaryInput(ValidatedObject, BinaryInputObject):
    _cov_criteria = DiscreteCOV


class MultiStateInput(ValidatedObject, MultiStateInputObject):
    _cov_criteria = DiscreteCOV


class AnalogValue(ValidatedObject, Commandable, AnalogValueObject):
    _cov_criteria = AnalogCOV


class BinaryValue(ValidatedObject, Commandable, BinaryValueObject):
    _cov_criteria = DiscreteCOV


class MultiStateValue(ValidatedObject, Commandable, MultiStateValueObject):
    _cov_criteria = DiscreteCOV


class MultiStateOutput(ValidatedObject, MultiStateOutputObject):
    _cov_criteria = DiscreteCOV


class AnalogOutput(ValidatedObject, AnalogOutputObject):
    _cov_criteria = AnalogCOV


class BinaryOutput(ValidatedObject, BinaryOutputObject):
    _cov_criteria = DiscreteCOV


OBJECT_CLASSES = {
    PointType.ANALOG_INPUT: AnalogInput,
    PointType.ANALOG_OUTPUT: AnalogOutput,
    PointType.ANALOG_VALUE: AnalogValue,
    PointType.BINARY_INPUT: BinaryInput,
    PointType.BINARY_OUTPUT: BinaryOutput,
    PointType.BINARY_VALUE: BinaryValue,
    PointType.MULTI_STATE_INPUT: MultiStateInput,
    PointType.MULTI_STATE_OUTPUT: MultiStateOutput,
    PointType.MULTI_STATE_VALUE: MultiStateValue,
}


def build_local_object(point: Point):
    properties = dict(
        objectIdentifier=(point.object_type.value, point.object_instance),
        objectName=point.object_name,
        description=point.description,
        presentValue=("active" if point.present_value else "inactive")
        if point.object_type.value.startswith("binary")
        else point.present_value,
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        reliability="no-fault-detected",
    )
    if point.object_type.value.startswith("analog"):
        properties.update(units=point.units or "noUnits", covIncrement=point.cov_increment)
    elif point.object_type.value.startswith("multiState"):
        properties.update(stateText=point.state_text, numberOfStates=len(point.state_text))
    elif point.object_type in (PointType.BINARY_INPUT, PointType.BINARY_OUTPUT):
        properties["polarity"] = "normal"
    obj = OBJECT_CLASSES[point.object_type](**properties)
    obj._point = point
    obj._sensor_value = obj.presentValue
    obj._sensor_revision = 0
    obj._write_revisions = {}
    return obj
