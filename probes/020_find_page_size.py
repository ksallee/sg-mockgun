"""020: how many rows one find page returns, what limit=0 does, and which part is client-side."""
import datetime

import _lib

env = _lib.load_env()
sg = _lib.client(env)
info = sg.info()
since = datetime.datetime.now() - datetime.timedelta(days=30)
filters = [["created_at", "greater_than", since]]


def count(**kw):
    r = _lib.ask(sg.find, "EventLogEntry", filters, ["id"], **kw)
    return len(r["ok"]) if "ok" in r else r


def raw(paging, **extra):
    params = {
        "type": "EventLogEntry",
        "return_fields": ["id"],
        "filters": {"logical_operator": "and", "conditions": [
            {"path": "created_at", "relation": "greater_than", "values": [since]}]},
        "return_only": "active",
        "return_paging_info": True,
    }
    if paging is not None:
        params["paging"] = paging
    params.update(extra)
    r = _lib.ask(sg._call_rpc, "read", params)
    if "ok" not in r:
        return r
    out = {"rows": len(r["ok"].get("entities", [])), "keys": sorted(r["ok"].keys())}
    if "paging_info" in r["ok"]:
        out["paging_info"] = r["ok"]["paging_info"]
    return out


answers = {
    "server_info api_max_entities_per_page": info.get("api_max_entities_per_page"),
    "client records_per_page": sg.config.records_per_page,
    "summarize count": sg.summarize("EventLogEntry", filters, [{"field": "id", "type": "count"}])["summaries"],
    "find page=1": count(page=1),
    "find page=2": count(page=2),
    "find no page no limit": count(),
    "find limit=0": count(limit=0),
    "find limit=0 page=1": count(limit=0, page=1),
    "find limit=10": count(limit=10),
    "find limit=501": count(limit=501),
    "find limit=-1": count(limit=-1),
    "find page=-1": count(page=-1),
    "find page=0 limit=5": count(page=0, limit=5),
    "raw no paging": raw(None),
    "raw paging current_page=1 only": raw({"current_page": 1}),
    "raw entities_per_page=0": raw({"entities_per_page": 0, "current_page": 1}),
    "raw entities_per_page=500": raw({"entities_per_page": 500, "current_page": 1}),
    "raw entities_per_page=501": raw({"entities_per_page": 501, "current_page": 1}),
    "raw entities_per_page=5000": raw({"entities_per_page": 5000, "current_page": 1}),
    "raw entities_per_page=5001": raw({"entities_per_page": 5001, "current_page": 1}),
    "client paging param": "return_paging_info_without_counts" if sg.server_caps.ensure_paging_info_without_counts_support() else "return_paging_info",
    "raw without_counts epp=5000 page 1": raw({"entities_per_page": 5000, "current_page": 1}, return_paging_info=False, return_paging_info_without_counts=True),
    "raw current_page=0": raw({"entities_per_page": 10, "current_page": 0}),
}
_lib.emit("020_find_page_size", answers, env, sg)
