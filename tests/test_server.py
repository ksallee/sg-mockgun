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
    mock.require_project = False  # the create contract is tested in test_records.py
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


def test_info_has_the_site_keys_and_needs_no_credentials(site):  # api3 046
    sg, mock = site
    assert sg.info() == mock.info()
    assert "totango_site_id" not in sg.info()
    stranger = shotgun_api3.Shotgun(sg.base_url, script_name="nobody", api_key="wrong", connect=False)
    assert stranger.info() == mock.info()
    assert sg.connect() is None


def test_summarize_over_the_wire(site):  # api3 040, 041
    sg, _ = site
    project = sg.create("Project", {"name": "Demo"})
    for status in ("wtg", "wtg", "ip"):
        sg.create("Task", {"content": "Anim", "project": project, "sg_status_list": status,
                           "due_date": datetime.date(2026, 3, 4)})
    on_project = [["project", "is", project]]
    answer = sg.summarize("Task", on_project, [{"field": "id", "type": "count"}, {"field": "due_date", "type": "latest"}],
                          grouping=[{"field": "sg_status_list", "type": "exact", "direction": "asc"}])
    assert answer["summaries"] == {"id": 3, "due_date": "2026-03-04"}
    assert [(x["group_value"], x["summaries"]["id"]) for x in answer["groups"]] == [("wtg", 2), ("ip", 1)]
    either = sg.summarize("Task", on_project + [["id", "is", 0]], [{"field": "id", "type": "count"}],
                          filter_operator="any")
    assert either["summaries"] == {"id": 3}
    with pytest.raises(shotgun_api3.Fault, match="duplicate summary request for field 'id'"):
        sg.summarize("Task", on_project, [{"field": "id", "type": "count"}, {"field": "id", "type": "maximum"}])


def test_text_search_over_the_wire(site):  # api3 043, 045
    sg, _ = site
    project = sg.create("Project", {"name": "Demo"})
    shot = sg.create("Shot", {"code": "sq010_sh010", "project": project})
    sg.create("Version", {"code": "v001", "entity": shot, "project": project})
    answer = sg.text_search("sq010", {"Shot": [["project", "is", project]], "Version": []},
                            project_ids=[project["id"]])
    assert answer["terms"] == ["sq010"]
    assert [(m["type"], m["links"]) for m in answer["matches"]] == [("Shot", ["", ""]), ("Version", ["Shot", "sq010_sh010"])]
    with pytest.raises(shotgun_api3.Fault, match="query text too short! must be 3 or more characters"):
        sg.text_search("ab", {"Shot": []})


def test_batch_over_the_wire_is_atomic(site):
    # api3 063
    sg, _ = site
    with pytest.raises(shotgun_api3.Fault, match=r"^API batch\(\) request with index 1 failed\.  All requests rolled back\.\n"):
        sg.batch([
            {"request_type": "create", "entity_type": "Shot", "data": {"code": "a"}},
            {"request_type": "update", "entity_type": "Shot", "entity_id": 0, "data": {"code": "b"}},
        ])
    assert sg.find("Shot", []) == []
