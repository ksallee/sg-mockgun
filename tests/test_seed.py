"""Seeding from JSON, snapshot and restore."""

import datetime
import json
import os

import pytest
from shotgun_api3 import ShotgunError

from sg_mockgun import Shotgun, schemas

SMALL = os.path.join(os.path.dirname(__file__), "fixtures", "seed", "small.json")


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="seed", api_key="x")


def write(tmp_path, data):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_load_keeps_the_ids_and_links(sg):
    sg.load(SMALL)
    shot = sg.find_one("Shot", [["code", "is", "sh010"]], ["project", "sg_cut_in", "sg_sequence.Sequence.code"])
    assert shot["id"] == 1001
    assert shot["sg_cut_in"] == 1001
    assert shot["project"]["id"] == 70
    assert shot["sg_sequence.Sequence.code"] == "sq010"


def test_a_create_after_load_takes_the_next_id(sg):
    sg.load(SMALL)
    assert sg.create("Shot", {"code": "sh030"})["id"] == 1003


def test_load_writes_no_event_log_rows(sg):
    before = len(sg.find("EventLogEntry", []))
    sg.load(SMALL)
    assert len(sg.find("EventLogEntry", [])) == before


def test_load_parses_date_time_strings(sg, tmp_path):
    sg.load(write(tmp_path, {"Shot": [{"id": 1, "code": "a", "updated_at": "2026-03-01T10:00:00Z"}]}))
    row = sg.find_one("Shot", [["id", "is", 1]], ["updated_at"])
    assert row["updated_at"] == datetime.datetime(2026, 3, 1, 10, tzinfo=datetime.timezone.utc)


def test_load_accepts_a_dict(sg):
    sg.load({"Project": [{"id": 3, "name": "P"}]})
    assert sg.find_one("Project", [["id", "is", 3]], ["name"])["name"] == "P"


def test_load_refuses_a_record_without_an_id(sg, tmp_path):
    with pytest.raises(ShotgunError, match="id"):
        sg.load(write(tmp_path, {"Shot": [{"code": "a"}]}))


def test_load_refuses_a_duplicate_id(sg, tmp_path):
    with pytest.raises(ShotgunError, match="already"):
        sg.load(write(tmp_path, {"Shot": [{"id": 1, "code": "a"}, {"id": 1, "code": "b"}]}))


def test_load_refuses_an_unknown_entity_type(sg, tmp_path):
    with pytest.raises(ShotgunError, match="Nope"):
        sg.load(write(tmp_path, {"Nope": [{"id": 1}]}))


def test_load_refuses_an_unknown_field(sg, tmp_path):
    with pytest.raises(ShotgunError, match="sg_nope"):
        sg.load(write(tmp_path, {"Shot": [{"id": 1, "sg_nope": 1}]}))


def test_load_refuses_a_link_to_a_missing_record(sg, tmp_path):
    with pytest.raises(ShotgunError, match="Project 9"):
        sg.load(write(tmp_path, {"Shot": [{"id": 1, "project": {"type": "Project", "id": 9}}]}))


def test_a_refused_load_leaves_the_records_as_they_were(sg, tmp_path):
    with pytest.raises(ShotgunError):
        sg.load(write(tmp_path, {"Shot": [{"id": 1}, {"id": 2, "project": {"type": "Project", "id": 9}}]}))
    assert sg.find("Shot", []) == []


def test_restore_rolls_back_records(sg):
    sg.load(SMALL)
    state = sg.snapshot()
    sg.create("Shot", {"code": "sh030"})
    sg.update("Shot", 1001, {"code": "changed"})
    sg.delete("Shot", 1002)
    sg.restore(state)
    codes = sorted(r["code"] for r in sg.find("Shot", [], ["code"]))
    assert codes == ["sh010", "sh020"]


def test_restore_rolls_back_the_schema(sg):
    state = sg.snapshot()
    sg.schema_field_create("Shot", "text", "Notes")
    sg.restore(state)
    assert "sg_notes" not in sg.schema_field_read("Shot")
    # The code was free before the snapshot, so it is free again.
    assert sg.schema_field_create("Shot", "text", "Notes") == "sg_notes"


def test_a_snapshot_restores_twice(sg):
    state = sg.snapshot()
    sg.create("Shot", {"code": "a"})
    sg.restore(state)
    sg.create("Shot", {"code": "b"})
    sg.restore(state)
    assert sg.find("Shot", []) == []


def test_a_snapshot_is_not_changed_by_later_writes(sg):
    sg.load(SMALL)
    state = sg.snapshot()
    sg.update("Shot", 1001, {"code": "changed"})
    sg.restore(state)
    assert sg.find_one("Shot", [["id", "is", 1001]], ["code"])["code"] == "sh010"
