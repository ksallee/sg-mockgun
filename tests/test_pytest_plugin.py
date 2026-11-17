"""The ``sg`` fixture from the pytest plugin."""

import datetime

from sg_mockgun import Shotgun, schemas
from sg_mockgun.pytest_plugin import make_sg

pytest_plugins = ["pytester"]


def test_make_sg_uses_the_bundled_schema():
    sg = make_sg()
    assert isinstance(sg, Shotgun)
    assert "Shot" in sg.schema_entity_read()
    assert "visible" in sg.schema_field_read("Shot", "code")["code"]


def test_make_sg_leaves_the_class_schema_paths_alone():
    Shotgun.set_schema_paths(*schemas.paths("upstream_3_10_5"))
    make_sg()
    assert Shotgun.get_schema_paths() == schemas.paths("upstream_3_10_5")


def test_instances_share_no_records_or_schema():
    a, b = make_sg(), make_sg()
    a.create("Shot", {"code": "a"})
    a.schema_field_create("Shot", "text", "Notes")
    assert b.find("Shot", []) == []
    assert "sg_notes" not in b.schema_field_read("Shot")


def test_the_clock_is_deterministic():
    stamps = []
    for _ in range(2):
        sg = make_sg()
        sg.create("Shot", {"code": "a"})
        stamps.append([e["created_at"] for e in sg.find("EventLogEntry", [["event_type", "is", "Shotgun_Shot_New"]], ["created_at"])])
    assert stamps[0] == stamps[1]
    assert stamps[0][0] == datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def test_the_clock_advances_one_second_per_reading():
    sg = make_sg()
    first, second = sg._clock(), sg._clock()
    assert second - first == datetime.timedelta(seconds=1)


def test_a_suite_uses_the_fixture_with_no_setup(pytester):
    pytester.makepyfile(
        """
        def test_one(sg):
            sg.create("Shot", {"code": "a"})
            assert len(sg.find("Shot", [])) == 1

        def test_two(sg):
            assert sg.find("Shot", []) == []

        def test_load(sg, tmp_path):
            path = tmp_path / "seed.json"
            path.write_text('{"Project": [{"id": 4, "name": "P"}]}')
            sg.load(str(path))
            assert sg.find_one("Project", [["id", "is", 4]])["id"] == 4
        """
    )
    pytester.runpytest("-p", "no:cacheprovider").assert_outcomes(passed=3)
