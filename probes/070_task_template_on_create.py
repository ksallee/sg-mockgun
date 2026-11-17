"""Q: does create() with task_template make the template's Tasks and edges in the same call, and what
does create() return? Also the EventLogEntry rows the apply writes (api3 074).

re-asks: findings 083, 090. Writes: 2 Shots in the sandbox, their generated Tasks; all deleted.
Run: uv run python probes/070_task_template_on_create.py --write
"""
import time

import _lib
import _schedule as S


def main():
    if not _lib.writes_allowed():
        raise SystemExit("this probe writes; pass --write")
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    tt = S.template(sg, S.TEMPLATE_CODES[0])
    ttasks = S.template_tasks(sg, tt)
    tnames = {t["id"]: t["content"] for t in ttasks}
    out = {"template_tasks": [t["content"] for t in ttasks],
           "template_edges": [S.dep_line(d, tnames) for d in S.deps_among(sg, ttasks)]}
    with _lib.Created(sg) as made:
        t0 = time.time()
        shot = made.add(sg.create("Shot", {"project": project, "code": "zzprobe_070_a", "task_template": tt}))
        out["create_seconds"] = round(time.time() - t0, 1)
        out["create_returned"] = {k: v for k, v in shot.items() if k != "id"}
        shot2_ret = sg.create("Shot", {"project": project, "code": "zzprobe_070_b", "task_template": tt},
                              return_fields=["tasks", "task_template"])
        made.add(shot2_ret)
        out["create_with_return_fields_tasks"] = {k: v for k, v in shot2_ret.items() if k != "id"}
        tasks = S.tasks_on(sg, shot)
        S.adopt(made, tasks)
        names = {t["id"]: t["content"] for t in tasks}
        edges = S.deps_among(sg, tasks)
        out["tasks_read_at_once"] = [S.line(t) for t in tasks]
        out["template_task_points_at_template"] = all(
            (t["template_task"] or {}).get("id") in tnames for t in tasks)
        out["task_project_is_sandbox"] = all(t["project"]["id"] == project["id"] for t in tasks)
        out["task_task_template_values"] = sorted({str(t["task_template"]) for t in tasks})
        out["edges_read_at_once"] = [S.dep_line(d, names) for d in edges]
        later = S.tasks_on(sg, shot, settle=5)
        out["tasks_5s_later"] = len(later)
        out["shot_tasks_field"] = len(sg.find_one("Shot", [["id", "is", shot["id"]]], ["tasks"])["tasks"])
        tasks2 = S.tasks_on(sg, shot2_ret)
        S.adopt(made, tasks2)
        out["shot_b_tasks"] = len(tasks2)

        # batch create, the same apply
        res = sg.batch([{"request_type": "create", "entity_type": "Shot",
                         "data": {"project": project, "code": "zzprobe_070_c", "task_template": tt}}])
        made.add(res[0])
        out["batch_returned"] = {k: v for k, v in res[0].items() if k != "id"}
        tasks3 = S.tasks_on(sg, res[0])
        S.adopt(made, tasks3)
        out["batch_tasks"] = len(tasks3)
        out["batch_edges"] = len(S.deps_among(sg, tasks3))

        # event log (api3 074)
        ids = [t["id"] for t in tasks]
        ev_fields = ["event_type", "attribute_name", "entity", "meta", "user", "session_uuid"]
        task_events = sg.find("EventLogEntry", [["event_type", "starts_with", "Shotgun_Task_"],
                                                ["created_at", "in_last", [1, "HOUR"]]], ev_fields,
                              order=[{"field_name": "id"}], limit=500)
        task_events = [e for e in task_events if (e.get("entity") or {}).get("id") in ids
                       or (e.get("meta") or {}).get("entity_id") in ids]
        shot_events = sg.find("EventLogEntry", [["event_type", "starts_with", "Shotgun_Shot_"],
                                                ["created_at", "in_last", [1, "HOUR"]]], ev_fields,
                              order=[{"field_name": "id"}], limit=500)
        shot_events = [e for e in shot_events if (e.get("meta") or {}).get("entity_id") == shot["id"]]
        dep_events = sg.find("EventLogEntry", [["event_type", "starts_with", "Shotgun_TaskDependency_"],
                                               ["created_at", "in_last", [1, "HOUR"]]], ev_fields,
                             order=[{"field_name": "id"}], limit=500)
        out["events_task_rows"] = len(task_events)
        out["events_task_by_attr"] = sorted({"%s %s" % (e["event_type"], e["attribute_name"]) for e in task_events})
        out["events_template_task_sample"] = next((e for e in task_events if e["attribute_name"] == "template_task"), None)
        out["events_shot_rows"] = ["%s %s in_create=%s" % (e["event_type"], e["attribute_name"],
                                                           (e["meta"] or {}).get("in_create")) for e in shot_events]
        edge_ids = {d["id"] for d in edges}
        dep_events = [e for e in dep_events if (e.get("meta") or {}).get("entity_id") in edge_ids]
        out["events_dep_rows"] = ["%s %s" % (e["event_type"], e["attribute_name"]) for e in dep_events]
        flt = sg.find("EventLogEntry", [["attribute_name", "is", "template_task"],
                                        ["entity", "in", [{"type": "Task", "id": i} for i in ids]]], ["id"])
        out["events_filter_template_task_entity_in"] = len(flt)
    _lib.emit("070_task_template_on_create", out, env, sg)


if __name__ == "__main__":
    main()
