"""schema_field_read("Shot") with and without project_entity: `visible` per field, and `hidden_values`."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
proj = _lib.sandbox(sg, env)
site = sg.schema_field_read("Shot")
scoped = sg.schema_field_read("Shot", project_entity=proj)
bad = _lib.ask(sg.schema_field_read, "Shot", project_entity={"type": "Project", "id": 999999999})


def vis(s):
    return {f: v["visible"]["value"] for f, v in s.items()}


vs, vp = vis(site), vis(scoped)
out = {
    "field count site / project": [len(site), len(scoped)],
    "visible false, site": sorted(f for f, v in vs.items() if not v),
    "visible false, project": sorted(f for f, v in vp.items() if not v),
    "visible shape, one field, project": scoped["code"]["visible"],
    "visible shape, one field, site": site["code"]["visible"],
    "visible shape, hidden field, project": scoped["sg_reel"]["visible"],
    "property keys differing": sorted({(f, k) for f in site for k in site[f]["properties"] if site[f]["properties"][k] != scoped[f]["properties"].get(k)}),
    "other keys differing": sorted({k for f in site for k in site[f] if f in scoped and k != "visible" and site[f][k] != scoped[f][k]}),
    "sg_status_list hidden_values site": site["sg_status_list"]["properties"].get("hidden_values"),
    "sg_status_list hidden_values project": scoped["sg_status_list"]["properties"].get("hidden_values"),
    "valid_values equal": site["sg_status_list"]["properties"]["valid_values"] == scoped["sg_status_list"]["properties"]["valid_values"],
    "valid_values": site["sg_status_list"]["properties"]["valid_values"],
    "one field read, project": _lib.ask(lambda: sg.schema_field_read("Shot", "sg_status_list", project_entity=proj)["sg_status_list"]["properties"]["hidden_values"]),
    "unknown project id": ("raised " + bad["raised"] + ": " + bad["message"]) if "raised" in bad else {
        "visible false": sorted(f for f, v in vis(bad["ok"]).items() if not v),
        "hidden_values": bad["ok"]["sg_status_list"]["properties"].get("hidden_values")},
}
_lib.emit("064_schema_per_project", out, env, sg)
