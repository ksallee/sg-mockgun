"""Attention, navigation and site reads: answers 047 to 052 in docs/api3."""

import datetime

import pytest
from shotgun_api3 import Fault, ShotgunError

from sg_mockgun import Shotgun as Mockgun, schemas

UTC = datetime.timezone.utc


@pytest.fixture
def sg():
    Mockgun.set_schema_paths(*schemas.paths())
    sg = Mockgun("https://mock.example.com", script_name="probe", api_key="x")
    sg.require_project = False  # the create contract is tested in test_records.py
    return sg


def at(minute):
    return datetime.datetime(2026, 9, 15, 12, minute, tzinfo=UTC)


@pytest.fixture
def thread(sg):
    user = sg.create("HumanUser", {"name": "Artist A", "login": "a"})
    other = sg.create("HumanUser", {"name": "Artist B", "login": "b"})
    attachment = sg.create("Attachment", {"created_at": at(30), "created_by": user})
    note = sg.create("Note", {"content": "Fix the edge.", "subject": "Edge", "created_at": at(0), "created_by": user,
                              "attachments": [attachment]})
    replies = [sg.create("Reply", {"entity": note, "content": "On it %d" % i, "user": other, "created_at": at(10 + i)})
               for i in range(2)]
    return note, attachment, replies, user, other


# api3 047
def test_note_thread_read_rows_oldest_first(sg, thread):
    note, attachment, replies, user, other = thread
    rows = sg.note_thread_read(note["id"])
    assert [r["type"] for r in rows] == ["Note", "Reply", "Reply", "Attachment"]
    assert sorted(rows[0]) == ["content", "created_at", "created_by", "id", "type"]
    assert sorted(rows[1]) == ["content", "created_at", "id", "type", "user"]
    assert sorted(rows[3]) == ["created_at", "created_by", "id", "type"]
    assert rows[0]["created_by"] == {"id": user["id"], "name": "Artist A", "type": "HumanUser"}
    assert rows[1]["user"] == {"id": other["id"], "name": "Artist B", "type": "HumanUser", "image": None}
    assert rows[0]["created_at"] == at(0)


def test_note_thread_read_entity_fields(sg, thread):
    note = thread[0]
    rows = sg.note_thread_read(note["id"], entity_fields={
        "Note": ["subject", "sg_not_a_field"], "Reply": ["entity"], "Attachment": ["filename"], "Bogus": ["code"]})
    assert sorted(rows[0]) == ["content", "created_at", "created_by", "id", "subject", "type"]
    assert rows[0]["subject"] == "Edge"
    assert sorted(rows[1]) == ["content", "created_at", "id", "type", "user"]
    assert "filename" in rows[3]


def test_note_thread_read_refusals(sg, thread):
    note = thread[0]
    with pytest.raises(ValueError, match="entity_fields parameter must be a dictionary"):
        sg.note_thread_read(note["id"], entity_fields=["subject"])
    with pytest.raises(Fault, match="^Not Found$"):
        sg.note_thread_read(999999999)
    with pytest.raises(Fault, match="^Not Found$"):
        sg.note_thread_read(0)
    with pytest.raises(Fault) as e:
        sg.note_thread_read("abc")
    assert str(e.value) == 'API note_thread_contents() \'note_id\' missing:\n{"note_id" => "abc", "entity_fields" => {}}'
    with pytest.raises(Fault, match="^Uncaught exception! no implicit conversion of Array into String$"):
        sg.note_thread_read(note["id"], entity_fields={"Note": "subject"})


# api3 048
@pytest.fixture
def stream(sg):
    project = sg.create("Project", {"name": "P"})
    shot = sg.create("Shot", {"code": "sh010", "project": project, "sg_status_list": "ip"})
    versions = [sg.create("Version", {"code": "v%03d" % i, "entity": shot, "project": project}) for i in range(30)]
    return project, shot, versions


def test_activity_stream_envelope_and_rows(sg, stream):
    project, shot, versions = stream
    answer = sg.activity_stream_read("Shot", shot["id"], limit=500)
    assert sorted(answer) == ["earliest_update_id", "entity_id", "entity_type", "latest_update_id", "updates"]
    assert answer["entity_type"] == "Shot" and answer["entity_id"] == shot["id"]
    ups = answer["updates"]
    assert len(ups) == 31
    ids = [u["id"] for u in ups]
    assert ids == sorted(ids, reverse=True)
    assert answer["earliest_update_id"] == 0
    row = ups[-1]
    assert sorted(row) == ["created_at", "created_by", "id", "meta", "primary_entity", "read", "update_type"]
    assert row["update_type"] == "create" and row["read"] is None
    assert row["meta"] == {"type": "new_entity", "entity_type": "Shot", "entity_id": shot["id"]}
    assert row["primary_entity"] == {"type": "Shot", "id": shot["id"], "name": "sh010", "status": "ip"}
    assert sorted(row["created_by"]) == ["id", "image", "name", "status", "type"]
    assert isinstance(row["created_at"], datetime.datetime)
    newest = max(sg._db["EventLogEntry"])
    assert answer["latest_update_id"] == newest


def test_activity_stream_limit(sg, stream):
    shot = stream[1]
    assert len(sg.activity_stream_read("Shot", shot["id"])["updates"]) == 25
    assert len(sg.activity_stream_read("Shot", shot["id"], limit=0)["updates"]) == 25
    three = sg.activity_stream_read("Shot", shot["id"], limit=3)
    assert len(three["updates"]) == 3
    assert three["earliest_update_id"] == three["updates"][-1]["id"]
    with pytest.raises(Fault, match="^Uncaught exception! Invalid parameter: page_size$"):
        sg.activity_stream_read("Shot", shot["id"], limit=-1)


def test_activity_stream_limit_caps_at_500(sg):
    project = sg.create("Project", {"name": "Big"})
    sg.generate_event_log_entries = True
    for i in range(510):
        sg.create("Shot", {"code": "s%d" % i, "project": project})
    assert len(sg.activity_stream_read("Project", project["id"], limit=501)["updates"]) == 500


def test_activity_stream_bounds_are_exclusive(sg, stream):
    shot = stream[1]
    ids = [u["id"] for u in sg.activity_stream_read("Shot", shot["id"], limit=500)["updates"]]
    mid = ids[10]
    below = sg.activity_stream_read("Shot", shot["id"], max_id=mid, limit=3)
    assert [u["id"] for u in below["updates"]] == ids[11:14]
    assert below["latest_update_id"] == ids[11]
    above = sg.activity_stream_read("Shot", shot["id"], min_id=mid, limit=500)
    assert [u["id"] for u in above["updates"]] == ids[:10]
    assert above["earliest_update_id"] == ids[9]
    empty = sg.activity_stream_read("Shot", shot["id"], min_id=ids[0] + 10 ** 7)
    newest = max(sg._db["EventLogEntry"])
    assert empty["updates"] == [] and empty["earliest_update_id"] == newest == empty["latest_update_id"]


def test_activity_stream_entity_fields_and_version(sg, stream):
    shot, versions = stream[1], stream[2]
    answer = sg.activity_stream_read("Shot", shot["id"], limit=500, entity_fields={"Version": ["entity", "sg_not_a_field"]})
    pe = next(u["primary_entity"] for u in answer["updates"] if u["primary_entity"]["type"] == "Version")
    assert sorted(pe) == ["entity", "id", "name", "status", "type"]
    own = sg.activity_stream_read("Version", versions[0]["id"])
    assert own["entity_type"] == "Version" and len(own["updates"]) == 1


def test_activity_stream_refusals(sg, stream):
    shot = stream[1]
    missing = "^Uncaught exception! Entity does not exist or user does not have permission$"
    for args in (("Shot", 999999999), ("Version", 999999999), ("Shot", 0)):
        with pytest.raises(Fault, match=missing):
            sg.activity_stream_read(*args)
    for args in (("Bogus", 1), ("shots", shot["id"])):
        with pytest.raises(Fault, match="^Invalid parameter: type$"):
            sg.activity_stream_read(*args)
    with pytest.raises(Fault, match="^Invalid parameter: id$"):
        sg.activity_stream_read("Shot", "abc")
    with pytest.raises(ValueError, match="entity_fields parameter must be a dictionary"):
        sg.activity_stream_read("Shot", shot["id"], entity_fields=["code"])


# api3 049
@pytest.fixture
def follows(sg):
    project = sg.create("Project", {"name": "P"})
    other = sg.create("Project", {"name": "Q"})
    user = sg.create("HumanUser", {"name": "Artist A", "login": "a", "sg_status_list": "act"})
    tasks = [sg.create("Task", {"content": "t%d" % i, "project": project}) for i in range(2)]
    note = sg.create("Note", {"content": "n", "project": other})
    sg.set_following({"type": "HumanUser", "id": user["id"]}, tasks + [note])
    return user, project, tasks, note


def test_following(sg, follows):
    user, project, tasks, note = follows
    rows = sg.following(user)
    assert sorted(rows, key=lambda r: (r["type"], r["id"])) == sorted(
        [{"type": "Task", "id": t["id"]} for t in tasks] + [{"type": "Note", "id": note["id"]}],
        key=lambda r: (r["type"], r["id"]))
    assert len(sg.following(user, entity_type="Task")) == 2
    assert len(sg.following(user, project=project)) == 2
    assert len(sg.following(user, project=project, entity_type="Note")) == 0


def test_following_refusals(sg, follows):
    user = follows[0]
    with pytest.raises(Fault) as e:
        sg.following(user, entity_type="tasks")
    assert str(e.value).startswith("API following() invalid/missing 'type' string:\n\"tasks\"\nValid types:\n[")
    with pytest.raises(Fault, match="^API following\\(\\) project not found: Project 999999999$"):
        sg.following(user, project={"type": "Project", "id": 999999999})
    with pytest.raises(Fault, match="^API following\\(\\) user not found: HumanUser 999999999$"):
        sg.following({"type": "HumanUser", "id": 999999999})
    with pytest.raises(Fault, match="^API following\\(\\) invalid user type. Must be HumanUser. Found: ApiUser$"):
        sg.following({"type": "ApiUser", "id": 1})


def test_followers(sg, follows):
    user, project, tasks, note = follows
    rows = sg.followers({"type": "Task", "id": tasks[0]["id"]})
    assert len(rows) == 1
    assert sorted(rows[0]) == ["id", "name", "status", "type", "uuid", "valid"]
    assert rows[0]["name"] == "Artist A" and rows[0]["status"] == "act" and rows[0]["valid"] == "valid"
    assert isinstance(rows[0]["uuid"], str)
    assert sg.followers({"type": "Shot", "id": sg.create("Shot", {"code": "x"})["id"]}) == []


def test_followers_refusals(sg):
    with pytest.raises(Fault, match="^API followers\\(\\) entity not found: Shot$"):
        sg.followers({"type": "Shot", "id": 999999999})
    with pytest.raises(Fault) as e:
        sg.followers({"type": "Bogus", "id": 1})
    assert str(e.value).startswith(
        "API followers() invalid/missing entity hash string 'type':\n{\"type\" => \"Bogus\", \"id\" => 1}\nValid entity types:\n[")
    with pytest.raises(Fault) as e:
        sg.followers({"type": "Shot"})
    assert str(e.value) == "API followers() invalid/missing entity hash integer 'id':\n{\"type\" => \"Shot\"}"


# api3 050
@pytest.fixture
def tree(sg):
    project = sg.create("Project", {"name": "Show"})
    seqs = [sg.create("Sequence", {"code": "seq%02d" % i, "project": project}) for i in (1, 2)]
    shots = [sg.create("Shot", {"code": "sh%d" % i, "project": project, "sg_sequence": seqs[0],
                                "sg_status_list": "ip"}) for i in (10, 20)]
    loose = sg.create("Shot", {"code": "loose", "project": project})
    prop = sg.create("Asset", {"code": "Acorn", "project": project, "sg_asset_type": "Prop"})
    return project, seqs, shots, loose, prop


def te(path):
    return {"type": "Version", "additional_filter_presets": [
        {"preset_name": "NAV_ENTRIES", "path": path, "seed": {"type": "Version", "field": "entity"}}]}


def test_nav_expand_root_and_project(sg, tree):
    project = tree[0]
    p = "/Project/%d" % project["id"]
    root = sg.nav_expand("/")
    assert root["label"] == "root" and root["ref"] == {"kind": "root", "value": None} and root["path"] == "/"
    assert root["target_entities"] == te("")
    assert root["children"][0] == {"label": "Show", "ref": {"kind": "entity", "value": {"type": "Project", "id": project["id"]}},
                                   "parent_path": "/", "path": p, "target_entities": te(p), "has_children": True}
    assert sg.nav_expand("") == root
    node = sg.nav_expand(p)
    assert node["parent_path"] == "/" and [c["label"] for c in node["children"]] == ["Assets", "Shots"]
    assert node["children"][1] == {"label": "Shots", "ref": {"kind": "entity_type", "value": "Shot"},
                                   "path": p + "/Shot", "target_entities": te(p + "/Shot"), "has_children": True}


def test_nav_expand_shots_repeat_the_bucket(sg, tree):
    project, seqs = tree[0], tree[1]
    p = "/Project/%d/Shot" % project["id"]
    node = sg.nav_expand(p)
    assert node["parent_path"] == "/Project/%d" % project["id"]
    kids = node["children"]
    assert [c["ref"]["kind"] for c in kids] == ["entity", "entity_type", "entity", "entity_type"]
    bucket = {"label": "Shots with no Sequence", "ref": {"kind": "entity_type", "value": "Shot"},
              "path": p + "/sg_sequence/Sequence/__none__", "target_entities": te(p + "/sg_sequence/Sequence/__none__"),
              "has_children": True}
    assert kids[1] == bucket == kids[3]
    assert kids[0]["path"] == p + "/sg_sequence/Sequence/%d" % seqs[0]["id"] and kids[0]["label"] == "seq01"


def test_nav_expand_group_bucket_and_assets(sg, tree):
    project, seqs, shots, loose, prop = tree
    p = "/Project/%d" % project["id"]
    group = sg.nav_expand(p + "/Shot/sg_sequence/Sequence/%d" % seqs[0]["id"], entity_fields={"Shot": ["sg_status_list"]})
    leaf = group["children"][0]
    assert leaf["ref"] == {"kind": "entity", "value": {"type": "Shot", "id": shots[0]["id"], "sg_status_list": "ip"}}
    assert leaf["path"] == p + "/Shot/sg_sequence/Sequence/%d/id/%d" % (seqs[0]["id"], shots[0]["id"])
    assert leaf["has_children"] is False
    empty = sg.nav_expand(p + "/Shot/sg_sequence/Sequence/%d" % seqs[1]["id"])
    assert empty["children"] == [{"label": "No Shots", "ref": {"kind": "empty", "value": None}, "has_children": False}]
    bucket = sg.nav_expand(p + "/Shot/sg_sequence/Sequence/__none__")
    assert [c["ref"]["value"]["id"] for c in bucket["children"]] == [loose["id"]]
    assert sg.nav_expand(p + "/Shot/sg_sequence/__none__")["label"] == "Shots with no __none__"
    assets = sg.nav_expand(p + "/Asset")["children"]
    assert all(c["ref"]["kind"] == "list" for c in assets)
    assert assets[-1]["label"] == "Assets with no Type"
    assert assets[-1]["ref"] == {"kind": "list", "value": "__none__"}
    assert assets[-1]["path"] == p + "/Asset/sg_asset_type/__none__"


def test_nav_expand_no_sequence_hides_shots(sg):
    project = sg.create("Project", {"name": "Flat"})
    sg.create("Shot", {"code": "a", "project": project})
    kids = sg.nav_expand("/Project/%d/Shot" % project["id"])["children"]
    assert kids == [{"label": "No Shots", "ref": {"kind": "empty", "value": None}, "has_children": False}]


def test_nav_expand_refusals(sg, tree):
    p = "/Project/%d" % tree[0]["id"]
    cases = [
        (("/Project/999999999",), "Unexpected result looking for project: 999999999: 0 found."),
        ((p + "/Bogus",), "Entity type provided is not part of the tree: Bogus"),
        ((p + "/shots",), "Entity type provided is not part of the tree: shots"),
        ((p + "/Shot/sg_not_a_field/Sequence/1",), "Unexpected field name in path: sg_not_a_field (expecting sg_sequence)"),
        (("/nope/nope/nope",), "Only 'Project' nav paths are currently supported: /nope/nope/nope"),
    ]
    for args, message in cases:
        with pytest.raises(Fault) as e:
            sg.nav_expand(*args)
        assert str(e.value) == message
    with pytest.raises(Fault) as e:
        sg.nav_expand(p + "/Shot", seed_entity_field="Shot.code")
    assert str(e.value) == "Entity type provided is not part of the tree: Shot"
    assert sg.nav_expand("/Project/999999999/Shot")["children"][0]["label"] == "No Shots"
    assert sg.nav_expand(p[1:])["path"] == p[1:]


def test_nav_search(sg, tree):
    project, seqs, shots, loose, prop = tree
    p = "/Project/%d" % project["id"]
    rows = sg.nav_search_string(p, "sh10")
    assert rows == [{"label": "sh10", "incremental_path": [
        p, p + "/Shot", p + "/Shot/sg_sequence/Sequence/%d" % seqs[0]["id"],
        p + "/Shot/sg_sequence/Sequence/%d/id/%d" % (seqs[0]["id"], shots[0]["id"])],
        "path_label": "Shots > seq01", "ref": {"id": shots[0]["id"], "type": "Shot"}, "project_id": project["id"]}]
    assert sg.nav_search_entity(p, {"type": "Shot", "id": shots[0]["id"]}) == rows
    assert sg.nav_search_entity(p, {"type": "Shot", "id": 999999999}) == []
    assert sg.nav_search_string(p, "zzz_no_such") == []
    short = sg.nav_search_string(p, "a")
    assert {"label": "Assets", "incremental_path": [p, p + "/Asset"], "path_label": "",
            "ref": {"id": None, "type": None}, "project_id": project["id"]} in short
    assert [r["label"] for r in short] == sorted(r["label"] for r in short)


def test_nav_search_failures_are_dicts(sg, tree):
    p = "/Project/%d" % tree[0]["id"]
    invalid = {"status": "failed", "description": "Unsupported or invalid root_path provided. "
               "Only paths with the format '/Project/<project_id>' are currently supported."}
    assert sg.nav_search_string(p + "/Shot", "abc") == invalid
    assert sg.nav_search_string("/nope", "abc") == invalid
    assert sg.nav_search_string("/Project/999999999", "abc") == {"status": "failed", "description": "undefined method 'select!' for nil"}
    assert sg.nav_search_entity(p, {"type": "Bogus", "id": 1}) == {"status": "failed", "description": "undefined method '[]' for nil"}


# api3 051
def test_preferences_read(sg):
    prefs = sg.preferences_read()
    assert len(prefs) == 17 and isinstance(prefs["hours_per_day"], float)
    assert isinstance(prefs["support_local_storage"], bool)
    assert sg.preferences_read(["hours_per_day"]) == {"hours_per_day": prefs["hours_per_day"]}
    assert sg.preferences_read(["zzprobe_not_a_pref"]) == {}
    with pytest.raises(Fault, match="^API preferences_read\\(\\) 'prefs' must be an array.$"):
        sg.preferences_read("hours_per_day")
    sg.set_preferences({"hours_per_day": 10.0})
    assert sg.preferences_read(["hours_per_day"]) == {"hours_per_day": 10.0}


def test_work_schedule_read(sg):
    week = sg.work_schedule_read("2026-03-02", "2026-03-15")
    assert list(week) == ["2026-03-%02d" % d for d in range(2, 16)]
    assert week["2026-03-02"] == {"working": True, "description": None, "reason": "STUDIO_WORK_WEEK"}
    assert week["2026-03-07"]["working"] is False
    assert len(sg.work_schedule_read("2026-03-02", "2026-03-08", project={"type": "Project", "id": 999999999})) == 7
    assert len(sg.work_schedule_read("2026-01-01", "2027-12-31")) == 730
    sg.set_work_schedule(exceptions={"2026-03-03": {"working": False, "description": "Closed", "reason": "STUDIO_EXCEPTION"}})
    assert sg.work_schedule_read("2026-03-03", "2026-03-03")["2026-03-03"]["description"] == "Closed"


def test_work_schedule_refusals(sg):
    with pytest.raises(Fault) as e:
        sg.work_schedule_read("2026-03-15", "2026-03-02")
    assert str(e.value) == (
        "API work_schedule_read() 'end_date' must be greater than or equal to 'start_date':\n"
        '{"start_date" => "2026-03-15",\n "end_date" => "2026-03-02",\n "project" => nil,\n "user" => nil}')
    with pytest.raises(Fault) as e:
        sg.work_schedule_read("nope", "2026-03-15")
    assert str(e.value) == (
        "API work_schedule_read() invalid format for 'start_date'. Valid format 'YYYY-MM-DD':\n"
        '{"start_date" => "nope",\n "end_date" => "2026-03-15",\n "project" => nil,\n "user" => nil}')
    with pytest.raises(ShotgunError, match="must be strings in YYYY-MM-DD format"):
        sg.work_schedule_read(datetime.date(2026, 3, 2), "2026-03-15")


def test_user_subscriptions_read(sg):
    assert sg.user_subscriptions_read() == {}
    sg.set_user_subscriptions({"7": "not_for_resale", "8": None})
    assert sg.user_subscriptions_read() == {"7": "not_for_resale", "8": None}


# api3 052
def test_export_page(sg):
    page = sg.create("Page", {"name": "p", "page_type": "canvas"})
    with pytest.raises(Fault, match="^Export for Page id=%d not available$" % page["id"]):
        sg.export_page(page["id"], "csv", layout_name="layout_0")
    with pytest.raises(Fault, match="^Trying to perform export for retired Page id=999999999$"):
        sg.export_page(999999999, "csv")
    with pytest.raises(Fault) as e:
        sg.export_page(page["id"], None)
    assert str(e.value) == "API export_page() 'format' missing:\n" \
        '{"format" => nil, "page_id" => %d, "layout_name" => nil}' % page["id"]
    with pytest.raises(Fault) as e:
        sg.export_page("abc", "csv")
    assert str(e.value) == "API export_page() invalid 'page_id':\n" \
        '{"format" => "csv", "page_id" => "abc", "layout_name" => nil}'
    with pytest.raises(Fault, match="'page_id' missing"):
        sg.export_page(None, "csv")
