"""Seed a mockgun instance from JSON, and snapshot and restore its state.

Seed format, one list of records per entity type::

    {"Shot": [{"id": 1, "code": "sh010", "project": {"type": "Project", "id": 70}}]}

Every record has an explicit ``id``. A link is ``{"type", "id"}`` and points at a record in the seed
or already on the instance. A ``date_time`` value is an ISO 8601 string. Seeding writes no event log
rows.
"""

import copy
import datetime
import json

from shotgun_api3 import ShotgunError

# Instance attributes that make up a mock site's records and schema.
_STATE = ("_db", "_schema", "_schema_entity", "_retired_fields", "_retired_at", "_column_ids", "_media_state")


def load(mock, source):
    """Add the records in ``source``, a seed file path or an already parsed dict, to ``mock``."""
    if isinstance(source, dict):
        data = source
    else:
        with open(source, encoding="utf-8") as f:
            data = json.load(f)
    staged = {}
    for entity_type, records in data.items():
        mock._validate_entity_type(entity_type)
        for record in records:
            entity_id = _id(entity_type, record, mock, staged)
            staged[(entity_type, entity_id)] = _row(mock, entity_type, record)
    for (entity_type, entity_id), row in staged.items():
        for link in _links(mock, entity_type, row):
            key = (link["type"], link["id"])
            if key not in staged and link["id"] not in mock._db.get(link["type"], {}):
                raise ShotgunError("%s %s links to %s %s, which is not in the seed or on the site"
                                   % (entity_type, entity_id, link["type"], link["id"]))
    for (entity_type, entity_id), row in staged.items():
        mock._db[entity_type][entity_id] = row


def snapshot(mock):
    """A copy of ``mock``'s records and schema, for ``restore``."""
    return {name: copy.deepcopy(getattr(mock, name)) for name in _STATE}


def restore(mock, state):
    """Put ``mock``'s records and schema back to ``state``; the state can be restored again."""
    for name in _STATE:
        setattr(mock, name, copy.deepcopy(state[name]))


def _id(entity_type, record, mock, staged):
    entity_id = record.get("id")
    if not isinstance(entity_id, int) or isinstance(entity_id, bool):
        raise ShotgunError("Seed record for %s needs an integer id: %r" % (entity_type, record))
    if (entity_type, entity_id) in staged or entity_id in mock._db[entity_type]:
        raise ShotgunError("%s %s is already seeded" % (entity_type, entity_id))
    return entity_id


def _row(mock, entity_type, record):
    fields = {k: v for k, v in record.items() if k not in ("id", "type")}
    mock._validate_entity_fields(entity_type, fields)
    for field, value in fields.items():
        if isinstance(value, str) and mock._get_field_type(entity_type, field) == "date_time":
            fields[field] = _parse_date_time(value)
    row = mock._get_new_row(entity_type)
    mock._update_row(entity_type, row, fields)
    row["id"] = record["id"]
    return row


def _links(mock, entity_type, row):
    for field, value in row.items():
        if field not in mock._schema[entity_type]:
            continue
        field_type = mock._get_field_type(entity_type, field)
        if field_type == "entity" and value:
            yield value
        elif field_type == "multi_entity":
            for item in value or []:
                yield item


def _parse_date_time(value):
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
