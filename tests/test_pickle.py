"""A mock instance survives pickling, as multiprocessing on macOS and Windows needs."""

import pickle

from sg_mockgun import Shotgun, schemas


def test_instance_pickles_with_its_records():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    project = sg.create("Project", {"name": "p"})
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    copy = pickle.loads(pickle.dumps(sg))
    assert copy.find_one("Shot", [["id", "is", shot["id"]]], ["code"])["code"] == "sh010"


def test_fixture_instance_pickles_and_keeps_its_clock():
    from sg_mockgun.pytest_plugin import make_sg

    sg = make_sg()
    first = sg._clock()
    copy = pickle.loads(pickle.dumps(sg))
    assert copy._clock() > first
