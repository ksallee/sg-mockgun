"""A real shotgun_api3 client against `sg-mockgun serve`."""

import datetime
import threading

import pytest
import shotgun_api3

from sg_mockgun import Shotgun as Mockgun, schemas
from sg_mockgun.server import make_server


@pytest.fixture
def site():
    Mockgun.set_schema_paths(*schemas.paths())
    mock = Mockgun("https://mock.example.com", script_name="server", api_key="x")
    server = make_server(mock, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:%d" % server.server_address[1]
    yield shotgun_api3.Shotgun(url, script_name="pipeline", api_key="anything"), mock
    server.shutdown()


def test_connects_and_reports_a_version(site):
    sg, _ = site
    assert tuple(sg.server_info["version"][:2]) == (8, 91)


def test_create_find_update_delete_revive(site):
    sg, _ = site
    project = sg.create("Project", {"name": "Demo"})
    shot = sg.create("Shot", {"code": "sh010", "project": project, "sg_cut_in": 1001})
    assert shot["code"] == "sh010" and shot["type"] == "Shot"
    found = sg.find_one("Shot", [["project", "is", project], ["code", "starts_with", "sh"]], ["sg_cut_in", "project"])
    assert found["id"] == shot["id"] and found["sg_cut_in"] == 1001
    assert found["project"]["id"] == project["id"]
    updated = sg.update("Shot", shot["id"], {"sg_cut_in": 1009})
    assert updated["sg_cut_in"] == 1009
    assert sg.delete("Shot", shot["id"]) is True
    assert sg.find("Shot", [["id", "is", shot["id"]]]) == []
    assert sg.revive("Shot", shot["id"]) is True


def test_any_filter_and_in(site):
    sg, _ = site
    for code in ("a", "b", "c"):
        sg.create("Shot", {"code": code})
    got = sg.find("Shot", [{"filter_operator": "any", "filters": [["code", "is", "a"], ["code", "is", "c"]]}], ["code"])
    assert sorted(r["code"] for r in got) == ["a", "c"]
    got = sg.find("Shot", [["code", "in", ["a", "b"]]], ["code"])
    assert sorted(r["code"] for r in got) == ["a", "b"]


def test_paging_returns_everything(site):
    sg, _ = site
    sg.config._records_per_page = 7
    sg.batch([{"request_type": "create", "entity_type": "Shot", "data": {"code": "s%02d" % i}} for i in range(23)])
    assert len(sg.find("Shot", [], ["code"])) == 23
    assert len(sg.find("Shot", [], ["code"], limit=10)) == 10


def test_order_desc(site):
    sg, _ = site
    for code in ("a", "b", "c"):
        sg.create("Shot", {"code": code})
    got = sg.find("Shot", [], ["code"], order=[{"field_name": "code", "direction": "desc"}])
    assert [r["code"] for r in got] == ["c", "b", "a"]


def test_datetimes_round_trip(site):
    sg, _ = site
    when = datetime.datetime(2026, 11, 12, 10, 0, 0, tzinfo=shotgun_api3.sg_timezone.utc)
    note = sg.create("Shot", {"code": "dt"})
    sg.update("Shot", note["id"], {"sg_cut_in": 1})
    rows = sg.find("EventLogEntry", [["entity", "is", {"type": "Shot", "id": note["id"]}]], ["created_at"])
    assert all(isinstance(r["created_at"], datetime.datetime) for r in rows)
    assert when.tzinfo is not None


def test_schema_calls_and_faults(site):
    sg, _ = site
    code = sg.schema_field_create("Shot", "text", "Vendor Note")
    assert code == "sg_vendor_note"
    assert sg.schema_field_read("Shot", code)[code]["data_type"]["value"] == "text"
    assert "Shot" in sg.schema_entity_read()
    assert code in sg.schema_read()["Shot"]
    with pytest.raises(shotgun_api3.Fault, match="invalid property 'data_type'"):
        sg.schema_field_update("Shot", code, {"data_type": "number"})
    assert sg.schema_field_update("Shot", code, {"name": "Vendor Notes"}) is True
    assert sg.schema_field_delete("Shot", code) is True
    with pytest.raises(shotgun_api3.Fault, match="there is a retired field with the same field_name: sg_vendor_note"):
        sg.schema_field_create("Shot", "text", "Vendor Note")


def test_unknown_method_is_not_permitted(site):
    sg, _ = site
    with pytest.raises(shotgun_api3.Fault, match=r'^Error: API method "schema_field_revive" is not permitted\.$'):
        sg._call_rpc("schema_field_revive", {"type": "Shot", "field_name": "sg_x"})


def test_events_name_the_calling_script(site):
    sg, _ = site
    sg.create("Shot", {"code": "x"})
    new = sg.find_one("EventLogEntry", [["event_type", "is", "Shotgun_Shot_New"]], ["user", "description"])
    assert new["description"] == "pipeline created new Shot "
