"""Checkbox `is None` and `is_not None`: refused or answered."""
import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    answers = {"total": len(sg.find("Version", [], ["id"]))}
    for relation in ("is", "is_not"):
        for value in (None, True, False):
            r = _lib.ask(sg.find, "Version", [["flagged", relation, value]], ["id"])
            if "ok" in r:
                r = {"ok": "%d rows" % len(r["ok"])}
            answers["flagged %s %r" % (relation, value)] = r
    r = _lib.ask(sg.find, "Version", [["flagged", "in", [None]]], ["id"], limit=1)
    answers["flagged in [None]"] = r
    _lib.emit("005_checkbox_none", answers, env, sg)


if __name__ == "__main__":
    main()
