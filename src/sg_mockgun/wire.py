"""Translate between the api3 JSON protocol and mockgun calls. Pure: no I/O, no state.

The client side of every shape here is shotgun_api3 3.10.5: ``_translate_filters`` builds
``{"logical_operator", "conditions": [{"path", "relation", "values"}]}``, field writes travel as
``[{"field_name", "value"}]`` and datetimes as ``YYYY-MM-DDTHH:MM:SSZ`` strings.
"""

import datetime
import re

_DATETIME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")
_MULTI_VALUE = {"in", "not_in", "between", "not_between", "type_is", "type_is_not", "in_last", "not_in_last",
                "in_next", "not_in_next"}


def split_payload(payload):
    """``(method, auth, params)`` from a request body; auth is ``{}`` when the call carries none."""
    method = payload.get("method_name")
    call = list(payload.get("params") or [])
    auth = {}
    if call and isinstance(call[0], dict) and any(k in call[0] for k in ("script_name", "session_token", "user_login")):
        auth = call.pop(0)
    params = call[0] if call else {}
    return method, auth, params


def filters_from_wire(node):
    """``conditions`` tree -> mockgun ``(filters, filter_operator)``."""
    operator = "any" if node.get("logical_operator") == "or" else "all"
    out = []
    for condition in node.get("conditions", []):
        if "conditions" in condition:
            sub, sub_op = filters_from_wire(condition)
            out.append({"filter_operator": sub_op, "filters": sub})
            continue
        values = condition.get("values", [])
        relation = condition["relation"]
        if relation in _MULTI_VALUE and not (relation in ("type_is", "type_is_not") and len(values) == 1):
            value = list(values)
        else:
            value = values[0] if values else None
        if relation in ("in_last", "not_in_last", "in_next", "not_in_next"):
            out.append([condition["path"], relation] + list(values))
        else:
            out.append([condition["path"], relation, value])
    return out, operator


def fields_from_wire(fields):
    """``[{"field_name", "value", "multi_entity_update_mode"?}]`` -> ``(data, modes)``."""
    data, modes = {}, {}
    for item in fields or []:
        data[item["field_name"]] = item.get("value")
        if item.get("multi_entity_update_mode"):
            modes[item["field_name"]] = item["multi_entity_update_mode"]
    return data, modes


def properties_from_wire(properties):
    return {p["property_name"]: p["value"] for p in properties or []}


def to_python(value, data_type):
    """A value off the wire, as mockgun stores it for a field of ``data_type``."""
    if data_type == "date_time" and isinstance(value, str):
        m = _DATETIME.match(value)
        if m:
            return datetime.datetime(*map(int, m.groups()), tzinfo=datetime.timezone.utc)
    return value


def to_wire(value):
    """Mockgun results -> JSON-safe values; datetimes in UTC as the client parses them."""
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {k: to_wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_wire(v) for v in value]
    return value


def page(records, paging):
    """One page of ``records`` and the paging_info the client reads."""
    per_page = int((paging or {}).get("entities_per_page") or 500)
    current = int((paging or {}).get("current_page") or 1)
    start = (current - 1) * per_page
    return {
        "entities": records[start:start + per_page],
        "paging_info": {"entity_count": len(records), "current_page": current,
                        "page_count": max(1, -(-len(records) // per_page)),
                        "has_next_page": start + per_page < len(records)},
    }


def fault(message, error_code=None):
    body = {"exception": True, "message": message}
    if error_code is not None:
        body["error_code"] = error_code
    return body
