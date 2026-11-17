"""Schema field writes over api3: finding 019 for codes, finding 040 for what a delete leaves."""

import pytest
import shotgun_api3

API3 = "docs/api3-probe-2026-11-12.md"


@pytest.mark.finding("019", api3=API3)
@pytest.mark.cell("schema_field_create", "-", "text")
def test_code_is_sg_and_the_lowercased_display_name(fields, run_token):
    assert fields.create("Shot", "text", "zzprobe mockgun %s With (Parens)" % run_token) == (
        "sg_zzprobe_mockgun_%s_with__parens_" % run_token)


@pytest.mark.finding("019", api3=API3)
@pytest.mark.cell("schema_field_create", "-", "number")
def test_a_taken_display_name_is_suffixed(fields, run_token):
    name = "zzprobe mockgun %s dup" % run_token
    first = fields.create("Version", "number", name)
    assert fields.create("Version", "number", name) == first + "_1"


@pytest.mark.finding("040", api3=API3)
@pytest.mark.cell("schema_field_delete", "-", "text")
def test_a_deleted_field_keeps_its_code_taken(site, fields, run_token):
    name = "zzprobe mockgun %s gone" % run_token
    code = fields.create("Version", "text", name)
    assert fields.delete("Version", code) is True
    with pytest.raises(shotgun_api3.Fault, match="retired field with the same field_name"):
        fields.create("Version", "number", name)


@pytest.mark.finding("040", api3=API3)
@pytest.mark.cell("schema_field_update", "-", "text")
def test_data_type_cannot_be_updated(site, fields, run_token):
    code = fields.create("Version", "text", "zzprobe mockgun %s typed" % run_token)
    with pytest.raises(shotgun_api3.Fault, match="invalid property 'data_type'"):
        fields.update("Version", code, {"data_type": "number"})
    assert site.schema_field_read("Version", code)[code]["data_type"]["value"] == "text"
