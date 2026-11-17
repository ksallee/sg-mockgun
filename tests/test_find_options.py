"""find and find_one options: limit, page, order, include_archived_projects, additional_filter_presets."""

import pytest
import datetime

from shotgun_api3 import Fault, ShotgunError

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


@pytest.fixture
def shots(sg):
    project = sg.create("Project", {"name": "p"})
    rows = [
        sg.create("Shot", {"code": code, "project": project, "sg_status_list": status})
        for code, status in [("c", "ip"), ("a", "wtg"), ("b", "ip"), ("d", "wtg")]
    ]
    return [r["id"] for r in rows]


def asc(field):
    return {"field_name": field, "direction": "asc"}


def desc(field):
    return {"field_name": field, "direction": "desc"}


def codes(rows):
    return [r["code"] for r in rows]


# finding 082, finding 006
def test_limit_applies_after_order(sg, shots):
    assert codes(sg.find("Shot", [], ["code"], order=[asc("code")], limit=2)) == ["a", "b"]


def test_limit_and_page_walk_the_ordered_set(sg, shots):
    order = [asc("code")]
    assert codes(sg.find("Shot", [], ["code"], order=order, limit=3, page=1)) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], order=order, limit=3, page=2)) == ["d"]
    assert sg.find("Shot", [], ["code"], order=order, limit=3, page=3) == []


def test_page_without_limit_uses_a_page_of_500(sg, monkeypatch):
    # api3 020: the client reads the page size from server_info, else 500.
    monkeypatch.setattr(type(sg), "server_info", {"api_max_entities_per_page": 500}, raising=False)
    for i in range(501):
        sg.create("Asset", {"code": "a%03d" % i})
    assert len(sg.find("Asset", [], page=1)) == 500
    assert len(sg.find("Asset", [], page=2)) == 1
    assert len(sg.find("Asset", [])) == 501


def test_limit_above_the_page_size_returns_that_many(sg):
    for i in range(502):
        sg.create("Asset", {"code": "a%03d" % i})
    assert len(sg.find("Asset", [], limit=501)) == 501


@pytest.mark.parametrize("kwargs", [{"limit": -1}, {"limit": "1"}, {"page": -1}, {"page": 1.0}])
def test_limit_and_page_are_validated_as_the_client_does(sg, kwargs):
    with pytest.raises(ValueError):
        sg.find("Shot", [], **kwargs)


def test_find_one_returns_the_first_ordered_row(sg, shots):
    assert sg.find_one("Shot", [], ["code"], order=[desc("code")])["code"] == "d"


# finding 026
def test_no_order_is_id_ascending(sg, shots):
    sg._db["Shot"] = dict(reversed(list(sg._db["Shot"].items())))
    assert [r["id"] for r in sg.find("Shot", [])] == sorted(shots)


def test_id_in_returns_id_ascending_not_list_order(sg, shots):
    rows = sg.find("Shot", [["id", "in", list(reversed(shots))]])
    assert [r["id"] for r in rows] == sorted(shots)


def test_first_order_key_is_primary(sg, shots):
    # api3 024: a status_list sorts by valid_values order, wtg before ip on Shot.
    rows = sg.find("Shot", [], ["code"], order=[asc("sg_status_list"), desc("code")])
    assert codes(rows) == ["d", "a", "c", "b"]


def test_ties_break_on_id_ascending(sg, shots):
    # api3 024: ties keep id ascending in both directions.
    rows = sg.find("Shot", [], ["code"], order=[desc("sg_status_list")])
    assert codes(rows) == ["c", "b", "a", "d"]


@pytest.mark.parametrize("field", ["open_notes_count", "sg_uploaded_movie", "sg_not_a_field_at_all",
                                   "entity.Shot.nope"])
def test_unsortable_or_unknown_order_field_is_ignored(sg, field):
    ids = [sg.create("Version", {"code": c})["id"] for c in ["b", "a"]]
    sg._db["Version"][ids[0]]["sg_uploaded_movie"] = {"url": "https://x/1", "name": "1"}
    rows = sg.find("Version", [], ["code"], order=[desc(field), asc("code")])
    assert codes(rows) == ["a", "b"]


def test_order_on_a_dotted_path(sg):
    project = sg.create("Project", {"name": "p"})
    sh_b = sg.create("Shot", {"code": "b", "project": project})
    sh_a = sg.create("Shot", {"code": "a", "project": project})
    sg.create("Version", {"code": "v1", "entity": sh_b, "project": project})
    sg.create("Version", {"code": "v2", "entity": sh_a, "project": project})
    rows = sg.find("Version", [], ["code"], order=[asc("entity.Shot.code")])
    assert codes(rows) == ["v2", "v1"]
    rows = sg.find("Version", [], ["code"], order=[desc("entity.Shot.code")])
    assert codes(rows) == ["v1", "v2"]


# documented, unprobed (sg-mockgun#39)
def test_include_archived_projects(sg):
    live = sg.create("Project", {"name": "live"})
    gone = sg.create("Project", {"name": "gone", "archived": True})
    sg.create("Shot", {"code": "a", "project": live})
    sg.create("Shot", {"code": "b", "project": gone})
    sg.create("Shot", {"code": "c"})
    assert codes(sg.find("Shot", [], ["code"])) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], include_archived_projects=True)) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], include_archived_projects=False)) == ["a", "c"]
    one = sg.find_one("Shot", [["code", "is", "b"]], include_archived_projects=False)
    assert one is None


def test_include_archived_projects_drops_archived_project_rows(sg):
    # api3 022
    sg.create("Project", {"name": "live"})
    sg.create("Project", {"name": "gone", "archived": True})
    names = [p["name"] for p in sg.find("Project", [], ["name"], include_archived_projects=False)]
    assert names == ["live"]


def test_empty_presets_change_nothing(sg, shots):
    assert len(sg.find("Shot", [], additional_filter_presets=None)) == 4
    assert len(sg.find_one("Shot", [], additional_filter_presets=[])) == 2


def latest(by):
    return [{"preset_name": "LATEST", "latest_by": by}]


def at(day):
    return datetime.datetime(2026, 1, day)


@pytest.fixture
def published(sg):
    project = sg.create("Project", {"name": "p"})
    asset = sg.create("Asset", {"code": "a", "project": project})
    task = sg.create("Task", {"content": "t", "project": project, "entity": asset})
    pft = sg.create("PublishedFileType", {"code": "Maya Scene"})
    base = {"project": project, "entity": asset, "task": task, "published_file_type": pft}

    def pf(code, name, day, **over):
        data = dict(base, code=code, name=name, created_at=at(day))
        data.update(over)
        return sg.create("PublishedFile", data)["id"]

    return {
        "old": pf("a.v001.ma", "a.ma", 1),
        "new": pf("a.v002.ma", "a.ma", 2),
        "other": pf("b.v001.ma", "b.ma", 1),
        "no_task": pf("c.v001.ma", "c.ma", 3, task=None),
        "no_type": pf("d.v001.ma", "d.ma", 3, published_file_type=None),
    }


def test_latest_published_file(sg, published):
    # api3 023: newest per (entity, task, published_file_type, name); a null in any drops the row.
    rows = sg.find("PublishedFile", [], ["id"], additional_filter_presets=latest("ENTITIES_CREATED_AT"))
    assert sorted(r["id"] for r in rows) == sorted([published["new"], published["other"]])


def test_latest_combines_with_filters(sg, published):
    rows = sg.find("PublishedFile", [["code", "starts_with", "a."]], ["id"],
                   additional_filter_presets=latest("ENTITIES_CREATED_AT"))
    assert [r["id"] for r in rows] == [published["new"]]


@pytest.fixture
def versions(sg):
    project = sg.create("Project", {"name": "p"})
    shot = sg.create("Shot", {"code": "s", "project": project})
    early = sg.create("Step", {"code": "Anim", "list_order": 1})
    late = sg.create("Step", {"code": "Light", "list_order": 2})
    t_early = sg.create("Task", {"content": "anim", "project": project, "entity": shot, "step": early})
    t_late = sg.create("Task", {"content": "light", "project": project, "entity": shot, "step": late})

    def v(code, day, task=None, entity=shot):
        return sg.create("Version", {"code": code, "project": project, "entity": entity,
                                     "sg_task": task, "created_at": at(day)})["id"]

    return {
        "light": v("light", 1, t_late),
        "anim": v("anim", 2, t_early),
        "loose": v("loose", 3, entity=None),
    }


def test_latest_version_by_created_at(sg, versions):
    rows = sg.find("Version", [], ["id"], additional_filter_presets=latest("ENTITIES_CREATED_AT"))
    assert [r["id"] for r in rows] == [versions["anim"]]


def test_latest_version_by_step(sg, versions):
    rows = sg.find("Version", [], ["id"],
                   additional_filter_presets=latest("BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT"))
    assert [r["id"] for r in rows] == [versions["light"]]


def test_latest_by_unknown_value_is_a_crud_error(sg, published):
    for preset in (latest("BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT"), latest("NOPE"),
                   [{"preset_name": "LATEST"}]):
        with pytest.raises(Fault) as e:
            sg.find("PublishedFile", [], ["id"], additional_filter_presets=preset)
        assert str(e.value) == "API read() CRUD ERROR #10: Read failed for entity type [PublishedFile]"


def test_unknown_preset_name(sg):
    with pytest.raises(Fault) as e:
        sg.find("PublishedFile", [], ["id"], additional_filter_presets=[{"preset_name": "NOPE"}])
    assert str(e.value) == (
        'API read() Invalid additional filter preset provided: \n'
        '{"type" => "PublishedFile",\n'
        ' "return_fields" => ["id"],\n'
        ' "filters" => {"logical_operator" => "and", "conditions" => []},\n'
        ' "return_only" => "active",\n'
        ' "paging" => {"entities_per_page" => 5000, "current_page" => 1},\n'
        ' "additional_filter_presets" => [{"preset_name" => "NOPE"}],\n'
        ' "api_return_image_urls" => true,\n'
        ' "return_paging_info_without_counts" => true}'
    )


def test_latest_on_a_type_without_presets(sg):
    with pytest.raises(Fault, match=r"^API read\(\) Invalid additional filter preset provided: \n\{\"type\" => \"Shot\""):
        sg.find("Shot", [], ["id"], limit=5, additional_filter_presets=latest("ENTITIES_CREATED_AT"))


def test_preset_that_is_not_a_hash(sg):
    with pytest.raises(Fault) as e:
        sg.find("PublishedFile", [], ["id"], additional_filter_presets=["LATEST"])
    assert str(e.value).startswith(
        'API read() invalid additional filter preset format. It must be a hash:\n{"type" => "PublishedFile",\n')


# api3 024
def test_status_list_sorts_by_valid_values(sg):
    for code, status in [("x", "rev"), ("y", "na"), ("z", "apr")]:
        sg.create("Version", {"code": code, "sg_status_list": status})
    assert codes(sg.find("Version", [], ["code"], order=[asc("sg_status_list")])) == ["y", "x", "z"]
    assert codes(sg.find("Version", [], ["code"], order=[desc("sg_status_list")])) == ["z", "x", "y"]


def test_entity_sorts_by_display_name(sg):
    project = sg.create("Project", {"name": "p"})
    b = sg.create("Shot", {"code": "b", "project": project})
    a = sg.create("Asset", {"code": "a", "project": project})
    sg.create("Version", {"code": "v1", "entity": b})
    sg.create("Version", {"code": "v2", "entity": a})
    assert codes(sg.find("Version", [], ["code"], order=[asc("entity")])) == ["v2", "v1"]
    assert codes(sg.find("Version", [], ["code"], order=[desc("entity")])) == ["v1", "v2"]


def test_bad_direction_is_a_fault(sg):
    with pytest.raises(Fault) as e:
        sg.find("Version", [], ["code"], order=[{"field_name": "code", "direction": "up"}])
    assert str(e.value) == (
        "API read() invalid/missing string 'direction':\n"
        '{"field_name" => "code", "direction" => "up"}'
    )


def test_client_fills_direction_and_reads_column(sg):
    for code in ["b", "a"]:
        sg.create("Version", {"code": code})
    assert codes(sg.find("Version", [], ["code"], order=[{"field_name": "code"}])) == ["a", "b"]
    assert codes(sg.find("Version", [], ["code"], order=[{"column": "code"}])) == ["a", "b"]


# api3 025
@pytest.mark.parametrize("field", ["description", "frame_count", "sg_status_list", "entity", "entity.Shot.code"])
def test_none_sorts_last_both_ways(sg, field):
    shot = sg.create("Shot", {"code": "s"})
    sg.create("Version", {"code": "set", "description": "b", "frame_count": 5, "sg_status_list": "rev", "entity": shot})
    sg.create("Version", {"code": "none1", "sg_status_list": None})
    sg.create("Version", {"code": "none2", "sg_status_list": None})
    for direction in ("asc", "desc"):
        rows = sg.find("Version", [], ["code"], order=[{"field_name": field, "direction": direction}])
        assert codes(rows) == ["set", "none1", "none2"]


# api3 027
def test_link_to_a_retired_row_reads_none_or_drops_out(sg):
    project = sg.create("Project", {"name": "p"})
    task = sg.create("Task", {"content": "t", "project": project})
    doomed = sg.create("Playlist", {"code": "doomed", "project": project})
    kept = sg.create("Playlist", {"code": "kept", "project": project})
    v = sg.create("Version", {"code": "v", "project": project, "sg_task": task, "playlists": [doomed, kept]})
    sg.delete("Task", task["id"])
    sg.delete("Playlist", doomed["id"])
    row = sg.find_one("Version", [["id", "is", v["id"]]], ["sg_task", "playlists"])
    assert row["sg_task"] is None
    assert [p["name"] for p in row["playlists"]] == ["kept"]
    sg.revive("Task", task["id"])
    sg.revive("Playlist", doomed["id"])
    row = sg.find_one("Version", [["id", "is", v["id"]]], ["sg_task", "playlists"])
    assert row["sg_task"]["name"] == "t"
    assert [p["name"] for p in row["playlists"]] == ["doomed", "kept"]


# api3 026
def test_note_tasks_carry_template_task_id(sg):
    project = sg.create("Project", {"name": "p"})
    from_template = sg.create("Task", {"content": "a", "project": project})
    sg._db["Task"][from_template["id"]]["template_task"] = {"type": "Task", "id": 999}
    plain = sg.create("Task", {"content": "b", "project": project})
    note = sg.create("Note", {"subject": "n", "project": project, "tasks": [from_template, plain]})
    tasks = sg.find_one("Note", [["id", "is", note["id"]]], ["tasks"])["tasks"]
    assert tasks == [
        {"type": "Task", "id": from_template["id"], "name": "a", "template_task_id": 999},
        {"type": "Task", "id": plain["id"], "name": "b", "template_task_id": None},
    ]
