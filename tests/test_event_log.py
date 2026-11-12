"""EventLogEntry rows mockgun writes, shaped like the api3 probe of 2026-11-12."""

import datetime

import pytest

from sg_mockgun import Shotgun, schemas

FIELDS = ["event_type", "attribute_name", "meta", "entity", "description", "user", "project", "created_at"]
T0 = datetime.datetime(2026, 11, 12, 21, 54, 8, tzinfo=datetime.timezone.utc)


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="probe-script", api_key="y")
    sg.set_clock(lambda: T0)
    return sg


def events(sg, after=0):
    return sg.find("EventLogEntry", [["id", "greater_than", after]], FIELDS, order=[{"field_name": "id", "direction": "asc"}])


def head(sg):
    return max(e["id"] for e in sg.find("EventLogEntry", [], ["id"]))


def test_create_logs_new_then_one_change_per_field(sg):
    project = sg.create("Project", {"name": "Demo"})
    start = head(sg)
    v = sg.create("Version", {"code": "v001", "description": "probe", "project": project})
    rows = events(sg, start)
    assert [r["event_type"] for r in rows] == ["Shotgun_Version_New"] + ["Shotgun_Version_Change"] * 3
    new = rows[0]
    assert new["meta"] == {"type": "new_entity", "entity_type": "Version", "entity_id": v["id"], "platform_id": None}
    assert new["description"] == "probe-script created new Version "
    assert new["entity"] == {"type": "Version", "id": v["id"]}
    assert new["project"] == {"type": "Project", "id": project["id"]}
    assert new["user"]["type"] == "ApiUser" and new["user"]["name"] == "probe-script"
    code = [r for r in rows if r["attribute_name"] == "code"][0]
    assert code["meta"] == {
        "type": "attribute_change", "attribute_name": "code", "entity_type": "Version", "entity_id": v["id"],
        "in_create": True, "field_data_type": "text", "old_value": None, "new_value": "v001", "platform_id": None,
    }
    assert code["description"] == 'probe-script changed "Version Name" from "" to "v001" on Version v001'


def test_update_logs_only_changed_fields(sg):
    v = sg.create("Version", {"code": "v001", "description": "probe", "sg_status_list": "rev"})
    start = head(sg)
    sg.update("Version", v["id"], {"description": "probe 2", "sg_status_list": "rev"})
    rows = events(sg, start)
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [("Shotgun_Version_Change", "description")]
    assert rows[0]["meta"]["old_value"] == "probe" and rows[0]["meta"]["new_value"] == "probe 2"
    assert "in_create" not in rows[0]["meta"]


def test_delete_and_revive(sg):
    v = sg.create("Version", {"code": "v001"})
    start = head(sg)
    sg.delete("Version", v["id"])
    sg.revive("Version", v["id"])
    rows = events(sg, start)
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [
        ("Shotgun_Version_Change", "retirement_date"),
        ("Shotgun_Version_Retirement", None),
        ("Shotgun_Version_Change", "retirement_date"),
        ("Shotgun_Version_Revival", None),
    ]
    assert rows[0]["meta"]["new_value"] == "2026-11-12 21:54:08 UTC"
    assert rows[1]["meta"] == {
        "entity_type": "Version", "class_name": "Version", "entity_id": v["id"], "id": v["id"],
        "type": "entity_retirement", "retirement_date": "2026-11-12 21:54:08 UTC", "display_name": "v001",
    }
    assert rows[1]["description"] == ' retired Version "v001"'
    assert rows[2]["meta"]["old_value"] == "2026-11-12 21:54:08 UTC" and rows[2]["meta"]["new_value"] is None
    assert rows[3]["meta"] == {
        "class_name": "Version", "display_name": "v001", "id": v["id"], "entity_type": "Version",
        "entity_id": v["id"], "type": "entity_revival",
    }


def test_delete_orphans_earlier_rows(sg):
    v = sg.create("Version", {"code": "v001"})
    sg.delete("Version", v["id"])
    linked = sg.find("EventLogEntry", [["entity", "is", {"type": "Version", "id": v["id"]}]], ["event_type"])
    assert linked == []
    by_meta = [e for e in events(sg) if (e["meta"] or {}).get("entity_id") == v["id"]]
    assert len(by_meta) == 4


def test_schema_writes_log_display_column_rows(sg):
    start = head(sg)
    code = sg.schema_field_create("Version", "text", "zzprobe mockgun a")
    sg.schema_field_update("Version", code, {"name": "zzprobe mockgun a renamed"})
    sg.schema_field_delete("Version", code)
    rows = events(sg, start)
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [
        ("Shotgun_DisplayColumn_New", None),
        ("Shotgun_DisplayColumn_Change", "human_name"),
        ("Shotgun_DisplayColumn_Change", "retirement_date"),
        ("Shotgun_DisplayColumn_Retirement", None),
    ]
    dc = rows[0]["meta"]["entity_id"]
    assert rows[0]["meta"] == {"type": "new_entity", "entity_type": "DisplayColumn", "entity_id": dc}
    assert rows[0]["description"] == "probe-script created new Field sg_zzprobe_mockgun_a"
    assert rows[1]["meta"]["old_value"] == "zzprobe mockgun a"
    assert rows[1]["description"] == (
        'probe-script changed "Field Name" from "zzprobe mockgun a" to "zzprobe mockgun a renamed" on Field sg_zzprobe_mockgun_a'
    )
    assert rows[3]["meta"]["display_name"] == "sg_zzprobe_mockgun_a" and rows[3]["meta"]["id"] == dc


def test_logging_can_be_switched_off_like_the_api_user_flag(sg):
    sg.generate_event_log_entries = False
    start = head(sg)
    sg.create("Version", {"code": "v001"})
    assert events(sg, start) == []


def test_batch_logs_through_the_same_paths(sg):
    start = head(sg)
    sg.batch([{"request_type": "create", "entity_type": "Version", "data": {"code": "v001"}}])
    assert [r["event_type"] for r in events(sg, start)] == ["Shotgun_Version_New", "Shotgun_Version_Change"]
