"""Pure helpers behind schema field writes. Expected strings are api3 answers recorded 2026-11-12."""

from sg_mockgun.fields import field_code, ruby_list, new_field


def test_field_code_from_display_name():
    assert field_code("zzprobe 019 With (Parens)") == "sg_zzprobe_019_with__parens_"
    assert field_code("sg_zzprobe mockgun b") == "sg_sg_zzprobe_mockgun_b"
    assert field_code("Shot Type") == "sg_shot_type"


def test_ruby_list_matches_the_site_layout():
    assert ruby_list(["a", "b"]) == '["a",\n "b"]'
    assert ruby_list([]) == "[]"


def test_new_field_has_the_site_shape():
    f = new_field("Shot", "number", "Frame Count", {"description": "frames"})
    assert f["data_type"] == {"value": "number", "editable": False}
    assert f["name"]["value"] == "Frame Count"
    assert f["description"]["value"] == "frames"
    assert f["entity_type"]["value"] == "Shot"
    assert f["visible"] == {"value": True, "editable": True}
    assert f["properties"]["default_value"]["value"] is None


def test_new_entity_field_keeps_valid_types():
    f = new_field("Shot", "entity", "Hero", {"valid_types": ["Asset"]})
    assert f["properties"]["valid_types"]["value"] == ["Asset"]
