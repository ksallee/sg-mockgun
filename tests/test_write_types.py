"""Field types on create and update, against the bundled schema."""

import pytest
from shotgun_api3 import ShotgunError

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


@pytest.fixture
def project(sg):
    return sg.create("Project", {"name": "p"})


def stored(sg, entity, field):
    return sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]


# field_types/color


@pytest.mark.parametrize("value", ["255,128,0", "0,0,0", "pipeline_step"])
def test_color_takes_a_triple_or_pipeline_step(sg, value):
    task = sg.create("Task", {"content": "t", "color": value})
    assert stored(sg, task, "color") == value


@pytest.mark.parametrize("value,expanded", [("Blue", "2,149,216"), ("red", "253,1,0"), ("Black", "45,45,45")])
def test_color_legacy_names_are_stored_expanded(sg, value, expanded):
    task = sg.create("Task", {"content": "t", "color": value})
    assert stored(sg, task, "color") == expanded


@pytest.mark.parametrize("value,message", [
    ("#ff8000", "Value is not a valid color token"),
    ("Gray", "Value is not a valid color token"),
    ("255, 128, 0", "At least one component value is not valid"),
    ("-1,0,0", "At least one component value is not valid"),
    ("255.0,128.0,0.0", "At least one component value is not valid"),
    ("300,0,0", "At least one component value is out of range"),
    ("255,128", "The value is not a valid color expression"),
    ("255,128,0,255", "The value is not a valid color expression"),
    ([255, 128, 0], "expected [String, NilClass] data type(s) but got Array"),
    (16744448, "expected [String, NilClass] data type(s) but got Integer"),
])
def test_color_refuses_malformed_values(sg, value, message):
    with pytest.raises(ShotgunError) as err:
        sg.create("Task", {"content": "t", "color": value})
    assert message in str(err.value)


# field_types/timecode


@pytest.fixture
def timecode(sg):
    return sg.schema_field_create("Sequence", "timecode", "TC")


@pytest.mark.parametrize("value", [3600000, 0, -3600000, 2**31 - 1, -(2**31), None])
def test_timecode_takes_a_signed_32_bit_int(sg, timecode, value):
    seq = sg.create("Sequence", {"code": "s", timecode: value})
    assert stored(sg, seq, timecode) == value


@pytest.mark.parametrize("value,cls", [("01:00:00:00", "String"), ("3600000", "String"), (1.5, "Float"), (True, "TrueClass")])
def test_timecode_refuses_other_classes(sg, timecode, value, cls):
    with pytest.raises(ShotgunError) as err:
        sg.create("Sequence", {"code": "s", timecode: value})
    assert "expected [Integer, NilClass] data type(s) but got %s" % cls in str(err.value)


def test_timecode_refuses_out_of_range(sg, timecode):
    with pytest.raises(ShotgunError, match="integer out of range"):
        sg.create("Sequence", {"code": "s", timecode: 2**31})
    seq = sg.create("Sequence", {"code": "s"})
    with pytest.raises(ShotgunError, match="Invalid statement"):
        sg.update("Sequence", seq["id"], {timecode: -(2**31) - 1})


# field_types/jsonb


@pytest.mark.parametrize("value", [{"a": {"b": [1, 2, 3]}, "c": True, "d": None}, [1, "two", None], {}, [], None])
def test_jsonb_takes_a_hash_or_array_on_create(sg, project, value):
    note = sg.create("Note", {"project": project, "meta": value})
    assert stored(sg, note, "meta") == value


@pytest.mark.parametrize("value", [42, 2.5, True, "hello", '{"a": 1}', ""])
def test_jsonb_refuses_other_classes(sg, project, value):
    with pytest.raises(ShotgunError, match=r"API create\(\) Note.meta expected \[Hash"):
        sg.create("Note", {"project": project, "meta": value})


@pytest.mark.parametrize("value", [{"a": 1}, {}, [], None])
def test_jsonb_is_editable_on_create_only(sg, project, value):
    note = sg.create("Note", {"project": project, "meta": {"a": 1}})
    with pytest.raises(ShotgunError, match=r"API update\(\) Note.meta is editable on create only."):
        sg.update("Note", note["id"], {"meta": value})


# field_types/image


def test_image_takes_none(sg, project):
    version = sg.create("Version", {"code": "v", "project": project, "image": None})
    sg.update("Version", version["id"], {"image": None})


@pytest.mark.parametrize("value,message", [
    ("https://example.com/thumb.png", "expected [Hash"),
    ("", "expected [Hash"),
    ({"url": "https://example.com/thumb.png"}, "invalid/missing entity hash string 'type'"),
    ({"type": "Attachment", "id": 1}, "Write access of the 'image' data type (Version.image) not yet supported in API"),
])
def test_image_refuses_every_other_value(sg, project, value, message):
    with pytest.raises(ShotgunError) as err:
        sg.create("Version", {"code": "v", "project": project, "image": value})
    assert message in str(err.value)
    version = sg.create("Version", {"code": "v", "project": project})
    with pytest.raises(ShotgunError) as err:
        sg.update("Version", version["id"], {"image": value})
    assert message in str(err.value)


# field_types/uuid, calculated, summary, pivot_column


@pytest.mark.parametrize("entity,field,base", [
    ("EventLogEntry", "session_uuid", {"event_type": "x"}),
    ("Task", "workload", {"content": "t"}),
    ("Version", "open_notes_count", {"code": "v"}),
    ("Shot", "step_0", {"code": "s"}),
])
@pytest.mark.parametrize("value", ["fin", 480, None])
def test_read_only_types_refuse_every_write(sg, entity, field, base, value):
    with pytest.raises(ShotgunError, match=r"API create\(\) %s.%s is read only." % (entity, field)):
        sg.create(entity, dict(base, **{field: value}))
    row = sg.create(entity, base)
    with pytest.raises(ShotgunError, match=r"API update\(\) %s.%s is read only." % (entity, field)):
        sg.update(entity, row["id"], {field: value})


# field_types/checkbox


@pytest.mark.parametrize("value,expected", [(True, True), (False, False), ("true", True), ("false", False)])
def test_checkbox_takes_bool_or_its_string(sg, project, value, expected):
    note = sg.create("Note", {"project": project, "client_note": value})
    assert stored(sg, note, "client_note") is expected


@pytest.mark.parametrize("value,message", [
    (None, "expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil"),
    (1, "expected [String, FalseClass, TrueClass] data type(s) but got Integer: 1"),
    ("1", "Invalid data for 'checkbox' data type. Value: 1"),
    ("yes", "Invalid data for 'checkbox' data type. Value: yes"),
])
def test_checkbox_refuses_none_and_other_values(sg, project, value, message):
    with pytest.raises(ShotgunError) as err:
        sg.create("Note", {"project": project, "client_note": value})
    assert message in str(err.value)


# field_types/multi_entity


def test_multi_entity_refuses_none(sg, project):
    note = sg.create("Note", {"project": project})
    with pytest.raises(ShotgunError, match=r"expected \[Array, Hash\] data type\(s\) but got NilClass: nil"):
        sg.update("Note", note["id"], {"tasks": None})


# field_types/float


@pytest.mark.parametrize("value,expected", [
    (2.5, 2.5), (-1.5, -1.5), ("3.75", 3.75), (" 4.5 ", 4.5),
    (1.23456789012345, 1.234568), (123456789.12345679, 123456789.123457), (1e-09, 0.0), (None, None),
])
def test_float_takes_a_float_or_numeric_string_rounded_to_6_dp(sg, project, value, expected):
    version = sg.create("Version", {"code": "v", "project": project, "sg_movie_aspect_ratio": value})
    assert stored(sg, version, "sg_movie_aspect_ratio") == expected


@pytest.mark.parametrize("value,message", [
    (2, "expected [String, BigDecimal, Float, NilClass] data type(s) but got Integer: 2"),
    (True, "but got TrueClass: true"),
    ("abc", "Invalid data for 'float' data type. Value: abc"),
    ("", "Invalid data for 'float' data type. Value: "),
])
def test_float_refuses_int_bool_and_other_strings(sg, project, value, message):
    with pytest.raises(ShotgunError) as err:
        sg.create("Version", {"code": "v", "project": project, "sg_movie_aspect_ratio": value})
    assert message in str(err.value)


# field_types/number


@pytest.mark.parametrize("value,expected", [(42, 42), ("42", 42), (-7, -7), (None, None), (2**31 - 1, 2**31 - 1), (-(2**31), -(2**31))])
def test_number_takes_an_int_or_numeric_string(sg, value, expected):
    shot = sg.create("Shot", {"code": "s", "sg_cut_order": value})
    assert stored(sg, shot, "sg_cut_order") == expected


@pytest.mark.parametrize("value,message", [
    (3.7, "expected [String, Integer, NilClass] data type(s) but got Float: 3.7"),
    (True, "expected [String, Integer, NilClass] data type(s) but got TrueClass: true"),
    ("42abc", "Invalid data for 'number' data type. Value: 42abc"),
    (2**31, "integer out of range"),
    (-(2**31) - 1, "integer out of range"),
    ("2147483648", "integer out of range"),
])
def test_number_refuses_bool_float_and_out_of_range(sg, value, message):
    with pytest.raises(ShotgunError) as err:
        sg.create("Shot", {"code": "s", "sg_cut_order": value})
    assert message in str(err.value)


def test_number_out_of_range_on_update(sg):
    shot = sg.create("Shot", {"code": "s"})
    with pytest.raises(ShotgunError, match=r"Update failed for \[Shot.sg_cut_order\]: Invalid statement."):
        sg.update("Shot", shot["id"], {"sg_cut_order": 2**31})
