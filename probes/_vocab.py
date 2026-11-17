"""One stock field per data type, a sample value per type, and the relations tried by probes 001 and 002."""

# (entity type, field, data type). Fields match the sg-groundtruth field_types cards where they can.
FIELDS = [
    ("Shot", "code", "text"),
    ("Version", "frame_count", "number"),
    ("Version", "sg_movie_aspect_ratio", "float"),
    ("Shot", "sg___complete", "percent"),
    ("Shot", "sg_bid___total", "duration"),
    ("Sequence", "sg_timecode", "timecode"),
    ("Shot", "sg_client_turnover_date", "date"),
    ("Version", "created_at", "date_time"),
    ("Version", "flagged", "checkbox"),
    ("Note", "sg_note_type", "list"),
    ("Version", "sg_status_list", "status_list"),
    ("Version", "entity", "entity"),
    ("Version", "tasks", "multi_entity"),
    ("Step", "entity_type", "entity_type"),
    ("Task", "color", "color"),
    ("Icon", "uuid", "uuid"),
    ("Version", "image", "image"),
    ("Note", "meta", "jsonb"),
    ("Version", "sg_uploaded_movie", "url"),
    ("Task", "workload", "calculated"),
    ("HumanUser", "password_proxy", "password"),
    ("Task", "splits", "serializable"),
    ("Shot", "open_notes_count", "summary"),
    ("Shot", "step_0", "pivot_column"),
]

# The union of every `Valid relations` list REST prints (finding 017, field_types/*).
UNION = [
    "is", "is_not", "contains", "not_contains", "starts_with", "ends_with", "in", "not_in",
    "greater_than", "less_than", "between", "in_last", "not_in_last", "in_next", "not_in_next",
    "in_calendar_day", "in_calendar_week", "in_calendar_month", "in_calendar_year",
    "name_contains", "name_not_contains", "name_is", "type_is", "type_is_not",
]
# Relations shotgun_api3's own mockgun knows that no REST list names.
EXTRA = ["not_between", "name_starts_with", "name_ends_with"]

SAMPLE = {
    "text": "zzprobe", "number": 1, "float": 1.0, "percent": 1, "duration": 60, "timecode": 0,
    "date": "2026-01-01", "date_time": "2026-01-01T00:00:00Z", "checkbox": True, "list": "zzprobe",
    "status_list": "ip", "entity": {"type": "Shot", "id": 1}, "multi_entity": {"type": "Task", "id": 1},
    "entity_type": "Shot", "color": "255,0,0", "uuid": "00000000-0000-0000-0000-000000000000",
    "image": None, "jsonb": {"zzprobe": 1}, "url": None, "calculated": None, "password": "zzprobe",
    "serializable": None, "summary": 1, "pivot_column": None,
}


def value_for(relation, data_type):
    """A well-formed value for ``relation`` on ``data_type``, so a refusal names the relation, not the value."""
    v = SAMPLE[data_type]
    if relation in ("in", "not_in"):
        return [v]
    if relation in ("between", "not_between"):
        return [v, v]
    if relation in ("in_last", "not_in_last", "in_next", "not_in_next"):
        return [1, "DAY"]
    if relation.startswith("in_calendar_"):
        return 0
    if relation.startswith("name_"):
        return "zzprobe"
    if relation in ("type_is", "type_is_not"):
        return "Shot"
    if relation in ("contains", "not_contains", "starts_with", "ends_with") and data_type != "jsonb":
        return "zzprobe"
    return v
