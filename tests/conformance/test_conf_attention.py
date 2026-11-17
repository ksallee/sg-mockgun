"""Attention, navigation and site reads as api3 answers 047 to 052 record them. Each call here reads; none follows or notifies."""

import pytest
from shotgun_api3 import Fault, ShotgunError


def fault(fn, *args, **kwargs):
    with pytest.raises(Fault) as e:
        fn(*args, **kwargs)
    return str(e.value)


# api3 047


@pytest.mark.finding("043", api3="047")
@pytest.mark.cell("note_thread_read", "-", "-")
def test_note_thread_read_rows(site, made, sandbox, run_token):
    note = made.create("Note", {"subject": "zzconf_%s_thread" % run_token, "content": "probe", "project": sandbox})
    reply = made.create("Reply", {"entity": note, "content": "probe reply"})
    rows = site.note_thread_read(note["id"])
    assert [(r["type"], r["id"]) for r in rows] == [("Note", note["id"]), ("Reply", reply["id"])]
    assert set(rows[0]) == {"content", "created_at", "created_by", "id", "type"}
    assert set(rows[1]) == {"content", "created_at", "id", "type", "user"}
    widened = site.note_thread_read(note["id"], entity_fields={"Note": ["subject", "sg_not_a_field"]})
    assert widened[0]["subject"] == "zzconf_%s_thread" % run_token and "sg_not_a_field" not in widened[0]


@pytest.mark.finding("043", api3="047")
@pytest.mark.cell("note_thread_read", "-", "-")
def test_note_thread_read_missing_note(site):
    assert fault(site.note_thread_read, 999999999) == "Not Found"
    with pytest.raises(ValueError, match="entity_fields parameter must be a dictionary"):
        site.note_thread_read(999999999, entity_fields=["subject"])


# api3 048


@pytest.mark.finding("066", api3="048")
@pytest.mark.cell("activity_stream_read", "-", "-")
def test_activity_stream_envelope(site, made, sandbox, run_token):
    shot = made.create("Shot", {"code": "zzconf_%s_stream" % run_token, "project": sandbox})
    answer = site.activity_stream_read("Shot", shot["id"])
    assert set(answer) == {"earliest_update_id", "entity_id", "entity_type", "latest_update_id", "updates"}
    assert (answer["entity_type"], answer["entity_id"]) == ("Shot", shot["id"])
    ids = [u["id"] for u in answer["updates"]]
    assert ids == sorted(ids, reverse=True)
    for update in answer["updates"]:
        assert {"created_at", "created_by", "id", "meta", "primary_entity", "read", "update_type"} <= set(update)
        assert update["read"] is None


@pytest.mark.finding("066", api3="048")
@pytest.mark.cell("activity_stream_read", "-", "-")
def test_activity_stream_refusals(site):
    assert fault(site.activity_stream_read, "Bogus", 1) == "Invalid parameter: type"
    assert fault(site.activity_stream_read, "Shot", 999999999) == (
        "Uncaught exception! Entity does not exist or user does not have permission")


# api3 049


@pytest.mark.finding("066", api3="049")
@pytest.mark.cell("followers", "-", "-")
def test_followers_and_following_refusals(site, made, sandbox, run_token):
    shot = made.create("Shot", {"code": "zzconf_%s_follow" % run_token, "project": sandbox})
    assert site.followers({"type": "Shot", "id": shot["id"]}) == []
    assert fault(site.followers, {"type": "Shot", "id": 999999999}) == "API followers() entity not found: Shot"
    assert fault(site.following, {"type": "Shot", "id": shot["id"]}) == (
        "API following() invalid user type. Must be HumanUser. Found: Shot")
    assert fault(site.following, {"type": "HumanUser", "id": 999999999}) == (
        "API following() user not found: HumanUser 999999999")


# api3 050


@pytest.mark.finding("064", api3="050")
@pytest.mark.cell("nav_expand", "-", "-")
def test_nav_expand_project_and_refusals(site, sandbox):
    node = site.nav_expand("/Project/%d" % sandbox["id"])
    assert node["path"] == "/Project/%d" % sandbox["id"]
    assert [(c["label"], c["ref"]) for c in node["children"]] == [
        ("Assets", {"kind": "entity_type", "value": "Asset"}), ("Shots", {"kind": "entity_type", "value": "Shot"})]
    assert fault(site.nav_expand, "/nope/nope/nope") == "Only 'Project' nav paths are currently supported: /nope/nope/nope"
    assert fault(site.nav_expand, "/Project/999999999") == "Unexpected result looking for project: 999999999: 0 found."
    assert fault(site.nav_expand, "/Project/%d/Bogus" % sandbox["id"]) == "Entity type provided is not part of the tree: Bogus"


@pytest.mark.finding("064", api3="050")
@pytest.mark.cell("nav_search_string", "-", "-")
def test_nav_search_failures_are_dicts(site):
    assert site.nav_search_string("/nope", "abc") == {
        "status": "failed",
        "description": "Unsupported or invalid root_path provided. Only paths with the format "
                       "'/Project/<project_id>' are currently supported."}


# api3 051


@pytest.mark.finding("047", api3="051")
@pytest.mark.cell("preferences_read", "-", "-")
def test_preferences_read(site):
    assert site.preferences_read(["zzprobe_not_a_pref"]) == {}
    assert set(site.preferences_read(["date_component_order"])) == {"date_component_order"}
    assert fault(site.preferences_read, "format_date_fields") == "API preferences_read() 'prefs' must be an array."


@pytest.mark.finding("047", api3="051")
@pytest.mark.cell("work_schedule_read", "-", "-")
def test_work_schedule_read(site):
    week = site.work_schedule_read("2026-03-02", "2026-03-15")
    assert len(week) == 14 and set(week["2026-03-02"]) == {"working", "description", "reason"}
    assert fault(site.work_schedule_read, "2026-03-15", "2026-03-02").startswith(
        "API work_schedule_read() 'end_date' must be greater than or equal to 'start_date':")
    assert fault(site.work_schedule_read, "nope", "2026-03-02").startswith(
        "API work_schedule_read() invalid format for 'start_date'. Valid format 'YYYY-MM-DD':")
    with pytest.raises(ShotgunError, match="must be strings in YYYY-MM-DD format"):
        site.work_schedule_read(None, None)


# api3 052


@pytest.mark.finding("072", api3="052")
@pytest.mark.cell("export_page", "-", "-")
def test_export_page_refusals(site):
    assert fault(site.export_page, 999999999, "csv") == "Trying to perform export for retired Page id=999999999"
    assert fault(site.export_page, None, "csv").startswith("API export_page() 'page_id' missing:")
