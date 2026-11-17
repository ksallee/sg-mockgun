"""Filters as api3 answers 001 to 015 record them, on rows each test makes in the sandbox."""

import pytest
from shotgun_api3 import Fault


def fault(fn, *args, **kwargs):
    with pytest.raises(Fault) as e:
        fn(*args, **kwargs)
    return str(e.value)


@pytest.fixture
def links(made, sandbox, run_token):
    """A Shot in a Sequence, an Asset, three Versions linking the Shot, the Asset and nothing, and three Notes alike."""
    p = "zzconf_%s_" % run_token
    seq = made.create("Sequence", {"code": p + "seq", "project": sandbox})
    shot = made.create("Shot", {"code": p + "shot", "sg_sequence": seq, "project": sandbox})
    asset = made.create("Asset", {"code": p + "asset", "project": sandbox})
    shot, asset = {"type": "Shot", "id": shot["id"]}, {"type": "Asset", "id": asset["id"]}
    versions = {}
    for name, link in (("v_shot", shot), ("v_asset", asset), ("v_none", None)):
        versions[made.create("Version", {"code": p + name, "entity": link, "project": sandbox})["id"]] = name
    notes = {}
    for name, link in (("n_shot", [shot]), ("n_asset", [asset]), ("n_none", [])):
        row = made.create("Note", {"subject": p + name, "content": "probe", "note_links": link, "project": sandbox})
        notes[row["id"]] = name
    return {"shot": shot, "asset": asset, "shot_code": p + "shot", "versions": versions, "notes": notes}


def names(site, links, entity_type, sg_filter):
    rows = links["versions"] if entity_type == "Version" else links["notes"]
    scope = [["id", "in", list(rows)]]
    return sorted(rows[r["id"]] for r in site.find(entity_type, scope + [sg_filter], ["id"]))


# api3 001, 002


@pytest.mark.finding("017", api3="001")
@pytest.mark.cell("find", "unknown relation", "text")
def test_unknown_relation_on_text_lists_the_valid_relations(site):
    assert fault(site.find, "Shot", [["code", "definitely_not_an_operator", "x"]], ["id"], limit=1) == (
        "API read() Shot.code's 'text' data type doesn't support 'definitely_not_an_operator' 'relation':\n"
        '{"path" => "code",\n "relation" => "definitely_not_an_operator",\n "values" => ["x"]}\n'
        'Valid relations:\n["contains",\n "not_contains",\n "is",\n "is_not",\n "starts_with",\n "ends_with",\n'
        ' "in",\n "not_in"]')


@pytest.mark.finding("017", api3="001")
@pytest.mark.cell("find", "unknown relation", "url")
def test_url_cannot_be_used_in_a_filter(site):
    assert fault(site.find, "Version", [["sg_uploaded_movie", "definitely_not_an_operator", "x"]], ["id"], limit=1) == (
        "API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter:\n"
        '{"path" => "sg_uploaded_movie",\n "relation" => "definitely_not_an_operator",\n "values" => ["x"]}')


@pytest.mark.finding("017", api3="002")
@pytest.mark.cell("find", "not_between", "number")
def test_not_between_is_refused(site):
    message = fault(site.find, "Version", [["frame_count", "not_between", [1, 2]]], ["id"], limit=1)
    assert message.startswith("API read() Version.frame_count's 'number' data type doesn't support 'not_between'")


# api3 003


@pytest.mark.finding("field_types/number", api3="003")
@pytest.mark.cell("find", "between", "number")
def test_between_needs_two_values(site):
    assert fault(site.find, "Version", [["frame_count", "between", [1]]], ["id"], limit=1) == (
        "API read() 'between' 'relation' expects a 2-element array:\n[1]")
    assert fault(site.find, "Version", [["frame_count", "between", [1, 50, 100]]], ["id"], limit=1) == (
        "API read() 'between' 'relation' expects a 2-element array:\n[1, 50, 100]")


# api3 004


@pytest.mark.finding("field_types/text", api3="004")
@pytest.mark.cell("find", "is", "status_list")
def test_text_and_status_is_ignore_case(site, made, sandbox, run_token):
    code = "zzconf_%s_case" % run_token
    made.create("Version", {"code": code, "sg_status_list": "rev", "project": sandbox})
    scope = [["project", "is", sandbox], ["code", "starts_with", code]]
    assert len(site.find("Version", scope + [["code", "is", code.upper()]], ["id"])) == 1
    assert len(site.find("Version", scope + [["code", "in", [code.swapcase()]]], ["id"])) == 1
    assert len(site.find("Version", scope + [["sg_status_list", "is", "REV"]], ["id"])) == 1


# api3 005


@pytest.mark.finding("field_types/checkbox", api3="005")
@pytest.mark.cell("find", "is", "checkbox")
def test_checkbox_is_none_is_refused(site, made, sandbox, run_token):
    code = "zzconf_%s_flag" % run_token
    made.create("Version", {"code": code, "project": sandbox})
    assert fault(site.find, "Version", [["flagged", "is", None]], ["id"], limit=1) == (
        "API read() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil")
    scope = [["project", "is", sandbox], ["code", "is", code]]
    assert len(site.find("Version", scope + [["flagged", "is", False]], ["id"])) == 1
    assert site.find("Version", scope + [["flagged", "is", True]], ["id"]) == []


# api3 010


@pytest.mark.finding("field_types/entity", api3="010")
@pytest.mark.cell("find", "type_is", "entity")
def test_entity_type_is_none_means_unset(site, links):
    assert names(site, links, "Version", ["entity", "type_is", None]) == ["v_none"]
    assert names(site, links, "Version", ["entity", "type_is_not", None]) == ["v_asset", "v_shot"]
    assert names(site, links, "Version", ["entity", "type_is_not", "Shot"]) == ["v_asset", "v_none"]


@pytest.mark.finding("field_types/entity", api3="010")
@pytest.mark.cell("find", "is_not", "entity")
def test_entity_negations_match_the_unset_row(site, links):
    assert names(site, links, "Version", ["entity", "is_not", links["shot"]]) == ["v_asset", "v_none"]
    assert names(site, links, "Version", ["entity", "not_in", [links["shot"]]]) == ["v_asset", "v_none"]
    assert names(site, links, "Version", ["entity", "name_not_contains", links["shot_code"]]) == ["v_asset", "v_none"]


@pytest.mark.finding("field_types/entity", api3="010")
@pytest.mark.cell("find", "name_is", "entity")
def test_entity_name_is_none_is_refused(site):
    assert fault(site.find, "Version", [["entity", "name_is", None]], ["id"], limit=1) == (
        "API read() Version.entity expected [String] data type(s) but got NilClass:\nnil")


# api3 011


@pytest.mark.finding("field_types/multi_entity", api3="011")
@pytest.mark.cell("find", "in", "multi_entity")
def test_multi_entity_in_and_not_in(site, links):
    both = [links["shot"], links["asset"]]
    assert names(site, links, "Note", ["note_links", "in", both]) == ["n_asset", "n_shot"]
    assert names(site, links, "Note", ["note_links", "not_in", both]) == ["n_none"]
    assert names(site, links, "Note", ["note_links", "is", None]) == ["n_none"]


@pytest.mark.finding("field_types/multi_entity", api3="011")
@pytest.mark.cell("find", "name_not_contains", "multi_entity")
def test_multi_entity_name_not_contains_matches_the_empty_row(site, links):
    assert names(site, links, "Note", ["note_links", "name_not_contains", "shot"]) == ["n_asset", "n_none"]
    assert names(site, links, "Note", ["note_links", "type_is", None]) == ["n_none"]


@pytest.mark.finding("field_types/multi_entity", api3="011")
@pytest.mark.cell("find", "is", "multi_entity")
def test_multi_entity_is_takes_one_entity(site, links):
    message = fault(site.find, "Note", [["note_links", "is", [links["shot"], links["asset"]]]], ["id"])
    assert message.startswith("API read() 'is' 'relation' expects a 1-element array:\n")


@pytest.mark.finding("field_types/multi_entity", api3="015")
@pytest.mark.cell("find", "in", "entity")
def test_entity_in_empty_list_fails_in_the_client(site):
    with pytest.raises(IndexError):
        site.find("Version", [["entity", "in", []]], ["id"])


# api3 012


@pytest.mark.finding("016", api3="012")
@pytest.mark.cell("find", "is", "dotted")
def test_dotted_path_reads_null_through_another_type(site, links):
    assert names(site, links, "Version", ["entity.Shot.code", "is", None]) == ["v_asset", "v_none"]
    assert names(site, links, "Version", ["entity.Shot.code", "is_not", "x"]) == ["v_asset", "v_none", "v_shot"]
    assert names(site, links, "Note", ["note_links.Shot.code", "is", None]) == ["n_asset", "n_none"]
    assert names(site, links, "Note", ["note_links.Shot.sg_sequence.Sequence.code", "is_not", None]) == ["n_shot"]


# api3 013


@pytest.mark.finding("028", api3="013")
@pytest.mark.cell("find", "is", "unknown field")
def test_unknown_field_is_refused_beside_an_empty_match(site):
    assert site.find("Version", [["id", "is", 0]], ["id"]) == []
    assert fault(site.find, "Version", [["id", "is", 0], ["zz_nope", "is", "x"]], ["id"]) == (
        'API read() Version.zz_nope doesn\'t exist:\n{"path" => "zz_nope", "relation" => "is", "values" => ["x"]}')


# api3 014


@pytest.mark.finding("field_types/date_time", api3="014")
@pytest.mark.cell("find", "in_last", "date_time")
def test_relative_date_operators(site, made, sandbox, run_token):
    code = "zzconf_%s_recent" % run_token
    made.create("Version", {"code": code, "project": sandbox})
    scope = [["project", "is", sandbox], ["code", "is", code]]

    def count(sg_filter):
        return len(site.find("Version", scope + [sg_filter], ["id"]))

    assert count(["created_at", "in_last", 1, "DAY"]) == 1
    assert count(["created_at", "in_last", [1, "HOUR"]]) == 1
    assert count(["created_at", "not_in_last", [1, "DAY"]]) == 0
    assert count(["created_at", "in_next", [1, "DAY"]]) == 0
    assert count(["created_at", "in_last", [0, "DAY"]]) == 0
    assert count(["created_at", "in_calendar_year", 0]) == 1


@pytest.mark.finding("field_types/date_time", api3="014")
@pytest.mark.cell("find", "in_last", "date_time")
def test_relative_date_refusals(site):
    assert fault(site.find, "Version", [["created_at", "in_last", [1, "MINUTE"]]], ["id"], limit=1) == (
        "API read() 'in_last' 'relation' doesn't support the 'MINUTE' time unit:\n[1, \"MINUTE\"]\n"
        'Valid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]')
    assert fault(site.find, "Version", [["created_at", "in_last", 1]], ["id"], limit=1) == (
        "API read() 'in_last' 'relation' expects a 2-element array:\n[1]")
    assert fault(site.find, "Version", [["created_at", "in_calendar_day", [0, "DAY"]]], ["id"], limit=1) == (
        "API read() 'in_calendar_day' 'relation' expects a 1-element array:\n[0, \"DAY\"]")
