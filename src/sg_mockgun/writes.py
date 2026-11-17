"""Value rules for writes to a field, by data type. Pure: no I/O, no state.

Every message is the REST wording; api3 unprobed (sg-groundtruth#109).
"""

import re

from shotgun_api3 import ShotgunError

from .fields import ruby_inspect

READ_ONLY_TYPES = ("uuid", "calculated", "summary", "pivot_column")

# Types whose rules here run before the "None is accepted" shortcut.
NONE_CHECKED_TYPES = READ_ONLY_TYPES + ("jsonb", "checkbox", "multi_entity")

INT_MIN, INT_MAX = -(2 ** 31), 2 ** 31 - 1

# field_types/color
LEGACY_COLORS = {
    "blue": "2,149,216", "orange": "253,141,3", "pink": "254,125,179", "red": "253,1,0",
    "green": "29,215,46", "purple": "183,0,188", "grey": "129,129,129", "black": "45,45,45",
}

_HASH_CLASSES = (
    "Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, "
    "ActionDispatch::Http::ParamsHashWithIndifferentAccess"
)
_NUMERIC = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
_INTEGER = re.compile(r"^[+-]?\d+$")


def ruby_class(value):
    """The Ruby class name the site reports for a JSON value."""
    if value is None:
        return "NilClass"
    if value is True:
        return "TrueClass"
    if value is False:
        return "FalseClass"
    for python_type, name in ((int, "Integer"), (float, "Float"), (str, "String"), (dict, "Hash"), (list, "Array")):
        if isinstance(value, python_type):
            return name
    return type(value).__name__


def _wrong_class(verb, entity_type, field, accepted, value):
    return ShotgunError("API %s() %s.%s expected [%s] data type(s) but got %s: %s" % (
        verb, entity_type, field, accepted, ruby_class(value), ruby_inspect(value)))


def _invalid(data_type, value):
    return ShotgunError("Invalid data for '%s' data type. Value: %s" % (data_type, value))


def _check_range(verb, entity_type, field, value):
    """Refuse an int outside signed 32-bit, as the two verbs word it (field_types/number)."""
    if INT_MIN <= value <= INT_MAX:
        return value
    if verb == "create":
        raise ShotgunError(
            "Create failed for [%s]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n" % entity_type)
    raise ShotgunError("Update failed for [%s.%s]: Invalid statement." % (entity_type, field))


def _color(verb, entity_type, field, value):
    if not isinstance(value, str):
        raise _wrong_class(verb, entity_type, field, "String, NilClass", value)
    if value == "pipeline_step":
        return value
    if value.lower() in LEGACY_COLORS:
        return LEGACY_COLORS[value.lower()]
    prefix = "%s failed for [%s.%s]: " % (verb.capitalize(), entity_type, field)
    parts = value.split(",")
    if len(parts) == 1:
        raise ShotgunError(prefix + "Value is not a valid color token: [%s]" % value)
    if len(parts) != 3:
        raise ShotgunError(prefix + "The value is not a valid color expression: [%s]" % value)
    if not all(part.isdigit() for part in parts):
        raise ShotgunError(prefix + "At least one component value is not valid: [%s]" % value)
    if any(int(part) > 255 for part in parts):
        raise ShotgunError(prefix + "At least one component value is out of range: [%s]" % value)
    return value


def _timecode(verb, entity_type, field, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise _wrong_class(verb, entity_type, field, "Integer, NilClass", value)
    return _check_range(verb, entity_type, field, value)


def _jsonb(verb, entity_type, field, value):
    if verb != "create":
        raise ShotgunError("API %s() %s.%s is editable on create only." % (verb, entity_type, field))
    if value is not None and not isinstance(value, (dict, list)):
        raise _wrong_class(verb, entity_type, field, _HASH_CLASSES + ", Array, NilClass", value)
    return value


def _image(verb, entity_type, field, value):
    if not isinstance(value, dict):
        raise _wrong_class(verb, entity_type, field, _HASH_CLASSES + ", NilClass", value)
    if "type" not in value:
        raise ShotgunError("API %s() invalid/missing entity hash string 'type': %s" % (verb, ruby_inspect(value)))
    raise ShotgunError("API %s(): Write access of the 'image' data type (%s.%s) not yet supported in API" % (
        verb, entity_type, field))


def _read_only(verb, entity_type, field, value):
    raise ShotgunError("API %s() %s.%s is read only." % (verb, entity_type, field))


def _checkbox(verb, entity_type, field, value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value in ("true", "false"):
            return value == "true"
        raise _invalid("checkbox", value)
    raise _wrong_class(verb, entity_type, field, "String, FalseClass, TrueClass", value)


def _multi_entity(verb, entity_type, field, value):
    if value is None:
        raise _wrong_class(verb, entity_type, field, "Array, Hash", value)
    return value


def _float(verb, entity_type, field, value):
    if isinstance(value, str):
        if not _NUMERIC.match(value.strip()):
            raise _invalid("float", value)
        value = float(value.strip())
    elif not isinstance(value, float):
        raise _wrong_class(verb, entity_type, field, "String, BigDecimal, Float, NilClass", value)
    return round(value, 6)


def _number(verb, entity_type, field, value):
    if isinstance(value, str):
        if not _INTEGER.match(value):
            raise _invalid("number", value)
        value = int(value)
    elif not isinstance(value, int) or isinstance(value, bool):
        raise _wrong_class(verb, entity_type, field, "String, Integer, NilClass", value)
    return _check_range(verb, entity_type, field, value)


RULES = {
    "color": _color,  # field_types/color
    "timecode": _timecode,  # field_types/timecode
    "jsonb": _jsonb,  # field_types/jsonb
    "image": _image,  # field_types/image
    "checkbox": _checkbox,  # field_types/checkbox
    "multi_entity": _multi_entity,  # field_types/multi_entity
    "float": _float,  # field_types/float
    "number": _number,  # field_types/number
}
RULES.update((data_type, _read_only) for data_type in READ_ONLY_TYPES)  # field_types/<type>, each card


def check_value(verb, entity_type, field, data_type, value):
    """Return the value as stored, or raise ShotgunError if the site refuses it.

    verb is "create" or "update". A type with no rule here returns the value unchanged.
    """
    rule = RULES.get(data_type)
    if rule is None or (value is None and data_type not in NONE_CHECKED_TYPES):
        return value
    return rule(verb, entity_type, field, value)
