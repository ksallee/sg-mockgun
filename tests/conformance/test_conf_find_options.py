"""find options and order as api3 answers 020 to 027 record them."""

import pytest
from shotgun_api3 import Fault


def ids(rows):
    return [r["id"] for r in rows]


# api3 020


@pytest.mark.finding("082", api3="020")
@pytest.mark.cell("find", "limit", "-")
def test_negative_limit_and_page_fail_in_the_client(site):
    with pytest.raises(ValueError, match="limit parameter must be a positive integer"):
        site.find("Version", [], ["id"], limit=-1)
    with pytest.raises(ValueError, match="page parameter must be a positive integer"):
        site.find("Version", [], ["id"], page=-1)


@pytest.mark.finding("082", api3="020")
@pytest.mark.cell("find", "limit", "-")
def test_limit_zero_is_no_limit(site, made, sandbox, run_token):
    code = "zzconf_%s_limit" % run_token
    for n in range(3):
        made.create("Version", {"code": "%s_%d" % (code, n), "project": sandbox})
    scope = [["project", "is", sandbox], ["code", "starts_with", code]]
    assert len(site.find("Version", scope, ["id"], limit=0)) == 3
    assert len(site.find("Version", scope, ["id"], limit=2)) == 2
    assert len(site.find("Version", scope, ["id"], page=2, limit=2)) == 1


# api3 021


@pytest.mark.finding("060", api3="021")
@pytest.mark.cell("find", "retired_only", "-")
def test_retired_only_returns_only_retired_rows(site, made, sandbox, run_token):
    active = made.create("Version", {"code": "zzconf_%s_active" % run_token, "project": sandbox})
    retired = made.create("Version", {"code": "zzconf_%s_retired" % run_token, "project": sandbox})
    scope = [["id", "in", [active["id"], retired["id"]]]]
    assert site.find("Version", scope, ["id"], retired_only=True) == []
    made.delete("Version", retired["id"])
    assert ids(site.find("Version", scope, ["id"])) == [active["id"]]
    assert ids(site.find("Version", scope, ["id"], retired_only=True)) == [retired["id"]]


@pytest.mark.finding("060", api3="021")
@pytest.mark.cell("find", "is_not", "retirement_date")
def test_retirement_date_cannot_be_filtered(site):
    with pytest.raises(Fault) as e:
        site.find("Version", [["retirement_date", "is_not", None]], ["id"])
    assert str(e.value) == ('API read() Version.retirement_date doesn\'t exist:\n'
                            '{"path" => "retirement_date", "relation" => "is_not", "values" => [nil]}')


# api3 022


@pytest.mark.finding("018", api3="022")
@pytest.mark.cell("find", "include_archived_projects", "-")
def test_archived_projects_drop_out(site, sandbox):
    assert site.find("Project", [["archived", "is", True]], ["id"], include_archived_projects=False) == []
    assert ids(site.find("Project", [["id", "is", sandbox["id"]]], ["id"], include_archived_projects=False)) == [
        sandbox["id"]]


# api3 023


@pytest.mark.finding("none", api3="023")
@pytest.mark.cell("find", "additional_filter_presets", "-")
def test_latest_keeps_the_newest_version_per_entity(site, made, sandbox, run_token):
    p = "zzconf_%s_latest_" % run_token
    shot = made.create("Shot", {"code": p + "shot", "project": sandbox})
    made.create("Version", {"code": p + "v1", "entity": shot, "project": sandbox})
    newest = made.create("Version", {"code": p + "v2", "entity": shot, "project": sandbox})
    made.create("Version", {"code": p + "none", "project": sandbox})
    preset = [{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}]
    rows = site.find("Version", [["project", "is", sandbox], ["code", "starts_with", p]], ["id"],
                     additional_filter_presets=preset)
    assert ids(rows) == [newest["id"]]


@pytest.mark.finding("none", api3="023")
@pytest.mark.cell("find", "additional_filter_presets", "-")
def test_unknown_preset_is_refused(site):
    with pytest.raises(Fault) as e:
        site.find("Version", [["id", "is", 0]], ["id"], additional_filter_presets=[{"preset_name": "NOPE"}])
    assert str(e.value).startswith("API read() Invalid additional filter preset provided: ")


# api3 024, 025


@pytest.fixture
def ordered(made, sandbox, run_token):
    """Four Versions as in api3 025: b, none, a, empty, created in that order, and the scope that finds them."""
    p = "zzconf_%s_order_" % run_token
    shot = made.create("Shot", {"code": p + "shot", "project": sandbox})
    rows = {}
    for name, data in (("b", {"description": "b", "frame_count": 5, "sg_status_list": "rev", "entity": shot}),
                       ("none", {"sg_status_list": None}),
                       ("a", {"description": "a", "frame_count": 1, "sg_status_list": "na"}),
                       ("empty", {"description": "", "frame_count": 0, "sg_status_list": "apr"})):
        data.update({"code": p + name, "project": sandbox})
        rows[made.create("Version", data)["id"]] = name
    return rows, [["project", "is", sandbox], ["code", "starts_with", p], ["id", "in", list(rows)]]


def order(site, ordered, field, direction):
    rows, scope = ordered
    found = site.find("Version", scope, ["id"], order=[{"field_name": field, "direction": direction}])
    return [rows[r["id"]] for r in found]


@pytest.mark.finding("026", api3="025")
@pytest.mark.cell("find", "order", "text")
def test_none_sorts_last_both_ways(site, ordered):
    assert order(site, ordered, "description", "asc") == ["a", "b", "none", "empty"]
    assert order(site, ordered, "description", "desc") == ["b", "a", "none", "empty"]
    assert order(site, ordered, "frame_count", "asc") == ["empty", "a", "b", "none"]
    assert order(site, ordered, "frame_count", "desc") == ["b", "a", "empty", "none"]


@pytest.mark.finding("026", api3="024")
@pytest.mark.cell("find", "order", "status_list")
def test_status_list_sorts_by_valid_values(site, ordered):
    assert order(site, ordered, "sg_status_list", "asc") == ["a", "b", "empty", "none"]
    assert order(site, ordered, "sg_status_list", "desc") == ["empty", "b", "a", "none"]


@pytest.mark.finding("026", api3="025")
@pytest.mark.cell("find", "order", "entity")
def test_entity_sorts_and_none_stays_last(site, ordered):
    assert order(site, ordered, "entity", "asc") == ["b", "none", "a", "empty"]
    assert order(site, ordered, "entity.Shot.code", "desc") == ["b", "none", "a", "empty"]


@pytest.mark.finding("026", api3="024")
@pytest.mark.cell("find", "order", "-")
def test_order_input_forms(site, ordered):
    rows, scope = ordered
    by_code = site.find("Version", scope, ["code"], order=[{"field_name": "code"}])
    assert [rows[r["id"]] for r in by_code] == ["a", "b", "empty", "none"]
    assert site.find("Version", scope, ["id"], order=[{"field_name": "sg_not_a_field_at_all", "direction": "desc"}]) == (
        site.find("Version", scope, ["id"]))
    with pytest.raises(Fault) as e:
        site.find("Version", scope, ["id"], order=[{"field_name": "code", "direction": "up"}])
    assert str(e.value) == ("API read() invalid/missing string 'direction':\n"
                            '{"field_name" => "code", "direction" => "up"}')


# api3 026, 027


@pytest.mark.finding("060", api3="026")
@pytest.mark.cell("find", "-", "entity")
def test_link_dicts_carry_the_display_name(site, made, sandbox, run_token):
    p = "zzconf_%s_name_" % run_token
    shot = made.create("Shot", {"code": p + "shot", "project": sandbox})
    v = made.create("Version", {"code": p + "v", "entity": shot, "project": sandbox})
    note = made.create("Note", {"subject": p + "subject", "content": "probe", "note_links": [shot], "project": sandbox})
    assert site.find_one("Version", [["id", "is", v["id"]]], ["entity"])["entity"] == {
        "type": "Shot", "id": shot["id"], "name": p + "shot"}
    link = site.find_one("Note", [["id", "is", note["id"]]], ["note_links"])["note_links"]
    assert link == [{"type": "Shot", "id": shot["id"], "name": p + "shot"}]
    project_link = site.find_one("Version", [["id", "is", v["id"]]], ["project"])["project"]
    assert set(project_link) == {"type", "id", "name"}
    assert site.find_one("Note", [["id", "is", note["id"]]], ["cached_display_name"])["cached_display_name"] == (
        p + "subject - probe")


@pytest.mark.finding("060", api3="027")
@pytest.mark.cell("find", "-", "multi_entity")
def test_a_link_to_a_retired_row_reads_null_and_comes_back(site, made, sandbox, run_token):
    p = "zzconf_%s_retlink_" % run_token
    task = made.create("Task", {"content": p + "task", "project": sandbox})
    doomed = made.create("Playlist", {"code": p + "doomed", "project": sandbox})
    kept = made.create("Playlist", {"code": p + "kept", "project": sandbox})
    v = made.create("Version", {"code": p + "v", "sg_task": task, "playlists": [doomed, kept], "project": sandbox})

    def read():
        return site.find_one("Version", [["id", "is", v["id"]]], ["sg_task", "playlists"])

    made.delete("Task", task["id"])
    made.delete("Playlist", doomed["id"])
    after = read()
    assert after["sg_task"] is None and ids(after["playlists"]) == [kept["id"]]
    assert site.find("Version", [["sg_task", "is", {"type": "Task", "id": task["id"]}]], ["id"]) == []
    made.revive("Task", task["id"])
    made.revive("Playlist", doomed["id"])
    back = read()
    assert back["sg_task"]["id"] == task["id"] and sorted(ids(back["playlists"])) == sorted([doomed["id"], kept["id"]])
