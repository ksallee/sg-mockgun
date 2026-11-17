"""Filters refuse and match as a site answers over api3 (docs/api3/001 to 006, 010 to 015, 021, 027, 030)."""

import datetime

import pytest
import shotgun_api3.shotgun as api3
from shotgun_api3 import Fault

from sg_mockgun import Shotgun, schemas

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    sg.set_clock(lambda: NOW)
    return sg


def put(sg, entity_type, field, values):
    """One row per value, the value written straight into the store."""
    ids = []
    for value in values:
        row = sg.create(entity_type, {})
        sg._db[entity_type][row["id"]][field] = value
        ids.append(row["id"])
    return ids


def match(sg, entity_type, ids, filters):
    found = {r["id"] for r in sg.find(entity_type, filters)}
    return [i for i, row_id in enumerate(ids) if row_id in found]


def fault(sg, entity_type, filters, **kwargs):
    with pytest.raises(Fault) as err:
        sg.find(entity_type, filters, **kwargs)
    return str(err.value)


# api3 001: one message, the sent filter and the list as Ruby pp at 80 columns.
def test_unknown_relation_on_text_wraps_filter_and_list(sg):
    assert fault(sg, "Shot", [["code", "definitely_not_an_operator", "x"]]) == (
        "API read() Shot.code's 'text' data type doesn't support 'definitely_not_an_operator' 'relation':\n"
        '{"path" => "code",\n'
        ' "relation" => "definitely_not_an_operator",\n'
        ' "values" => ["x"]}\n'
        "Valid relations:\n"
        '["contains",\n "not_contains",\n "is",\n "is_not",\n "starts_with",\n "ends_with",\n "in",\n "not_in"]'
    )


def test_short_filter_and_list_stay_on_one_line(sg):
    assert fault(sg, "Version", [["frame_count", "not_between", [1]]]) == (
        "API read() Version.frame_count's 'number' data type doesn't support 'not_between' 'relation':\n"
        '{"path" => "frame_count", "relation" => "not_between", "values" => [1]}\n'
        "Valid relations:\n"
        '["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]'
    )


def test_unfilterable_type_echoes_the_filter(sg):
    assert fault(sg, "Version", [["sg_uploaded_movie", "definitely_not_an_operator", "x"]]) == (
        "API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter:\n"
        '{"path" => "sg_uploaded_movie",\n'
        ' "relation" => "definitely_not_an_operator",\n'
        ' "values" => ["x"]}'
    )


# api3 002
@pytest.mark.parametrize("entity_type, field", [("Shot", "code"), ("Version", "entity"), ("Version", "created_at")])
@pytest.mark.parametrize("relation", ["not_between", "name_starts_with", "name_ends_with"])
def test_mockgun_only_relations_are_refused(sg, entity_type, field, relation):
    assert "doesn't support '%s' 'relation'" % relation in fault(sg, entity_type, [[field, relation, "x"]])


# api3 003
@pytest.mark.parametrize("value, echo", [([1], "[1]"), ([1, 50, 100], "[1, 50, 100]"), (1, "[1]"), ([], "[]")])
def test_between_arity(sg, value, echo):
    msg = fault(sg, "Version", [["frame_count", "between", value]])
    assert msg == "API read() 'between' 'relation' expects a 2-element array:\n" + echo


# api3 005
@pytest.mark.parametrize("relation", ["is", "is_not"])
def test_checkbox_none(sg, relation):
    assert fault(sg, "Version", [["flagged", relation, None]]) == (
        "API read() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil")


# api3 006
def test_calculated_filters_with_its_result_type(sg):
    ids = put(sg, "Task", "workload", [3000, 4000, None])
    assert match(sg, "Task", ids, [["workload", "is", 3000]]) == [0]
    assert match(sg, "Task", ids, [["workload", "greater_than", 3000]]) == [1]
    assert match(sg, "Task", ids, [["workload", "between", [3000, 3000]]]) == [0]
    assert match(sg, "Task", ids, [["workload", "in", [3000]]]) == [0]
    assert match(sg, "Task", ids, [["workload", "is", None]]) == [2]


@pytest.mark.parametrize("relation", ["in", "not_in"])
def test_calculated_in_none_is_a_crud_error(sg, relation):
    assert fault(sg, "Task", [["workload", relation, [None]]]) == (
        "API read() CRUD ERROR #10: Read failed for entity type [Task]")


@pytest.fixture
def links(sg):
    seq = sg.create("Sequence", {"code": "seq"})
    shot = sg.create("Shot", {"code": "p_shot", "sg_sequence": seq})
    asset = sg.create("Asset", {"code": "p_asset"})
    versions = [sg.create("Version", {"code": c, "entity": e})["id"]
                for c, e in (("v_shot", shot), ("v_asset", asset), ("v_none", None))]
    notes = [sg.create("Note", {"subject": s, "note_links": l})["id"]
             for s, l in (("n_shot", [shot]), ("n_asset", [asset]), ("n_none", []))]
    return shot, asset, versions, notes


# api3 010
def test_entity_type_is_none_means_unset(sg, links):
    _, _, versions, _ = links
    assert match(sg, "Version", versions, [["entity", "type_is", None]]) == [2]
    assert match(sg, "Version", versions, [["entity", "type_is_not", None]]) == [0, 1]
    assert match(sg, "Version", versions, [["entity", "type_is_not", "Shot"]]) == [1, 2]
    assert match(sg, "Version", versions, [["entity", "name_not_contains", "x"]]) == [0, 1, 2]


@pytest.mark.parametrize("relation", ["name_is", "name_contains", "name_not_contains"])
def test_entity_name_relations_refuse_none(sg, relation):
    assert fault(sg, "Version", [["entity", relation, None]]) == (
        "API read() Version.entity expected [String] data type(s) but got NilClass:\nnil")


# api3 011
def test_multi_entity_negations_match_empty_rows(sg, links):
    _, _, _, notes = links
    assert match(sg, "Note", notes, [["note_links", "type_is", None]]) == [2]
    assert match(sg, "Note", notes, [["note_links", "type_is_not", None]]) == [0, 1]
    assert match(sg, "Note", notes, [["note_links", "name_not_contains", "shot"]]) == [1, 2]
    assert match(sg, "Note", notes, [["note_links", "name_not_contains", "x"]]) == [0, 1, 2]


def test_multi_entity_name_is_none_is_refused(sg):
    assert fault(sg, "Note", [["note_links", "name_is", None]]) == (
        "API read() Note.note_links expected [String] data type(s) but got NilClass:\nnil")


def test_multi_entity_is_two_entities(sg):
    a, b = {"type": "Shot", "id": 1}, {"type": "Asset", "id": 2}
    assert fault(sg, "Note", [["note_links", "is", [a, b]]]) == (
        "API read() 'is' 'relation' expects a 1-element array:\n"
        '[{"type" => "Shot", "id" => 1}, {"type" => "Asset", "id" => 2}]')


# api3 011, api3 015: the client reads values[0] before sending.
@pytest.mark.parametrize("entity_type, field", [("Note", "note_links"), ("Version", "entity"), ("Icon", "uuid")])
@pytest.mark.parametrize("relation", ["in", "not_in"])
def test_empty_list_raises_index_error_as_the_client_does(sg, entity_type, field, relation):
    with pytest.raises(IndexError, match="list index out of range"):
        sg.find(entity_type, [[field, relation, []]])


@pytest.mark.parametrize("entity_type, field", [("Note", "note_links"), ("Version", "entity")])
@pytest.mark.parametrize("relation", ["in", "not_in"])
def test_empty_list_faults_with_the_optimisation_off(sg, monkeypatch, entity_type, field, relation):
    monkeypatch.setattr(api3, "SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION", True)
    assert fault(sg, entity_type, [[field, relation, []]]) == (
        "API read() '%s' 'relation' expects at least a 1-element array:\n[]" % relation)


def test_empty_id_list_reaches_the_server(sg):
    assert sg.find("Version", [["id", "in", [1]]]) == []


# api3 012
def test_dotted_path_with_no_link_reads_null(sg, links):
    _, _, versions, notes = links
    assert match(sg, "Version", versions, [["entity.Shot.code", "is", None]]) == [1, 2]
    assert match(sg, "Version", versions, [["entity.Shot.code", "is_not", "x"]]) == [0, 1, 2]
    assert match(sg, "Note", notes, [["note_links.Shot.code", "is", None]]) == [1, 2]
    assert match(sg, "Note", notes, [["note_links.Shot.code", "is_not", "x"]]) == [0, 1, 2]
    path = "note_links.Shot.sg_sequence.Sequence.code"
    assert match(sg, "Note", notes, [[path, "is_not", None]]) == [0]
    assert match(sg, "Note", notes, [[path, "is", None]]) == [1, 2]


# api3 013
def test_unknown_plain_field_is_refused_before_the_scan(sg):
    assert fault(sg, "Version", [["id", "is", 0], ["zz_nope", "is", "x"]]) == (
        'API read() Version.zz_nope doesn\'t exist:\n{"path" => "zz_nope", "relation" => "is", "values" => ["x"]}')


def test_unknown_dotted_field_echoes_the_filter(sg):
    flt = {"filter_operator": "any", "filters": [["id", "is", 0], ["note_links.Booking.code", "is", "x"]]}
    assert fault(sg, "Note", [flt]) == (
        "API read() Note.note_links.Booking.code doesn't exist:\n"
        '{"path" => "note_links.Booking.code", "relation" => "is", "values" => ["x"]}')


def test_entity_unknown_relation_wraps_the_list(sg):
    assert fault(sg, "Version", [["id", "is", 0], ["entity", "bogus_op", "x"]]) == (
        "API read() Version.entity's 'entity' data type doesn't support 'bogus_op' 'relation':\n"
        '{"path" => "entity", "relation" => "bogus_op", "values" => ["x"]}\n'
        "Valid relations:\n"
        '["is",\n "is_not",\n "name_contains",\n "name_not_contains",\n "name_is",\n "type_is",\n'
        ' "type_is_not",\n "in",\n "not_in"]')


# api3 021
def test_retirement_date_does_not_exist(sg):
    assert fault(sg, "Version", [["retirement_date", "is_not", None]], retired_only=True) == (
        "API read() Version.retirement_date doesn't exist:\n"
        '{"path" => "retirement_date", "relation" => "is_not", "values" => [nil]}')


# api3 027
def test_link_to_a_retired_row_matches_nothing(sg):
    task = sg.create("Task", {"content": "t"})
    pl = sg.create("Playlist", {"code": "doomed"})
    sg.create("Version", {"code": "v", "sg_task": task, "playlists": [pl]})
    sg.delete("Task", task["id"])
    sg.delete("Playlist", pl["id"])
    assert sg.find("Version", [["sg_task", "is", task]]) == []
    assert sg.find("Version", [["playlists", "is", pl]]) == []


# api3 030
def test_text_is_empty_string_matches_null(sg):
    ids = put(sg, "Version", "description", [None, "a"])
    assert match(sg, "Version", ids, [["description", "is", ""]]) == [0]


# api3 014
@pytest.fixture
def stamped(sg):
    stamps = [NOW - datetime.timedelta(seconds=5), NOW - datetime.timedelta(days=3),
              NOW + datetime.timedelta(hours=2), NOW - datetime.timedelta(days=400), None]
    return put(sg, "Version", "created_at", stamps)


@pytest.mark.parametrize("flt, rows", [
    (["created_at", "in_last", 1, "DAY"], [0]),
    (["created_at", "in_last", [1, "DAY"]], [0]),
    (["created_at", "in_last", [1, "WEEK"]], [0, 1]),
    (["created_at", "in_last", [1, "HOUR"]], [0]),
    (["created_at", "in_last", [2, "YEAR"]], [0, 1, 3]),
    (["created_at", "in_last", [0, "DAY"]], []),
    (["created_at", "not_in_last", [1, "DAY"]], [1, 2, 3, 4]),
    (["created_at", "in_next", [1, "DAY"]], [2]),
    (["created_at", "not_in_next", [1, "DAY"]], [0, 1, 3, 4]),
    (["created_at", "in_calendar_day", 0], [0, 2]),
    (["created_at", "in_calendar_day", [0]], [0, 2]),
    (["created_at", "in_calendar_day", -3], [1]),
    (["created_at", "in_calendar_month", 0], [0, 1, 2]),
    (["created_at", "in_calendar_year", 0], [0, 1, 2]),
    (["created_at", "in_calendar_year", -1], [3]),
])
def test_relative_dates_match(sg, stamped, flt, rows):
    assert match(sg, "Version", stamped, [flt]) == rows


def test_relative_date_on_a_date_field(sg):
    ids = put(sg, "Task", "start_date", ["2026-11-18", "2026-11-13", None])
    assert match(sg, "Task", ids, [["start_date", "in_last", [10, "DAY"]]]) == [0, 1]
    assert match(sg, "Task", ids, [["start_date", "in_last", [2, "DAY"]]]) == [0]
    assert match(sg, "Task", ids, [["start_date", "not_in_last", [2, "DAY"]]]) == [1, 2]
    assert match(sg, "Task", ids, [["start_date", "in_calendar_day", -5]]) == [1]


@pytest.mark.parametrize("flt, msg", [
    (["created_at", "in_last", [1, "MINUTE"]],
     "API read() 'in_last' 'relation' doesn't support the 'MINUTE' time unit:\n[1, \"MINUTE\"]\n"
     'Valid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]'),
    (["created_at", "in_last", [1, "day"]],
     "API read() 'in_last' 'relation' doesn't support the 'day' time unit:\n[1, \"day\"]\n"
     'Valid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]'),
    (["created_at", "in_last", [-1, "DAY"]],
     "API read() 'in_last' 'relation' expects at a positive Integer time unit:\n[-1, \"DAY\"]"),
    (["created_at", "in_last", [1.5, "DAY"]],
     "API read() Version.created_at expected Integer data type(s) but got Float (1.5):\n[1.5, \"DAY\"]"),
    (["created_at", "in_last", ["1", "DAY"]],
     "API read() Version.created_at expected Integer data type(s) but got String (1):\n[\"1\", \"DAY\"]"),
    (["created_at", "in_last", ["DAY", 1]],
     "API read() Version.created_at expected Integer data type(s) but got String (DAY):\n[\"DAY\", 1]"),
    (["created_at", "in_last", 1], "API read() 'in_last' 'relation' expects a 2-element array:\n[1]"),
    (["created_at", "in_calendar_day", [0, "DAY"]],
     "API read() 'in_calendar_day' 'relation' expects a 1-element array:\n[0, \"DAY\"]"),
    (["created_at", "in_calendar_day", "0"],
     "API read() Version.created_at expected Integer data type(s) but got String (0):\n[\"0\"]"),
    (["created_at", "in_calendar_day", None],
     "API read() Version.created_at expected Integer data type(s) but got NilClass ():\n[nil]"),
])
def test_relative_date_refusals(sg, flt, msg):
    assert fault(sg, "Version", [flt]) == msg
