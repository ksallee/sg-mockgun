"""A real shotgun_api3 client against `sg-mockgun serve` for answers 047 to 052 in docs/api3."""

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


def test_note_thread_and_stream_over_the_wire(site):
    sg, mock = site
    when = datetime.datetime(2026, 9, 15, 12, 0, tzinfo=datetime.timezone.utc)
    user = mock.create("HumanUser", {"name": "A", "login": "a"})
    note = mock.create("Note", {"content": "c", "created_at": when, "created_by": user})
    mock.create("Reply", {"entity": note, "content": "r", "user": user, "created_at": when + datetime.timedelta(minutes=1)})
    rows = sg.note_thread_read(note["id"])  # api3 047
    assert [r["type"] for r in rows] == ["Note", "Reply"]
    assert isinstance(rows[0]["created_at"], datetime.datetime)
    with pytest.raises(shotgun_api3.Fault, match="^Not Found$"):
        sg.note_thread_read(999999999)
    shot = sg.create("Shot", {"code": "sh010"})
    answer = sg.activity_stream_read("Shot", shot["id"])  # api3 048
    assert answer["updates"][0]["primary_entity"]["name"] == "sh010"
    with pytest.raises(shotgun_api3.Fault, match="^Invalid parameter: type$"):
        sg.activity_stream_read("shots", shot["id"])


def test_follows_nav_site_reads_export_over_the_wire(site):
    sg, mock = site
    user = mock.create("HumanUser", {"name": "A", "login": "a"})
    project = mock.create("Project", {"name": "Show"})
    task = mock.create("Task", {"content": "t", "project": project})
    mock.set_following(user, [task])
    assert sg.following(user) == [{"type": "Task", "id": task["id"]}]  # api3 049
    assert [r["id"] for r in sg.followers(task)] == [user["id"]]
    p = "/Project/%d" % project["id"]
    assert [c["label"] for c in sg.nav_expand(p)["children"]] == ["Assets", "Shots"]  # api3 050
    assert sg.nav_search_string("/nope", "abc")["status"] == "failed"
    assert sg.preferences_read(["hours_per_day"]) == {"hours_per_day": 8.0}  # api3 051
    assert len(sg.work_schedule_read("2026-03-02", "2026-03-08")) == 7
    with pytest.raises(shotgun_api3.Fault, match="invalid format for 'start_date'"):
        sg.work_schedule_read("nope", "2026-03-08")
    assert sg.user_subscriptions_read() == {}
    page = mock.create("Page", {"name": "p"})
    with pytest.raises(shotgun_api3.Fault, match="^Export for Page id=%d not available$" % page["id"]):  # api3 052
        sg.export_page(page["id"], "csv")
