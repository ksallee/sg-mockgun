"""Filter relations per data type, and the pure checks behind them."""

from .fields import ruby_inspect

_NUMERIC = ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
_DATE = [
    "is", "is_not", "greater_than", "less_than", "in_last", "not_in_last", "in_next", "not_in_next",
    "in_calendar_week", "in_calendar_month", "in_calendar_day", "in_calendar_year", "between", "in", "not_in",
]
_CHOICE = ["is", "is_not", "in", "not_in"]

# The `Valid relations` list each data type answers, in the site's order (finding 017,
# field_types/<type>). Entity and multi_entity are not listed here.
RELATIONS = {
    "text": ["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"],
    "number": _NUMERIC,
    "float": _NUMERIC,
    "percent": _NUMERIC,
    "duration": _NUMERIC,
    "timecode": _NUMERIC,
    "date": _DATE,
    "date_time": _DATE,
    "checkbox": ["is", "is_not"],
    "list": _CHOICE,
    "status_list": _CHOICE,
    "entity_type": _CHOICE,
    "color": _CHOICE,
    "uuid": _CHOICE,
    "image": ["is", "is_not"],
    "jsonb": ["is", "is_not", "contains", "not_contains"],
    "pivot_column": ["is", "is_not"],
}

# finding 017
UNFILTERABLE = ("calculated", "password", "serializable", "summary", "url")

# report 008: the site accepts any relation on these jsonb fields and returns every row.
IGNORED = {("PageSetting", "settings_json"), ("EventLogEntry", "audit_trail")}


def filter_refusal(entity_type, field, data_type, operator, rval):
    """The site's error for a filter it refuses, or None when the filter is accepted.

    ``entity_type`` and ``field`` name the last hop of a dotted path. Wording is REST wording;
    api3 is unprobed (sg-mockgun#39).
    """
    path = "%s.%s" % (entity_type, field)
    if data_type in UNFILTERABLE:
        return "API read() %s's '%s' data type cannot be used in a filter." % (path, data_type)
    relations = RELATIONS.get(data_type)
    if relations is None:
        return None
    if operator not in relations:
        return "API read() %s's '%s' data type doesn't support '%s' 'relation'. Valid relations: %s" % (
            path, data_type, operator, ruby_inspect(relations))
    # field_types/pivot_column: both listed relations are refused.
    if data_type == "pivot_column":
        return "API read() of data type 'pivot_column' not supported in API"
    # field_types/number
    if operator == "between" and not (isinstance(rval, list) and len(rval) == 2):
        return "API read() 'between' 'relation' expects a 2-element array: %s" % _values(rval)
    # field_types/uuid
    if operator == "in" and rval == []:
        return "API read() 'in' 'relation' expects at least a 1-element array: []"
    # field_types/checkbox
    if data_type == "checkbox" and rval is None:
        return "API read() %s expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil" % path
    # field_types/uuid
    if data_type == "uuid" and (rval is None or (isinstance(rval, list) and None in rval)):
        return "API read() %s expected [String] data type(s) but got NilClass: nil" % path
    # field_types/image
    if data_type == "image" and rval is not None:
        return "API read() '%s' 'relation' expects a nil value for 'image' data type: %s" % (
            operator, _values(rval))
    return None


def _values(rval):
    """The filter's values as the site echoes them: always an array."""
    return ruby_inspect(rval if isinstance(rval, list) else [rval])


def jsonb_contains(stored, wanted):
    """Whether a stored jsonb value contains ``wanted``, matching objects only at the top (field_types/jsonb)."""
    if not isinstance(stored, dict) or not isinstance(wanted, dict):
        return False
    return _contains(stored, wanted)


def _contains(stored, wanted):
    if isinstance(wanted, dict):
        return isinstance(stored, dict) and all(
            k in stored and _contains(stored[k], v) for k, v in wanted.items())
    if isinstance(wanted, list):
        return isinstance(stored, list) and all(
            any(_contains(s, w) for s in stored) for w in wanted)
    return stored == wanted
