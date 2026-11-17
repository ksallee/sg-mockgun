"""The answers of ``summarize()``: request checks, summary values and nested groups (api3 040 to 042).

Pure functions. The caller reads the rows and passes a ``field_type`` callable that returns a field's
data type, or None when the type lacks the field.
"""

import datetime
import math

from shotgun_api3 import Fault, ShotgunError

from .fields import Sym, ruby_inspect, ruby_pp

_NUMERIC = ["record_count", "count", "sum", "maximum", "minimum", "average"]
_DATES = ["record_count", "count", "earliest", "latest"]

# The valid summary types per data type, in the order the Fault lists them (api3 042).
# float and duration follow number: their accepted types were measured, their Fault was not.
SUMMARY_TYPES = {
    "number": _NUMERIC,
    "percent": _NUMERIC,
    "float": _NUMERIC,
    "duration": _NUMERIC,
    "date": _DATES,
    "date_time": _DATES,
    "text": ["record_count", "count"],
    "checkbox": ["record_count", "checked", "unchecked"],
    "status_list": ["record_count", "status_list", "status_percentage", "status_percentage_as_float"],
}
_OTHER_SUMMARY_TYPES = ["record_count", "count"]  # list and other types: unprobed, as text

_BUCKETS = ["exact", "tens", "hundreds", "thousands", "tensofthousands", "hundredsofthousands", "millions"]
_LINKS = ["exact", "entitytype", "firstletter"]

# The valid grouping types per data type, in the order the Fault lists them (api3 042).
GROUPING_TYPES = {
    "number": _BUCKETS,
    "percent": _BUCKETS,
    "float": _BUCKETS,  # unprobed, as number
    "date": ["exact", "day", "week", "month", "quarter", "year", "clustered_date"],
    "date_time": ["exact", "day", "week", "month", "quarter", "year", "clustered_date"],
    "duration": ["exact", "oneday", "fivedays"],
    "text": ["exact", "firstletter"],
    "list": ["exact", "firstletter"],
    "entity": _LINKS,
    "multi_entity": _LINKS,
    "checkbox": ["exact"],
    "status_list": ["exact"],
}

_BUCKET_SIZE = {"tens": 10, "hundreds": 100, "thousands": 1000, "tensofthousands": 10000,
                "hundredsofthousands": 100000, "millions": 1000000}
_WORKING_DAY = 480  # minutes per day in a duration bucket (api3 041)
_PERCENTAGES = ("status_percentage", "status_percentage_as_float")


def _fault(message):
    return Fault("API summarize() " + message)


def _symbols(names):
    return ruby_pp([Sym(n) for n in names])


def check_request(entity_type, params, entity_types, field_type):
    """Raise the Fault the site answers for a bad summarize request, in the order the site checks."""
    summaries, grouping = params["summaries"], params.get("grouping")
    if entity_type not in entity_types:
        raise _fault("invalid/missing string entity 'type':\n%s\nValid entity types:\n%s"
                     % (ruby_pp(params), ruby_pp(sorted(entity_types))))
    filters = params["filters"]
    if not isinstance(filters, dict) or "logical_operator" not in filters:
        raise _fault("invalid/missing filters string 'logical_operator' (general condition):\n%s" % ruby_pp(filters))
    _check_conditions(entity_type, filters, field_type)
    if not isinstance(summaries, list):
        raise Fault("Uncaught exception! no implicit conversion of String into Integer")
    seen = set()
    for item in summaries:
        for key in ("type", "field"):
            if key not in item:
                raise _fault("invalid/missing key '%s' in 'summaries' hash:\n%s" % (key, ruby_inspect(item)))
        field, kind = item["field"], item["type"]
        data_type = field_type(field)
        if data_type is None:
            raise _fault("%s.%s doesn't exist:\n%s" % (entity_type, field, ruby_inspect(item)))
        if field in seen:
            raise _fault("duplicate summary request for field '%s':\n%s" % (field, ruby_inspect(item)))
        seen.add(field)
        if data_type == "entity" and kind != "record_count":
            raise Fault("Uncaught exception! Summary type not supported: entity %s" % kind)
        if data_type == "multi_entity":
            raise Fault("Uncaught exception! undefined method 'process_summary_deep' for an instance of "
                        "ShotgunHasManyAssociationField")
        valid = SUMMARY_TYPES.get(data_type, _OTHER_SUMMARY_TYPES)
        if kind not in valid:
            raise _fault("summary type '%s' not valid for field %s.%s with data type '%s'\nValid summary types:\n%s"
                         % (kind, entity_type, field, data_type, _symbols(valid)))
        if kind in _PERCENTAGES and "value" not in item:
            raise _fault("invalid/missing key 'value'. Percentage-based summaries require a valid 'value' key in "
                         "the 'summaries' hash:\n%s" % ruby_inspect(item))
    for item in grouping or []:
        field, kind = item.get("field"), item.get("type")
        data_type = field_type(field)
        if data_type is None:
            raise _fault("%s.%s doesn't exist:\n%s" % (entity_type, field, ruby_inspect(item)))
        valid = GROUPING_TYPES.get(data_type, ["exact"])
        if kind not in valid:
            raise _fault("grouping option '%s' not valid for field %s.%s with data type '%s'\nValid grouping types:\n%s"
                         % (kind, entity_type, field, data_type, _symbols(valid)))
        if item.get("direction") not in ("asc", "desc"):
            raise _fault("invalid/missing string 'direction':\n%s\nValid direction values:[\"asc\", \"desc\"]"
                         % ruby_inspect(item))


def _check_conditions(entity_type, node, field_type):
    for condition in node.get("conditions", []):
        if "conditions" in condition:
            _check_conditions(entity_type, condition, field_type)
        elif field_type(condition.get("path")) is None:
            raise _fault("%s.%s doesn't exist:\n%s" % (entity_type, condition.get("path"), ruby_inspect(condition)))


def summarize(rows, summaries, grouping, field_type, status_order):
    """The ``{"summaries", "groups"}`` answer over ``rows``, each a dict of the fields asked for.

    ``status_order(field)`` lists a status field's statuses in the order an ``asc`` grouping sorts them.
    """
    result = {"summaries": _summaries(rows, summaries, field_type), "groups": []}
    if grouping is not None:
        # api3 041: an empty grouping list answers groups None.
        result["groups"] = _groups(rows, summaries, grouping, field_type, status_order) if grouping else None
    return result


def _summaries(rows, summaries, field_type):
    return dict((item["field"], _summary(rows, item, field_type(item["field"]))) for item in summaries)


def _summary(rows, item, data_type):
    kind, field = item["type"], item["field"]
    values = [row.get(field) for row in rows]
    present = [v for v in values if v is not None]
    zero = 0.0 if data_type == "float" else 0
    if kind == "record_count":
        return len(rows)
    if kind == "count":
        return len(present)
    if kind == "sum":
        return sum(present, zero)
    if kind == "maximum":
        return max(present) if present else zero
    if kind == "minimum":
        return min(present) if present else zero
    if kind == "average":
        return round(float(sum(present)) / len(present), 4) if present else 0.0
    if kind in ("earliest", "latest"):
        if not present:
            return None
        value = min(present) if kind == "earliest" else max(present)
        return _date_text(value)
    if kind == "checked":
        return sum(1 for v in values if v is True)
    if kind == "unchecked":
        return sum(1 for v in values if v is not True)
    if kind == "status_list":
        return _status_roll_up(values)
    # status_percentage rounds, status_percentage_as_float floors; both are integers (api3 040).
    share = 100.0 * sum(1 for v in values if v == item["value"]) / len(rows) if rows else 0.0
    return int(math.floor(share + 0.5)) if kind == "status_percentage" else int(math.floor(share))


def _date_text(value):
    """A date as ``YYYY-MM-DD``, a date_time as ``YYYY-MM-DD HH:MM:SS UTC`` (api3 040)."""
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc)
        return value.strftime("%Y-%m-%d %H:%M:%S UTC")
    return value


def _status_roll_up(values):
    """One status rolls up to itself, a mix to ``ip``, no row to ``na`` (finding 079, api3 040)."""
    distinct = set(values)
    if not values or distinct == {None}:
        return "na"
    if len(distinct) == 1:
        return values[0]
    return "ip"


def _groups(rows, summaries, grouping, field_type, status_order):
    item, rest = grouping[0], grouping[1:]
    field, kind = item["field"], item["type"]
    data_type = field_type(field)
    if kind == "clustered_date":
        # The buckets depend on the day the call is made and were not all recorded.
        raise ShotgunError("clustered_date grouping is not modelled by sg-mockgun (sg-mockgun#39).")
    buckets = {}
    for row in rows:
        values = row.get(field)
        if data_type == "multi_entity":
            values = values or [None]  # unprobed: a row is counted under each linked entity
        else:
            values = [values]
        for value in values:
            key, name, group_value = _bucket(value, data_type, kind)
            entry = buckets.setdefault(key, {"name": name, "value": group_value, "rows": []})
            entry["rows"].append(row)
    keys = sorted(buckets, key=lambda k: _sort_key(k, buckets[k]["name"], data_type, kind, field, status_order))
    if item["direction"] == "desc":
        keys.reverse()
    out = []
    for key in keys:
        entry = buckets[key]
        group = {"group_name": entry["name"], "group_value": entry["value"],
                 "summaries": _summaries(entry["rows"], summaries, field_type)}
        if rest:
            group["groups"] = _groups(entry["rows"], summaries, rest, field_type, status_order)
        out.append(group)
    return out


def _bucket(value, data_type, kind):
    """``(sort key, group_name, group_value)`` for one value under one grouping (api3 041)."""
    if value is None or value == "":
        return None, "", None
    if kind == "entitytype":
        return value["type"], value["type"], value["type"]
    if kind == "firstletter":
        text = value.get("name") if isinstance(value, dict) else value
        letter = (text or "")[:1].upper()
        return (letter, letter, letter) if letter else (None, "", None)
    if data_type in ("entity", "multi_entity"):
        link = {"type": value["type"], "id": value["id"], "name": value.get("name"), "valid": "valid"}
        return (value["type"], value["id"]), value.get("name"), link
    if kind in _BUCKET_SIZE:
        size = _BUCKET_SIZE[kind]
        floor = int(value // size * size)
        return floor, floor, floor
    if kind in ("oneday", "fivedays"):
        days = int(value // _WORKING_DAY)
        if kind == "fivedays":
            days -= days % 5
        minutes = "%.1f" % (days * _WORKING_DAY)
        return days, "%d %s" % (days, "day" if days < 2 else "days"), minutes
    if data_type == "checkbox":
        return (1, "[x]", "t") if value else (0, "[ ]", "f")
    if data_type in ("date", "date_time"):
        return _date_bucket(value, data_type, kind)
    return value, value, value


def _date_bucket(value, data_type, kind):
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc)  # the site's time zone is not modelled
        day = value.date()
    else:
        day = datetime.datetime.strptime(value, "%Y-%m-%d").date()
    if kind == "exact" and data_type == "date":
        return day, day.strftime("%b %d %y"), day.isoformat()
    if kind == "exact":
        text = _date_text(value)  # unprobed for date_time
        return value, text, text
    if kind == "day":
        return day, _long(day), day.isoformat()
    if kind == "week":
        start = day - datetime.timedelta(days=(day.weekday() + 1) % 7)  # weeks start on Sunday
        end = start + datetime.timedelta(days=6)
        return start, "%s to %s" % (_long(start), _long(end)), start.isoformat()
    if kind == "month":
        start = day.replace(day=1)
        return start, start.strftime("%B %Y"), start.isoformat()
    if kind == "quarter":
        start = day.replace(month=(day.month - 1) // 3 * 3 + 1, day=1)
        return start, "Q%d %d" % ((day.month - 1) // 3 + 1, day.year), start.isoformat()
    start = day.replace(month=1, day=1)  # year
    return start, str(day.year), start.isoformat()


def _long(day):
    return day.strftime("%B %d, %Y")


def _sort_key(key, name, data_type, kind, field, status_order):
    """Ascending order: the field's status order on a status_list, natural order otherwise, empty last."""
    if key is None:
        return (1, 0, "")
    if data_type == "status_list":
        order = status_order(field)
        return (0, order.index(key) if key in order else len(order), key)
    if data_type in ("entity", "multi_entity") and kind == "exact":
        return (0, 0, (str(name), key[1]))  # unprobed: by name, then id
    return (0, 0, key)
