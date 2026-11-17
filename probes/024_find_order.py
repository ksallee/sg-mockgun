"""024: find order: two keys, and order on summary, url, unknown, entity and dotted fields."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
name = _lib.need(env, "FPT_PROBE_SAMPLE_PROJECTS").split(",")[0].strip()
project = sg.find_one("Project", [["name", "is", name]], ["id"])
F = [["project", "is", project]]
fields = ["code", "sg_status_list", "entity", "entity.Shot.code", "user", "created_at"]


def ids(order, **kw):
    r = _lib.ask(sg.find, "Version", F, fields, order=order, **kw)
    return [x["id"] for x in r["ok"]] if "ok" in r else r


def asc(f):
    return [{"field_name": f, "direction": "asc"}]


def desc(f):
    return [{"field_name": f, "direction": "desc"}]


default = ids(None)
by_id = ids(asc("id"))
by_id_desc = ids(desc("id"))
rows = {r["id"]: r for r in sg.find("Version", F, fields)}


def describe(got):
    if not isinstance(got, list):
        return got
    return {"== default": got == default, "== id asc": got == by_id, "== id desc": got == by_id_desc,
            "first 4": got[:4]}


def sorted_by(got, keyfn, reverse=False):
    """True when the ids are in the order keyfn gives, ties by id ascending."""
    if not isinstance(got, list):
        return got
    want = sorted(rows, key=lambda i: (keyfn(rows[i]), i))
    if reverse:
        want = sorted(rows, key=lambda i: (keyfn(rows[i]), -i), reverse=True)
    return got == want


def ent(r, part):
    e = r.get("entity") or {}
    return (e.get(part) or "") if part != "id" else (e.get("id") or 0)


answers = {"rows": len(default), "default == id asc": default == by_id}
valid = sg.schema_field_read("Version", "sg_status_list")["sg_status_list"]["properties"]["valid_values"]["value"]
rank = lambda r: valid.index(r["sg_status_list"])  # noqa: E731
answers["status valid_values"] = valid
answers["status asc, values in order"] = list(dict.fromkeys(rows[i]["sg_status_list"] for i in ids(asc("sg_status_list"))))
answers["status asc == valid_values order, ties id asc"] = ids(asc("sg_status_list")) == sorted(rows, key=lambda i: (rank(rows[i]), i))
answers["status asc == alphabetical"] = ids(asc("sg_status_list")) == sorted(rows, key=lambda i: (rows[i]["sg_status_list"], i))
answers["status desc == valid_values order reversed, ties id asc"] = ids(desc("sg_status_list")) == sorted(rows, key=lambda i: (-rank(rows[i]), i))
answers["status asc, id asc == status asc"] = ids(asc("sg_status_list") + asc("id")) == ids(asc("sg_status_list"))
answers["status asc, id desc: first 4"] = ids(asc("sg_status_list") + desc("id"))[:4]
answers["status asc, id desc == status primary, id desc tiebreak"] = (
    ids(asc("sg_status_list") + desc("id")) == sorted(rows, key=lambda i: (rank(rows[i]), -i)))
answers["id desc, status asc == id desc (first key primary)"] = ids(desc("id") + asc("sg_status_list")) == by_id_desc
answers["code asc, by code"] = sorted_by(ids(asc("code")), lambda r: (r["code"] or "").lower())
answers["code asc, by code case-sensitive"] = sorted_by(ids(asc("code")), lambda r: r["code"] or "")
answers["open_notes_count (summary) asc"] = describe(ids(asc("open_notes_count")))
answers["open_notes_count (summary) desc"] = describe(ids(desc("open_notes_count")))
answers["sg_uploaded_movie (url) asc"] = describe(ids(asc("sg_uploaded_movie")))
answers["sg_uploaded_movie (url) desc"] = describe(ids(desc("sg_uploaded_movie")))
answers["sg_not_a_field_at_all asc"] = describe(ids(asc("sg_not_a_field_at_all")))
answers["sg_not_a_field_at_all desc"] = describe(ids(desc("sg_not_a_field_at_all")))
answers["direction 'up'"] = describe(ids([{"field_name": "code", "direction": "up"}]))
answers["no direction (client fills asc)"] = sorted_by(ids([{"field_name": "code"}]), lambda r: (r["code"] or "").lower())
answers["'column' instead of field_name"] = sorted_by(ids([{"column": "code"}]), lambda r: (r["code"] or "").lower())
answers["entity types present"] = sorted({ent(r, "type") for r in rows.values()})
e_asc = ids(asc("entity"))
answers["entity asc"] = describe(e_asc)
answers["entity asc sorted by entity name"] = sorted_by(e_asc, lambda r: ent(r, "name").lower())
answers["entity asc sorted by entity id"] = sorted_by(e_asc, lambda r: ent(r, "id"))
answers["entity asc sorted by (entity type, name)"] = sorted_by(e_asc, lambda r: (ent(r, "type"), ent(r, "name").lower()))
answers["entity desc sorted by entity name desc"] = sorted_by(ids(desc("entity")), lambda r: ent(r, "name").lower(), reverse=True)
answers["entity asc, entity name sequence"] = [ent(rows[i], "name") for i in e_asc][:12]
d_asc = ids(asc("entity.Shot.code"))
answers["entity.Shot.code asc"] = describe(d_asc)
answers["entity.Shot.code asc, values in order"] = [rows[i]["entity.Shot.code"] for i in d_asc][:12]
answers["entity.Shot.code desc, values in order"] = [rows[i]["entity.Shot.code"] for i in ids(desc("entity.Shot.code"))][:12]
answers["entity.Shot.nope asc"] = describe(ids(asc("entity.Shot.nope")))
answers["user (HumanUser link) asc, names in order"] = [(rows[i]["user"] or {}).get("name") for i in ids(asc("user"))][:6]
_lib.emit("024_find_order", answers, env, sg)
