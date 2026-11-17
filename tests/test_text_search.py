"""text_search() on the mock. Expected values and messages are api3 answers 043 to 045."""

import pytest
from shotgun_api3 import Fault


@pytest.fixture
def site(sg):
    project = sg.create("Project", {"name": "Demo"})
    other = sg.create("Project", {"name": "Other"})
    shots = {}
    for code in ("sq010_sh010", "sq010_sh020", "sh010", "demo_01_roto"):
        shots[code] = sg.create("Shot", {"code": code, "project": project, "description": "flickers"})
    asset = sg.create("Asset", {"code": "env_kitchen", "project": project})
    sg.create("Shot", {"code": "sq010_elsewhere", "project": other})
    sg.create("Version", {"code": "sq010_sh010_v001", "entity": shots["sq010_sh010"], "project": project,
                          "sg_status_list": "rev"})
    sg.create("Version", {"code": "v002", "entity": shots["sq010_sh010"], "project": project})
    sg.create("Task", {"content": "Model", "entity": asset, "project": project})
    return sg, project


def names(answer):
    return [m["name"] for m in answer["matches"]]


def test_the_answer_shape(site):  # api3 043
    sg, project = site
    answer = sg.text_search("sh020", {"Shot": []}, project_ids=[project["id"]])
    assert answer == {"matches": [{"id": answer["matches"][0]["id"], "type": "Shot", "name": "sq010_sh020",
                                   "project_id": project["id"], "links": ["", ""], "status": "wtg",
                                   "image": None}], "terms": ["sh020"]}
    version = sg.text_search("v001", {"Version": []})["matches"][0]
    assert version["links"] == ["Shot", "sq010_sh010"] and version["status"] == "rev"


def test_matching_rules(site):  # api3 044
    sg, project = site
    pid = [project["id"]]

    def search(text):
        return names(sg.text_search(text, {"Shot": [], "Asset": []}, project_ids=pid))

    assert search("SQ010") == search("sq010") == ["sq010_sh010", "sq010_sh020"]
    assert sg.text_search("SQ010", {"Shot": []}, project_ids=pid)["terms"] == ["sq010"]
    assert search("h01") == ["sh010", "sq010_sh010"]
    assert search("0_s") == ["sq010_sh010", "sq010_sh020"]
    assert search("sh020 sq010") == ["sq010_sh020"]
    assert search("  sq010  ") == ["sq010_sh010", "sq010_sh020"]
    assert search("sq010 kitchen") == []
    assert search("sq010 x") == []
    assert search("itche") == ["env_kitchen"]
    assert search("demo-01") == [] and search("demo 01") == ["demo_01_roto"]
    assert search("sq0*") == []
    assert search("flickers") == []


def test_a_row_matches_on_its_linked_name_and_comes_after_own_matches(site):  # api3 043, 044
    sg, project = site
    answer = sg.text_search("sq010_sh010", {"Shot": [], "Version": []}, project_ids=[project["id"]])
    assert names(answer) == ["sq010_sh010", "sq010_sh010_v001", "v002"]
    assert names(sg.text_search("kitchen", {"Task": []})) == ["Model"]


def test_filters_project_ids_and_limit(site):  # api3 043, 045
    sg, project = site
    on_project = [["project", "is", project]]
    assert names(sg.text_search("sq010", {"Shot": on_project + [["code", "ends_with", "20"]]})) == ["sq010_sh020"]
    assert names(sg.text_search("sq010", {"Shot": [["id", "is", 0]]})) == []
    assert "sq010_elsewhere" in names(sg.text_search("sq010", {"Shot": []}))
    assert "sq010_elsewhere" not in names(sg.text_search("sq010", {"Shot": []}, project_ids=[project["id"]]))
    assert names(sg.text_search("sq010", {"Shot": []}, project_ids=[0])) == []
    assert len(sg.text_search("sq010", {"Shot": []}, limit=1)["matches"]) == 1
    assert sg.text_search("sq010", {"Shot": []}, limit=0)["matches"] == []
    assert sg.text_search("sq010", {"Shot": []}, limit="ten")["matches"] == []
    # A field the type lacks is ignored (api3 045).
    assert len(sg.text_search("sq010", {"Shot": [["sg_not_a_field", "is", "x"]]})["matches"]) == 3
    # No entity type searches every type.
    types = set(m["type"] for m in sg.text_search("sq010", {})["matches"])
    assert types == {"Shot", "Version"}


def test_the_default_limit_is_25(sg):  # api3 043
    for i in range(30):
        sg.create("Shot", {"code": "zz_%02d" % i})
    assert len(sg.text_search("zz_", {"Shot": []})["matches"]) == 25
    assert len(sg.text_search("zz_", {"Shot": []}, limit=26)["matches"]) == 26


def test_text_faults(site):  # api3 045
    sg, project = site
    request = ('{"text" => "ab",\n "entity_types" =>\n  {"Shot" => {"logical_operator" => "and", "conditions" => []}},\n'
               ' "project_ids" => [%d],\n "max_results" => nil}' % project["id"])
    with pytest.raises(Fault) as e:
        sg.text_search("ab", {"Shot": []}, project_ids=[project["id"]])
    assert str(e.value) == "API query_display_name_cache() query text too short! must be 3 or more characters :\n" + request
    for text in ("", 123):
        with pytest.raises(Fault, match="query text too short"):
            sg.text_search(text, {"Shot": []})
    with pytest.raises(Fault) as e:
        sg.text_search(None, {"Shot": []})
    assert str(e.value).startswith("API query_display_name_cache() 'text' missing:\n{\"text\" => nil,")
    assert sg.text_search("   ", {"Shot": []}) == {"matches": [], "terms": []}
    assert sg.text_search("abc d", {"Shot": []})["terms"] == ["abc", "d"]


def test_argument_faults(site):  # api3 045
    sg, project = site
    with pytest.raises(Fault) as e:
        sg.text_search("sq010", {"Shot": [], "NotAType": []})
    assert str(e.value) == "API query_display_name_cache() invalid entity type. Found: NotAType"
    with pytest.raises(ValueError, match="entity_types parameter must be a dictionary"):
        sg.text_search("sq010", ["Shot"])
    with pytest.raises(ValueError, match=r"value of entity_types\['Shot'\] must be a list or tuple\."):
        sg.text_search("sq010", {"Shot": None})
    with pytest.raises(Fault) as e:
        sg.text_search("sq010", {"Shot": [["code", "nope", "x"]]})
    assert str(e.value) == "Uncaught exception! No condition node type matches <nope> for column Shot a.code"
    with pytest.raises(IndexError):
        sg.text_search("sq010", {"Shot": [["code"]]})
    with pytest.raises(Fault) as e:
        sg.text_search("sq010", {"Shot": []}, project_ids=project["id"])
    assert str(e.value) == "Uncaught exception! undefined method 'collect' for an instance of Integer"
    with pytest.raises(Fault, match="LIMIT must not be negative"):
        sg.text_search("sq010", {"Shot": []}, limit=-1)
