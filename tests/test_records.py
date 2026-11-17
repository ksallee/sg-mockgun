"""Create contract, status values, update and batch answers, per-project schema, link clearing on delete."""

import pytest
from shotgun_api3 import Fault

from sg_mockgun import Shotgun, schemas

SHOT_STATUSES = "'wtg', 'ip', 'fin', 'rev', 'apr', 'hld', 'omt', 'awd', 'bid', 'to'"


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


@pytest.fixture
def project(sg):
    return sg.create("Project", {"name": "p"})


def read(sg, entity, field):
    return sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field], retired_only=False)[field]


# api3 060


@pytest.mark.parametrize("entity_type", ["Shot", "Version"])
def test_create_without_project_is_refused(sg, entity_type):
    with pytest.raises(Fault) as e:
        sg.create(entity_type, {"code": "x"})
    assert str(e.value) == 'API create() missing \'project\' attribute:\n[{"field_name" => "code", "value" => "x"}]'
    assert sg.find(entity_type, []) == []


@pytest.mark.parametrize("entity_type", ["Shot", "Version", "Project"])
def test_create_with_no_fields_is_refused(sg, entity_type):
    # api3 061 for Project
    with pytest.raises(Fault) as e:
        sg.create(entity_type, {})
    assert str(e.value) == (
        "API create() invalid/missing array 'fields':\n"
        '{"type" => "%s", "fields" => [], "return_fields" => ["id"]}' % entity_type
    )


@pytest.mark.parametrize("entity_type", ["Shot", "Version"])
def test_omitted_code_becomes_new_type_id(sg, project, entity_type):
    row = sg.create(entity_type, {"project": project})
    assert "code" not in row
    assert read(sg, row, "code") == "New %s %d" % (entity_type, row["id"])


def test_omitted_identity_uses_the_type_display_name(sg, project):
    # finding 012
    row = sg.create("PublishedFile", {"project": project})
    assert read(sg, row, "code") == "New Published File %d" % row["id"]


@pytest.mark.parametrize("value", ["", None])
def test_empty_code_is_refused_and_spends_an_id(sg, project, value):
    first = sg.create("Shot", {"project": project, "code": "a"})
    with pytest.raises(Fault) as e:
        sg.create("Shot", {"project": project, "code": value})
    assert str(e.value) == "API create() CRUD ERROR #6: Create failed for [Shot]: Cannot set identifier field to empty. (Shot)"
    assert len(sg.find("Shot", [])) == 1
    assert sg.create("Shot", {"project": project, "code": "b"})["id"] == first["id"] + 2


def test_code_is_not_unique(sg, project):
    a = sg.create("Shot", {"project": project, "code": "dup"})
    b = sg.create("Shot", {"project": project, "code": "dup"})
    assert a["id"] != b["id"]
    assert len(sg.find("Shot", [["code", "is", "dup"]])) == 2


# api3 062


def test_status_outside_the_list_is_refused_on_create(sg, project):
    with pytest.raises(Fault) as e:
        sg.create("Shot", {"project": project, "code": "s", "sg_status_list": "zz_bad"})
    assert str(e.value) == (
        "API create() CRUD ERROR #6: Invalid field value, update failed [5 - Update failed for "
        "[Shot.sg_status_list]: 'zz_bad' is not a valid status. Valid statuses: %s.]" % SHOT_STATUSES
    )
    assert sg.find("Shot", []) == []


def test_status_outside_the_list_is_refused_on_update(sg, project):
    shot = sg.create("Shot", {"project": project, "code": "s"})
    with pytest.raises(Fault) as e:
        sg.update("Shot", shot["id"], {"sg_status_list": "zz_bad"})
    assert str(e.value) == (
        "API update() CRUD ERROR #5: Update failed for [Shot.sg_status_list]: 'zz_bad' is not a valid status. "
        "Valid statuses: %s." % SHOT_STATUSES
    )
    assert read(sg, shot, "sg_status_list") == "wtg"


@pytest.mark.parametrize("value", ["", None])
def test_empty_status_stores_null(sg, project, value):
    shot = sg.create("Shot", {"project": project, "code": "s"})
    assert sg.update("Shot", shot["id"], {"sg_status_list": value}) == {
        "type": "Shot", "id": shot["id"], "sg_status_list": None}
    assert read(sg, shot, "sg_status_list") is None


def test_status_hidden_in_the_project_is_accepted(sg, project):
    sg.set_project_schema(project, "Shot", "sg_status_list", hidden_values=["awd"])
    shot = sg.create("Shot", {"project": project, "code": "s"})
    sg.update("Shot", shot["id"], {"sg_status_list": "awd"})
    assert read(sg, shot, "sg_status_list") == "awd"


def test_update_returns_the_row(sg, project):
    shot = sg.create("Shot", {"project": project, "code": "s"})
    assert sg.update("Shot", shot["id"], {"description": "d"}) == {"type": "Shot", "id": shot["id"], "description": "d"}


# api3 063


def _rolled_back(index, inner):
    return "API batch() request with index %d failed.  All requests rolled back.\n%s" % (index, inner)


@pytest.mark.parametrize("bad, inner", [
    ({"request_type": "update", "entity_type": "Shot", "entity_id": 0, "data": {"description": "x"}},
     "API update() CRUD ERROR #3: Entity of type [Shot] with id=0 does not exist."),
    ({"request_type": "delete", "entity_type": "Shot", "entity_id": 999999999},
     "API delete() CRUD ERROR #3: Entity of type [Shot] with id=999999999 does not exist."),
])
def test_batch_rolls_back_every_request(sg, project, bad, inner):
    base = sg.create("Shot", {"project": project, "code": "base", "description": "before"})
    events = len(sg.find("EventLogEntry", []))
    with pytest.raises(Fault) as e:
        sg.batch([
            {"request_type": "create", "entity_type": "Shot", "data": {"project": project, "code": "a"}},
            {"request_type": "update", "entity_type": "Shot", "entity_id": base["id"], "data": {"description": "after"}},
            bad,
        ])
    assert str(e.value) == _rolled_back(2, inner)
    assert sg.find("Shot", [["code", "is", "a"]]) == []
    assert read(sg, base, "description") == "before"
    assert len(sg.find("EventLogEntry", [])) == events
    # A rolled-back create spends its id.
    assert sg.create("Shot", {"project": project, "code": "c"})["id"] == base["id"] + 2


def test_batch_applies_the_create_checks(sg):
    with pytest.raises(Fault) as e:
        sg.batch([{"request_type": "create", "entity_type": "Version", "data": {"code": "x"}}])
    assert str(e.value) == _rolled_back(
        0, 'API create() missing \'project\' attribute:\n[{"field_name" => "code", "value" => "x"}]')


def test_batch_results_are_in_request_order(sg, project):
    base = sg.create("Shot", {"project": project, "code": "base"})
    out = sg.batch([
        {"request_type": "update", "entity_type": "Shot", "entity_id": base["id"], "data": {"description": "u1"}},
        {"request_type": "create", "entity_type": "Shot", "data": {"project": project, "code": "o1"}},
        {"request_type": "delete", "entity_type": "Shot", "entity_id": base["id"]},
    ])
    assert out[0] == {"type": "Shot", "id": base["id"], "description": "u1"}
    assert out[1]["code"] == "o1"
    assert out[2] is True


def test_update_of_a_missing_id(sg):
    with pytest.raises(Fault) as e:
        sg.update("Shot", 0, {"description": "x"})
    assert str(e.value) == "API update() CRUD ERROR #3: Entity of type [Shot] with id=0 does not exist."


# api3 064


def test_schema_read_with_a_project_applies_its_overlay(sg, project):
    sg.set_project_schema(project, "Shot", "sg_status_list", hidden_values=["awd", "bid", "to"])
    sg.set_project_schema(project, "Shot", "description", visible=False)
    scoped = sg.schema_field_read("Shot", project_entity=project)
    assert scoped["sg_status_list"]["properties"]["hidden_values"] == {"value": ["awd", "bid", "to"], "editable": False}
    assert scoped["description"]["visible"]["value"] is False
    one = sg.schema_field_read("Shot", "sg_status_list", project_entity=project)
    assert one["sg_status_list"]["properties"]["hidden_values"]["value"] == ["awd", "bid", "to"]
    site = sg.schema_field_read("Shot")
    assert site["sg_status_list"]["properties"]["hidden_values"]["value"] == []
    assert site["description"]["visible"]["value"] is True


def test_schema_read_with_an_unknown_project_reads_as_site(sg, project):
    sg.set_project_schema(project, "Shot", "description", visible=False)
    other = sg.schema_field_read("Shot", project_entity={"type": "Project", "id": 999999999})
    assert other["description"]["visible"]["value"] is True


# api3 065


def test_delete_nulls_links_and_revive_restores_them(sg, project):
    task = sg.create("Task", {"project": project, "content": "t"})
    version = sg.create("Version", {"project": project, "code": "v", "sg_task": task})
    assert sg.delete("Task", task["id"]) is True
    assert read(sg, version, "sg_task") is None
    assert sg.find("Version", [["sg_task", "is", task]]) == []
    assert sg.revive("Task", task["id"]) is True
    assert read(sg, version, "sg_task") == {"type": "Task", "id": task["id"], "name": "t"}


# api3 027


def test_delete_retires_versions_of_the_entity_and_revive_revives_them(sg, project):
    asset = sg.create("Asset", {"project": project, "code": "a"})
    version = sg.create("Version", {"project": project, "code": "v", "entity": asset})
    other = sg.create("Version", {"project": project, "code": "w"})
    sg.delete("Asset", asset["id"])
    assert sg.find("Version", [["id", "is", version["id"]]]) == []
    assert sg.find("Version", [["id", "is", version["id"]]], retired_only=True) != []
    assert sg.find("Version", [["id", "is", other["id"]]]) != []
    sg.revive("Asset", asset["id"])
    assert read(sg, version, "entity") == {"type": "Asset", "id": asset["id"], "name": "a"}
