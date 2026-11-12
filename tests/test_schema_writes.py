"""schema_field_create / update / delete against the bundled schema, worded as the site answers."""

import pytest
from shotgun_api3 import Fault

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


def test_create_returns_the_code_and_the_field_is_writable(sg):
    code = sg.schema_field_create("Shot", "number", "Frame Count")
    assert code == "sg_frame_count"
    assert sg.schema_field_read("Shot", code)[code]["data_type"]["value"] == "number"
    shot = sg.create("Shot", {"code": "sh010", code: 48})
    assert sg.find_one("Shot", [["id", "is", shot["id"]]], [code])[code] == 48


def test_existing_rows_get_the_default(sg):
    shot = sg.create("Shot", {"code": "sh010"})
    code = sg.schema_field_create("Shot", "text", "Notes Two")
    assert sg.find_one("Shot", [["id", "is", shot["id"]]], [code])[code] is None


def test_duplicate_display_name_is_silently_suffixed(sg):
    assert sg.schema_field_create("Version", "text", "zz a") == "sg_zz_a"
    assert sg.schema_field_create("Version", "text", "zz a") == "sg_zz_a_1"
    assert sg.schema_field_create("Version", "text", "zz a") == "sg_zz_a_2"


def test_schema_is_per_instance(sg):
    sg.schema_field_create("Shot", "text", "Only Here")
    other = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    assert "sg_only_here" not in other.schema_field_read("Shot")


@pytest.mark.parametrize("data_type", ["query", "summary", "color", "image", "nope"])
def test_uncreatable_types(sg, data_type):
    with pytest.raises(Fault) as e:
        sg.schema_field_create("Version", data_type, "zz bad")
    assert str(e.value).startswith("API schema_field_create() can't create '%s' data type.  Valid data types:\n[\"calculated\",\n \"checkbox\"," % data_type)


def test_calculated_fails_like_the_site(sg):
    with pytest.raises(Fault, match=r"^API schema_field_create\(\) NoMethodError: undefined method 'strip' for nil$"):
        sg.schema_field_create("Version", "calculated", "zz calc")


def test_entity_needs_valid_types(sg):
    with pytest.raises(Fault, match=r"""^API schema_field_create\(\) missing required 'properties' \["valid_types"\]$"""):
        sg.schema_field_create("Version", "entity", "zz link")


def test_checkbox_needs_a_boolean_default(sg):
    with pytest.raises(Fault, match=r"^API schema_field_create\(\) Crud::ParameterError: Only true or false allowed in checkbox$"):
        sg.schema_field_create("Version", "checkbox", "zz flag")
    assert sg.schema_field_create("Version", "checkbox", "zz flag", {"default_value": False}) == "sg_zz_flag"


def test_unknown_entity_type(sg):
    with pytest.raises(Fault, match=r"^API schema_field_create\(\) invalid/missing string entity 'type':"):
        sg.schema_field_create("NotAType", "text", "zz")


def test_data_type_cannot_change(sg):
    code = sg.schema_field_create("Version", "text", "zz a")
    with pytest.raises(Fault) as e:
        sg.schema_field_update("Version", code, {"data_type": "number"})
    assert str(e.value) == (
        "API schema_field_update() invalid property 'data_type':\n"
        '{"property_name" => "data_type", "value" => "number"}\n'
        "Valid property names:\n"
        '["name",\n "visible",\n "description",\n "summary_default",\n "custom_metadata",\n "unique"]'
    )
    assert sg.schema_field_read("Version", code)[code]["data_type"]["value"] == "text"


def test_update_with_no_properties(sg):
    code = sg.schema_field_create("Version", "text", "zz a")
    with pytest.raises(Fault, match=r"^API schema_field_update\(\) can't create/update with no 'properties':\n\[\]$"):
        sg.schema_field_update("Version", code, {})


def test_rename_keeps_the_code(sg):
    code = sg.schema_field_create("Version", "text", "zz a")
    assert sg.schema_field_update("Version", code, {"name": "zz a renamed"}) is True
    assert sg.schema_field_read("Version", code)[code]["name"]["value"] == "zz a renamed"


def test_update_unknown_field(sg):
    with pytest.raises(Fault, match=r"^API schema_field_update\(\) Version.sg_nope doesn't exist:\n"):
        sg.schema_field_update("Version", "sg_nope", {"name": "x"})


def test_delete_hides_the_field_and_spends_the_name(sg):
    code = sg.schema_field_create("Version", "text", "zz a")
    assert sg.schema_field_delete("Version", code) is True
    with pytest.raises(Fault, match=r"^API schema_field_read\(\) Version.sg_zz_a doesn't exist:\n"):
        sg.schema_field_read("Version", code)
    with pytest.raises(Fault, match=r"^API schema_field_delete\(\) Version.sg_zz_a doesn't exist:\n"):
        sg.schema_field_delete("Version", code)
    for data_type in ("text", "number"):
        with pytest.raises(Fault) as e:
            sg.schema_field_create("Version", data_type, "zz a")
        assert str(e.value) == (
            "API schema_field_create() failed, there is a retired field with the same field_name: "
            "sg_zz_a. Delete the retired field forever from the Trash Page in Shotgun and try again."
        )
    assert code not in sg.schema_field_read("Version")


def test_deleted_field_values_are_no_longer_returned_by_schema(sg):
    code = sg.schema_field_create("Version", "text", "zz a")
    sg.create("Version", {"code": "v1", code: "x"})
    sg.schema_field_delete("Version", code)
    assert code not in sg.schema_read()["Version"]
