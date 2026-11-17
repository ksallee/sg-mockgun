"""Q: does delete() of an upstream Task retire its TaskDependency rows, and does revive() restore them?

re-asks: finding 089. Writes: 1 Shot, 2 Tasks, 1 TaskDependency in the sandbox; all deleted.
Run: uv run python probes/073_task_delete_revive.py --write
"""
import _lib
import _schedule as S


def main():
    if not _lib.writes_allowed():
        raise SystemExit("this probe writes; pass --write")
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    out = {}
    with _lib.Created(sg) as made:
        shot = made.add(sg.create("Shot", {"project": project, "code": "zzprobe_073"}))
        dates = {"start_date": "2026-03-02", "due_date": "2026-03-03"}
        up = made.add(sg.create("Task", dict(project=project, entity=shot, content="up", **dates)))
        dn = made.add(sg.create("Task", dict(project=project, entity=shot, content="dn", **dates)))
        dep = made.add(sg.create("TaskDependency", {"task": dn, "dependent_task": up,
                                                    "dependency_type": "finish-to-start-next-day"}))
        f = ["dependency_type"]

        def read(label):
            ts = {t["content"]: t for t in S.tasks_on(sg, shot)}
            out[label] = {
                "tasks": {k: S.line(v) + " up=%s down=%s" % ([x["id"] == up["id"] and "up" or x["id"] for x in v["upstream_tasks"]],
                                                             [x["id"] == dn["id"] and "dn" or x["id"] for x in v["downstream_tasks"]])
                          for k, v in ts.items()},
                "dep_find_one": sg.find_one("TaskDependency", [["id", "is", dep["id"]]], f) is not None,
                "dep_retired_only": len(sg.find("TaskDependency", [["id", "is", dep["id"]]], f, retired_only=True)),
                "up_find_one": sg.find_one("Task", [["id", "is", up["id"]]], ["content"]) is not None,
                "dn_upstream_filter": len(sg.find("Task", [["upstream_tasks", "is", up]], ["id"])),
            }

        read("0_linked")
        out["1_delete_returned"] = sg.delete("Task", up["id"])
        read("1_after_delete")
        out["2_revive_returned"] = sg.revive("Task", up["id"])
        read("2_after_revive")
        out["3_revive_again"] = sg.revive("Task", up["id"])

        # second delete: calls on the retired edge itself
        sg.delete("Task", up["id"])
        out["4_dep_update_while_retired"] = _lib.ask(sg.update, "TaskDependency", dep["id"], {"offset_days": 1})
        out["4_dep_delete_while_retired"] = _lib.ask(sg.delete, "TaskDependency", dep["id"])
        out["4_dep_revive_alone"] = _lib.ask(sg.revive, "TaskDependency", dep["id"])
        read("4_after_dep_revive_alone_up_still_retired")
        out["5_revive_task_returned"] = sg.revive("Task", up["id"])
        read("5_after_task_revive")
    _lib.emit("073_task_delete_revive", out, env, sg)


if __name__ == "__main__":
    main()
