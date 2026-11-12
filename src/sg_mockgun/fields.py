"""Pure helpers for schema field writes. No I/O, no state.

Every string here is what a Flow PT 8.91 site answered over api3 on 2026-11-12
(docs/api3-probe-2026-11-12.md) unless a comment says otherwise.
"""

import re

# The list the site prints when it refuses a data type, in its order.
CREATABLE_TYPES = [
    "calculated", "checkbox", "currency", "date", "date_time", "duration", "entity", "float", "footage",
    "list", "multi_entity", "number", "percent", "status_list", "text", "timecode", "url", "uuid",
]

# What schema_field_update accepts, in the order the site lists them.
UPDATABLE_PROPERTIES = ["name", "visible", "description", "summary_default", "custom_metadata", "unique"]


def field_code(display_name):
    """The programmatic name the site gives a new field: ``sg_`` + lowercase, non-alphanumerics to ``_``."""
    return "sg_" + re.sub(r"[^a-z0-9]", "_", display_name.lower())


def ruby_inspect(value):
    """One-line Ruby ``inspect`` of a Python value, as the site echoes parameters back."""
    if isinstance(value, dict):
        return "{" + ", ".join("%s => %s" % (ruby_inspect(k), ruby_inspect(v)) for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(ruby_inspect(v) for v in value) + "]"
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')
    return str(value)


def ruby_list(items):
    """A list of strings laid out the way the site's ``pp`` prints one: one item per line."""
    if not items:
        return "[]"
    return "[" + ",\n ".join(ruby_inspect(i) for i in items) + "]"


def ruby_params(params):
    """A request echoed back in an error. One line when short, one key per line otherwise.

    The site's exact line breaking for long payloads was not recorded; this follows ``pp``'s
    80-column rule closely enough to read the same.
    """
    flat = ruby_inspect(params)
    if len(flat) <= 80:
        return flat
    return "{" + ",\n ".join("%s => %s" % (ruby_inspect(k), ruby_inspect(v)) for k, v in params.items()) + "}"


def new_field(entity_type, data_type, display_name, properties=None):
    """A field definition in the shape ``schema_field_read`` returns on a live site."""
    properties = dict(properties or {})

    def ro(v):
        return {"value": v, "editable": False}

    def rw(v):
        return {"value": v, "editable": True}

    props = {
        "default_value": rw(properties.pop("default_value", None)),
        "summary_default": rw(properties.pop("summary_default", "none")),
    }
    if data_type in ("entity", "multi_entity"):
        props["valid_types"] = rw(list(properties.pop("valid_types", [])))
    if data_type in ("list", "status_list"):
        props["valid_values"] = rw(list(properties.pop("valid_values", [])))
    description = properties.pop("description", "")
    for key, value in properties.items():
        props[key] = rw(value)
    return {
        "custom_metadata": rw(""),
        "data_type": ro(data_type),
        "description": rw(description),
        "editable": ro(True),
        "entity_type": ro(entity_type),
        "mandatory": ro(False),
        "name": rw(display_name),
        "properties": props,
        "ui_value_displayable": ro(True),
        "unique": rw(False),
        "visible": rw(True),
    }
