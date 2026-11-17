"""summarize and text_search as api3 answers 040 to 045 record them, on rows each test makes in the sandbox."""

import time

import pytest
from shotgun_api3 import Fault


@pytest.fixture
def versions(made, sandbox, run_token):
    """Four Versions: three rev and one apr, two with a frame count, two on a Shot, and the filter that scopes to them."""
    p = "zzconf_%s_sum_" % run_token
    shot = made.create("Shot", {"code": p + "shot", "project": sandbox})
    for n, (status, frames, entity) in enumerate((("rev", 10, shot), ("rev", 30, shot), ("rev", None, None),
                                                   ("apr", None, None))):
        made.create("Version", {"code": "%s%d" % (p, n), "sg_status_list": status, "frame_count": frames,
                                "entity": entity, "project": sandbox})
    return [["project", "is", sandbox], ["code", "starts_with", p]], shot


def fault(fn, *args, **kwargs):
    with pytest.raises(Fault) as e:
        fn(*args, **kwargs)
    return str(e.value)


# api3 040


@pytest.mark.finding("020", api3="040")
@pytest.mark.cell("summarize", "-", "number")
def test_summaries_without_grouping(site, versions):
    scope, _ = versions
    answer = site.summarize("Version", scope, [{"field": "id", "type": "count"},
                                               {"field": "frame_count", "type": "sum"},
                                               {"field": "code", "type": "count"}])
    assert answer == {"summaries": {"id": 4, "frame_count": 40, "code": 4}, "groups": []}


@pytest.mark.finding("079", api3="040")
@pytest.mark.cell("summarize", "-", "status_list")
def test_status_percentage_is_the_share_in_that_status(site, versions):
    scope, _ = versions
    answer = site.summarize("Version", scope, [{"field": "sg_status_list", "type": "status_percentage", "value": "rev"}])
    assert answer["summaries"] == {"sg_status_list": 75}
    assert fault(site.summarize, "Version", scope, [{"field": "sg_status_list", "type": "status_percentage"}]) == (
        "API summarize() invalid/missing key 'value'. Percentage-based summaries require a valid 'value' key in the "
        "'summaries' hash:\n{\"field\" => \"sg_status_list\", \"type\" => \"status_percentage\"}")


@pytest.mark.finding("020", api3="040")
@pytest.mark.cell("summarize", "-", "number")
def test_empty_match_and_duplicate_field(site, sandbox):
    nothing = [["project", "is", sandbox], ["id", "is", 0]]
    answer = site.summarize("Version", nothing, [{"field": "id", "type": "count"},
                                                 {"field": "frame_count", "type": "average"},
                                                 {"field": "created_at", "type": "latest"}])
    assert answer == {"summaries": {"id": 0, "frame_count": 0.0, "created_at": None}, "groups": []}
    assert fault(site.summarize, "Version", nothing, [{"field": "id", "type": "count"},
                                                      {"field": "id", "type": "maximum"}]) == (
        "API summarize() duplicate summary request for field 'id':\n{\"field\" => \"id\", \"type\" => \"maximum\"}")


# api3 041


@pytest.mark.finding("079", api3="041")
@pytest.mark.cell("summarize", "grouping", "status_list")
def test_grouping_by_status(site, versions):
    scope, _ = versions
    answer = site.summarize("Version", scope, [{"field": "id", "type": "count"}],
                            grouping=[{"field": "sg_status_list", "type": "exact", "direction": "asc"}])
    assert answer["summaries"] == {"id": 4}
    assert answer["groups"] == [
        {"group_name": "rev", "group_value": "rev", "summaries": {"id": 3}},
        {"group_name": "apr", "group_value": "apr", "summaries": {"id": 1}},
    ]
    assert site.summarize("Version", scope, [{"field": "id", "type": "count"}], grouping=[])["groups"] is None


@pytest.mark.finding("079", api3="041")
@pytest.mark.cell("summarize", "grouping", "entity")
def test_grouping_nests_and_empty_group_is_last(site, versions):
    scope, shot = versions
    answer = site.summarize("Version", scope, [{"field": "id", "type": "count"}],
                            grouping=[{"field": "entity", "type": "exact", "direction": "asc"},
                                      {"field": "sg_status_list", "type": "exact", "direction": "asc"}])
    first, empty = answer["groups"]
    assert (first["group_name"], first["group_value"], first["summaries"]) == (
        shot["code"], {"type": "Shot", "id": shot["id"], "name": shot["code"], "valid": "valid"}, {"id": 2})
    assert (empty["group_name"], empty["group_value"], empty["summaries"]) == ("", None, {"id": 2})
    assert [(g["group_name"], g["summaries"]["id"]) for g in empty["groups"]] == [("rev", 1), ("apr", 1)]
    assert "groups" not in empty["groups"][0]


# api3 042


@pytest.mark.finding("020", api3="042")
@pytest.mark.cell("summarize", "-", "text")
def test_summary_type_must_fit_the_data_type(site, sandbox):
    nothing = [["project", "is", sandbox], ["id", "is", 0]]
    assert fault(site.summarize, "Shot", nothing, [{"field": "code", "type": "sum"}]) == (
        "API summarize() summary type 'sum' not valid for field Shot.code with data type 'text'\n"
        "Valid summary types:\n[:record_count, :count]")
    assert fault(site.summarize, "Shot", nothing, [{"field": "sg_not_a_field", "type": "count"}]) == (
        "API summarize() Shot.sg_not_a_field doesn't exist:\n{\"field\" => \"sg_not_a_field\", \"type\" => \"count\"}")
    assert fault(site.summarize, "Shot", nothing, [{"field": "id", "type": "count"}],
                 grouping=[{"field": "sg_status_list", "type": "nope", "direction": "asc"}]) == (
        "API summarize() grouping option 'nope' not valid for field Shot.sg_status_list with data type 'status_list'\n"
        "Valid grouping types:\n[:exact]")


# api3 043, 044


def search(site, text, entity_types, project_ids, limit=None, want=0):
    """text_search, polled for up to 30 s on a live site until ``want`` rows match: the name index can lag a create."""
    deadline = time.time() + 30
    while True:
        answer = site.text_search(text, entity_types, project_ids=project_ids, limit=limit)
        if len(answer["matches"]) >= want or time.time() > deadline:
            return answer
        time.sleep(2)


@pytest.fixture
def named(made, sandbox, run_token):
    """Two Shots, an Asset and a Version on the first Shot, with names that share a token."""
    p = "zzconf%sq" % run_token
    sh1 = made.create("Shot", {"code": p + "_sh010", "project": sandbox})
    made.create("Shot", {"code": p + "_sh020", "project": sandbox})
    made.create("Asset", {"code": p + "_kitchen", "project": sandbox})
    made.create("Version", {"code": "take_" + p[-6:] + "_one", "entity": sh1, "project": sandbox})
    return p


@pytest.mark.finding("046", api3="043")
@pytest.mark.cell("text_search", "-", "-")
def test_text_search_rows_and_terms(site, named, sandbox):
    answer = search(site, named.upper() + " sh010", {"Shot": [], "Asset": []}, [sandbox["id"]], want=1)
    assert answer["terms"] == [named.lower(), "sh010"]
    assert [m["name"] for m in answer["matches"]] == [named + "_sh010"]
    row = answer["matches"][0]
    assert set(row) == {"id", "type", "name", "project_id", "links", "status", "image"}
    assert (row["type"], row["project_id"], row["links"], row["status"]) == ("Shot", sandbox["id"], ["", ""], "wtg")


@pytest.mark.finding("053", api3="044")
@pytest.mark.cell("text_search", "-", "-")
def test_text_search_matches_substrings_and_links(site, named, sandbox):
    answer = search(site, named[-6:], {"Shot": [], "Asset": []}, [sandbox["id"]], want=3)
    assert sorted(m["name"] for m in answer["matches"]) == sorted(
        [named + "_kitchen", named + "_sh010", named + "_sh020"])
    filtered = search(site, named, {"Shot": [["code", "ends_with", "sh020"]], "Asset": []}, [sandbox["id"]], want=2)
    assert sorted(m["name"] for m in filtered["matches"]) == sorted([named + "_kitchen", named + "_sh020"])
    linked = search(site, named + "_sh010", {"Version": []}, [sandbox["id"]], want=1)
    assert [(m["type"], m["links"]) for m in linked["matches"]] == [("Version", ["Shot", named + "_sh010"])]


# api3 045


@pytest.mark.finding("053", api3="045")
@pytest.mark.cell("text_search", "-", "-")
def test_text_search_refusals(site, sandbox):
    with pytest.raises(Fault) as e:
        site.text_search("ab", {"Shot": []}, project_ids=[sandbox["id"]])
    assert str(e.value).startswith("API query_display_name_cache() query text too short! must be 3 or more characters :\n")
    with pytest.raises(Fault) as e:
        site.text_search("abc", {"NotAType": []}, project_ids=[sandbox["id"]])
    assert str(e.value) == "API query_display_name_cache() invalid entity type. Found: NotAType"
    assert site.text_search("ab cd", {"Shot": []}, project_ids=[sandbox["id"]]) == {"matches": [], "terms": ["ab", "cd"]}
