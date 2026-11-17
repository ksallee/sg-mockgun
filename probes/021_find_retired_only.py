"""021: retired_only=True on find: only retired rows, before and after a delete and a revive. Needs --write."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("needs --write")
project = _lib.sandbox(sg, env)
P = [["project", "is", project]]


def found(filters, **kw):
    r = _lib.ask(sg.find, "Version", filters, ["code"], **kw)
    return [x["id"] for x in r["ok"]] if "ok" in r else r


answers = {}
with _lib.Created(sg) as made:
    keep = made.add(sg.create("Version", {"project": project, "code": "zzprobe_021_active"}))
    gone = made.add(sg.create("Version", {"project": project, "code": "zzprobe_021_retired"}))
    mine = [["id", "in", [keep["id"], gone["id"]]]]
    answers["both active: default"] = found(mine)
    answers["both active: retired_only"] = found(mine, retired_only=True)
    answers["delete one"] = sg.delete("Version", gone["id"])
    answers["after delete: default"] = found(mine)
    answers["after delete: retired_only"] = found(mine, retired_only=True)
    answers["after delete: retired_only, no filter, project only, any active row in it"] = (
        lambda ids: {"rows": len(ids), "active rows among them": len(found([["id", "in", ids]])) if ids else 0}
    )(found(P, retired_only=True))
    answers["retired row, fields"] = _lib.ask(
        sg.find_one, "Version", [["id", "is", gone["id"]]], ["code", "project", "retirement_date"], retired_only=True)
    answers["retired_only filter on retirement_date is_not None"] = found(mine + [["retirement_date", "is_not", None]], retired_only=True)
    answers["default filter on retirement_date is_not None"] = found(mine + [["retirement_date", "is_not", None]])
    answers["summarize count, retired row id"] = sg.summarize("Version", [["id", "is", gone["id"]]], [{"field": "id", "type": "count"}])["summaries"]
    answers["revive"] = sg.revive("Version", gone["id"])
    answers["after revive: default"] = found(mine)
    answers["after revive: retired_only"] = found(mine, retired_only=True)
answers["after cleanup: retired_only"] = found(mine, retired_only=True)
answers["after cleanup: default"] = found(mine)
answers["ids"] = {"active": keep["id"], "retired": gone["id"]}
_lib.emit("021_find_retired_only", answers, env, sg)
