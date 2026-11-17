"""summarize() on the mock. Expected values and messages are api3 answers 040 to 042."""

import datetime

import pytest
from shotgun_api3 import Fault, ShotgunError

COUNT = [{"field": "id", "type": "count"}]


def g(field, kind="exact", direction="asc"):
    return {"field": field, "type": kind, "direction": direction}


@pytest.fixture
def site(sg):
    project = sg.create("Project", {"name": "Demo"})
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    asset = sg.create("Asset", {"code": "char_hero", "project": project})
    tasks = [
        ("Anim", shot, "wtg", 1800, "2026-03-04", True),
        ("Comp", shot, "wtg", 2400, "2026-03-10", False),
        ("Light", shot, "ip", 1800, None, False),
        ("Model", asset, "fin", None, "2026-08-25", False),
    ]
    for content, entity, status, minutes, due, milestone in tasks:
        sg.create("Task", {"content": content, "entity": entity, "project": project, "sg_status_list": status,
                           "est_in_mins": minutes, "due_date": due, "milestone": milestone})
    return sg, [["project", "is", project]]


def summary(site, field, kind, **extra):
    sg, on_project = site
    item = dict({"field": field, "type": kind}, **extra)
    return sg.summarize("Task", on_project, [item])


def test_counts_and_numbers(site):  # api3 040
    assert summary(site, "id", "record_count") == {"summaries": {"id": 4}, "groups": []}
    assert summary(site, "due_date", "count")["summaries"] == {"due_date": 3}
    assert summary(site, "est_in_mins", "sum")["summaries"] == {"est_in_mins": 6000}
    assert summary(site, "est_in_mins", "maximum")["summaries"] == {"est_in_mins": 2400}
    assert summary(site, "est_in_mins", "minimum")["summaries"] == {"est_in_mins": 1800}
    assert summary(site, "est_in_mins", "average")["summaries"] == {"est_in_mins": 2000.0}
    assert summary(site, "milestone", "checked")["summaries"] == {"milestone": 1}
    assert summary(site, "milestone", "unchecked")["summaries"] == {"milestone": 3}


def test_dates_are_strings(site):  # api3 040
    assert summary(site, "due_date", "earliest")["summaries"] == {"due_date": "2026-03-04"}
    assert summary(site, "due_date", "latest")["summaries"] == {"due_date": "2026-08-25"}
    sg, on_project = site
    when = datetime.datetime(2026, 9, 25, 15, 45, 47, tzinfo=datetime.timezone.utc)
    sg.create("Version", {"code": "v001", "project": on_project[0][2], "client_approved_at": when})
    answer = sg.summarize("Version", on_project, [{"field": "client_approved_at", "type": "latest"}])
    assert answer["summaries"] == {"client_approved_at": "2026-09-25 15:45:47 UTC"}
    year = sg.summarize("Version", on_project, COUNT, grouping=[g("client_approved_at", "year")])["groups"]
    assert (year[0]["group_name"], year[0]["group_value"]) == ("2026", "2026-01-01")


def test_status_roll_up_and_share(site):  # api3 040, finding 079
    assert summary(site, "sg_status_list", "status_list")["summaries"] == {"sg_status_list": "ip"}
    # 2 of 4 wtg, 1 of 4 ip: 50 and 25 both ways; 1 of 3 shows the round and the floor.
    assert summary(site, "sg_status_list", "status_percentage", value="wtg")["summaries"] == {"sg_status_list": 50}
    sg, on_project = site
    three = on_project + [["entity", "type_is", "Shot"]]
    for kind, expected in (("status_percentage", 67), ("status_percentage_as_float", 66)):
        answer = sg.summarize("Task", three, [{"field": "sg_status_list", "type": kind, "value": "wtg"}])
        assert answer["summaries"] == {"sg_status_list": expected}
    one = sg.summarize("Task", on_project + [["content", "is", "Model"]], [{"field": "sg_status_list", "type": "status_list"}])
    assert one["summaries"] == {"sg_status_list": "fin"}


def test_no_row_matches(site):  # api3 040
    sg, on_project = site
    answer = sg.summarize("Task", on_project + [["id", "is", 0]], [
        {"field": "id", "type": "count"}, {"field": "due_date", "type": "latest"},
        {"field": "est_in_mins", "type": "average"}, {"field": "sg_status_list", "type": "status_list"}])
    assert answer == {"summaries": {"id": 0, "due_date": None, "est_in_mins": 0.0, "sg_status_list": "na"},
                      "groups": []}
    assert sg.summarize("Task", on_project, []) == {"summaries": {}, "groups": []}


def test_dotted_summary_field(site):  # api3 042
    sg, on_project = site
    answer = sg.summarize("Task", on_project, [{"field": "entity.Shot.code", "type": "count"}])
    assert answer == {"summaries": {"entity.Shot.code": 3}, "groups": []}


def test_summary_faults(site):  # api3 040, 042
    sg, on_project = site
    cases = [
        ([{"field": "id", "type": "count"}, {"field": "id", "type": "maximum"}],
         "API summarize() duplicate summary request for field 'id':\n{\"field\" => \"id\", \"type\" => \"maximum\"}"),
        ([{"field": "sg_status_list", "type": "status_percentage"}],
         "API summarize() invalid/missing key 'value'. Percentage-based summaries require a valid 'value' key in "
         "the 'summaries' hash:\n{\"field\" => \"sg_status_list\", \"type\" => \"status_percentage\"}"),
        ([{"field": "id", "type": "nope"}],
         "API summarize() summary type 'nope' not valid for field Task.id with data type 'number'\n"
         "Valid summary types:\n[:record_count, :count, :sum, :maximum, :minimum, :average]"),
        ([{"field": "milestone", "type": "percentage"}],
         "API summarize() summary type 'percentage' not valid for field Task.milestone with data type 'checkbox'\n"
         "Valid summary types:\n[:record_count, :checked, :unchecked]"),
        ([{"field": "id"}], "API summarize() invalid/missing key 'type' in 'summaries' hash:\n{\"field\" => \"id\"}"),
        ([{"type": "count"}], "API summarize() invalid/missing key 'field' in 'summaries' hash:\n{\"type\" => \"count\"}"),
        ([{"field": "sg_not_a_field", "type": "count"}],
         "API summarize() Task.sg_not_a_field doesn't exist:\n{\"field\" => \"sg_not_a_field\", \"type\" => \"count\"}"),
        ([{"field": "entity", "type": "count"}], "Uncaught exception! Summary type not supported: entity count"),
        ({"field": "id", "type": "count"}, "Uncaught exception! no implicit conversion of String into Integer"),
    ]
    for summaries, message in cases:
        with pytest.raises(Fault) as e:
            sg.summarize("Task", on_project, summaries)
        assert str(e.value) == message


def test_filter_and_entity_type_faults(site):  # api3 040, 042
    sg, on_project = site
    with pytest.raises(Fault) as e:
        sg.summarize("Task", [["sg_not_a_field", "is", 1]], COUNT)
    assert str(e.value) == ("API summarize() Task.sg_not_a_field doesn't exist:\n"
                            "{\"path\" => \"sg_not_a_field\", \"relation\" => \"is\", \"values\" => [1]}")
    with pytest.raises(Fault) as e:
        sg.summarize("Task", {"filter_operator": "all", "filters": []}, COUNT)
    assert str(e.value).startswith("API summarize() invalid/missing filters string 'logical_operator' (general condition):\n")
    with pytest.raises(Fault) as e:
        sg.summarize("NotAType", on_project, COUNT)
    assert str(e.value).startswith("API summarize() invalid/missing string entity 'type':\n{\"type\" => \"NotAType\",\n")
    assert "\nValid entity types:\n[\"ActionMenuItem\",\n" in str(e.value)


def test_wire_form_dict_filters(site):  # api3 040
    sg, _ = site
    answer = sg.summarize("Task", {"logical_operator": "and", "conditions": [
        {"path": "content", "relation": "is", "values": ["Anim"]}]}, COUNT)
    assert answer["summaries"] == {"id": 1}


def test_grouping_none_and_empty(site):  # api3 041
    sg, on_project = site
    assert sg.summarize("Task", on_project, COUNT)["groups"] == []
    assert sg.summarize("Task", on_project, COUNT, grouping=[])["groups"] is None
    with pytest.raises(ValueError, match=r"summarize\(\) 'grouping' parameter must be a list or None"):
        sg.summarize("Task", on_project, COUNT, grouping=g("sg_status_list"))


def test_status_groups_follow_the_status_order(site):  # api3 041
    sg, on_project = site
    groups = sg.summarize("Task", on_project, COUNT, grouping=[g("sg_status_list")])["groups"]
    assert groups == [
        {"group_name": "wtg", "group_value": "wtg", "summaries": {"id": 2}},
        {"group_name": "ip", "group_value": "ip", "summaries": {"id": 1}},
        {"group_name": "fin", "group_value": "fin", "summaries": {"id": 1}},
    ]
    desc = sg.summarize("Task", on_project, COUNT, grouping=[g("sg_status_list", direction="desc")])["groups"]
    assert [x["group_value"] for x in desc] == ["fin", "ip", "wtg"]


def test_two_levels_nest_and_the_leaf_has_no_groups(site):  # api3 041
    sg, on_project = site
    answer = sg.summarize("Task", on_project, COUNT, grouping=[g("entity"), g("sg_status_list")])
    first = answer["groups"][0]
    assert sorted(first) == ["group_name", "group_value", "groups", "summaries"]
    assert first["group_name"] == "char_hero"
    assert first["group_value"] == {"type": "Asset", "id": first["group_value"]["id"], "name": "char_hero",
                                    "valid": "valid"}
    shot = answer["groups"][1]
    assert shot["summaries"] == {"id": 3}
    assert sum(c["summaries"]["id"] for c in shot["groups"]) == 3
    assert all("groups" not in c for c in shot["groups"])


def test_bucket_names_and_values(site):  # api3 041
    sg, on_project = site

    def first(field, kind):
        return sg.summarize("Task", on_project, COUNT, grouping=[g(field, kind)])["groups"][0]

    def pair(group):
        return group["group_name"], group["group_value"]

    assert pair(first("due_date", "exact")) == ("Mar 04 26", "2026-03-04")
    assert pair(first("due_date", "day")) == ("March 04, 2026", "2026-03-04")
    assert pair(first("due_date", "week")) == ("March 01, 2026 to March 07, 2026", "2026-03-01")
    assert pair(first("due_date", "month")) == ("March 2026", "2026-03-01")
    assert pair(first("due_date", "quarter")) == ("Q1 2026", "2026-01-01")
    assert pair(first("due_date", "year")) == ("2026", "2026-01-01")
    assert pair(first("milestone", "exact")) == ("[ ]", "f")
    assert pair(first("est_in_mins", "oneday")) == ("3 days", "1440.0")
    assert pair(first("est_in_mins", "fivedays")) == ("0 day", "0.0")
    assert pair(first("entity", "entitytype")) == ("Asset", "Asset")
    assert pair(first("content", "firstletter")) == ("A", "A")
    tens = first("id", "tens")
    assert tens["group_name"] == tens["group_value"] and tens["group_value"] % 10 == 0
    last = sg.summarize("Task", on_project, COUNT, grouping=[g("due_date", "year")])["groups"][-1]
    assert last == {"group_name": "", "group_value": None, "summaries": {"id": 1}}


def test_grouping_faults(site):  # api3 041, 042
    sg, on_project = site
    cases = [
        ({"field": "sg_status_list", "type": "exact"},
         "API summarize() invalid/missing string 'direction':\n{\"field\" => \"sg_status_list\", \"type\" => \"exact\"}"
         "\nValid direction values:[\"asc\", \"desc\"]"),
        (g("sg_status_list", "nope"),
         "API summarize() grouping option 'nope' not valid for field Task.sg_status_list with data type "
         "'status_list'\nValid grouping types:\n[:exact]"),
        (g("id", "day"),
         "API summarize() grouping option 'day' not valid for field Task.id with data type 'number'\n"
         "Valid grouping types:\n[:exact,\n :tens,\n :hundreds,\n :thousands,\n :tensofthousands,\n"
         " :hundredsofthousands,\n :millions]"),
        (g("est_in_mins", "day"),
         "API summarize() grouping option 'day' not valid for field Task.est_in_mins with data type 'duration'\n"
         "Valid grouping types:\n[:exact, :oneday, :fivedays]"),
        (g("sg_not_a_field"),
         "API summarize() Task.sg_not_a_field doesn't exist:\n"
         "{\"field\" => \"sg_not_a_field\", \"type\" => \"exact\", \"direction\" => \"asc\"}"),
    ]
    for entry, message in cases:
        with pytest.raises(Fault) as e:
            sg.summarize("Task", on_project, COUNT, grouping=[entry])
        assert str(e.value) == message


def test_clustered_date_is_not_modelled(site):
    sg, on_project = site
    with pytest.raises(ShotgunError, match="clustered_date"):
        sg.summarize("Task", on_project, COUNT, grouping=[g("due_date", "clustered_date")])
