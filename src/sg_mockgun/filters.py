"""Filter relations per data type, and the pure checks behind them."""

import datetime

from .fields import ruby_inspect, ruby_pp

_NUMERIC = ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
_DATE = [
    "is", "is_not", "greater_than", "less_than", "in_last", "not_in_last", "in_next", "not_in_next",
    "in_calendar_week", "in_calendar_month", "in_calendar_day", "in_calendar_year", "between", "in", "not_in",
]
_CHOICE = ["is", "is_not", "in", "not_in"]
_LINK = ["is", "is_not", "name_contains", "name_not_contains", "name_is", "type_is", "type_is_not", "in", "not_in"]

# The `Valid relations` list each data type answers, in the site's order (api3 001, api3 002).
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
    "entity": _LINK,
    "multi_entity": _LINK,
}

# api3 001
UNFILTERABLE = ("password", "serializable", "summary", "url")

# report 008: the site accepts any relation on these jsonb fields and returns every row.
IGNORED = {("PageSetting", "settings_json"), ("EventLogEntry", "audit_trail")}

RELATIVE = ("in_last", "not_in_last", "in_next", "not_in_next")
CALENDAR = ("in_calendar_day", "in_calendar_week", "in_calendar_month", "in_calendar_year")
TIME_UNITS = ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]

# The api3 client reads `values[0]` for these relations on any path but `id` (api3 011, api3 015).
_CLIENT_INDEXED = ("is", "is_not", "in", "not_in")


def filter_values(rval):
    """The `values` array the api3 client sends for a filter's value."""
    return list(rval) if isinstance(rval, (list, tuple)) else [rval]


def client_index_error(path, operator, rval, optimisation_disabled):
    """Whether the api3 client raises ``IndexError`` building this filter (api3 011, api3 015)."""
    return (not optimisation_disabled and path != "id" and operator in _CLIENT_INDEXED
            and filter_values(rval) == [])


def condition(path, operator, rval):
    """The filter as the site echoes it in a Fault: Ruby pp of path, relation and values."""
    return ruby_pp({"path": path, "relation": operator, "values": filter_values(rval)})


def unknown_field(entity_type, path, operator, rval):
    """The Fault text for a filter path naming a field that does not exist (api3 013, api3 021)."""
    return "API read() %s.%s doesn't exist:\n%s" % (entity_type, path, condition(path, operator, rval))


def calculated_type(properties):
    """The data type whose relations a calculated field takes: its renderer's (api3 006)."""
    renderer = ((properties or {}).get("renderer") or {}).get("value")
    return renderer if renderer in RELATIONS else "float"


def filter_refusal(entity_type, field, data_type, operator, rval, path=None):
    """The site's Fault text for a filter it refuses, or None when the filter is accepted.

    ``entity_type`` and ``field`` name the last hop of a dotted path; ``path`` is the path as sent.
    A calculated field arrives as the data type of its result (``calculated_type``).
    """
    path = path or field
    name = "%s.%s" % (entity_type, field)
    values = filter_values(rval)
    if data_type in UNFILTERABLE:
        return "API read() %s's '%s' data type cannot be used in a filter:\n%s" % (
            name, data_type, condition(path, operator, rval))
    relations = RELATIONS.get(data_type)
    if relations is None:
        return None
    if operator not in relations:
        return "API read() %s's '%s' data type doesn't support '%s' 'relation':\n%s\nValid relations:\n%s" % (
            name, data_type, operator, condition(path, operator, rval), ruby_pp(relations))
    # api3 002
    if data_type == "pivot_column":
        return "API read() of data type 'pivot_column' not supported in API"
    # api3 003
    if operator == "between" and len(values) != 2:
        return "API read() 'between' 'relation' expects a 2-element array:\n%s" % ruby_pp(values)
    # api3 011, api3 015, field_types/uuid
    if values == [] and (operator == "in" or (operator == "not_in" and data_type in ("entity", "multi_entity"))):
        return "API read() '%s' 'relation' expects at least a 1-element array:\n[]" % operator
    # api3 011
    if data_type == "multi_entity" and operator == "is" and len(values) != 1:
        return "API read() 'is' 'relation' expects a 1-element array:\n%s" % ruby_pp(values)
    # api3 010, api3 011
    if data_type in ("entity", "multi_entity") and operator.startswith("name_") and rval is None:
        return "API read() %s expected [String] data type(s) but got NilClass:\nnil" % name
    # api3 005
    if data_type == "checkbox" and rval is None:
        return "API read() %s expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil" % name
    # field_types/uuid. REST wording; api3 unprobed (sg-mockgun#39)
    if data_type == "uuid" and None in values:
        return "API read() %s expected [String] data type(s) but got NilClass: nil" % name
    # field_types/image. REST wording; api3 unprobed (sg-mockgun#39)
    if data_type == "image" and rval is not None:
        return "API read() '%s' 'relation' expects a nil value for 'image' data type: %s" % (
            operator, ruby_inspect(values))
    if operator in RELATIVE or operator in CALENDAR:
        return relative_refusal(name, operator, values)
    return None


def _ruby_class(value):
    """The Ruby class name and ``to_s`` of a value the site received."""
    if value is None:
        return "NilClass", ""
    if value is True or value is False:
        return ("TrueClass" if value else "FalseClass"), str(value).lower()
    if isinstance(value, float):
        return "Float", repr(value)
    if isinstance(value, str):
        return "String", value
    return type(value).__name__, str(value)


def relative_refusal(name, operator, values):
    """The Fault text for a malformed relative date value, or None (api3 014)."""
    size = 2 if operator in RELATIVE else 1
    if len(values) != size:
        return "API read() '%s' 'relation' expects a %d-element array:\n%s" % (operator, size, ruby_pp(values))
    count = values[0]
    if not isinstance(count, int) or isinstance(count, bool):
        cls, text = _ruby_class(count)
        return "API read() %s expected Integer data type(s) but got %s (%s):\n%s" % (
            name, cls, text, ruby_pp(values))
    if size == 2:
        unit = values[1]
        if unit not in TIME_UNITS:
            return "API read() '%s' 'relation' doesn't support the '%s' time unit:\n%s\nValid time units: %s" % (
                operator, unit, ruby_pp(values), ruby_inspect(TIME_UNITS))
        if count < 0:
            return "API read() '%s' 'relation' expects at a positive Integer time unit:\n%s" % (
                operator, ruby_pp(values))
    return None


def _shift_months(moment, months):
    """``moment`` moved by whole calendar months, the day clamped to the target month's length."""
    index = moment.year * 12 + moment.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return moment.replace(year=year, month=month, day=min(moment.day, days))


def _shift(moment, count, unit):
    if unit == "HOUR":
        return moment + datetime.timedelta(hours=count)
    if unit == "DAY":
        return moment + datetime.timedelta(days=count)
    if unit == "WEEK":
        return moment + datetime.timedelta(weeks=count)
    if unit == "MONTH":
        return _shift_months(moment, count)
    return _shift_months(moment, 12 * count)


def _as_utc(value, is_date):
    """A stored date as a ``date``, or a stored date_time as an aware UTC datetime."""
    if isinstance(value, str):
        if is_date:
            return datetime.date.fromisoformat(value[:10])
        value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if is_date:
        return value.date() if isinstance(value, datetime.datetime) else value
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def relative_match(lval, operator, values, now, is_date):
    """Whether a stored date or date_time is in a relative range, the clock reading ``now`` (api3 014).

    Negations match null rows (field_types/date). A date compares against today's UTC date, and an
    HOUR range on a date is today (field_types/date). Calendar periods are UTC (field_types/date_time).
    The week starts on Monday; the site's week start is unmeasured.
    """
    negate = operator.startswith("not_")
    if lval is None:
        return negate
    lval = _as_utc(lval, is_date)
    now = now.astimezone(datetime.timezone.utc)
    today = now.date()
    if operator in RELATIVE:
        count, unit = values
        origin = today if is_date else now
        if is_date and unit == "HOUR":
            start = end = today
        elif operator.endswith("in_last"):
            start, end = _shift(origin, -count, unit), origin
        else:
            start, end = origin, _shift(origin, count, unit)
        return (start <= lval <= end) != negate
    offset = values[0]
    day = lval if is_date else lval.date()
    if operator == "in_calendar_day":
        return day == today + datetime.timedelta(days=offset)
    if operator == "in_calendar_week":
        monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=offset)
        return monday <= day < monday + datetime.timedelta(days=7)
    if operator == "in_calendar_month":
        target = _shift_months(today.replace(day=1), offset)
        return (day.year, day.month) == (target.year, target.month)
    return day.year == today.year + offset


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
