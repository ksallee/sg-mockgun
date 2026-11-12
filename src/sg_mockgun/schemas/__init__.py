"""Schemas bundled with sg-mockgun, each pulled from a live site by tools/pull_schema.py."""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def paths(name="fpt_8_91"):
    """``(schema_path, schema_entity_path)`` for a bundled schema, ready for ``Shotgun.set_schema_paths``."""
    folder = os.path.join(_HERE, name)
    return os.path.join(folder, "schema.pickle"), os.path.join(folder, "schema_entity.pickle")
