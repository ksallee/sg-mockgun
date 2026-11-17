"""Writes per data type as api3 answers 030 to 039 record them, on rows each test makes in the sandbox."""

import datetime

import pytest
from shotgun_api3 import Fault


def read(site, entity_type, entity_id, fields):
    return site.find_one(entity_type, [["id", "is", entity_id]], fields)


def refused_update(made, entity_type, entity_id, data):
    with pytest.raises(Fault) as e:
        made.update(entity_type, entity_id, data)
    return str(e.value)


@pytest.fixture
def version(made, sandbox, run_token):
    return made.create("Version", {"code": "zzconf_%s_write" % run_token, "project": sandbox})


# api3 030


@pytest.mark.finding("field_types/text", api3="030")
@pytest.mark.cell("update", "-", "text")
def test_text_is_stripped_and_blank_stores_null(site, made, sandbox, run_token):
    shot = made.create("Shot", {"code": "zzconf_%s_text" % run_token, "description": "", "project": sandbox})
    assert shot["description"] is None
    assert made.update("Shot", shot["id"], {"description": "  x  "}) == {"type": "Shot", "id": shot["id"], "description": "x"}
    assert made.update("Shot", shot["id"], {"description": "   "})["description"] is None
    scope = [["id", "is", shot["id"]]]
    assert len(site.find("Shot", scope + [["description", "is", ""]], ["id"])) == 1


# api3 031


@pytest.mark.finding("field_types/checkbox", api3="031")
@pytest.mark.cell("update", "-", "checkbox")
def test_checkbox_takes_only_booleans(site, made, version):
    assert read(site, "Version", version["id"], ["flagged"])["flagged"] is False
    assert refused_update(made, "Version", version["id"], {"flagged": "true"}) == (
        'API update() Version.flagged expected [FalseClass, TrueClass] data type(s) but got String:\n"true"')
    assert refused_update(made, "Version", version["id"], {"flagged": None}) == (
        "API update() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil")
    assert made.update("Version", version["id"], {"flagged": True})["flagged"] is True


# api3 032


@pytest.mark.finding("field_types/float", api3="032")
@pytest.mark.cell("update", "-", "float")
def test_float_refuses_int_and_rounds_to_six_places(site, made, version):
    assert refused_update(made, "Version", version["id"], {"sg_movie_aspect_ratio": 2}) == (
        "API update() Version.sg_movie_aspect_ratio expected [BigDecimal, Float, NilClass] data type(s) but got Integer:\n2")
    assert refused_update(made, "Version", version["id"], {"sg_movie_aspect_ratio": "2.5"}).endswith('String:\n"2.5"')
    made.update("Version", version["id"], {"sg_movie_aspect_ratio": 1.23456789})
    assert read(site, "Version", version["id"], ["sg_movie_aspect_ratio"])["sg_movie_aspect_ratio"] == 1.234568


# api3 033


@pytest.mark.finding("field_types/number", api3="033")
@pytest.mark.cell("update", "-", "number")
def test_number_is_signed_32_bit_and_refuses_strings(site, made, version):
    assert refused_update(made, "Version", version["id"], {"frame_count": 2 ** 31}) == (
        "API update() CRUD ERROR #5: Update failed for [Version.frame_count]: Invalid statement.")
    assert refused_update(made, "Version", version["id"], {"frame_count": "7"}) == (
        'API update() Version.frame_count expected [Integer, NilClass] data type(s) but got String:\n"7"')
    made.update("Version", version["id"], {"frame_count": 2 ** 31 - 1})
    assert read(site, "Version", version["id"], ["frame_count"])["frame_count"] == 2147483647


# api3 034


@pytest.mark.finding("field_types/multi_entity", api3="034")
@pytest.mark.cell("update", "-", "multi_entity")
def test_multi_entity_refuses_none_and_clears_on_empty_list(site, made, sandbox, run_token):
    p = "zzconf_%s_multi_" % run_token
    other = made.create("Shot", {"code": p + "other", "project": sandbox})
    shot = made.create("Shot", {"code": p + "shot", "shots": [other], "project": sandbox})
    assert refused_update(made, "Shot", shot["id"], {"shots": None}) == (
        "API update() Shot.shots expected [Array] data type(s) but got NilClass:\nnil")
    assert len(read(site, "Shot", shot["id"], ["shots"])["shots"]) == 1
    assert made.update("Shot", shot["id"], {"shots": []}) == {"type": "Shot", "id": shot["id"], "shots": []}


# api3 035


@pytest.mark.finding("field_types/color", api3="035")
@pytest.mark.cell("update", "-", "color")
def test_task_color(site, made, sandbox, run_token):
    task = made.create("Task", {"content": "zzconf_%s_color" % run_token, "project": sandbox})
    assert read(site, "Task", task["id"], ["color"])["color"] == "pipeline_step"
    made.update("Task", task["id"], {"color": "red"})
    assert read(site, "Task", task["id"], ["color"])["color"] == "253,1,0"
    assert refused_update(made, "Task", task["id"], {"color": None}).startswith(
        "API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) Value cannot be nil for Task.color.")


@pytest.mark.finding("field_types/jsonb", api3="035")
@pytest.mark.cell("update", "-", "jsonb")
def test_note_meta_is_create_only(site, made, sandbox, run_token):
    meta = {"a": {"b": [1, 2]}, "n": None}
    note = made.create("Note", {"subject": "zzconf_%s_meta" % run_token, "content": "probe", "meta": meta,
                                "project": sandbox})
    assert read(site, "Note", note["id"], ["meta"])["meta"] == meta
    assert refused_update(made, "Note", note["id"], {"meta": {"a": 1}}) == (
        'API update() Note.meta is editable on create only:\n{"field_name" => "meta", "value" => {"a" => 1}}')


# api3 036


@pytest.mark.finding("field_types/summary", api3="036")
@pytest.mark.cell("update", "-", "summary")
def test_read_only_types_refuse_writes(site, made, sandbox, run_token):
    shot = made.create("Shot", {"code": "zzconf_%s_ro" % run_token, "project": sandbox})
    assert read(site, "Shot", shot["id"], ["open_notes_count"])["open_notes_count"] == 0
    assert refused_update(made, "Shot", shot["id"], {"open_notes_count": 3}) == (
        'API update() Shot.open_notes_count is read only:\n{"field_name" => "open_notes_count", "value" => 3}')


# api3 038


@pytest.mark.finding("024", api3="038")
@pytest.mark.cell("create", "-", "entity")
def test_create_returns_the_fields_sent(site, made, sandbox, run_token):
    code = "zzconf_%s_return" % run_token
    name = site.find_one("Project", [["id", "is", sandbox["id"]]], ["name"])["name"]
    row = made.create("Version", {"code": code, "project": sandbox})
    assert row == {"type": "Version", "id": row["id"], "code": code,
                   "project": {"type": "Project", "id": sandbox["id"], "name": name}}
    asked = made.create("Version", {"code": code + "_2", "project": sandbox}, ["created_by", "updated_by"])
    assert set(asked) == {"type", "id", "code", "project", "created_by", "updated_by"}
    assert asked["created_by"]["type"] == "ApiUser" and asked["created_by"] == asked["updated_by"]


@pytest.mark.finding("024", api3="038")
@pytest.mark.cell("update", "-", "date_time")
def test_created_at_is_editable_on_create_only(site, made, sandbox, run_token):
    when = datetime.datetime(2020, 1, 2, 3, 4, 5)
    row = made.create("Version", {"code": "zzconf_%s_at" % run_token, "created_at": when, "project": sandbox})
    assert read(site, "Version", row["id"], ["created_at"])["created_at"] == when.astimezone()
    message = refused_update(made, "Version", row["id"], {"updated_at": when})
    assert message.startswith('API update() Version.updated_at is editable on create only:\n'
                              '{"field_name" => "updated_at", "value" => "2020-01-02T')


# api3 039


@pytest.mark.finding("028", api3="039")
@pytest.mark.cell("update", "-", "unknown field")
def test_unknown_field_refuses_the_write(site, made, version):
    assert refused_update(made, "Version", version["id"], {"description": "changed", "sg_not_a_field": "x"}) == (
        'API update() Version.sg_not_a_field doesn\'t exist:\n{"field_name" => "sg_not_a_field", "value" => "x"}')
    assert read(site, "Version", version["id"], ["description"])["description"] is None


@pytest.mark.finding("024", api3="039")
@pytest.mark.cell("update", "-", "dotted")
def test_dotted_update_writes_the_linked_row(site, made, sandbox, run_token):
    p = "zzconf_%s_dotted_" % run_token
    shot = made.create("Shot", {"code": p + "shot", "project": sandbox})
    v = made.create("Version", {"code": p + "v", "entity": shot, "project": sandbox})
    made.update("Version", v["id"], {"entity.Shot.description": "via dotted"})
    assert read(site, "Shot", shot["id"], ["description"])["description"] == "via dotted"
