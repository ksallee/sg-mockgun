"""Whether a filter on a calculated field (Task.workload) is applied: counts against a client-side count."""
import collections

import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = sg.find_one("Task", [["workload", "greater_than", 0]], ["project"])["project"]
    scope = [["project", "is", project]]
    rows = sg.find("Task", scope, ["workload"])
    values = collections.Counter(r["workload"] for r in rows)
    common = max((v for v in values if v), key=lambda v: values[v])
    answers = {
        "tasks in project": len(rows),
        "distinct workload values": len(values),
        "value tested": common,
        "client count is value": values[common],
        "client count > value": sum(n for v, n in values.items() if v is not None and v > common),
        "client count None": values[None],
    }
    for name, f in (
        ("is value", ["workload", "is", common]),
        ("is_not value", ["workload", "is_not", common]),
        ("greater_than value", ["workload", "greater_than", common]),
        ("between [value, value]", ["workload", "between", [common, common]]),
        ("is 123456789", ["workload", "is", 123456789]),
        ("is None", ["workload", "is", None]),
        ("in [value]", ["workload", "in", [common]]),
    ):
        r = _lib.ask(sg.find, "Task", scope + [f], ["id"])
        answers["server " + name] = len(r["ok"]) if "ok" in r else r
    r = _lib.ask(sg.find, "Task", scope, ["id"], order=[{"field_name": "workload", "direction": "desc"}], limit=1)
    answers["order by workload"] = "ok" if "ok" in r else r
    _lib.emit("006_calculated_filter", answers, env, sg)


if __name__ == "__main__":
    main()
