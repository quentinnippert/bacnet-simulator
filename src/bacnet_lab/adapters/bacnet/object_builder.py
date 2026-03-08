from __future__ import annotations

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Point

BACNET_OBJECT_TYPE_MAP = {
    PointType.ANALOG_INPUT: "analogInput",
    PointType.ANALOG_OUTPUT: "analogOutput",
    PointType.ANALOG_VALUE: "analogValue",
    PointType.BINARY_INPUT: "binaryInput",
    PointType.BINARY_OUTPUT: "binaryOutput",
    PointType.BINARY_VALUE: "binaryValue",
    PointType.MULTI_STATE_INPUT: "multiStateInput",
    PointType.MULTI_STATE_OUTPUT: "multiStateOutput",
    PointType.MULTI_STATE_VALUE: "multiStateValue",
}


def build_local_object_config(point: Point) -> dict:
    """Build the configuration dict used by BAC0 to create a local object."""
    obj_type = BACNET_OBJECT_TYPE_MAP.get(point.object_type, point.object_type.value)
    config = {
        "object_type": obj_type,
        "instance": point.object_instance,
        "name": point.object_name,
        "description": point.description,
        "presentValue": point.present_value,
    }
    if point.units:
        config["units"] = point.units
    return config
