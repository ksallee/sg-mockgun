"""The create contract, status values, batch, per-project schema and delete effects, as api3 answers 060 to 065 record them."""

import pytest
from shotgun_api3 import Fault


def read(site, entity_type, entity_id, fields):
    return site.find_one(entity_type, [["id", "is", entity_id]], fields)


# api3 060


@pytest.mark.finding("012", api3="060")
@pytest.mark.cell("create", "-", "-")
def test_create_needs_a_project_and_a_field(made):
    e = made.refused("create", "Shot", {"code": "x"})
    assert isinstance(e, Fault)
    assert str(e) == 'API create() missing \'project\' attribute:\n[{"field_name" => "code", "value" => "x"}]'
    e = made.refused("create", "Version", {})
    assert str(e) == ('API create() invalid/missing array \'fields\':\n'
                      '{"type" => "Version", "fields" => [], "return_fields" => ["id"]}')


@pytest.mark.finding("012", api3="060")
@pytest.mark.cell("create", "-", "text")
def test_omitted_code_is_generated_and_empty_code_refused(site, made, sandbox, run_token):
    shot = made.create("Shot", {"project": sandbox})
    assert "code" not in shot
    assert read(site, "Shot", shot["id"], ["code"])["code"] == "New Shot %d" % shot["id"]
    e = made.refused("create", "Shot", {"project": sandbox, "code": ""})
    assert str(e) == "API create() CRUD ERROR #6: Create failed for [Shot]: Cannot set identifier field to empty. (Shot)"
    code = "zzconf_%s_twin" % run_token
    made.create("Shot", {"code": code, "project": sandbox})
    made.create("Shot", {"code": code, "project": sandbox})
    assert len(site.find("Shot", [["project", "is", sandbox], ["code", "is", code]], ["id"])) == 2


# api3 062


def statuses(site, entity_type):
    values = site.schema_field_read(entity_type, "sg_status_list")["sg_status_list"]["properties"]["valid_values"]["value"]
    return ", ".join("'%s'" % v for v in values)


@pytest.mark.finding("094", api3="062")
@pytest.mark.cell("create", "-", "status_list")
def test_status_outside_the_list_is_refused(site, made, sandbox, run_token):
    e = made.refused("create", "Shot", {"code": "zzconf_%s_bad" % run_token, "sg_status_list": "zz_bad", "project": sandbox})
    assert str(e) == ("API create() CRUD ERROR #6: Invalid field value, update failed [5 - Update failed for "
                      "[Shot.sg_status_list]: 'zz_bad' is not a valid status. Valid statuses: %s.]" % statuses(site, "Shot"))
    shot = made.create("Shot", {"code": "zzconf_%s_status" % run_token, "project": sandbox})
    assert read(site, "Shot", shot["id"], ["sg_status_list"])["sg_status_list"] == "wtg"
    with pytest.raises(Fault) as e:
        made.update("Shot", shot["id"], {"sg_status_list": "zz_bad"})
    assert str(e.value) == ("API update() CRUD ERROR #5: Update failed for [Shot.sg_status_list]: 'zz_bad' is not a "
                            "valid status. Valid statuses: %s." % statuses(site, "Shot"))
    assert made.update("Shot", shot["id"], {"sg_status_list": ""}) == {"type": "Shot", "id": shot["id"], "sg_status_list": None}


# api3 063


@pytest.mark.finding("028", api3="063")
@pytest.mark.cell("batch", "-", "-")
def test_batch_rolls_back_when_a_request_fails(site, made, sandbox, run_token):
    p = "zzconf_%s_atomic_" % run_token
    base = made.create("Shot", {"code": p + "base", "description": "before", "project": sandbox})
    e = made.refused("batch", [
        {"request_type": "create", "entity_type": "Shot", "data": {"code": p + "new", "project": sandbox}},
        {"request_type": "update", "entity_type": "Shot", "entity_id": base["id"], "data": {"description": "after"}},
        {"request_type": "update", "entity_type": "Shot", "entity_id": 0, "data": {"description": "x"}},
    ])
    assert str(e) == ("API batch() request with index 2 failed.  All requests rolled back.\n"
                      "API update() CRUD ERROR #3: Entity of type [Shot] with id=0 does not exist.")
    assert site.find("Shot", [["project", "is", sandbox], ["code", "is", p + "new"]], ["id"]) == []
    assert read(site, "Shot", base["id"], ["description"])["description"] == "before"


@pytest.mark.finding("028", api3="063")
@pytest.mark.cell("batch", "-", "-")
def test_batch_results_in_request_order(made, sandbox, run_token):
    p = "zzconf_%s_order_" % run_token
    base = made.create("Shot", {"code": p + "base", "project": sandbox})
    results = made.batch([
        {"request_type": "update", "entity_type": "Shot", "entity_id": base["id"], "data": {"description": "d"}},
        {"request_type": "create", "entity_type": "Shot", "data": {"code": p + "new", "project": sandbox}},
    ])
    assert results[0] == {"type": "Shot", "id": base["id"], "description": "d"}
    assert results[1]["code"] == p + "new" and set(results[1]) == {"type", "id", "code", "project"}
    assert made.batch([{"request_type": "delete", "entity_type": "Shot", "entity_id": results[1]["id"]}]) == [True]
    e = made.refused("batch", [{"request_type": "create", "entity_type": "Shot", "data": {"code": "x"}}])
    assert str(e) == ("API batch() request with index 0 failed.  All requests rolled back.\n"
                      'API create() missing \'project\' attribute:\n[{"field_name" => "code", "value" => "x"}]')


# api3 064


@pytest.mark.finding("115", api3="064")
@pytest.mark.cell("schema_field_read", "-", "status_list")
def test_project_scope_keeps_valid_values(site, sandbox):
    plain = site.schema_field_read("Shot", "sg_status_list")["sg_status_list"]
    scoped = site.schema_field_read("Shot", "sg_status_list", project_entity=sandbox)["sg_status_list"]
    assert plain["properties"]["hidden_values"]["value"] == []
    assert scoped["properties"]["valid_values"] == plain["properties"]["valid_values"]
    missing = site.schema_field_read("Shot", "sg_status_list", project_entity={"type": "Project", "id": 999999999})
    assert missing["sg_status_list"] == plain


# api3 065


@pytest.mark.finding("089", api3="065")
@pytest.mark.cell("delete", "-", "entity")
def test_task_delete_nulls_version_sg_task_and_revive_restores_it(site, made, sandbox, run_token):
    p = "zzconf_%s_taskdel_" % run_token
    task = made.create("Task", {"content": p + "task", "project": sandbox})
    v = made.create("Version", {"code": p + "v", "sg_task": task, "project": sandbox})
    link = {"type": "Task", "id": task["id"]}
    assert made.delete("Task", task["id"]) is True
    assert read(site, "Version", v["id"], ["sg_task"])["sg_task"] is None
    assert site.find("Version", [["sg_task", "is", link]], ["id"]) == []
    assert made.revive("Task", task["id"]) is True
    assert read(site, "Version", v["id"], ["sg_task"])["sg_task"]["id"] == task["id"]
