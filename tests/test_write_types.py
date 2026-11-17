"""Field types on create and update, against the bundled schema."""

import datetime
import os

import pytest
from shotgun_api3 import Fault, ShotgunError

from sg_mockgun import Shotgun, schemas
from sg_mockgun.writes import TASK_COLOR_HELP, check_value


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    sg.require_project = False  # the create contract is tested in test_records.py
    return sg


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


@pytest.mark.parametrize("value", [{"a": {"b": [1, 2, 3]}, "c": True, "d": None}, [1, "two", None], {}, [], None, "x"])
def test_jsonb_takes_a_hash_array_or_string_on_create(sg, project, value):
    # api3 035: a string is stored too.
    note = sg.create("Note", {"project": project, "meta": value})
    assert stored(sg, note, "meta") == value


@pytest.mark.parametrize("value", [42, 2.5, True])
def test_jsonb_refuses_other_classes(sg, project, value):
    with pytest.raises(Fault, match=r"API create\(\) Note.meta expected \[Hash"):
        sg.create("Note", {"project": project, "meta": value})


@pytest.mark.parametrize("value,echo", [({"a": 1}, '{"a" => 1}'), (None, "nil"), ([], "[]")])
def test_jsonb_is_editable_on_create_only(sg, project, value, echo):
    note = sg.create("Note", {"project": project, "meta": {"a": 1}})
    with pytest.raises(Fault) as err:
        sg.update("Note", note["id"], {"meta": value})
    assert str(err.value) == 'API update() Note.meta is editable on create only:\n{"field_name" => "meta", "value" => %s}' % echo


# field_types/image, api3 035: the client uploads a non-None image as a file, after the row is made.


def test_image_takes_none(sg, project):
    version = sg.create("Version", {"code": "v", "project": project, "image": None})
    sg.update("Version", version["id"], {"image": None})
    assert stored(sg, version, "image") is None


def test_image_string_that_is_not_a_file_raises_after_create(sg, project, tmp_path):
    missing = str(tmp_path / "a.png")
    with pytest.raises(ShotgunError) as err:
        sg.create("Version", {"code": "v_img", "project": project, "image": missing})
    assert not isinstance(err.value, Fault)
    assert str(err.value) == "Path must be a valid file, got '%s'" % missing
    assert len(sg.find("Version", [["code", "is", "v_img"]])) == 1


def test_image_string_that_is_not_a_file_raises_on_update(sg, project, tmp_path):
    version = sg.create("Version", {"code": "v", "project": project})
    with pytest.raises(ShotgunError) as err:
        sg.update("Version", version["id"], {"image": "https://example.com/a.png"})
    assert str(err.value) == "Path must be a valid file, got '%s'" % os.path.abspath("https://example.com/a.png")


def test_image_file_goes_to_upload_thumbnail(sg, project, tmp_path, monkeypatch):
    path = tmp_path / "a.png"
    path.write_bytes(b"x")
    calls = []
    monkeypatch.setattr(sg, "upload_thumbnail", lambda *args, **kwargs: calls.append(args))
    version = sg.create("Version", {"code": "v", "project": project, "image": str(path)})
    assert calls == [("Version", version["id"], str(path))]
    assert "image" in version


# field_types/uuid, calculated, summary, pivot_column; api3 036


@pytest.mark.parametrize("entity,field,base", [
    ("EventLogEntry", "session_uuid", {"event_type": "x"}),
    ("Task", "workload", {"content": "t"}),
    ("Version", "open_notes_count", {"code": "v"}),
    ("Shot", "step_0", {"code": "s"}),
])
@pytest.mark.parametrize("value,echo", [(480, "480"), (None, "nil")])
def test_read_only_types_refuse_every_write(sg, entity, field, base, value, echo):
    body = '{"field_name" => "%s", "value" => %s}' % (field, echo)
    with pytest.raises(Fault) as err:
        sg.create(entity, dict(base, **{field: value}))
    assert str(err.value) == "API create() %s.%s is read only:\n%s" % (entity, field, body)
    row = sg.create(entity, base)
    with pytest.raises(Fault) as err:
        sg.update(entity, row["id"], {field: value})
    assert str(err.value) == "API update() %s.%s is read only:\n%s" % (entity, field, body)


def test_read_only_echo_wraps_a_long_hash(sg):
    event = sg.create("EventLogEntry", {"event_type": "x"})
    with pytest.raises(Fault) as err:
        sg.update("EventLogEntry", event["id"], {"session_uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"})
    assert str(err.value) == (
        'API update() EventLogEntry.session_uuid is read only:\n{"field_name" => "session_uuid",\n'
        ' "value" => "3f2504e0-4f89-11d3-9a0c-0305e82c3301"}')


@pytest.mark.parametrize("verb", ["create", "update"])
def test_editable_summary_field_is_not_supported(verb):
    with pytest.raises(Fault) as err:
        check_value(verb, "Asset", "sg_latest_version", "summary", None, editable=True)
    assert str(err.value) == "API %s() of data type 'summary' not supported in API" % verb


# field_types/checkbox, api3 031


@pytest.mark.parametrize("value", [True, False])
def test_checkbox_takes_a_bool(sg, project, value):
    note = sg.create("Note", {"project": project, "client_note": value})
    assert stored(sg, note, "client_note") is value


@pytest.mark.parametrize("value,tail", [
    (None, "NilClass:\nnil"), (1, "Integer:\n1"), ("true", 'String:\n"true"'), ("false", 'String:\n"false"'),
    ("yes", 'String:\n"yes"'),
])
def test_checkbox_refuses_everything_but_a_bool(sg, project, value, tail):
    with pytest.raises(Fault) as err:
        sg.create("Note", {"project": project, "client_note": value})
    assert str(err.value) == "API create() Note.client_note expected [FalseClass, TrueClass] data type(s) but got " + tail


# field_types/multi_entity, api3 034


def test_multi_entity_refuses_none(sg, project):
    note = sg.create("Note", {"project": project})
    with pytest.raises(Fault) as err:
        sg.update("Note", note["id"], {"tasks": None})
    assert str(err.value) == "API update() Note.tasks expected [Array] data type(s) but got NilClass:\nnil"


# field_types/float, api3 032


@pytest.mark.parametrize("value,expected", [
    (2.5, 2.5), (-1.5, -1.5), (1.23456789, 1.234568), (123456789.12345679, 123456789.123457), (1e-09, 0.0), (None, None),
])
def test_float_takes_a_float_rounded_to_6_dp(sg, project, value, expected):
    version = sg.create("Version", {"code": "v", "project": project, "sg_movie_aspect_ratio": value})
    assert stored(sg, version, "sg_movie_aspect_ratio") == expected


@pytest.mark.parametrize("value,tail", [(2, "Integer:\n2"), (True, "TrueClass:\ntrue"), ("2.5", 'String:\n"2.5"'), ("abc", 'String:\n"abc"')])
def test_float_refuses_int_bool_and_strings(sg, project, value, tail):
    with pytest.raises(Fault) as err:
        sg.create("Version", {"code": "v", "project": project, "sg_movie_aspect_ratio": value})
    assert str(err.value) == (
        "API create() Version.sg_movie_aspect_ratio expected [BigDecimal, Float, NilClass] data type(s) but got " + tail)


# field_types/number, api3 033


@pytest.mark.parametrize("value", [42, -7, None, 2**31 - 1, -(2**31)])
def test_number_takes_an_int(sg, value):
    shot = sg.create("Shot", {"code": "s", "sg_cut_order": value})
    assert stored(sg, shot, "sg_cut_order") == value


@pytest.mark.parametrize("value,tail", [(3.7, "Float:\n3.7"), (True, "TrueClass:\ntrue"), ("7", 'String:\n"7"')])
def test_number_refuses_bool_float_and_strings(sg, value, tail):
    with pytest.raises(Fault) as err:
        sg.create("Shot", {"code": "s", "sg_cut_order": value})
    assert str(err.value) == "API create() Shot.sg_cut_order expected [Integer, NilClass] data type(s) but got " + tail


@pytest.mark.parametrize("value", [2**31, -(2**31) - 1])
def test_number_out_of_range_on_create(sg, value):
    with pytest.raises(Fault) as err:
        sg.create("Shot", {"code": "s_big", "sg_cut_order": value})
    assert str(err.value) == (
        "API create() CRUD ERROR #6: Create failed for [Shot]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n")
    assert sg.find("Shot", [["code", "is", "s_big"]]) == []


def test_number_out_of_range_on_update(sg):
    shot = sg.create("Shot", {"code": "s"})
    with pytest.raises(Fault) as err:
        sg.update("Shot", shot["id"], {"sg_cut_order": 2**31})
    assert str(err.value) == "API update() CRUD ERROR #5: Update failed for [Shot.sg_cut_order]: Invalid statement."


# Task.color, api3 035


def test_a_new_task_reads_pipeline_step(sg):
    task = sg.create("Task", {"content": "t"})
    assert stored(sg, task, "color") == "pipeline_step"


def test_task_color_refuses_none(sg):
    task = sg.create("Task", {"content": "t"})
    with pytest.raises(Fault) as err:
        sg.update("Task", task["id"], {"color": None})
    assert str(err.value) == (
        "API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) Value cannot be nil for Task.color."
        + TASK_COLOR_HELP)
    with pytest.raises(Fault) as err:
        sg.create("Task", {"content": "t_none", "color": None})
    assert str(err.value) == (
        "API create() CRUD ERROR #6: Invalid field value, update failed [5 - Update failed for [Task.color]:  (task.rb) "
        "Value cannot be nil for Task.color." + TASK_COLOR_HELP + "]")
    assert sg.find("Task", [["content", "is", "t_none"]]) == []


@pytest.mark.parametrize("value,reason", [
    ("#ff0000", "Value is not a valid color token: [#ff0000]"),
    ("", "The value is not a valid color expression: []"),
])
def test_task_color_refusal_wording(sg, value, reason):
    task = sg.create("Task", {"content": "t"})
    with pytest.raises(Fault) as err:
        sg.update("Task", task["id"], {"color": value})
    assert str(err.value) == "API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) " + reason + TASK_COLOR_HELP


def test_task_color_help_text_is_the_recorded_text():
    assert TASK_COLOR_HELP.startswith("Unsupported format for Task color field. The Task color can not be nil,")
    assert TASK_COLOR_HELP.endswith("render using the color of the Task's Pipeline Step.")


# Task.splits, api3 037

SPLIT_A = {"start": "2026-01-05", "end": "2026-01-06"}
SPLIT_B = {"start": "2026-01-08", "end": "2026-01-09"}


@pytest.mark.parametrize("value,expected", [([SPLIT_A], None), ([], None), (None, None), ([SPLIT_A, SPLIT_B], [SPLIT_A, SPLIT_B])])
def test_splits_store_two_or_more(sg, value, expected):
    task = sg.create("Task", {"content": "t"})
    sg.update("Task", task["id"], {"splits": value})
    assert stored(sg, task, "splits") == expected
    created = sg.create("Task", {"content": "t", "splits": value})
    assert stored(sg, created, "splits") == expected


def test_splits_refuse_a_hash_and_a_string(sg):
    task = sg.create("Task", {"content": "t"})
    with pytest.raises(Fault) as err:
        sg.update("Task", task["id"], {"splits": {"a": 1}})
    assert str(err.value) == "API update() CRUD ERROR #5: Update failed for [Task.splits]: no implicit conversion of String into Integer"
    with pytest.raises(Fault) as err:
        sg.update("Task", task["id"], {"splits": "hello"})
    assert str(err.value) == (
        "API update() Task.splits expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n"
        " ActionDispatch::Http::Parameters,\n ActionController::Parameters,\n Array,\n NilClass] data type(s) "
        'but got String:\n"hello"')


# create return, server-set fields, api3 038


def test_create_returns_the_fields_sent(sg, project):
    version = sg.create("Version", {"project": project, "code": "v"})
    assert sorted(version) == ["code", "id", "project", "type"]
    assert version["project"]["name"] == "p"


def test_create_return_fields_add_to_the_fields_sent(sg, project):
    fields = ["created_at", "updated_at", "created_by", "updated_by", "cached_display_name"]
    version = sg.create("Version", {"project": project, "code": "v"}, return_fields=fields)
    assert sorted(version) == sorted(fields + ["code", "id", "project", "type"])


def test_a_new_row_has_server_set_fields(sg, project):
    version = sg.create("Version", {"project": project, "code": "v"})
    row = sg.find_one("Version", [["id", "is", version["id"]]],
                      ["created_at", "updated_at", "created_by", "updated_by", "cached_display_name", "open_notes_count"])
    assert isinstance(row["created_at"], datetime.datetime) and row["created_at"] == row["updated_at"]
    assert row["created_by"]["type"] == "ApiUser" and row["created_by"] == row["updated_by"]
    assert row["created_by"]["name"] == "x"
    assert row["cached_display_name"] == "v"
    assert row["open_notes_count"] == 0  # api3 036


def test_created_at_is_accepted_on_create(sg, project):
    when = datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
    version = sg.create("Version", {"project": project, "code": "v", "created_at": when})
    assert stored(sg, version, "created_at") == when


@pytest.mark.parametrize("field", ["created_at", "updated_at"])
def test_created_at_and_updated_at_are_refused_on_update(sg, project, field):
    version = sg.create("Version", {"project": project, "code": "v"})
    when = datetime.datetime(2020, 1, 2, 9, 4, 5, tzinfo=datetime.timezone.utc)
    with pytest.raises(Fault) as err:
        sg.update("Version", version["id"], {field: when})
    assert str(err.value) == (
        'API update() Version.%s is editable on create only:\n{"field_name" => "%s", "value" => "2020-01-02T09:04:05Z"}'
        % (field, field))


# unknown and dotted names, api3 039


@pytest.mark.parametrize("verb", ["create", "update"])
def test_an_unknown_field_is_refused(sg, project, verb):
    version = sg.create("Version", {"project": project, "code": "v"})
    with pytest.raises(Fault) as err:
        if verb == "create":
            sg.create("Version", {"project": project, "code": "v2", "sg_not_a_field": "x"})
        else:
            sg.update("Version", version["id"], {"description": "changed", "sg_not_a_field": "x"})
    assert str(err.value) == (
        'API %s() Version.sg_not_a_field doesn\'t exist:\n{"field_name" => "sg_not_a_field", "value" => "x"}' % verb)
    assert sg.find("Version", [["code", "is", "v2"]]) == []
    assert stored(sg, version, "description") is None


def test_a_dotted_name_writes_the_linked_row(sg, project):
    shot = sg.create("Shot", {"project": project, "code": "s"})
    version = sg.create("Version", {"project": project, "code": "v", "entity": shot})
    result = sg.update("Version", version["id"], {"entity.Shot.description": "via dotted"})
    result = result[0] if isinstance(result, list) else result
    assert result["entity.Shot.description"] == "via dotted"
    assert stored(sg, shot, "description") == "via dotted"
