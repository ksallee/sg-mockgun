"""Filters on dotted paths through entity and multi_entity fields."""

import pytest
from shotgun_api3 import Fault, ShotgunError

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="probe-script", api_key="y")


@pytest.fixture
def notes(sg):
    seq = sg.create("Sequence", {"code": "sq010"})
    sh010 = sg.create("Shot", {"code": "sh010", "sg_sequence": seq})
    sh020 = sg.create("Shot", {"code": "sh020"})
    char = sg.create("Asset", {"code": "charA", "sg_asset_type": "Character"})
    n_shot = sg.create("Note", {"subject": "on sh010", "note_links": [sh010]})
    n_both = sg.create("Note", {"subject": "on sh020 and charA", "note_links": [sh020, char]})
    n_asset = sg.create("Note", {"subject": "on charA", "note_links": [char]})
    n_none = sg.create("Note", {"subject": "no link"})
    return {"shot": n_shot, "both": n_both, "asset": n_asset, "none": n_none}


def ids(rows):
    return sorted(r["id"] for r in rows)


def test_python_api_298_entity_path_to_another_type_reads_null(sg):
    # python-api#298; field_types/entity: a Version linked to an Asset reads entity.Shot.code as null.
    shot = sg.create("Shot", {"code": "bunny_080_0010"})
    asset = sg.create("Asset", {"code": "mp_415"})
    v_shot = sg.create("Version", {"code": "v_shot", "entity": shot})
    v_asset = sg.create("Version", {"code": "v_asset", "entity": asset})
    rows = sg.find("Version", [["entity.Shot.code", "is", "bunny_080_0010"]], ["code", "description"])
    assert ids(rows) == [v_shot["id"]]
    read = sg.find_one("Version", [["id", "is", v_asset["id"]]], ["entity.Shot.code"])
    assert read["entity.Shot.code"] is None


def test_positive_dotted_filters_through_multi_entity_match(sg, notes):
    # finding 016: one hop and two hops resolve, negative controls match nothing.
    assert ids(sg.find("Note", [["note_links.Shot.code", "is", "sh010"]])) == [notes["shot"]["id"]]
    assert ids(sg.find("Note", [["note_links.Asset.code", "contains", "char"]])) == ids([notes["both"], notes["asset"]])
    assert ids(sg.find("Note", [["note_links.Shot.sg_sequence.Sequence.code", "is", "sq010"]])) == [notes["shot"]["id"]]
    assert sg.find("Note", [["note_links.Shot.code", "is", "ZZZNOPE"]]) == []
    assert sg.find("Note", [["note_links.Asset.sg_asset_type", "is", "ZZZNOPE"]]) == []


def test_is_not_null_two_hops_through_multi_entity_matches_linked_rows(sg, notes):
    # finding 016: note_links.Shot.sg_sequence.Sequence.code is_not null matched linked Notes.
    # api3 012: rows with no Shot link read null.
    rows = sg.find("Note", [["note_links.Shot.sg_sequence.Sequence.code", "is_not", None]])
    assert ids(rows) == [notes["shot"]["id"]]


@pytest.mark.parametrize("path", [
    "note_links.Booking.code",
    "note_links.Group.name",
    "note_links.ZzNotAType.code",
    "note_links.Shot.zz_nope.Sequence.code",
])
def test_dotted_path_the_named_type_lacks_is_refused(sg, notes, path):
    # finding 016: the path is validated against the named type, not the link's valid_types.
    # api3 013: the wording.
    with pytest.raises(Fault) as err:
        sg.find("Note", [[path, "contains", "bunn"]])
    assert str(err.value).startswith("API read() Note.%s doesn't exist:\n{" % path)


def test_cached_display_name_through_multi_entity_is_accepted(sg, notes):
    # finding 016: every type answers to cached_display_name.
    sg.find("Note", [["note_links.Booking.cached_display_name", "contains", "bunn"]])
