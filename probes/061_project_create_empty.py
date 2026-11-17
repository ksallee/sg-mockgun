"""What does `create("Project", {})` answer? It is expected to be refused; the probe checks no row was made."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("this probe writes: pass --write")
before = sg.summarize("Project", [], [{"field": "id", "type": "count"}])["summaries"]["id"]
r = _lib.ask(sg.create, "Project", {})
after = sg.summarize("Project", [], [{"field": "id", "type": "count"}])["summaries"]["id"]
out = {"create Project {}": r, "project count delta": after - before}
if "ok" in r:
    out["WARNING"] = "a Project was created: report it, do not delete"
_lib.emit("061_project_create_empty", out, env, sg)
