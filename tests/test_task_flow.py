"""Task Templates, the dependency cascade, and Task delete and revive, as api3 answers them."""

import pytest
from shotgun_api3 import Fault

TASK = ["content", "step", "template_task", "task_template", "sg_status_list", "start_date", "due_date",
        "duration", "pinned", "dependency_violation", "upstream_tasks", "downstream_tasks"]
DEP = ["task", "dependent_task", "dependency_type", "offset_days"]


@pytest.fixture
def site(sg):
    project = sg.create("Project", {"name": "Sandbox"})
    steps = dict((code, sg.create("Step", {"code": code, "entity_type": "Shot"})) for code in ("Model", "Comp", "Light"))
    return sg, project, steps


def template(sg, steps, code, tasks, edges):
    """A TaskTemplate with template Tasks ``(content, step code, extra)`` and edges ``(down, up, type, offset)``."""
    tt = sg.create("TaskTemplate", {"code": code, "entity_type": "Shot"})
    made = {}
    for content, step, extra in tasks:
        data = {"content": content, "task_template": tt, "step": steps[step]}
        data.update(extra)
        made[content] = sg.create("Task", data)
    for down, up, kind, offset in edges:
        data = {"task": made[down], "dependent_task": made[up], "dependency_type": kind}
        if offset is not None:
            data["offset_days"] = offset
        sg.create("TaskDependency", data)
    return tt, made


def tasks_on(sg, entity):
    return sg.find("Task", [["entity", "is", entity]], TASK, order=[{"field_name": "id", "direction": "asc"}])


def deps_among(sg, tasks):
    return sg.find("TaskDependency", [["task", "in", [{"type": "Task", "id": t["id"]} for t in tasks]]], DEP)


def pairs(sg, tasks):
    names = dict((t["id"], t["content"]) for t in tasks)
    return sorted((names[d["task"]["id"]], names[d["dependent_task"]["id"]], d["dependency_type"], d["offset_days"])
                  for d in deps_among(sg, tasks))


def live_template(sg, steps):
    return template(sg, steps, "live", [("Model", "Model", {}), ("Light", "Light", {"duration": 3360}),
                                        ("Comp", "Comp", {})],
                    [("Light", "Model", "finish-to-start-next-day", None), ("Comp", "Light", "start-to-start", 1)])


# api3 070

def test_create_with_task_template_makes_tasks_and_edges(site):
    sg, project, steps = site
    tt, made = live_template(sg, steps)
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": tt})
    assert sorted(shot) == ["code", "id", "project", "task_template", "type"]
    tasks = tasks_on(sg, shot)
    assert sorted(t["content"] for t in tasks) == ["Comp", "Light", "Model"]
    by = dict((t["content"], t) for t in tasks)
    assert by["Light"]["template_task"]["id"] == made["Light"]["id"]
    assert by["Light"]["duration"] == 3360
    assert all(t["task_template"] is None and t["pinned"] is False for t in tasks)
    assert pairs(sg, tasks) == [("Comp", "Light", "start-to-start", 1),
                                ("Light", "Model", "finish-to-start-next-day", None)]
    assert [u["id"] for u in by["Light"]["upstream_tasks"]] == [by["Model"]["id"]]
    assert [d["id"] for d in by["Light"]["downstream_tasks"]] == [by["Comp"]["id"]]


def test_create_return_fields_tasks_reads_empty(site):
    sg, project, steps = site
    tt, _ = live_template(sg, steps)
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": tt}, return_fields=["tasks"])
    assert shot["tasks"] == []
    assert len(tasks_on(sg, shot)) == 3


def test_batch_create_applies_the_template(site):
    sg, project, steps = site
    tt, _ = live_template(sg, steps)
    shot = sg.batch([{"request_type": "create", "entity_type": "Shot",
                      "data": {"project": project, "code": "sh", "task_template": tt}}])[0]
    tasks = tasks_on(sg, shot)
    assert len(tasks) == 3 and len(deps_among(sg, tasks)) == 2


def test_create_without_task_template_makes_no_task(site):
    sg, project, steps = site
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": None})
    assert tasks_on(sg, shot) == []


# api3 071

def small_template(sg, steps):
    return template(sg, steps, "small", [("Model", "Model", {}), ("Comp", "Comp", {})],
                    [("Comp", "Model", "finish-to-start-next-day", None)])


def test_reapply_adds_missing_resyncs_linked_and_rewires(site):
    sg, project, steps = site
    small, _ = small_template(sg, steps)
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": small})
    comp, model = sorted(tasks_on(sg, shot), key=lambda t: t["content"])
    sg.update("Task", comp["id"], {"content": "renamed", "sg_status_list": "ip"})
    for d in deps_among(sg, [comp, model]):
        sg.delete("TaskDependency", d["id"])
    sg.delete("Task", model["id"])
    sg.create("Task", {"project": project, "entity": shot, "content": "Model", "step": steps["Model"]})

    sg.update("Shot", shot["id"], {"task_template": small})  # the stored value: nothing happens
    assert sorted(t["content"] for t in tasks_on(sg, shot)) == ["Model", "renamed"]
    sg.update("Shot", shot["id"], {"task_template": None})
    assert sorted(t["content"] for t in tasks_on(sg, shot)) == ["Model", "renamed"]
    sg.update("Shot", shot["id"], {"task_template": small})
    tasks = tasks_on(sg, shot)
    assert sorted((t["content"], t["sg_status_list"], bool(t["template_task"])) for t in tasks) == [
        ("Comp", "ip", True), ("Model", "wtg", False), ("Model", "wtg", True)]
    linked = [t for t in tasks if t["template_task"]]
    assert pairs(sg, linked) == [("Comp", "Model", "finish-to-start-next-day", None)]


def test_switching_template_adds_its_tasks_and_removes_none(site):
    sg, project, steps = site
    small, _ = small_template(sg, steps)
    live, _ = live_template(sg, steps)
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": small})
    sg.update("Shot", shot["id"], {"task_template": live})
    tasks = tasks_on(sg, shot)
    assert len(tasks) == 5 and len(deps_among(sg, tasks)) == 3


def test_reapply_erases_an_edge_the_template_lacks(site):
    # finding 102
    sg, project, steps = site
    small, _ = small_template(sg, steps)
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": small})
    comp, model = sorted(tasks_on(sg, shot), key=lambda t: t["content"])
    edge = deps_among(sg, [comp])[0]
    sg.update("TaskDependency", edge["id"], {"dependency_type": "finish-to-finish"})
    sg.update("Shot", shot["id"], {"task_template": None})
    sg.update("Shot", shot["id"], {"task_template": small})
    edges = deps_among(sg, [comp])
    assert [(e["dependency_type"], e["id"] != edge["id"]) for e in edges] == [("finish-to-start-next-day", True)]
    assert sg.find("TaskDependency", [["id", "is", edge["id"]]], ["id"], retired_only=True) == []


# api3 072

@pytest.fixture
def chain(site):
    sg, project, _ = site
    dates = {"start_date": "2026-03-02", "due_date": "2026-03-03"}
    up = sg.create("Task", dict(project=project, content="up", **dates))
    dn = sg.create("Task", dict(project=project, content="dn", **dates))
    return sg, up, dn


def read(sg, task):
    t = sg.find_one("Task", [["id", "is", task["id"]]], TASK)
    return (t["start_date"], t["due_date"], t["duration"], t["pinned"], t["dependency_violation"])


def test_new_task_reads_duration_from_its_dates(chain):
    sg, up, dn = chain
    assert read(sg, dn) == ("2026-03-02", "2026-03-03", 960, False, False)


def test_cascade_pins_and_violation(chain):
    sg, up, dn = chain
    dep = sg.create("TaskDependency", {"task": dn, "dependent_task": up, "dependency_type": "finish-to-start-next-day"})
    assert dep["dependency_type"] == "finish-to-start-next-day"
    steps = [
        (None, None, ("2026-03-02", "2026-03-03", 960, False, False), ("2026-03-04", "2026-03-05", 960, False, False)),
        (up, {"due_date": "2026-03-05"}, ("2026-03-02", "2026-03-05", 1920, False, False),
         ("2026-03-06", "2026-03-09", 960, False, False)),
        (up, {"due_date": "2026-03-02"}, ("2026-03-02", "2026-03-02", 480, False, False),
         ("2026-03-03", "2026-03-04", 960, False, False)),
        (dn, {"duration": 1920}, None, ("2026-03-03", "2026-03-06", 1920, False, False)),
        (up, {"due_date": "2026-03-04"}, None, ("2026-03-05", "2026-03-10", 1920, False, False)),
        (dn, {"due_date": "2026-03-13"}, None, ("2026-03-05", "2026-03-13", 3360, False, False)),
        (up, {"due_date": "2026-03-03"}, None, ("2026-03-04", "2026-03-12", 3360, False, False)),
        (up, {"duration": 2880}, ("2026-03-02", "2026-03-09", 2880, False, False),
         ("2026-03-10", "2026-03-18", 3360, False, False)),
        (dn, {"start_date": "2026-03-04"}, None, ("2026-03-04", "2026-03-12", 3360, True, True)),
        (up, {"due_date": "2026-03-10"}, None, ("2026-03-04", "2026-03-12", 3360, True, True)),
        (up, {"due_date": "2026-03-02"}, None, ("2026-03-04", "2026-03-12", 3360, True, False)),
        (up, {"due_date": "2026-03-10"}, None, ("2026-03-04", "2026-03-12", 3360, True, True)),
        (dn, {"pinned": False}, None, ("2026-03-11", "2026-03-19", 3360, False, False)),
        (dn, {"pinned": True}, None, ("2026-03-11", "2026-03-19", 3360, True, False)),
        (up, {"due_date": "2026-03-12"}, None, ("2026-03-11", "2026-03-19", 3360, True, True)),
    ]
    for task, data, want_up, want_dn in steps:
        if task is not None:
            sg.update("Task", task["id"], data)
        if want_up is not None:
            assert read(sg, up) == want_up, data
        assert read(sg, dn) == want_dn, data


def test_dependency_violation_is_read_only(chain):
    sg, up, dn = chain
    with pytest.raises(Fault) as e:
        sg.update("Task", dn["id"], {"dependency_violation": False})
    assert str(e.value) == ('API update() Task.dependency_violation is read only:\n'
                            '{"field_name" => "dependency_violation", "value" => false}')


def test_omitted_dependency_type_is_finish_to_start_next_day(chain):
    # finding 085
    sg, up, dn = chain
    dep = sg.create("TaskDependency", {"task": dn, "dependent_task": up})
    assert sg.find_one("TaskDependency", [["id", "is", dep["id"]]], ["dependency_type"])["dependency_type"] == \
        "finish-to-start-next-day"


def test_work_week_setter(chain):
    sg, up, dn = chain
    sg.set_work_week([True] * 7)
    sg.update("Task", up["id"], {"duration": 2880})
    assert read(sg, up)[:2] == ("2026-03-02", "2026-03-07")


# api3 073

def test_delete_retires_edges_and_revive_restores_them(chain):
    sg, up, dn = chain
    dep = sg.create("TaskDependency", {"task": dn, "dependent_task": up, "dependency_type": "finish-to-start-next-day"})
    assert sg.delete("Task", up["id"]) is True
    assert sg.find_one("TaskDependency", [["id", "is", dep["id"]]], ["id"]) is None
    assert len(sg.find("TaskDependency", [["id", "is", dep["id"]]], ["id"], retired_only=True)) == 1
    t = sg.find_one("Task", [["id", "is", dn["id"]]], TASK)
    assert t["upstream_tasks"] == [] and (t["start_date"], t["due_date"]) == ("2026-03-04", "2026-03-05")
    assert sg.revive("Task", up["id"]) is True
    assert sg.find_one("TaskDependency", [["id", "is", dep["id"]]], ["id"]) is not None
    t = sg.find_one("Task", [["id", "is", dn["id"]]], TASK)
    assert [u["id"] for u in t["upstream_tasks"]] == [up["id"]]
    assert [d["id"] for d in sg.find_one("Task", [["id", "is", up["id"]]], TASK)["downstream_tasks"]] == [dn["id"]]
    assert sg.revive("Task", up["id"]) is False


def test_edge_revived_alone_links_nothing_until_the_task_revives(chain):
    sg, up, dn = chain
    dep = sg.create("TaskDependency", {"task": dn, "dependent_task": up, "dependency_type": "finish-to-start-next-day"})
    sg.delete("Task", up["id"])
    sg.update("TaskDependency", dep["id"], {"offset_days": 1})
    assert sg.delete("TaskDependency", dep["id"]) is False
    assert sg.revive("TaskDependency", dep["id"]) is True
    assert sg.find_one("Task", [["id", "is", dn["id"]]], TASK)["upstream_tasks"] == []
    assert sg.revive("Task", up["id"]) is True
    assert read(sg, dn)[:2] == ("2026-03-05", "2026-03-06")


# api3 074

def test_template_apply_event_rows(site):
    sg, project, steps = site
    tt, made = live_template(sg, steps)
    head = max(e["id"] for e in sg.find("EventLogEntry", [], ["id"]))
    shot = sg.create("Shot", {"project": project, "code": "sh", "task_template": tt})
    rows = sg.find("EventLogEntry", [["id", "greater_than", head]], ["event_type", "attribute_name", "meta", "entity"],
                   order=[{"field_name": "id", "direction": "asc"}])
    tasks = tasks_on(sg, shot)
    ids = set(t["id"] for t in tasks)
    shot_rows = [(r["event_type"], r["attribute_name"]) for r in rows if r["meta"].get("entity_id") == shot["id"]
                 and r["meta"].get("entity_type") == "Shot"]
    assert shot_rows.count(("Shotgun_Shot_Change", "tasks")) == 3
    tasks_row = next(r for r in rows if r["attribute_name"] == "tasks")
    assert tasks_row["meta"]["in_create"] is True and tasks_row["meta"]["removed"] == []
    assert tasks_row["meta"]["added"][0]["type"] == "Task"
    tt_rows = [r for r in rows if r["attribute_name"] == "template_task"]
    assert sorted(r["meta"]["entity_id"] for r in tt_rows) == sorted(ids)
    assert tt_rows[0]["meta"]["in_create"] is True and tt_rows[0]["meta"]["old_value"] is None
    links = [r for r in rows if r["attribute_name"] in ("upstream_tasks", "downstream_tasks")]
    assert len(links) == 4
    dep_rows = [(r["event_type"], r["attribute_name"]) for r in rows if r["event_type"].startswith("Shotgun_TaskDependency_")]
    assert sorted(dep_rows) == sorted([
        ("Shotgun_TaskDependency_New", None), ("Shotgun_TaskDependency_Change", "task"),
        ("Shotgun_TaskDependency_Change", "dependent_task"),
        ("Shotgun_TaskDependency_New", None), ("Shotgun_TaskDependency_Change", "task"),
        ("Shotgun_TaskDependency_Change", "dependent_task"), ("Shotgun_TaskDependency_Change", "dependency_type"),
        ("Shotgun_TaskDependency_Change", "offset_days")])
    filtered = sg.find("EventLogEntry", [["attribute_name", "is", "template_task"],
                                         ["entity", "in", [{"type": "Task", "id": i} for i in ids]]], ["id"])
    assert len(filtered) == 3


def test_template_task_update_applies_nothing(site):
    sg, project, steps = site
    small, made = small_template(sg, steps)
    other = sg.create("TaskTemplate", {"code": "other", "entity_type": "Shot"})
    before = len(sg.find("Task", [], ["id"]))
    sg.update("Task", made["Model"]["id"], {"task_template": other})
    assert len(sg.find("Task", [], ["id"])) == before
