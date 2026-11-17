"""Q: does an upstream date write reschedule the downstream Task; which writes pin it; does a pinned one
flag dependency_violation; does a duration write pin?

re-asks: findings 087, 092, 093, 100. Writes: 1 Shot, 2 Tasks, 1 TaskDependency in the sandbox; all deleted.
Run: uv run python probes/072_dependency_cascade.py --write
"""
import _lib
import _schedule as S


def main():
    if not _lib.writes_allowed():
        raise SystemExit("this probe writes; pass --write")
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    steps = []
    with _lib.Created(sg) as made:
        shot = made.add(sg.create("Shot", {"project": project, "code": "zzprobe_072"}))
        dates = {"start_date": "2026-03-02", "due_date": "2026-03-03"}  # Mon..Tue
        up = made.add(sg.create("Task", dict(project=project, entity=shot, content="up", **dates)))
        dn = made.add(sg.create("Task", dict(project=project, entity=shot, content="dn", **dates)))

        def look(label, returned=None):
            ts = {t["content"]: t for t in S.tasks_on(sg, shot)}
            row = {"step": label, "up": S.line(ts["up"]), "dn": S.line(ts["dn"])}
            if returned is not None:
                row["returned"] = returned
            steps.append(row)

        look("created, no edge")
        dep = sg.create("TaskDependency", {"task": dn, "dependent_task": up,
                                           "dependency_type": "finish-to-start-next-day"})
        made.add(dep)
        look("edge created (dn on up, finish-to-start-next-day)", {k: v for k, v in dep.items() if k != "id"})
        look("up due_date 03-05", sg.update("Task", up["id"], {"due_date": "2026-03-05"}))
        look("up due_date 03-02 (earlier)", sg.update("Task", up["id"], {"due_date": "2026-03-02"}))
        look("dn duration 1920", sg.update("Task", dn["id"], {"duration": 1920}))
        look("up due_date 03-04", sg.update("Task", up["id"], {"due_date": "2026-03-04"}))
        look("dn due_date 03-13", sg.update("Task", dn["id"], {"due_date": "2026-03-13"}))
        look("up due_date 03-03", sg.update("Task", up["id"], {"due_date": "2026-03-03"}))
        look("up duration 2880", sg.update("Task", up["id"], {"duration": 2880}))
        look("dn start_date 03-04 (before up ends)", sg.update("Task", dn["id"], {"start_date": "2026-03-04"}))
        look("up due_date 03-10", sg.update("Task", up["id"], {"due_date": "2026-03-10"}))
        look("up due_date 03-02", sg.update("Task", up["id"], {"due_date": "2026-03-02"}))
        look("up due_date 03-10 again", sg.update("Task", up["id"], {"due_date": "2026-03-10"}))
        look("dn pinned false", sg.update("Task", dn["id"], {"pinned": False}))
        look("dn pinned true", sg.update("Task", dn["id"], {"pinned": True}))
        look("up due_date 03-12", sg.update("Task", up["id"], {"due_date": "2026-03-12"}))
        look("dependency_violation write", _lib.ask(sg.update, "Task", dn["id"], {"dependency_violation": False}))
    _lib.emit("072_dependency_cascade", steps, env, sg)


if __name__ == "__main__":
    main()
