"""Entity and multi_entity filters match and refuse as the site does."""

import os

import pytest
from shotgun_api3 import Fault, ShotgunError

from sg_mockgun import Shotgun as Mockgun

SCHEMA = os.path.join(os.path.dirname(__file__), "fixtures", "upstream")


@pytest.fixture
def sg():
    Mockgun.set_schema_paths(
        os.path.join(SCHEMA, "schema.pickle"),
        os.path.join(SCHEMA, "schema_entity.pickle"),
    )
    sg = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")
    sg.require_project = False  # the create contract is tested in test_records.py
    return sg


@pytest.fixture
def versions(sg):
    """Versions linked to shot A, shot B, an asset, and nothing."""
    a = sg.create("Shot", {"code": "sh010_0010"})
    b = sg.create("Shot", {"code": "sh020_0010"})
    asset = sg.create("Asset", {"code": "charA"})
    rows = {
        "a": sg.create("Version", {"code": "va", "entity": a}),
        "b": sg.create("Version", {"code": "vb", "entity": b}),
        "asset": sg.create("Version", {"code": "vasset", "entity": asset}),
        "none": sg.create("Version", {"code": "vnone", "entity": None}),
    }
    return sg, a, b, asset, rows


def codes(sg, entity_type, filters):
    return sorted(r["code"] for r in sg.find(entity_type, filters, ["code"]))


# field_types/entity


def test_entity_in_matches_any_listed_entity(versions):
    # finding 017: 3 rows for one hash, 6 for two
    sg, a, b, _, _ = versions
    assert codes(sg, "Version", [["entity", "in", [a, b]]]) == ["va", "vb"]
    assert codes(sg, "Version", [["entity", "in", a]]) == ["va"]


def test_entity_not_in(versions):
    sg, a, b, _, _ = versions
    # api3 010: negation matches unset rows
    assert codes(sg, "Version", [["entity", "not_in", [a, b]]]) == ["vasset", "vnone"]
    assert codes(sg, "Version", [["entity", "not_in", a]]) == ["vasset", "vb", "vnone"]


def test_entity_type_is(versions):
    sg = versions[0]
    assert codes(sg, "Version", [["entity", "type_is", "Shot"]]) == ["va", "vb"]
    # api3 010: `type_is None` means unset.
    assert codes(sg, "Version", [["entity", "type_is", None]]) == ["vnone"]


def test_entity_type_is_not(versions):
    sg = versions[0]
    assert codes(sg, "Version", [["entity", "type_is_not", "Shot"]]) == ["vasset", "vnone"]
    assert codes(sg, "Version", [["entity", "type_is_not", None]]) == ["va", "vasset", "vb"]


def test_entity_name_operators(versions):
    sg = versions[0]
    assert codes(sg, "Version", [["entity", "name_is", "sh010_0010"]]) == ["va"]
    assert codes(sg, "Version", [["entity", "name_is", "Shot"]]) == []
    assert codes(sg, "Version", [["entity", "name_contains", "010_0010"]]) == ["va"]
    assert codes(sg, "Version", [["entity", "name_not_contains", "sh010"]]) == ["vasset", "vb", "vnone"]


@pytest.mark.parametrize("operator", ["name_is", "name_contains", "name_not_contains"])
def test_entity_name_operator_refuses_none(versions, operator):
    sg = versions[0]
    with pytest.raises(ShotgunError):
        sg.find("Version", [["entity", operator, None]])


@pytest.mark.parametrize("operator", ["name_starts_with", "name_ends_with"])
def test_entity_refuses_operators_the_site_lacks(versions, operator):
    sg = versions[0]
    with pytest.raises(ShotgunError, match=operator):
        sg.find("Version", [["entity", operator, "sh"]])


def test_entity_name_filter_leaves_stored_rows_alone(versions):
    sg, _, _, _, rows = versions
    sg.find("Version", [["entity", "name_is", "sh010_0010"]])
    assert "name" not in sg._db["Version"][rows["a"]["id"]]["entity"]


# field_types/multi_entity


@pytest.fixture
def playlists(sg):
    """Versions AB, A_only, B_only and empty, linked through Version.playlists."""
    a = sg.create("Playlist", {"code": "zz_target_a"})
    b = sg.create("Playlist", {"code": "zz_target_b"})
    sg.create("Version", {"code": "AB", "playlists": [a, b]})
    sg.create("Version", {"code": "A_only", "playlists": [a]})
    sg.create("Version", {"code": "B_only", "playlists": [b]})
    sg.create("Version", {"code": "empty", "playlists": []})
    return sg, a, b


def test_multi_entity_is(playlists):
    sg, a, _ = playlists
    assert codes(sg, "Version", [["playlists", "is", a]]) == ["AB", "A_only"]
    assert codes(sg, "Version", [["playlists", "is", None]]) == ["empty"]


def test_multi_entity_is_compares_type_and_id(playlists):
    sg, a, _ = playlists
    other = {"type": "Shot", "id": a["id"]}
    assert codes(sg, "Version", [["playlists", "is", other]]) == []
    assert codes(sg, "Version", [["playlists", "is_not", other]]) == ["AB", "A_only", "B_only", "empty"]


def test_multi_entity_is_not(playlists):
    sg, a, _ = playlists
    assert codes(sg, "Version", [["playlists", "is_not", a]]) == ["B_only", "empty"]
    assert codes(sg, "Version", [["playlists", "is_not", None]]) == ["AB", "A_only", "B_only"]


def test_multi_entity_is_refuses_two_entities(playlists):
    sg, a, b = playlists
    with pytest.raises(ShotgunError, match="'is' 'relation' expects a 1-element array"):
        sg.find("Version", [["playlists", "is", [a, b]]])


def test_multi_entity_in(playlists):
    sg, a, b = playlists
    assert codes(sg, "Version", [["playlists", "in", [a]]]) == ["AB", "A_only"]
    assert codes(sg, "Version", [["playlists", "in", [a, b]]]) == ["AB", "A_only", "B_only"]


def test_multi_entity_in_empty_list_raises_index_error(playlists):
    # api3 011: the api3 client raises before sending.
    sg = playlists[0]
    with pytest.raises(IndexError):
        sg.find("Version", [["playlists", "in", []]])


def test_multi_entity_not_in(playlists):
    sg, a, b = playlists
    assert codes(sg, "Version", [["playlists", "not_in", [a]]]) == ["B_only", "empty"]
    assert codes(sg, "Version", [["playlists", "not_in", [a, b]]]) == ["empty"]


def test_multi_entity_type_operators(playlists):
    sg = playlists[0]
    assert codes(sg, "Version", [["playlists", "type_is", "Playlist"]]) == ["AB", "A_only", "B_only"]
    assert codes(sg, "Version", [["playlists", "type_is_not", "Playlist"]]) == ["empty"]


def test_multi_entity_name_operators(playlists):
    sg = playlists[0]
    assert codes(sg, "Version", [["playlists", "name_is", "zz_target_a"]]) == ["AB", "A_only"]
    assert codes(sg, "Version", [["playlists", "name_contains", "_target_a"]]) == ["AB", "A_only"]
    assert codes(sg, "Version", [["playlists", "name_contains", "ZZZNOPE"]]) == []


def test_multi_entity_refuses_bare_contains(playlists):
    # finding 016
    sg = playlists[0]
    with pytest.raises(ShotgunError, match="contains"):
        sg.find("Version", [["playlists", "contains", "zz"]])


# finding 060: name operators compare the name `find` returns in the link.


def test_entity_name_is_compares_the_display_name(sg):
    task = sg.create("Task", {"content": "comp"})
    sg.create("Version", {"code": "v1", "sg_task": task})
    named = sg.find("Version", [["sg_task", "name_is", "comp"]], ["sg_task"])
    assert [row["sg_task"]["name"] for row in named] == ["comp"]


def test_multi_entity_name_is_compares_the_display_name(sg):
    task = sg.create("Task", {"content": "comp"})
    sg.create("Version", {"code": "v1", "tasks": [task]})
    assert codes(sg, "Version", [["tasks", "name_contains", "com"]]) == ["v1"]


# field_types/entity, field_types/multi_entity: the site's `Valid relations` list.

_LINK_RELATIONS = (
    '\\["is",\n "is_not",\n "name_contains",\n "name_not_contains",\n "name_is",\n "type_is",\n'
    ' "type_is_not",\n "in",\n "not_in"\\]'
)


def test_entity_unknown_operator_names_the_valid_relations(sg):
    # api3 001
    pattern = "Version.entity's 'entity' data type doesn't support 'starts_with' 'relation':\n.*\nValid relations:\n"
    with pytest.raises(Fault, match=pattern + _LINK_RELATIONS):
        sg.find("Version", [["entity", "starts_with", "sh"]])


def test_multi_entity_bare_contains_names_the_type_and_field(sg):
    pattern = "Version.playlists's 'multi_entity' data type doesn't support 'contains' 'relation':\n.*\nValid relations:\n"
    with pytest.raises(Fault, match=pattern + _LINK_RELATIONS):
        sg.find("Version", [["playlists", "contains", "zz"]])


# api3 013: refusals are raised before the scan.


@pytest.mark.parametrize("sg_filter", [
    ["entity", "starts_with", "sh"],
    ["sg_uploaded_movie", "is", None],
    ["entity.Shot.no_such_field", "is", "x"],
    ["playlists", "is", [{"type": "Playlist", "id": 1}, {"type": "Playlist", "id": 2}]],
    ["entity", "name_is", None],
])
def test_refusals_raise_on_an_empty_table(sg, sg_filter):
    with pytest.raises(Fault):
        sg.find("Version", [sg_filter])


def test_refusals_raise_inside_a_nested_group_on_an_empty_table(sg):
    nested = {"filter_operator": "any", "filters": [["code", "is", "x"], ["entity", "name_is", None]]}
    with pytest.raises(Fault):
        sg.find("Version", [nested])


def test_entity_in_empty_list_raises_index_error(versions):
    # api3 015: the api3 client raises before sending.
    with pytest.raises(IndexError):
        versions[0].find("Version", [["entity", "in", []]])
