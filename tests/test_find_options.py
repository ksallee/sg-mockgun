"""find and find_one options: limit, page, order, include_archived_projects, additional_filter_presets."""

import pytest
from shotgun_api3 import ShotgunError

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


@pytest.fixture
def shots(sg):
    project = sg.create("Project", {"name": "p"})
    rows = [
        sg.create("Shot", {"code": code, "project": project, "sg_status_list": status})
        for code, status in [("c", "ip"), ("a", "wtg"), ("b", "ip"), ("d", "wtg")]
    ]
    return [r["id"] for r in rows]


def asc(field):
    return {"field_name": field, "direction": "asc"}


def desc(field):
    return {"field_name": field, "direction": "desc"}


def codes(rows):
    return [r["code"] for r in rows]


# finding 082, finding 006
def test_limit_applies_after_order(sg, shots):
    assert codes(sg.find("Shot", [], ["code"], order=[asc("code")], limit=2)) == ["a", "b"]


def test_limit_and_page_walk_the_ordered_set(sg, shots):
    order = [asc("code")]
    assert codes(sg.find("Shot", [], ["code"], order=order, limit=3, page=1)) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], order=order, limit=3, page=2)) == ["d"]
    assert sg.find("Shot", [], ["code"], order=order, limit=3, page=3) == []


def test_page_without_limit_uses_a_page_of_500(sg):
    # finding 082: the default page size is 500.
    for i in range(501):
        sg.create("Asset", {"code": "a%03d" % i})
    assert len(sg.find("Asset", [], page=1)) == 500
    assert len(sg.find("Asset", [], page=2)) == 1
    assert len(sg.find("Asset", [])) == 501


def test_limit_above_the_page_size_returns_that_many(sg):
    for i in range(502):
        sg.create("Asset", {"code": "a%03d" % i})
    assert len(sg.find("Asset", [], limit=501)) == 501


@pytest.mark.parametrize("kwargs", [{"limit": -1}, {"limit": "1"}, {"page": -1}, {"page": 1.0}])
def test_limit_and_page_are_validated_as_the_client_does(sg, kwargs):
    with pytest.raises(ValueError):
        sg.find("Shot", [], **kwargs)


def test_find_one_returns_the_first_ordered_row(sg, shots):
    assert sg.find_one("Shot", [], ["code"], order=[desc("code")])["code"] == "d"


# finding 026
def test_no_order_is_id_ascending(sg, shots):
    sg._db["Shot"] = dict(reversed(list(sg._db["Shot"].items())))
    assert [r["id"] for r in sg.find("Shot", [])] == sorted(shots)


def test_id_in_returns_id_ascending_not_list_order(sg, shots):
    rows = sg.find("Shot", [["id", "in", list(reversed(shots))]])
    assert [r["id"] for r in rows] == sorted(shots)


def test_first_order_key_is_primary(sg, shots):
    rows = sg.find("Shot", [], ["code"], order=[asc("sg_status_list"), desc("code")])
    assert codes(rows) == ["c", "b", "d", "a"]


def test_ties_break_on_id_ascending(sg, shots):
    rows = sg.find("Shot", [], ["code"], order=[desc("sg_status_list")])
    assert codes(rows) == ["a", "d", "c", "b"]


@pytest.mark.parametrize("field", ["open_notes_count", "sg_uploaded_movie", "sg_not_a_field_at_all"])
def test_unsortable_or_unknown_order_field_is_ignored(sg, field):
    ids = [sg.create("Version", {"code": c})["id"] for c in ["b", "a"]]
    sg._db["Version"][ids[0]]["sg_uploaded_movie"] = {"url": "https://x/1", "name": "1"}
    rows = sg.find("Version", [], ["code"], order=[desc(field), asc("code")])
    assert codes(rows) == ["a", "b"]


def test_order_on_a_dotted_path(sg):
    project = sg.create("Project", {"name": "p"})
    sh_b = sg.create("Shot", {"code": "b", "project": project})
    sh_a = sg.create("Shot", {"code": "a", "project": project})
    sg.create("Version", {"code": "v1", "entity": sh_b, "project": project})
    sg.create("Version", {"code": "v2", "entity": sh_a, "project": project})
    rows = sg.find("Version", [], ["code"], order=[asc("entity.Shot.code")])
    assert codes(rows) == ["v2", "v1"]
    rows = sg.find("Version", [], ["code"], order=[desc("entity.Shot.code")])
    assert codes(rows) == ["v1", "v2"]


# documented, unprobed (sg-groundtruth#109)
def test_include_archived_projects(sg):
    live = sg.create("Project", {"name": "live"})
    gone = sg.create("Project", {"name": "gone", "archived": True})
    sg.create("Shot", {"code": "a", "project": live})
    sg.create("Shot", {"code": "b", "project": gone})
    sg.create("Shot", {"code": "c"})
    assert codes(sg.find("Shot", [], ["code"])) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], include_archived_projects=True)) == ["a", "b", "c"]
    assert codes(sg.find("Shot", [], ["code"], include_archived_projects=False)) == ["a", "c"]
    one = sg.find_one("Shot", [["code", "is", "b"]], include_archived_projects=False)
    assert one is None


def test_additional_filter_presets(sg, shots):
    assert len(sg.find("Shot", [], additional_filter_presets=None)) == 4
    assert len(sg.find_one("Shot", [], additional_filter_presets=[])) == 2
    with pytest.raises(ShotgunError, match="additional_filter_presets"):
        sg.find("Shot", [], additional_filter_presets=[{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}])
    with pytest.raises(ShotgunError, match="additional_filter_presets"):
        sg.find_one("Shot", [], additional_filter_presets=[{"preset_name": "LATEST"}])
