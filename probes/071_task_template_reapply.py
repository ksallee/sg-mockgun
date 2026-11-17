"""Q: what does update() of task_template on a Shot that has Tasks do: add the missing, re-sync the linked?

re-asks: findings 084, 102. Writes: 1 Shot in the sandbox and its Tasks; all deleted.
Run: uv run python probes/071_task_template_reapply.py --write
"""
import _lib
import _schedule as S


def snap(sg, shot):
    tasks = S.tasks_on(sg, shot)
    names = {t["id"]: t["content"] for t in tasks}
    return tasks, {"tasks": [S.line(t) for t in tasks],
                   "edges": [S.dep_line(d, names) + " id=%s" % d["id"] for d in S.deps_among(sg, tasks)]}


def main():
    if not _lib.writes_allowed():
        raise SystemExit("this probe writes; pass --write")
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    live, small = (S.template(sg, c) for c in S.TEMPLATE_CODES)
    stasks = S.template_tasks(sg, small)
    snames = {t["id"]: t["content"] for t in stasks}
    out = {"small_template": [t["content"] + "@" + (t["step"] or {}).get("name", "None") for t in stasks],
           "small_edges": [S.dep_line(d, snames) for d in S.deps_among(sg, stasks)]}
    with _lib.Created(sg) as made:
        shot = made.add(sg.create("Shot", {"project": project, "code": "zzprobe_071", "task_template": small}))
        tasks, out["0_created_with_small"] = snap(sg, shot)
        S.adopt(made, tasks)
        first, second = tasks[0], tasks[1]
        # change the linked Tasks: rename one and set it ip, delete the other, drop their edge
        sg.update("Task", first["id"], {"content": "renamed", "sg_status_list": "ip"})
        edges = S.deps_among(sg, tasks)
        for d in edges:
            sg.delete("TaskDependency", d["id"])
        sg.delete("Task", second["id"])
        made.rows.remove(("Task", second["id"]))
        hand = made.add(sg.create("Task", {"project": project, "entity": shot, "content": second["content"],
                                            "step": second["step"]}))
        _, out["1_after_edits"] = snap(sg, shot)
        out["1_hand_made_copy_of_deleted"] = second["content"]

        out["2_update_same_value_returned"] = sg.update("Shot", shot["id"], {"task_template": small})
        _, out["2_after_same_value"] = snap(sg, shot)

        out["3_update_null_returned"] = sg.update("Shot", shot["id"], {"task_template": None})
        _, out["3_after_null"] = snap(sg, shot)

        out["4_update_small_returned"] = sg.update("Shot", shot["id"], {"task_template": small})
        tasks, out["4_after_small_again"] = snap(sg, shot)
        S.adopt(made, tasks)

        out["5_update_live_returned"] = sg.update("Shot", shot["id"], {"task_template": live})
        tasks, out["5_after_live"] = snap(sg, shot)
        S.adopt(made, tasks)
        out["6_mode_key"] = _lib.ask(sg.update, "Shot", shot["id"],
                                     {"task_template": small, "task_template_mode": "replace"})
        out["6_after_mode_key_template"] = sg.find_one("Shot", [["id", "is", shot["id"]]], ["task_template"])["task_template"]
        tasks, _ = snap(sg, shot)
        S.adopt(made, tasks)
    _lib.emit("071_task_template_reapply", out, env, sg)
    left = sg.find("Task", [["content", "in", ["renamed"]], ["project", "is", project]], ["id"])
    print("left renamed Tasks:", len(left))


if __name__ == "__main__":
    main()
