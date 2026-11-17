"""Server answers for attention, navigation and site reads: answers 047 to 052 in docs/api3.

Each function takes the mockgun instance and the RPC params as the client sends them, and returns
what the site returns or raises the site's Fault. Client-side checks stay in the thin methods on
``Shotgun``, so the HTTP server can call these directly.
"""

import datetime
import re
import uuid

from shotgun_api3 import Fault

from .fields import ruby_inspect, ruby_list, ruby_params

# Site data the mock cannot know. Shapes are recorded (api3 051); values are the ones get_preferences
# in the corpus names, the rest are placeholders of the recorded type.
DEFAULT_PREFERENCES = {
    "creative_review_settings": "{}",
    "date_component_order": "month_day",
    "duration_units": "days",
    "enable_rv_integration": False,
    "enable_shotgun_review_for_rv": False,
    "format_currency_fields_decimal_options": "",
    "format_currency_fields_display_dollar_sign": False,
    "format_currency_fields_negative_options": "",
    "format_date_fields": "08/04/22 OR 04/08/22",
    "format_float_fields": "",
    "format_float_fields_rounding": "",
    "format_footage_fields": "",
    "format_number_fields": "",
    "format_time_hour_fields": "",
    "hours_per_day": 8.0,
    "support_local_storage": True,
    "view_master_settings": "{}",
}
DEFAULT_WORK_WEEK = (True, True, True, True, True, False, False)  # Monday first


def state(mock):
    """The site data this module reads, created with its defaults on first use."""
    return mock.__dict__.setdefault("_attention", {
        "follows": {},  # HumanUser id -> list of {type, id}
        "preferences": dict(DEFAULT_PREFERENCES),
        "work_week": list(DEFAULT_WORK_WEEK),
        "work_exceptions": {},  # YYYY-MM-DD -> {working, description, reason}
        "subscriptions": {},  # HumanUser id as a string -> subscription or None
    })


def _live(mock, entity_type, entity_id):
    row = mock._db.get(entity_type, {}).get(entity_id) if isinstance(entity_id, int) else None
    return row if row is not None and not row["__retired"] else None


def mock_name(row):
    for field in ("name", "code", "content", "title"):
        if row.get(field):
            return row[field]
    return None


def _widen(mock, out, entity_type, row, fields):
    """Add the requested fields to ``out``; a field the schema does not have is dropped."""
    for field in fields:
        try:
            mock._validate_entity_fields(entity_type, [field])
            out[field] = mock._read_field(entity_type, row, field)
        except Exception:  # an unknown field or path is dropped without error
            continue
    return out


def _check_entity_fields(entity_fields):
    for value in entity_fields.values():
        if not isinstance(value, (list, tuple)):
            raise Fault("Uncaught exception! no implicit conversion of Array into String")


# api3 047
def note_thread_contents(mock, note_id, entity_fields):
    if not isinstance(note_id, int) or isinstance(note_id, bool):
        raise Fault("API note_thread_contents() 'note_id' missing:\n%s"
                    % ruby_params({"note_id": note_id, "entity_fields": entity_fields}))
    note = _live(mock, "Note", note_id)
    if note is None:
        raise Fault("Not Found")
    _check_entity_fields(entity_fields)

    def stamp(row):
        return row.get("created_at")

    rows = []
    out = {"type": "Note", "id": note["id"], "content": note.get("content"), "created_at": stamp(note),
           "created_by": _user_link(mock, note.get("created_by"))}
    rows.append(_widen(mock, out, "Note", note, entity_fields.get("Note", [])))
    for reply in mock._db.get("Reply", {}).values():
        if reply["__retired"] or not isinstance(reply.get("entity"), dict):
            continue
        if (reply["entity"].get("type"), reply["entity"].get("id")) != ("Note", note["id"]):
            continue
        user = _user_link(mock, reply.get("user"))
        if user is not None:
            user["image"] = None
        rows.append({"type": "Reply", "id": reply["id"], "content": reply.get("content"), "user": user,
                     "created_at": stamp(reply)})
    for link in note.get("attachments") or []:
        attachment = _live(mock, "Attachment", link.get("id"))
        if attachment is None:
            continue
        out = {"type": "Attachment", "id": attachment["id"], "created_by": _user_link(mock, attachment.get("created_by")),
               "created_at": stamp(attachment)}
        rows.append(_widen(mock, out, "Attachment", attachment, entity_fields.get("Attachment", [])))
    floor = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    rows.sort(key=lambda r: r["created_at"] or floor)  # stable: the Note stays first on a tie
    return rows


def _user_link(mock, link):
    if not isinstance(link, dict):
        return None
    row = mock._db.get(link.get("type"), {}).get(link.get("id"))
    return {"id": link["id"], "name": mock_name(row) if row else link.get("name"), "type": link["type"]}


# api3 048
def activity_stream(mock, entity_type, entity_id, entity_fields, min_id, max_id, limit):
    if entity_type not in mock._schema:
        raise Fault("Invalid parameter: type")
    if not isinstance(entity_id, int) or isinstance(entity_id, bool):
        raise Fault("Invalid parameter: id")
    if mock._db[entity_type].get(entity_id) is None:
        raise Fault("Uncaught exception! Entity does not exist or user does not have permission")
    if limit is not None and limit < 0:
        raise Fault("Uncaught exception! Invalid parameter: page_size")
    limit = min(limit or 25, 500)
    _check_entity_fields(entity_fields)
    target = {"type": entity_type, "id": entity_id}
    events = mock._db.get("EventLogEntry", {})
    newest = max(events) if events else 0

    picked = []
    for event_id in sorted(events, reverse=True):
        if max_id is not None and event_id >= max_id:
            continue
        if min_id is not None and event_id <= min_id:
            break
        update = _create_update(mock, events[event_id], target, entity_fields)
        if update is not None:
            picked.append(update)
    more = len(picked) > limit
    picked = picked[:limit]
    latest = newest if max_id is None else (picked[0]["id"] if picked else newest)
    if not picked:
        earliest = latest
    elif min_id is None and not more:
        earliest = 0  # the stream ran out
    else:
        earliest = picked[-1]["id"]
    return {"entity_type": entity_type, "entity_id": entity_id, "latest_update_id": latest,
            "earliest_update_id": earliest, "updates": picked}


def _create_update(mock, event, target, entity_fields):
    """A ``create`` update for ``event`` when it creates ``target`` or a row linked to it, else None."""
    meta = event.get("meta") or {}
    if meta.get("type") != "new_entity" or meta.get("entity_type") not in mock._schema:
        return None
    created_type, created_id = meta["entity_type"], meta.get("entity_id")
    row = mock._db[created_type].get(created_id)
    if row is None:
        return None
    if (created_type, created_id) != (target["type"], target["id"]) and not _links_to(mock, created_type, row, target):
        return None
    primary = {"type": created_type, "id": created_id, "name": mock_name(row), "status": row.get("sg_status_list")}
    _widen(mock, primary, created_type, row, entity_fields.get(created_type, []))
    user = dict(event.get("user") or {})
    return {
        "id": event["id"],
        "update_type": "create",
        "meta": {"type": "new_entity", "entity_type": created_type, "entity_id": created_id},
        "created_at": event.get("created_at"),
        "read": None,
        "primary_entity": primary,
        "created_by": {"type": user.get("type"), "id": user.get("id"), "name": user.get("name"),
                       "status": None, "image": None},
    }


def _links_to(mock, entity_type, row, target):
    for field, info in mock._schema[entity_type].items():
        if info["data_type"]["value"] != "entity":
            continue
        value = row.get(field)
        if isinstance(value, dict) and (value.get("type"), value.get("id")) == (target["type"], target["id"]):
            return True
    return False


# api3 049
def following(mock, params):
    user = params.get("user") or {}
    if user.get("type") != "HumanUser":
        raise Fault("API following() invalid user type. Must be HumanUser. Found: %s" % user.get("type"))
    if _live(mock, "HumanUser", user.get("id")) is None:
        raise Fault("API following() user not found: HumanUser %s" % user.get("id"))
    project = params.get("project")
    if project and _live(mock, "Project", project.get("id")) is None:
        raise Fault("API following() project not found: Project %s" % project.get("id"))
    entity_type = params.get("entity_type")
    if entity_type is not None and entity_type not in mock._schema:
        raise Fault("API following() invalid/missing 'type' string:\n%s\nValid types:\n%s"
                    % (ruby_inspect(entity_type), ruby_list(sorted(mock._schema))))
    rows = []
    for followed in state(mock)["follows"].get(user["id"], []):
        if entity_type and followed["type"] != entity_type:
            continue
        row = _live(mock, followed["type"], followed["id"])
        if row is None:
            continue
        if project and (row.get("project") or {}).get("id") != project["id"]:
            continue
        rows.append({"type": followed["type"], "id": followed["id"]})
    return rows


def followers(mock, entity):
    entity = entity or {}
    if entity.get("type") not in mock._schema:
        raise Fault("API followers() invalid/missing entity hash string 'type':\n%s\nValid entity types:\n%s"
                    % (ruby_params(entity), ruby_list(sorted(mock._schema))))
    if not isinstance(entity.get("id"), int):
        raise Fault("API followers() invalid/missing entity hash integer 'id':\n%s" % ruby_params(entity))
    if _live(mock, entity["type"], entity["id"]) is None:
        raise Fault("API followers() entity not found: %s" % entity["type"])
    key = {"type": entity["type"], "id": entity["id"]}
    rows = []
    for user_id in sorted(state(mock)["follows"]):
        user = _live(mock, "HumanUser", user_id)
        if user is None or key not in state(mock)["follows"][user_id]:
            continue
        rows.append({"type": "HumanUser", "id": user_id, "name": user.get("name"), "status": user.get("sg_status_list"),
                     "valid": "valid", "uuid": user.get("uuid") or str(uuid.uuid5(uuid.NAMESPACE_OID, "HumanUser/%d" % user_id))})
    return rows


# api3 050
_TREE = {  # entity type under a project -> (grouping field, group entity type or None for a list field)
    "Asset": ("sg_asset_type", None),
    "Shot": ("sg_sequence", "Sequence"),
}
_INVALID_ROOT = ("Unsupported or invalid root_path provided. "
                 "Only paths with the format '/Project/<project_id>' are currently supported.")


def _targets(path):
    return {"type": "Version", "additional_filter_presets": [
        {"preset_name": "NAV_ENTRIES", "path": path, "seed": {"type": "Version", "field": "entity"}}]}


def _node(label, ref, path, has_children, parent_path=None, parent_first=False):
    node = {"label": label, "ref": ref}
    if parent_first:
        node["parent_path"] = parent_path
    node.update({"path": path, "target_entities": _targets(path), "has_children": has_children})
    if parent_path is not None and not parent_first:
        node["parent_path"] = parent_path
    return node


def _empty(entity_type):
    return {"label": "No %ss" % entity_type, "ref": {"kind": "empty", "value": None}, "has_children": False}


def _plural(mock, entity_type):
    return "%ss" % mock._schema_entity[entity_type]["name"]["value"]


def _project_rows(mock, entity_type, project_id):
    return [r for _, r in sorted(mock._db[entity_type].items())
            if not r["__retired"] and (r.get("project") or {}).get("id") == project_id]


def _leaf(mock, row, path, entity_fields):
    value = {"type": row["type"], "id": row["id"]}
    _widen(mock, value, row["type"], row, (entity_fields or {}).get(row["type"], []))
    return _node(mock_name(row), {"kind": "entity", "value": value}, "%s/id/%d" % (path, row["id"]), False)


def _groups(mock, project_id, entity_type, base):
    """``(node, members)`` per child of ``<project>/<entity_type>``, in the order the site lists them."""
    field, group_type = _TREE[entity_type]
    rows = _project_rows(mock, entity_type, project_id)
    out = []
    if group_type is None:
        values = mock._schema[entity_type][field]["properties"].get("valid_values", {}).get("value") or []
        for value in values:
            out.append((_node(value, {"kind": "list", "value": value}, "%s/%s/%s" % (base, field, value), True),
                        [r for r in rows if r.get(field) == value]))
        label = "%s with no %s" % (_plural(mock, entity_type), mock._display_name(entity_type, field))
        out.append((_node(label, {"kind": "list", "value": "__none__"}, "%s/%s/__none__" % (base, field), True),
                    [r for r in rows if not r.get(field)]))
        return out
    bucket_path = "%s/%s/%s/__none__" % (base, field, group_type)
    label = "%s with no %s" % (_plural(mock, entity_type), group_type)
    bucket = (_node(label, {"kind": "entity_type", "value": entity_type}, bucket_path, True),
              [r for r in rows if not r.get(field)])
    for group in _project_rows(mock, group_type, project_id):
        members = [r for r in rows if (r.get(field) or {}).get("id") == group["id"]]
        out.append((_node(mock_name(group), {"kind": "entity", "value": {"type": group_type, "id": group["id"]}},
                          "%s/%s/%s/%d" % (base, field, group_type, group["id"]), True), members))
        out.append(bucket)  # the site repeats the bucket after every group
    return out


def nav_expand(mock, path, seed_entity_field, entity_fields):
    path = path or "/"
    if path == "/":
        children = [_node(p["name"], {"kind": "entity", "value": {"type": "Project", "id": p["id"]}},
                          "/Project/%d" % p["id"], True, "/", parent_first=True)
                    for _, p in sorted(mock._db["Project"].items()) if not p["__retired"]]
        return {"label": "root", "ref": {"kind": "root", "value": None}, "path": "/",
                "target_entities": _targets(""), "has_children": True, "children": children}
    slash = "/" if path.startswith("/") else ""
    segs = path.strip("/").split("/")
    if segs[0] != "Project" or len(segs) < 2 or not segs[1].isdigit():
        raise Fault("Only 'Project' nav paths are currently supported: %s" % path)
    project_id = int(segs[1])
    project = _live(mock, "Project", project_id)
    base = "%sProject/%d" % (slash, project_id)
    if len(segs) == 2:
        if project is None:
            raise Fault("Unexpected result looking for project: %d: 0 found." % project_id)
        children = [_node(_plural(mock, t), {"kind": "entity_type", "value": t}, "%s/%s" % (base, t), True)
                    for t in sorted(_TREE)]
        node = _node(project["name"], {"kind": "entity", "value": {"type": "Project", "id": project_id}},
                     base, True, slash or "/", parent_first=True)
        node["children"] = children
        return node
    entity_type = segs[2]
    if entity_type not in _TREE:
        raise Fault("Entity type provided is not part of the tree: %s" % entity_type)
    if seed_entity_field:
        raise Fault("Entity type provided is not part of the tree: %s" % str(seed_entity_field).split(".")[0])
    type_path = "%s/%s" % (base, entity_type)
    groups = _groups(mock, project_id, entity_type, type_path)
    if len(segs) == 3:
        node = _node(_plural(mock, entity_type), {"kind": "entity_type", "value": entity_type}, type_path, True, base)
        has_groups = _TREE[entity_type][1] is None or len(groups) > 1
        node["children"] = [g for g, _ in groups] if has_groups else [_empty(entity_type)]
        return node
    field = _TREE[entity_type][0]
    if segs[3] != field:
        raise Fault("Unexpected field name in path: %s (expecting %s)" % (segs[3], field))
    group_path = "%s%s" % (slash, "/".join(segs))
    match = [(node, members) for node, members in groups if node["path"] == group_path]
    if match:
        node, members = match[0]
    elif group_path == "%s/%s/__none__" % (type_path, field):
        # The search spelling of the bucket, without the group type segment, answers too.
        members = [r for r in _project_rows(mock, entity_type, project_id) if not r.get(field)]
        node = _node("%s with no __none__" % _plural(mock, entity_type),
                     {"kind": "entity_type", "value": entity_type}, group_path, True)
    else:
        node, members = _node(segs[-1], {"kind": "empty", "value": None}, group_path, True), []
    node = dict(node, parent_path=type_path)
    node["children"] = [_leaf(mock, r, group_path, entity_fields) for r in members] or [_empty(entity_type)]
    return node


def nav_search(mock, root_path, criteria):
    m = re.match(r"^/Project/(\d+)$", root_path or "")
    if not m:
        return {"status": "failed", "description": _INVALID_ROOT}
    project_id = int(m.group(1))
    if _live(mock, "Project", project_id) is None:
        return {"status": "failed", "description": "undefined method 'select!' for nil"}
    base = root_path
    rows = []
    for entity_type in sorted(_TREE):
        type_path = "%s/%s" % (base, entity_type)
        rows.append({"label": _plural(mock, entity_type), "incremental_path": [base, type_path], "path_label": "",
                     "ref": {"id": None, "type": None}, "project_id": project_id})
        seen = set()
        for node, members in _groups(mock, project_id, entity_type, type_path):
            for row in members:
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                rows.append({"label": mock_name(row),
                             "incremental_path": [base, type_path, node["path"], "%s/id/%d" % (node["path"], row["id"])],
                             "path_label": "%s > %s" % (_plural(mock, entity_type), node["label"]),
                             "ref": {"id": row["id"], "type": entity_type}, "project_id": project_id})
    if "entity" in criteria:
        entity = criteria["entity"] or {}
        if entity.get("type") not in mock._schema:
            return {"status": "failed", "description": "undefined method '[]' for nil"}
        return [r for r in rows if r["ref"] == {"id": entity.get("id"), "type": entity.get("type")}]
    text = (criteria.get("search_string") or "").lower()
    found = [r for r in rows if text in (r["label"] or "").lower()]
    return sorted(found, key=lambda r: r["label"] or "")


# api3 051
def preferences_read(mock, prefs):
    if not isinstance(prefs, list):
        raise Fault("API preferences_read() 'prefs' must be an array.")
    if not prefs:
        return dict(state(mock)["preferences"])
    return {k: v for k, v in state(mock)["preferences"].items() if k in prefs}


def work_schedule_read(mock, params):
    def parse(key):
        try:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", params.get(key) or ""):
                raise ValueError
            return datetime.date.fromisoformat(params[key])
        except ValueError:
            raise Fault("API work_schedule_read() invalid format for '%s'. Valid format 'YYYY-MM-DD':\n%s"
                        % (key, ruby_params(params)))

    start, end = parse("start_date"), parse("end_date")
    if end < start:
        raise Fault("API work_schedule_read() 'end_date' must be greater than or equal to 'start_date':\n%s"
                    % ruby_params(params))
    out = {}
    day = start
    while day <= end:
        key = day.isoformat()
        out[key] = dict(state(mock)["work_exceptions"].get(key) or {
            "working": state(mock)["work_week"][day.weekday()], "description": None, "reason": "STUDIO_WORK_WEEK"})
        day += datetime.timedelta(days=1)
    return out


# api3 052
def export_page(mock, params):
    page_id = params.get("page_id")
    if page_id is None:
        raise Fault("API export_page() 'page_id' missing:\n%s" % ruby_params(params))
    if not isinstance(page_id, int) or isinstance(page_id, bool) or page_id <= 0:
        raise Fault("API export_page() invalid 'page_id':\n%s" % ruby_params(params))
    if params.get("format") is None:
        raise Fault("API export_page() 'format' missing:\n%s" % ruby_params(params))
    if _live(mock, "Page", page_id) is None:
        raise Fault("Trying to perform export for retired Page id=%d" % page_id)
    raise Fault("Export for Page id=%d not available" % page_id)
