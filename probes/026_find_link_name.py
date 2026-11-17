"""026: does find return `name` in entity link dicts, and is it the target's cached_display_name."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)

# (target type, entity type, field)
LINKS = [
    ("ApiUser", "Version", "created_by"),
    ("ApiUser", "Note", "created_by"),
    ("HumanUser", "Version", "user"),
    ("HumanUser", "Task", "task_assignees"),
    ("ClientUser", "Note", "created_by"),
    ("ClientUser", "Version", "created_by"),
    ("Step", "Task", "step"),
    ("PublishedFileType", "PublishedFile", "published_file_type"),
    ("Task", "Version", "sg_task"),
    ("Task", "Note", "tasks"),
    ("Note", "Version", "notes"),
    ("Note", "Reply", "entity"),
    ("Version", "PublishedFile", "version"),
    ("Version", "Playlist", "versions"),
    ("Playlist", "Version", "playlists"),
    ("Tag", "Version", "tags"),
    ("Tag", "Shot", "tags"),
    ("Project", "Version", "project"),
    ("Shot", "Version", "entity"),
    ("Asset", "Task", "entity"),
    ("Group", "Note", "addressings_to"),
    ("Group", "HumanUser", "groups"),
    ("Tag", "Asset", "tags"),
    ("Tag", "Task", "tags"),
    ("Tag", "Note", "tags"),
    ("Department", "HumanUser", "department"),
    ("Sequence", "Shot", "sg_sequence"),
    ("Delivery", "Version", "entity"),
]


def data_type(entity_type, field):
    r = _lib.ask(sg.schema_field_read, entity_type, field)
    return r["ok"][field]["data_type"]["value"] if "ok" in r else r["message"].splitlines()[0]


answers = {}
for target, entity_type, field in LINKS:
    label = "%s.%s -> %s" % (entity_type, field, target)
    dt = data_type(entity_type, field)
    rows = _lib.ask(sg.find, entity_type, [[field, "type_is", target]], [field], limit=20)
    if "ok" not in rows:
        answers[label] = {"data_type": dt, "find": rows}
        continue
    links = []
    for r in rows["ok"]:
        value = r[field]
        for link in (value if isinstance(value, list) else [value]):
            if link and link["type"] == target:
                links.append(link)
    if not links:
        answers[label] = {"data_type": dt, "links read": 0,
                          "%s rows on the site" % target: _lib.ask(lambda: len(sg.find(target, [], ["id"], limit=50)))}
        continue
    ids = sorted({link["id"] for link in links})
    ident = ["subject", "content"] if target == "Note" else []
    targets = {t["id"]: t for t in sg.find(target, [["id", "in", ids]], ["cached_display_name"] + ident)}
    cdn = {i: t.get("cached_display_name") for i, t in targets.items()}
    answers[label] = {
        "data_type": dt,
        "links read": len(links),
        "dict keys": sorted({",".join(sorted(link.keys())) for link in links}),
        "name null": sum(1 for link in links if link.get("name") is None),
        "name == cached_display_name": sum(1 for link in links if link.get("name") == cdn.get(link["id"])),
        "differ": [dict({"name": link.get("name"), "cached_display_name": cdn.get(link["id"])},
                        **{f: targets.get(link["id"], {}).get(f) for f in ident})
                   for link in links if link.get("name") != cdn.get(link["id"])][:3],
        "example name": links[0].get("name"),
    }
_lib.emit("026_find_link_name", answers, env, sg)
