"""Value rules for writes to a field, by data type. Pure: no I/O, no state.

Messages are the api3 wording (`# api3 NNN`) where an answer records it, else the REST wording,
marked where it stays.
"""

import datetime

from shotgun_api3 import Fault

from .fields import ruby_inspect, ruby_params

READ_ONLY_TYPES = ("uuid", "calculated", "summary", "pivot_column")

# Types whose rules here run before the "None is accepted" shortcut.
NONE_CHECKED_TYPES = READ_ONLY_TYPES + ("jsonb", "checkbox", "multi_entity", "color", "serializable")

# Fields the site sets on a new row and refuses on update (api3 038).
CREATE_ONLY_FIELDS = ("created_at", "updated_at")

INT_MIN, INT_MAX = -(2 ** 31), 2 ** 31 - 1

# field_types/color
LEGACY_COLORS = {
    "blue": "2,149,216", "orange": "253,141,3", "pink": "254,125,179", "red": "253,1,0",
    "green": "29,215,46", "purple": "183,0,188", "grey": "129,129,129", "black": "45,45,45",
}

# api3 035: appended to every Task.color refusal.
TASK_COLOR_HELP = (
    "Unsupported format for Task color field. The Task color can not be nil, the expected format is r,g,b "
    "where the values of r,g and b are in the range 0-255. The value of the color can also be set using the "
    "legacy color strings which are; Blue, Orange, Pink, Red, Green, Purple, Grey and Black. The value can also "
    "be set to the value pipeline_step to indicate that the Gantt bar should render using the color of the "
    "Task's Pipeline Step."
)

# api3 037: the class list of Task.splits, as the site wraps it.
SPLITS_CLASSES = (
    "Hash,\n ActiveSupport::HashWithIndifferentAccess,\n ActionDispatch::Http::Parameters,\n"
    " ActionController::Parameters,\n Array,\n NilClass"
)

_HASH_CLASSES = (
    "Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, "
    "ActionDispatch::Http::ParamsHashWithIndifferentAccess"
)


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
    # api3 031: a newline separates the class from the value.
    return Fault("API %s() %s.%s expected [%s] data type(s) but got %s:\n%s" % (
        verb, entity_type, field, accepted, ruby_class(value), ruby_inspect(value)))


def _echo(field, value):
    """The request hash the site appends to a field refusal (api3 036)."""
    return ruby_params({"field_name": field, "value": value})


def _crud_prefix(verb):
    """The prefix of a refusal raised by the site's storage layer (api3 033)."""
    return "API update() CRUD ERROR #5: " if verb == "update" else "API create() CRUD ERROR #6: "


def _check_range(verb, entity_type, field, value):
    """Refuse an int outside signed 32-bit, as the two verbs word it (api3 033)."""
    if INT_MIN <= value <= INT_MAX:
        return value
    if verb == "create":
        raise Fault(_crud_prefix(verb) + (
            "Create failed for [%s]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n" % entity_type))
    raise Fault(_crud_prefix(verb) + "Update failed for [%s.%s]: Invalid statement." % (entity_type, field))


def _color_reason(value):
    """Why a color string is refused, or None when it is valid (field_types/color)."""
    if value == "":
        return "The value is not a valid color expression: []"  # api3 035
    parts = value.split(",")
    if len(parts) == 1:
        return "Value is not a valid color token: [%s]" % value
    if len(parts) != 3:
        return "The value is not a valid color expression: [%s]" % value
    if not all(part.isdigit() for part in parts):
        return "At least one component value is not valid: [%s]" % value
    if any(int(part) > 255 for part in parts):
        return "At least one component value is out of range: [%s]" % value
    return None


def _task_color_refusal(verb, reason):
    """The Fault for a refused Task.color write (api3 035)."""
    inner = "Update failed for [Task.color]:  (task.rb) %s%s" % (reason, TASK_COLOR_HELP)
    if verb == "create":
        return Fault(_crud_prefix(verb) + "Invalid field value, update failed [5 - %s]" % inner)
    return Fault(_crud_prefix(verb) + inner)


def _color(verb, entity_type, field, value):
    is_task_color = entity_type == "Task" and field == "color"
    if value is None:
        if is_task_color:
            raise _task_color_refusal(verb, "Value cannot be nil for Task.color.")
        return None  # field_types/color: Project.color holds null
    if not isinstance(value, str):
        # REST wording; api3 unprobed (sg-mockgun#39)
        raise _wrong_class(verb, entity_type, field, "String, NilClass", value)
    if value == "pipeline_step":
        return value
    if value.lower() in LEGACY_COLORS:
        return LEGACY_COLORS[value.lower()]
    reason = _color_reason(value)
    if reason is None:
        return value
    if is_task_color:
        raise _task_color_refusal(verb, reason)
    # REST wording; api3 unprobed (sg-mockgun#39)
    raise Fault("%s failed for [%s.%s]: %s" % (verb.capitalize(), entity_type, field, reason))


def _timecode(verb, entity_type, field, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise _wrong_class(verb, entity_type, field, "Integer, NilClass", value)  # api3 035
    return _check_range(verb, entity_type, field, value)


def _jsonb(verb, entity_type, field, value):
    if verb != "create":
        raise Fault("API %s() %s.%s is editable on create only:\n%s" % (
            verb, entity_type, field, _echo(field, value)))  # api3 035
    if value is not None and not isinstance(value, (dict, list, str)):
        # REST wording; api3 unprobed (sg-mockgun#39). api3 035 stores a string.
        raise _wrong_class(verb, entity_type, field, _HASH_CLASSES + ", Array, NilClass", value)
    return value


def _image(verb, entity_type, field, value):
    # The client uploads a non-None image as a file and never sends it (api3 035). This rule covers
    # filmstrip_image and other image fields. REST wording; api3 unprobed (sg-mockgun#39).
    if not isinstance(value, dict):
        raise _wrong_class(verb, entity_type, field, _HASH_CLASSES + ", NilClass", value)
    if "type" not in value:
        raise Fault("API %s() invalid/missing entity hash string 'type': %s" % (verb, ruby_inspect(value)))
    raise Fault("API %s(): Write access of the 'image' data type (%s.%s) not yet supported in API" % (
        verb, entity_type, field))


def _read_only(verb, entity_type, field, value):
    raise Fault("API %s() %s.%s is read only:\n%s" % (verb, entity_type, field, _echo(field, value)))  # api3 036


def _checkbox(verb, entity_type, field, value):
    if isinstance(value, bool):
        return value
    raise _wrong_class(verb, entity_type, field, "FalseClass, TrueClass", value)  # api3 031


def _multi_entity(verb, entity_type, field, value):
    if value is None:
        raise _wrong_class(verb, entity_type, field, "Array", value)  # api3 034
    return value


def _float(verb, entity_type, field, value):
    if not isinstance(value, float):
        raise _wrong_class(verb, entity_type, field, "BigDecimal, Float, NilClass", value)  # api3 032
    return round(value, 6)


def _number(verb, entity_type, field, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise _wrong_class(verb, entity_type, field, "Integer, NilClass", value)  # api3 033
    return _check_range(verb, entity_type, field, value)


def _splits(verb, entity_type, field, value):
    """Task.splits: fewer than two splits store None, two or more are stored (api3 037)."""
    if value is None:
        return None
    if isinstance(value, dict):
        raise Fault(_crud_prefix(verb) + "Update failed for [Task.splits]: no implicit conversion of String into Integer")
    if not isinstance(value, list):
        raise _wrong_class(verb, entity_type, field, SPLITS_CLASSES, value)
    if len(value) < 2:
        return None
    if not all(isinstance(item, dict) and "start" in item and "end" in item for item in value):
        # REST wording; api3 unprobed (sg-mockgun#39)
        raise Fault(_crud_prefix(verb) + "Update failed for [Task.splits]: undefined method '<' for nil")
    return value


def _serializable(verb, entity_type, field, value):
    if entity_type == "Task" and field == "splits":
        return _splits(verb, entity_type, field, value)
    return value


RULES = {
    "color": _color,  # field_types/color
    "timecode": _timecode,  # field_types/timecode
    "jsonb": _jsonb,  # field_types/jsonb
    "image": _image,  # field_types/image
    "checkbox": _checkbox,  # field_types/checkbox
    "multi_entity": _multi_entity,  # field_types/multi_entity
    "float": _float,  # field_types/float
    "number": _number,  # field_types/number
    "serializable": _serializable,  # field_types/serializable
}
RULES.update((data_type, _read_only) for data_type in READ_ONLY_TYPES)  # field_types/<type>, each card


def check_value(verb, entity_type, field, data_type, value, editable=False):
    """Return the value as stored, or raise Fault if the site refuses it.

    verb is "create" or "update". editable is the field's schema flag; an editable summary field
    is refused with its own wording (api3 036). A type with no rule here returns the value unchanged.
    """
    if data_type == "summary" and editable:
        raise Fault("API %s() of data type 'summary' not supported in API" % verb)  # api3 036
    if verb == "update" and field in CREATE_ONLY_FIELDS:
        raise Fault("API update() %s.%s is editable on create only:\n%s" % (
            entity_type, field, _echo(field, utc_iso(value))))  # api3 038
    if field in CREATE_ONLY_FIELDS and isinstance(value, datetime.datetime):
        return value.astimezone(datetime.timezone.utc)  # api3 038: a naive value is local time
    rule = RULES.get(data_type)
    if rule is None or (value is None and data_type not in NONE_CHECKED_TYPES):
        return value
    return rule(verb, entity_type, field, value)


def unknown_field(verb, entity_type, field, value):
    """The Fault for a field name the entity type does not have (api3 039)."""
    return Fault("API %s() %s.%s doesn't exist:\n%s" % (verb, entity_type, field, _echo(field, value)))


def utc_iso(value):
    """A datetime as the client sends it: a naive one is local time, converted to UTC (api3 038)."""
    if not isinstance(value, datetime.datetime):
        return value
    return value.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_row_values(entity_type, fields, user, now, name):
    """The values the site sets on a new row, for the fields the entity type has (api3 038, api3 036)."""
    values = {
        "created_at": now, "updated_at": now,
        "created_by": dict(user), "updated_by": dict(user),
        "cached_display_name": name,
        "open_notes_count": 0,  # api3 036
    }
    if entity_type == "Task":
        values["color"] = "pipeline_step"  # api3 035
    return dict((field, value) for field, value in values.items() if field in fields)
