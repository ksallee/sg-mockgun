"""Filter relations, null rules and refusals per data type, as the site answers them over REST."""

import pytest
from shotgun_api3 import ShotgunError

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


def put(sg, entity_type, field, values):
    """Create one row per value, writing the value straight into the store."""
    ids = []
    for value in values:
        row = sg.create(entity_type, {})
        sg._db[entity_type][row["id"]][field] = value
        ids.append(row["id"])
    return ids


def match(sg, entity_type, ids, flt):
    """The positions in ``ids`` of the rows that match ``flt``."""
    found = {r["id"] for r in sg.find(entity_type, [flt])}
    return [i for i, row_id in enumerate(ids) if row_id in found]


# field_types/number: rows 1001, 0, null, null.
@pytest.mark.parametrize("entity_type,field", [
    ("Shot", "sg_cut_order"),                  # number
    ("Task", "time_percent_of_est"),           # percent
    ("Task", "duration"),                      # duration
])
def test_whole_number_relations_and_null_rules(sg, entity_type, field):
    ids = put(sg, entity_type, field, [1001, 0, None, None])
    assert match(sg, entity_type, ids, [field, "is", None]) == [2, 3]
    assert match(sg, entity_type, ids, [field, "is_not", 1001]) == [1, 2, 3]
    assert match(sg, entity_type, ids, [field, "greater_than", -1]) == [0, 1]
    assert match(sg, entity_type, ids, [field, "less_than", 1]) == [1]
    assert match(sg, entity_type, ids, [field, "between", [0, 2000]]) == [0, 1]
    assert match(sg, entity_type, ids, [field, "in", [1001, 0]]) == [0, 1]
    assert match(sg, entity_type, ids, [field, "not_in", [1001]]) == [1, 2, 3]
    assert match(sg, entity_type, ids, [field, "not_in", [999999]]) == [0, 1, 2, 3]


def test_timecode_takes_the_numeric_relations(sg):
    # field_types/timecode
    field = sg.schema_field_create("Sequence", "timecode", "TC")
    ids = put(sg, "Sequence", field, [3600000, 0, None, None])
    assert match(sg, "Sequence", ids, [field, "between", [0, 7200000]]) == [0, 1]
    assert match(sg, "Sequence", ids, [field, "not_in", [999999999]]) == [0, 1, 2, 3]
    assert match(sg, "Sequence", ids, [field, "greater_than", -1]) == [0, 1]


def test_float_not_in_includes_null(sg):
    # field_types/float: rows 0.0, null, 1.0
    ids = put(sg, "Version", "sg_movie_aspect_ratio", [0.0, None, 1.0])
    assert match(sg, "Version", ids, ["sg_movie_aspect_ratio", "not_in", [1.0]]) == [0, 1]
    assert match(sg, "Version", ids, ["sg_movie_aspect_ratio", "less_than", 2.0]) == [0, 2]


@pytest.mark.parametrize("value", [1001, [1001], [0, 1, 2]])
def test_between_needs_two_values(sg, value):
    # field_types/number
    put(sg, "Shot", "sg_cut_order", [1001])
    expected = "API read() 'between' 'relation' expects a 2-element array: %s" % (
        "[1001]" if value == 1001 else str(value))
    with pytest.raises(ShotgunError) as e:
        sg.find("Shot", [["sg_cut_order", "between", value]])
    assert str(e.value) == expected


@pytest.mark.parametrize("field", ["sg_cut_order", "created_at"])
def test_not_between_is_refused(sg, field):
    # field_types/number, field_types/date_time: no type lists not_between.
    put(sg, "Shot", field, [None])
    with pytest.raises(ShotgunError, match="doesn't support 'not_between' 'relation'"):
        sg.find("Shot", [[field, "not_between", [1, 2]]])


def test_date_null_rules_and_not_in(sg):
    # field_types/date: a dated row and a null row.
    ids = put(sg, "Task", "due_date", ["2026-09-02", None])
    assert match(sg, "Task", ids, ["due_date", "not_in", ["2026-09-02"]]) == [1]
    assert match(sg, "Task", ids, ["due_date", "is_not", "2026-09-02"]) == [1]
    assert match(sg, "Task", ids, ["due_date", "greater_than", "2026-09-01"]) == [0]
    assert match(sg, "Task", ids, ["due_date", "less_than", "2026-09-03"]) == [0]
    assert match(sg, "Task", ids, ["due_date", "between", ["2026-09-03", "2026-09-01"]]) == [0]
    assert match(sg, "Task", ids, ["due_date", "between", ["2026-09-02", None]]) == []


def test_entity_type_relations_are_case_sensitive(sg):
    # field_types/entity_type
    ids = put(sg, "Step", "entity_type", ["Shot", "Asset", None])
    assert match(sg, "Step", ids, ["entity_type", "is", "shot"]) == []
    assert match(sg, "Step", ids, ["entity_type", "is_not", "Shot"]) == [1, 2]
    assert match(sg, "Step", ids, ["entity_type", "in", ["Shot", "Asset"]]) == [0, 1]
    assert match(sg, "Step", ids, ["entity_type", "not_in", ["Shot"]]) == [1, 2]
    assert match(sg, "Step", ids, ["entity_type", "is", ""]) == [2]


def test_color_relations(sg):
    # field_types/color
    ids = put(sg, "Project", "color", ["0,126,174", None])
    assert match(sg, "Project", ids, ["color", "is", "0,126,174"]) == [0]
    assert match(sg, "Project", ids, ["color", "is_not", "0,126,174"]) == [1]
    assert match(sg, "Project", ids, ["color", "in", ["0,126,174"]]) == [0]
    assert match(sg, "Project", ids, ["color", "not_in", ["0,126,174"]]) == [1]


def test_uuid_relations_and_null_refusal(sg):
    # field_types/uuid: "" matches the null rows, a null value is refused.
    a = "11111111-2222-11df-8888-999999999999"
    ids = put(sg, "Icon", "uuid", [a, None])
    assert match(sg, "Icon", ids, ["uuid", "is", a]) == [0]
    assert match(sg, "Icon", ids, ["uuid", "is", ""]) == [1]
    assert match(sg, "Icon", ids, ["uuid", "is_not", a]) == [1]
    assert match(sg, "Icon", ids, ["uuid", "not_in", [a]]) == [1]
    with pytest.raises(ShotgunError) as e:
        sg.find("Icon", [["uuid", "is", None]])
    assert str(e.value) == "API read() Icon.uuid expected [String] data type(s) but got NilClass: nil"


def test_in_needs_one_value(sg):
    # field_types/uuid
    put(sg, "Icon", "uuid", [None])
    with pytest.raises(ShotgunError) as e:
        sg.find("Icon", [["uuid", "in", []]])
    assert str(e.value) == "API read() 'in' 'relation' expects at least a 1-element array: []"


def test_image_takes_only_none(sg):
    # field_types/image
    ids = put(sg, "Version", "image", ["https://x/thumb.jpg", None])
    assert match(sg, "Version", ids, ["image", "is", None]) == [1]
    assert match(sg, "Version", ids, ["image", "is_not", None]) == [0]
    with pytest.raises(ShotgunError) as e:
        sg.find("Version", [["image", "is", ""]])
    assert str(e.value) == "API read() 'is' 'relation' expects a nil value for 'image' data type: [\"\"]"


def test_jsonb_relations(sg):
    # field_types/jsonb
    ids = put(sg, "Note", "meta", [{"a": {"b": [1, 2, 3]}, "c": 1}, [{"x": 1}], None])
    assert match(sg, "Note", ids, ["meta", "is", {"c": 1, "a": {"b": [1, 2, 3]}}]) == [0]
    assert match(sg, "Note", ids, ["meta", "is", {"a": {"b": [1, 2, 3]}}]) == []
    assert match(sg, "Note", ids, ["meta", "is", None]) == [2]
    assert match(sg, "Note", ids, ["meta", "is_not", {"a": {"b": [1, 2, 3]}, "c": 1}]) == [1, 2]
    assert match(sg, "Note", ids, ["meta", "contains", {"a": {"b": [1]}}]) == [0]
    assert match(sg, "Note", ids, ["meta", "contains", {"c": 1.0}]) == [0]
    assert match(sg, "Note", ids, ["meta", "contains", {}]) == [0]
    assert match(sg, "Note", ids, ["meta", "contains", {"x": 1}]) == []
    assert match(sg, "Note", ids, ["meta", "not_contains", {"a": {"b": [1]}}]) == [1, 2]


def test_audit_trail_filter_is_ignored(sg):
    # report 008: any relation on EventLogEntry.audit_trail returns every row.
    ids = put(sg, "EventLogEntry", "audit_trail", [{"a": 1}, None])
    assert match(sg, "EventLogEntry", ids, ["audit_trail", "is", None]) == [0, 1]
    assert match(sg, "EventLogEntry", ids, ["audit_trail", "is_not", None]) == [0, 1]
    assert match(sg, "EventLogEntry", ids, ["audit_trail", "contains", {"zz": 1}]) == [0, 1]


@pytest.mark.parametrize("operator", ["is", "is_not"])
def test_checkbox_refuses_none(sg, operator):
    # field_types/checkbox
    put(sg, "Version", "flagged", [False])
    with pytest.raises(ShotgunError) as e:
        sg.find("Version", [["flagged", operator, None]])
    assert str(e.value) == (
        "API read() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil")


@pytest.mark.parametrize("field", ["sg_version_type", "sg_status_list"])
def test_list_matches_case_insensitively(sg, field):
    # field_types/list, field_types/status_list
    ids = put(sg, "Version", field, ["Type A", "Type B", None])
    assert match(sg, "Version", ids, [field, "is", "type a"]) == [0]
    assert match(sg, "Version", ids, [field, "is_not", "TYPE A"]) == [1, 2]
    assert match(sg, "Version", ids, [field, "in", ["type a", "zzprobe"]]) == [0]
    assert match(sg, "Version", ids, [field, "not_in", ["type a"]]) == [1, 2]
    assert match(sg, "Version", ids, [field, "is", ""]) == [2]


def test_unknown_operator_has_the_site_wording(sg):
    # finding 017
    put(sg, "Shot", "code", ["sh010"])
    with pytest.raises(ShotgunError) as e:
        sg.find("Shot", [["code", "definitely_not_an_operator", "x"]])
    assert str(e.value) == (
        "API read() Shot.code's 'text' data type doesn't support 'definitely_not_an_operator' 'relation'. "
        'Valid relations: ["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]')


def test_list_refuses_text_relations(sg):
    # finding 017, probe 068
    put(sg, "Note", "sg_note_type", ["Client"])
    with pytest.raises(ShotgunError, match=r"^API read\(\) Note.sg_note_type's 'list' data type doesn't support "
                                            r"'contains' 'relation'\. Valid relations: \[\"is\", \"is_not\", "
                                            r"\"in\", \"not_in\"\]$"):
        sg.find("Note", [["sg_note_type", "contains", "Client"]])


def test_unknown_operator_names_the_leaf_of_a_dotted_path(sg):
    shot = sg.create("Shot", {"code": "sh010"})
    sg.create("Version", {"entity": shot})
    with pytest.raises(ShotgunError, match=r"^API read\(\) Shot.code's 'text' data type doesn't support 'bogus'"):
        sg.find("Version", [["entity.Shot.code", "bogus", "x"]])


@pytest.mark.parametrize("entity_type,field,data_type", [
    ("Task", "workload", "calculated"),
    ("Task", "splits", "serializable"),
    ("Shot", "open_notes_count", "summary"),
    ("Version", "sg_uploaded_movie", "url"),
])
def test_unfilterable_types(sg, entity_type, field, data_type):
    # finding 017
    put(sg, entity_type, field, [None])
    with pytest.raises(ShotgunError) as e:
        sg.find(entity_type, [[field, "is", None]])
    assert str(e.value) == "API read() %s.%s's '%s' data type cannot be used in a filter." % (
        entity_type, field, data_type)


def test_password_is_unfilterable(sg):
    # finding 017
    field = sg.schema_field_create("Shot", "text", "Secret")
    sg._schema["Shot"][field]["data_type"]["value"] = "password"
    put(sg, "Shot", field, [None])
    with pytest.raises(ShotgunError, match="'password' data type cannot be used in a filter."):
        sg.find("Shot", [[field, "is", None]])


def test_pivot_column_is_not_supported(sg):
    # field_types/pivot_column
    put(sg, "Shot", "step_8", [None])
    with pytest.raises(ShotgunError) as e:
        sg.find("Shot", [["step_8", "is", None]])
    assert str(e.value) == "API read() of data type 'pivot_column' not supported in API"
    with pytest.raises(ShotgunError, match=r"'pivot_column' data type doesn't support 'contains' 'relation'\. "
                                           r"Valid relations: \[\"is\", \"is_not\"\]$"):
        sg.find("Shot", [["step_8", "contains", "fin"]])
