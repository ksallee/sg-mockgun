"""create, update, delete, revive and batch, each read back with find."""

import pytest


def read(site, entity_type, entity_id, fields):
    return site.find_one(entity_type, [["id", "is", entity_id]], fields)


@pytest.mark.finding("024")
@pytest.mark.cell("create", "-", "text")
def test_create_returns_what_was_sent_and_reads_back(site, made, sandbox, run_token):
    code = "zzconf_%s_create" % run_token
    row = made.create("Shot", {"code": code, "description": "probe", "project": sandbox})
    assert row["type"] == "Shot" and row["code"] == code and row["description"] == "probe"
    assert read(site, "Shot", row["id"], ["code", "description"])["description"] == "probe"


@pytest.mark.finding("024")
@pytest.mark.cell("update", "-", "text")
def test_update_reads_back(site, made, sandbox, run_token):
    row = made.create("Shot", {"code": "zzconf_%s_update" % run_token, "description": "probe", "project": sandbox})
    made.update("Shot", row["id"], {"description": "probe 2"})
    assert read(site, "Shot", row["id"], ["description"])["description"] == "probe 2"


@pytest.mark.finding("024")
@pytest.mark.cell("delete", "-", "-")
def test_delete_hides_the_row_from_find(site, made, sandbox, run_token):
    row = made.create("Shot", {"code": "zzconf_%s_delete" % run_token, "project": sandbox})
    assert made.delete("Shot", row["id"]) is True
    assert read(site, "Shot", row["id"], ["code"]) is None


@pytest.mark.finding("048")
@pytest.mark.cell("revive", "-", "-")
def test_revive_brings_back_the_values_the_row_had(site, made, sandbox, run_token):
    code = "zzconf_%s_revive" % run_token
    row = made.create("Shot", {"code": code, "description": "probe", "project": sandbox})
    made.delete("Shot", row["id"])
    assert made.revive("Shot", row["id"]) is True
    back = read(site, "Shot", row["id"], ["code", "description"])
    assert (back["code"], back["description"]) == (code, "probe")


@pytest.mark.finding("048")
@pytest.mark.cell("revive", "-", "-")
def test_revive_of_a_live_row_does_nothing(made, sandbox, run_token):
    row = made.create("Shot", {"code": "zzconf_%s_revive_live" % run_token, "project": sandbox})
    assert made.revive("Shot", row["id"]) is False


@pytest.mark.finding("024")
@pytest.mark.cell("batch", "-", "-")
def test_batch_create_update_delete(site, made, sandbox, run_token):
    prefix = "zzconf_%s_batch_" % run_token
    created = made.batch([
        {"request_type": "create", "entity_type": "Shot", "data": {"code": prefix + "a", "project": sandbox}},
        {"request_type": "create", "entity_type": "Shot", "data": {"code": prefix + "b", "project": sandbox}},
    ])
    assert [r["code"] for r in created] == [prefix + "a", prefix + "b"]
    a, b = created[0]["id"], created[1]["id"]
    made.batch([
        {"request_type": "update", "entity_type": "Shot", "entity_id": a, "data": {"description": "batched"}},
        {"request_type": "delete", "entity_type": "Shot", "entity_id": b},
    ])
    assert read(site, "Shot", a, ["description"])["description"] == "batched"
    assert read(site, "Shot", b, ["code"]) is None
