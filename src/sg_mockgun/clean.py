"""Clean a schema read from a live site down to what any site ships. Pure: no I/O.

A field is kept when the site cannot hide it (``visible.editable`` false, sg-groundtruth finding 056)
or when upstream's test schema already carries it, which brings back the few stock template fields
that read hideable. Every custom field is named with an ``sg_`` prefix (finding 019), so a hideable
field without one, and not the reverse side of a custom link (``<type>_sg_...``), is stock too. Custom entities a site has enabled and renamed are dropped with every field and
connection entity that points at them; disabled custom entities stay, as they do on a fresh site.
"""

import copy
import re

_CUSTOM_ENTITY = re.compile(r"^Custom(NonProject|Threaded)?Entity\d+$")
_CUSTOM_CONNECTION = re.compile(r"_sg_.*_Connection$")


def _hideable(field_def):
    return field_def.get("visible", {}).get("editable", True)


def _custom_name(name):
    return name.startswith("sg_") or "_sg_" in name


def _enabled_custom(name, entity_def):
    return bool(_CUSTOM_ENTITY.match(name)) and entity_def.get("visible", {}).get("value", False)


def clean_schema(site_schema, site_entities, upstream_schema):
    """Return ``(schema, entities, report)``; inputs are left untouched."""
    dropped_entities = sorted(
        name
        for name in site_schema
        if _enabled_custom(name, site_entities.get(name, {}))
        or _CUSTOM_CONNECTION.search(name)
        or any(name.startswith(c + "_") for c in site_schema if _enabled_custom(c, site_entities.get(c, {})))
    )
    gone = set(dropped_entities)

    schema, dropped_fields = {}, []
    for entity_type, fields in site_schema.items():
        if entity_type in gone:
            continue
        upstream_fields = upstream_schema.get(entity_type, {})
        kept = {}
        for name, field_def in fields.items():
            if _hideable(field_def) and name not in upstream_fields and _custom_name(name):
                dropped_fields.append((entity_type, name))
                continue
            field_def = copy.deepcopy(field_def)
            valid_types = field_def.get("properties", {}).get("valid_types")
            if valid_types and isinstance(valid_types.get("value"), list):
                valid_types["value"] = [t for t in valid_types["value"] if t not in gone]
            kept[name] = field_def
        schema[entity_type] = kept

    entities = {k: copy.deepcopy(v) for k, v in site_entities.items() if k not in gone}
    report = {"dropped_entities": dropped_entities, "dropped_fields": sorted(dropped_fields)}
    return schema, entities, report
