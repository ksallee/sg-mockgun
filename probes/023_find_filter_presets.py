"""023: additional_filter_presets: which rows LATEST keeps, and the Faults for bad presets."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)


def key(v):
    return v["id"] if isinstance(v, dict) else v


def latest(entity_type, latest_by, **kw):
    preset = [{"preset_name": "LATEST", "latest_by": latest_by}]
    return _lib.ask(lambda: {r["id"] for r in sg.find(entity_type, [], ["id"], additional_filter_presets=preset, **kw)})


def predict(rows, group_fields, sort_key):
    """Newest row per group, rows with a null group field skipped."""
    groups = {}
    for r in rows:
        k = tuple(key(r.get(f)) for f in group_fields)
        if None in k:
            continue
        groups.setdefault(k, []).append(r)
    return {max(v, key=sort_key)["id"] for v in groups.values()}


def compare(got, want):
    if "ok" not in got:
        return got
    return {"rows": len(got["ok"]), "predicted": len(want), "missing": sorted(want - got["ok"]),
            "extra": sorted(got["ok"] - want)}


answers = {}
by_created = lambda r: (r["created_at"], r["id"])  # noqa: E731

pf_group = ["entity", "task", "published_file_type", "name"]
pf = sg.find("PublishedFile", [], ["created_at"] + pf_group)
answers["PublishedFile rows"] = len(pf)
answers["PublishedFile rows with a null in (entity, task, published_file_type, name)"] = sum(
    1 for r in pf if None in tuple(key(r.get(f)) for f in pf_group))
answers["PublishedFile LATEST ENTITIES_CREATED_AT vs newest per (entity, task, published_file_type, name)"] = compare(
    latest("PublishedFile", "ENTITIES_CREATED_AT"), predict(pf, pf_group, by_created))

steps = {s["id"]: s.get("list_order") or 0 for s in sg.find("Step", [], ["list_order"])}
ver = sg.find("Version", [], ["created_at", "entity", "sg_task.Task.step"])
answers["Version rows"] = len(ver)
answers["Version rows with null entity"] = sum(1 for r in ver if not r.get("entity"))
answers["Version LATEST ENTITIES_CREATED_AT vs newest per entity"] = compare(
    latest("Version", "ENTITIES_CREATED_AT"), predict(ver, ["entity"], by_created))
answers["Version LATEST BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT vs per entity, max (step list_order, created_at)"] = compare(
    latest("Version", "BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT"),
    predict(ver, ["entity"], lambda r: (steps.get(key(r.get("sg_task.Task.step")), -1), r["created_at"], r["id"])))

for latest_by in ("BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT", "ENTITY_CREATED_AT", "NOPE"):
    answers["PublishedFile LATEST latest_by %s" % latest_by] = latest("PublishedFile", latest_by)
answers["PublishedFile LATEST, no latest_by"] = _lib.ask(
    sg.find, "PublishedFile", [], ["id"], additional_filter_presets=[{"preset_name": "LATEST"}])
answers["PublishedFile LATEST ENTITIES_CREATED_AT with a filter, limit 5"] = _lib.ask(
    lambda: len(sg.find("PublishedFile", [["entity", "is_not", None]], ["id"], limit=5,
                        additional_filter_presets=[{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}])))
answers["Shot LATEST ENTITIES_CREATED_AT"] = _lib.ask(
    lambda: len(sg.find("Shot", [], ["id"], limit=5,
                        additional_filter_presets=[{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}])))
answers["unknown preset_name"] = _lib.ask(
    sg.find, "PublishedFile", [], ["id"], additional_filter_presets=[{"preset_name": "NOPE"}])
answers["a string, not a dict"] = _lib.ask(
    sg.find, "PublishedFile", [], ["id"], additional_filter_presets=["LATEST"])
for k, v in answers.items():
    if isinstance(v, dict) and "ok" in v and isinstance(v["ok"], set):
        answers[k] = {"ok": "%d rows" % len(v["ok"])}
_lib.emit("023_find_filter_presets", answers, env, sg)
