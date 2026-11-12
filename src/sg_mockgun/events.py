"""Pure builders for EventLogEntry rows. No I/O, no ids, no clock: the caller supplies both.

Shapes and wording follow the api3 probe of 2026-11-12 (docs/api3-probe-2026-11-12.md) and
sg-groundtruth findings 025 and 049. Each builder returns a list of partial rows:
``{event_type, attribute_name, meta, description}``; the caller adds entity, project, user, created_at.
"""


def stamp(when):
    """A retirement date as the site writes it into meta: ``2026-11-12 21:54:08 UTC``."""
    return when.strftime("%Y-%m-%d %H:%M:%S UTC")


def _shown(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return value.get("name") or "%s %s" % (value.get("type"), value.get("id"))
    if isinstance(value, list):
        return ", ".join(_shown(v) for v in value)
    return str(value)


def _row(event_type, meta, description, attribute_name=None):
    return {"event_type": event_type, "attribute_name": attribute_name, "meta": meta, "description": description}


def attribute_change(user, entity_type, entity_id, name, attribute, display, data_type, old, new, in_create=False):
    meta = {"type": "attribute_change", "attribute_name": attribute, "entity_type": entity_type, "entity_id": entity_id}
    if in_create:
        meta["in_create"] = True
    meta.update({"field_data_type": data_type, "old_value": old, "new_value": new, "platform_id": None})
    description = '%s changed "%s" from "%s" to "%s" on %s %s' % (
        user, display, _shown(old), _shown(new), entity_type, name or "")
    return _row("Shotgun_%s_Change" % entity_type, meta, description, attribute)


def entity_created(user, entity_type, entity_id, name, changes):
    """``changes``: ``(attribute, display, data_type, value)`` per field the create set, in order."""
    rows = [_row(
        "Shotgun_%s_New" % entity_type,
        {"type": "new_entity", "entity_type": entity_type, "entity_id": entity_id, "platform_id": None},
        "%s created new %s " % (user, entity_type),
    )]
    for attribute, display, data_type, value in changes:
        rows.append(attribute_change(user, entity_type, entity_id, name, attribute, display, data_type,
                                     None, value, in_create=True))
    return rows


def entity_retired(user, entity_type, entity_id, name, when):
    date = stamp(when)
    change = _row(
        "Shotgun_%s_Change" % entity_type,
        {"type": "attribute_change", "attribute_name": "retirement_date", "entity_type": entity_type,
         "entity_id": entity_id, "old_value": None, "new_value": date, "platform_id": None},
        '%s changed "Retirement Date" from "" to "%s" on %s %s' % (user, date, entity_type, name or ""),
        "retirement_date",
    )
    retirement = _row(
        "Shotgun_%s_Retirement" % entity_type,
        {"entity_type": entity_type, "class_name": entity_type, "entity_id": entity_id, "id": entity_id,
         "type": "entity_retirement", "retirement_date": date, "display_name": name},
        ' retired %s "%s"' % (entity_type, name),
    )
    return [change, retirement]


def entity_revived(user, entity_type, entity_id, name, retired_at):
    date = stamp(retired_at)
    change = _row(
        "Shotgun_%s_Change" % entity_type,
        {"type": "attribute_change", "attribute_name": "retirement_date", "entity_type": entity_type,
         "entity_id": entity_id, "old_value": date, "new_value": None, "platform_id": None},
        '%s changed "Retirement Date" from "%s" to "" on %s %s' % (user, date, entity_type, name or ""),
        "retirement_date",
    )
    revival = _row(
        "Shotgun_%s_Revival" % entity_type,
        {"class_name": entity_type, "display_name": name, "id": entity_id, "entity_type": entity_type,
         "entity_id": entity_id, "type": "entity_revival"},
        ' revived %s "%s"' % (entity_type, name),
    )
    return [change, revival]


def field_created(user, column_id, code):
    return [_row(
        "Shotgun_DisplayColumn_New",
        {"type": "new_entity", "entity_type": "DisplayColumn", "entity_id": column_id},
        "%s created new Field %s" % (user, code),
    )]


def field_renamed(user, column_id, code, old, new):
    # The site also logs a "properties" row holding internal property hashes; it is not reproduced.
    return [_row(
        "Shotgun_DisplayColumn_Change",
        {"type": "attribute_change", "attribute_name": "human_name", "entity_type": "DisplayColumn",
         "entity_id": column_id, "field_data_type": "text", "old_value": old, "new_value": new},
        '%s changed "Field Name" from "%s" to "%s" on Field %s' % (user, old, new, code),
        "human_name",
    )]


def field_retired(user, column_id, code, when):
    date = stamp(when)
    return [
        _row(
            "Shotgun_DisplayColumn_Change",
            {"type": "attribute_change", "attribute_name": "retirement_date", "entity_type": "DisplayColumn",
             "entity_id": column_id, "old_value": None, "new_value": date},
            '%s changed "Retirement Date" from "" to "%s" on Field %s' % (user, date, code),
            "retirement_date",
        ),
        _row(
            "Shotgun_DisplayColumn_Retirement",
            {"entity_type": "DisplayColumn", "class_name": "DisplayColumn", "entity_id": column_id, "id": column_id,
             "type": "entity_retirement", "retirement_date": date, "display_name": code},
            ' retired DisplayColumn "%s"' % code,
        ),
    ]


def field_revived(user, column_id, code, retired_at):
    date = stamp(retired_at)
    return [
        _row(
            "Shotgun_DisplayColumn_Change",
            {"type": "attribute_change", "attribute_name": "retirement_date", "entity_type": "DisplayColumn",
             "entity_id": column_id, "old_value": date, "new_value": None},
            '%s changed "Retirement Date" from "%s" to "" on Field %s' % (user, date, code),
            "retirement_date",
        ),
        _row(
            "Shotgun_DisplayColumn_Revival",
            {"class_name": "DisplayColumn", "display_name": code, "id": column_id, "entity_type": "DisplayColumn",
             "entity_id": column_id, "type": "entity_revival"},
            ' revived DisplayColumn "%s"' % code,
        ),
    ]
