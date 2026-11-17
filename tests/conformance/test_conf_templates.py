"""Task Templates and the dependency cascade as api3 answers 070 to 074 record them.

On the mock each test seeds a template. On a live site it reads an existing Shot template and never writes to it.
"""

import pytest
from shotgun_api3 import Fault

TASK = ["content", "template_task", "task_template", "start_date", "due_date", "duration", "pinned",
        "dependency_violation", "upstream_tasks"]


def link(row):
    return {"type": row["type"], "id": row["id"]}


@pytest.fixture
def template(live, client):
    """A Shot TaskTemplate with at least two Tasks, its Task ids and its edge count."""
    if live:
        for tt in client.find("TaskTemplate", [["entity_type", "is", "Shot"]], ["code"],
                              order=[{"field_name": "id", "direction": "asc"}]):
            tasks = client.find("Task", [["task_template", "is", link(tt)]], ["id"])
            if len(tasks) >= 2:
                break
        else:
            pytest.skip("No Shot TaskTemplate with two Tasks on this site.")
    else:
        client.require_project = False  # template Tasks have no project
        step = client.create("Step", {"code": "Comp", "entity_type": "Shot"})
        tt = client.create("TaskTemplate", {"code": "conformance", "entity_type": "Shot"})
        tasks = [client.create("Task", {"content": c, "task_template": tt, "step": step}) for c in ("Model", "Comp")]
        client.create("TaskDependency", {"task": tasks[1], "dependent_task": tasks[0],
                                         "dependency_type": "finish-to-start-next-day"})
        client.require_project = True
    ids = [t["id"] for t in tasks]
    edges = client.find("TaskDependency", [["task", "in", [{"type": "Task", "id": i} for i in ids]]], ["id"])
    return link(tt), ids, len(edges)


def generated(site, made, shot):
    """The Tasks on ``shot`` and the edges among them, each tracked for cleanup."""
    tasks = site.find("Task", [["entity", "is", link(shot)]], TASK, order=[{"field_name": "id", "direction": "asc"}])
    for t in tasks:
        made.track("Task", t["id"])
    edges = site.find("TaskDependency", [["task", "in", [link(t) for t in tasks]]], ["id"]) if tasks else []
    for e in edges:
        made.track("TaskDependency", e["id"])
    return tasks, edges


# api3 070


@pytest.mark.finding("083", api3="070")
@pytest.mark.cell("create", "task_template", "entity")
def test_create_with_a_template_makes_its_tasks_and_edges(site, made, sandbox, run_token, template):
    tt, template_ids, edge_count = template
    shot = made.create("Shot", {"code": "zzconf_%s_tt" % run_token, "task_template": tt, "project": sandbox})
    assert "tasks" not in shot
    tasks, edges = generated(site, made, shot)
    assert sorted(t["template_task"]["id"] for t in tasks) == sorted(template_ids)
    assert all(t["task_template"] is None for t in tasks)
    assert len(edges) == edge_count
    assert len(site.find_one("Shot", [["id", "is", shot["id"]]], ["tasks"])["tasks"]) == len(template_ids)


# api3 071


@pytest.mark.finding("084", api3="071")
@pytest.mark.cell("update", "task_template", "entity")
def test_reapply_adds_only_the_missing_tasks(site, made, sandbox, run_token, template):
    tt, template_ids, _ = template
    shot = made.create("Shot", {"code": "zzconf_%s_reapply" % run_token, "task_template": tt, "project": sandbox})
    tasks, _ = generated(site, made, shot)
    made.delete("Task", tasks[0]["id"])
    again = made.update("Shot", shot["id"], {"task_template": tt})
    assert (set(again), again["task_template"]["id"]) == ({"type", "id", "task_template"}, tt["id"])
    assert len(generated(site, made, shot)[0]) == len(template_ids) - 1
    made.update("Shot", shot["id"], {"task_template": None})
    made.update("Shot", shot["id"], {"task_template": tt})
    after, _ = generated(site, made, shot)
    assert sorted(t["template_task"]["id"] for t in after) == sorted(template_ids)
    with pytest.raises(Fault) as e:
        made.update("Shot", shot["id"], {"task_template": None, "task_template_mode": "replace"})
    assert str(e.value).startswith("API update() Shot.task_template_mode doesn't exist:\n")


# api3 072, 073


@pytest.fixture
def chain(made, sandbox, run_token):
    """Tasks up and dn, both 2026-03-02 to 03-03, and the edge dn on up, finish-to-start-next-day."""
    p = "zzconf_%s_chain_" % run_token
    up = made.create("Task", {"content": p + "up", "start_date": "2026-03-02", "due_date": "2026-03-03", "project": sandbox})
    dn = made.create("Task", {"content": p + "dn", "start_date": "2026-03-02", "due_date": "2026-03-03", "project": sandbox})
    edge = made.create("TaskDependency", {"task": dn, "dependent_task": up, "dependency_type": "finish-to-start-next-day"})
    return up, dn, edge


def dates(site, task):
    row = site.find_one("Task", [["id", "is", task["id"]]], TASK)
    return row["start_date"], row["due_date"], row["pinned"], row["dependency_violation"]


@pytest.mark.finding("092", api3="072")
@pytest.mark.cell("update", "-", "date")
def test_upstream_dates_move_the_downstream_task(site, made, chain):
    up, dn, _ = chain
    assert dates(site, dn) == ("2026-03-04", "2026-03-05", False, False)
    assert site.find_one("Task", [["id", "is", up["id"]]], ["duration"])["duration"] == 960
    made.update("Task", up["id"], {"due_date": "2026-03-05"})
    assert dates(site, dn) == ("2026-03-06", "2026-03-09", False, False)


@pytest.mark.finding("093", api3="072")
@pytest.mark.cell("update", "-", "date")
def test_a_start_date_write_pins_and_flags_a_violation(site, made, chain):
    up, dn, _ = chain
    made.update("Task", dn["id"], {"start_date": "2026-03-04"})
    assert dates(site, dn)[2:] == (False, False)
    made.update("Task", dn["id"], {"start_date": "2026-03-05"})
    assert dates(site, dn) == ("2026-03-05", "2026-03-06", True, False)
    made.update("Task", up["id"], {"due_date": "2026-03-10"})
    assert dates(site, dn) == ("2026-03-05", "2026-03-06", True, True)
    with pytest.raises(Fault) as e:
        made.update("Task", dn["id"], {"dependency_violation": False})
    assert str(e.value) == ('API update() Task.dependency_violation is read only:\n'
                            '{"field_name" => "dependency_violation", "value" => false}')


@pytest.mark.finding("089", api3="073")
@pytest.mark.cell("delete", "-", "-")
def test_task_delete_retires_its_edges_and_revive_restores_them(site, made, chain):
    up, dn, edge = chain
    assert made.delete("Task", up["id"]) is True
    assert site.find_one("TaskDependency", [["id", "is", edge["id"]]], ["id"]) is None
    assert [r["id"] for r in site.find("TaskDependency", [["id", "is", edge["id"]]], ["id"], retired_only=True)] == [edge["id"]]
    assert dates(site, dn)[:2] == ("2026-03-04", "2026-03-05")
    assert site.find_one("Task", [["id", "is", dn["id"]]], ["upstream_tasks"])["upstream_tasks"] == []
    assert made.revive("Task", up["id"]) is True
    assert site.find_one("TaskDependency", [["id", "is", edge["id"]]], ["id"]) is not None
    assert [t["id"] for t in site.find_one("Task", [["id", "is", dn["id"]]], ["upstream_tasks"])["upstream_tasks"]] == [up["id"]]


# api3 074


@pytest.mark.finding("090", api3="074")
@pytest.mark.cell("create", "task_template", "event_log")
def test_generated_tasks_log_a_template_task_row(site, made, sandbox, run_token, template):
    tt, template_ids, _ = template
    shot = made.create("Shot", {"code": "zzconf_%s_ttlog" % run_token, "task_template": tt, "project": sandbox})
    tasks, _ = generated(site, made, shot)
    rows = site.find("EventLogEntry", [["attribute_name", "is", "template_task"], ["entity", "in", [link(t) for t in tasks]]],
                     ["event_type", "meta"])
    if not rows:
        pytest.skip("No events logged. The script's ApiUser has generate_event_log_entries off (finding 049).")
    assert len(rows) == len(template_ids)
    assert all(r["event_type"] == "Shotgun_Task_Change" and r["meta"]["in_create"] is True for r in rows)
