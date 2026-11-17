"""How entity, multi_entity and dotted-link filters match unset rows, which values they refuse, and
whether a refused filter on an empty query still faults.

Writes, with `--write`, in the sandbox project: a Sequence, a Shot in it, an Asset, three Versions
(entity set to the Shot, to the Asset, unset) and three Notes (note_links to the Shot, to the Asset,
none). No Note is addressed to anyone. Every row is deleted at the end.

Answers are labels of the rows each filter matched, scoped to those rows, or the exception raised.
"""
import sys

import shotgun_api3
import shotgun_api3.shotgun as api3

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import _lib  # noqa: E402

PREFIX = "zzprobe_mockgun_010_"


def version_cases(shot, asset):
    """(label, filters) on Version, each ANDed with the scope filters."""
    x = {"type": "Shot", "id": shot["id"]}
    return [
        ("entity is None", [["entity", "is", None]]),
        ("entity is_not None", [["entity", "is_not", None]]),
        ("entity is_not Shot", [["entity", "is_not", x]]),
        ("entity type_is None", [["entity", "type_is", None]]),
        ("entity type_is_not None", [["entity", "type_is_not", None]]),
        ("entity type_is Shot", [["entity", "type_is", "Shot"]]),
        ("entity type_is_not Shot", [["entity", "type_is_not", "Shot"]]),
        ("entity not_in [Shot]", [["entity", "not_in", [x]]]),
        ("entity in [Shot]", [["entity", "in", [x]]]),
        ("entity name_not_contains x", [["entity", "name_not_contains", "x"]]),
        ("entity name_not_contains <shot code>", [["entity", "name_not_contains", shot["code"]]]),
        ("entity name_is None", [["entity", "name_is", None]]),
        ("entity name_contains None", [["entity", "name_contains", None]]),
        ("entity name_not_contains None", [["entity", "name_not_contains", None]]),
        ("entity.Shot.code is None", [["entity.Shot.code", "is", None]]),
        ("entity.Shot.code is_not None", [["entity.Shot.code", "is_not", None]]),
        ("entity.Shot.code is_not x", [["entity.Shot.code", "is_not", "x"]]),
        ("entity.Shot.code not_in [x]", [["entity.Shot.code", "not_in", ["x"]]]),
        ("entity.Shot.code not_contains x", [["entity.Shot.code", "not_contains", "x"]]),
        ("entity.Asset.code is None", [["entity.Asset.code", "is", None]]),
    ]


def note_cases(shot, asset):
    """(label, filters) on Note, each ANDed with the scope filters."""
    s = {"type": "Shot", "id": shot["id"]}
    a = {"type": "Asset", "id": asset["id"]}
    return [
        ("note_links is Shot", [["note_links", "is", s]]),
        ("note_links is [Shot, Asset]", [["note_links", "is", [s, a]]]),
        ("note_links is None", [["note_links", "is", None]]),
        ("note_links is_not None", [["note_links", "is_not", None]]),
        ("note_links is_not Shot", [["note_links", "is_not", s]]),
        ("note_links in [Shot]", [["note_links", "in", [s]]]),
        ("note_links in [Shot, Asset]", [["note_links", "in", [s, a]]]),
        ("note_links not_in [Shot]", [["note_links", "not_in", [s]]]),
        ("note_links not_in [Shot, Asset]", [["note_links", "not_in", [s, a]]]),
        ("note_links type_is Shot", [["note_links", "type_is", "Shot"]]),
        ("note_links type_is_not Shot", [["note_links", "type_is_not", "Shot"]]),
        ("note_links type_is None", [["note_links", "type_is", None]]),
        ("note_links type_is_not None", [["note_links", "type_is_not", None]]),
        ("note_links name_is <shot code>", [["note_links", "name_is", shot["code"]]]),
        ("note_links name_contains <shot suffix>", [["note_links", "name_contains", "shot"]]),
        ("note_links name_not_contains <shot suffix>", [["note_links", "name_not_contains", "shot"]]),
        ("note_links name_not_contains x", [["note_links", "name_not_contains", "x"]]),
        ("note_links name_is None", [["note_links", "name_is", None]]),
        ("note_links in []", [["note_links", "in", []]]),
        ("note_links not_in []", [["note_links", "not_in", []]]),
        ("note_links.Shot.code is None", [["note_links.Shot.code", "is", None]]),
        ("note_links.Shot.code is_not None", [["note_links.Shot.code", "is_not", None]]),
        ("note_links.Shot.code is_not x", [["note_links.Shot.code", "is_not", "x"]]),
        ("note_links.Shot.sg_sequence.Sequence.code is_not None",
         [["note_links.Shot.sg_sequence.Sequence.code", "is_not", None]]),
        ("note_links.Shot.sg_sequence.Sequence.code is None",
         [["note_links.Shot.sg_sequence.Sequence.code", "is", None]]),
    ]


def empty_query_cases():
    """(label, entity type, filters): a refused filter ANDed with `id is 0`, which matches no row."""
    none = ["id", "is", 0]
    return [
        ("Version id is 0 alone", "Version", [none]),
        ("Version id is 0 + entity bogus_op", "Version", [none, ["entity", "bogus_op", "x"]]),
        ("Version id is 0 + zz_nope is x", "Version", [none, ["zz_nope", "is", "x"]]),
        ("Version id is 0 + entity name_is None", "Version", [none, ["entity", "name_is", None]]),
        ("Note id is 0 + note_links.Booking.code is x", "Note", [none, ["note_links.Booking.code", "is", "x"]]),
        ("Note id is 0 + note_links bogus_op", "Note", [none, ["note_links", "bogus_op", "x"]]),
        ("Note id is 0 OR note_links.Booking.code is x", "Note",
         {"filter_operator": "any", "filters": [none, ["note_links.Booking.code", "is", "x"]]}),
    ]


def date_cases():
    """(label, filters) on Version.created_at; every probe row was created seconds ago."""
    f = "created_at"
    return [
        ("in_last 1, DAY as two args", [[f, "in_last", 1, "DAY"]]),
        ("in_last [1, DAY]", [[f, "in_last", [1, "DAY"]]]),
        ("not_in_last [1, DAY]", [[f, "not_in_last", [1, "DAY"]]]),
        ("in_next [1, DAY]", [[f, "in_next", [1, "DAY"]]]),
        ("not_in_next [1, DAY]", [[f, "not_in_next", [1, "DAY"]]]),
        ("in_last [1, HOUR]", [[f, "in_last", [1, "HOUR"]]]),
        ("in_last [1, WEEK]", [[f, "in_last", [1, "WEEK"]]]),
        ("in_last [1, MONTH]", [[f, "in_last", [1, "MONTH"]]]),
        ("in_last [1, YEAR]", [[f, "in_last", [1, "YEAR"]]]),
        ("in_last [1, MINUTE]", [[f, "in_last", [1, "MINUTE"]]]),
        ("in_last [1, day]", [[f, "in_last", [1, "day"]]]),
        ("in_last [0, DAY]", [[f, "in_last", [0, "DAY"]]]),
        ("in_last [-1, DAY]", [[f, "in_last", [-1, "DAY"]]]),
        ("in_last [1.5, DAY]", [[f, "in_last", [1.5, "DAY"]]]),
        ("in_last [\"1\", DAY]", [[f, "in_last", ["1", "DAY"]]]),
        ("in_last 1", [[f, "in_last", 1]]),
        ("in_last [DAY, 1]", [[f, "in_last", ["DAY", 1]]]),
        ("in_calendar_day 0", [[f, "in_calendar_day", 0]]),
        ("in_calendar_day [0]", [[f, "in_calendar_day", [0]]]),
        ("in_calendar_day -1", [[f, "in_calendar_day", -1]]),
        ("in_calendar_day 1", [[f, "in_calendar_day", 1]]),
        ("in_calendar_week 0", [[f, "in_calendar_week", 0]]),
        ("in_calendar_month 0", [[f, "in_calendar_month", 0]]),
        ("in_calendar_year 0", [[f, "in_calendar_year", 0]]),
        ("in_calendar_year -1", [[f, "in_calendar_year", -1]]),
        ("in_calendar_day [0, DAY]", [[f, "in_calendar_day", [0, "DAY"]]]),
        ("in_calendar_day \"0\"", [[f, "in_calendar_day", "0"]]),
        ("in_calendar_day None", [[f, "in_calendar_day", None]]),
    ]


def payloads():
    """The `conditions` api3 builds for each relative date filter, before any request."""
    out = {}
    for label, filters in date_cases():
        out[label] = api3._translate_filters(filters, "all")["conditions"]
    for label, filters in [("multi_entity in []", [["note_links", "in", []]]),
                           ("multi_entity is [A, B]", [["note_links", "is", [{"type": "Shot", "id": 1},
                                                                             {"type": "Asset", "id": 2}]]])]:
        out[label] = _lib.ask(api3._translate_filters, filters, "all")
    return out


def matched(sg, entity_type, scope, filters, labels):
    """Row labels a filter matched within the scope, or the exception."""
    answer = _lib.ask(sg.find, entity_type, scope + filters, ["id"])
    if "ok" in answer:
        return sorted(labels.get(r["id"], "other:%s" % r["id"]) for r in answer["ok"])
    return answer


def unoptimized(fn, *args):
    """Call with api3's entity payload optimisation off, which skips its `values[0]` index."""
    api3.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION = True
    try:
        return _lib.ask(fn, *args)
    finally:
        api3.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION = False


def main():
    env = _lib.load_env()
    answers = {"payloads": payloads()}
    if not _lib.writes_allowed():
        _lib.emit("010_filter_links (payloads only, run with --write)", answers, env)
        return
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    with _lib.Created(sg) as made:
        seq = made.add(sg.create("Sequence", {"project": project, "code": PREFIX + "seq"}))
        shot = made.add(sg.create("Shot", {"project": project, "code": PREFIX + "shot", "sg_sequence": seq}))
        asset = made.add(sg.create("Asset", {"project": project, "code": PREFIX + "asset"}))
        vlabels, nlabels = {}, {}
        for label, link in (("v_shot", shot), ("v_asset", asset), ("v_none", None)):
            row = made.add(sg.create("Version", {"project": project, "code": PREFIX + label, "entity": link}))
            vlabels[row["id"]] = label
        for label, links in (("n_shot", [shot]), ("n_asset", [asset]), ("n_none", [])):
            row = made.add(sg.create("Note", {"project": project, "subject": PREFIX + label,
                                              "content": "probe row", "note_links": links}))
            nlabels[row["id"]] = label

        vscope = [["project", "is", project], ["code", "starts_with", PREFIX]]
        nscope = [["project", "is", project], ["subject", "starts_with", PREFIX]]
        answers["version"] = {k: matched(sg, "Version", vscope, f, vlabels) for k, f in version_cases(shot, asset)}
        answers["note"] = {k: matched(sg, "Note", nscope, f, nlabels) for k, f in note_cases(shot, asset)}
        answers["note unoptimized"] = {
            "note_links in []": unoptimized(sg.find, "Note", nscope + [["note_links", "in", []]], ["id"]),
            "note_links not_in []": unoptimized(sg.find, "Note", nscope + [["note_links", "not_in", []]], ["id"]),
        }
        answers["empty query"] = {}
        for k, entity_type, f in empty_query_cases():
            if isinstance(f, dict):
                answers["empty query"][k] = _lib.ask(sg.find, entity_type, f["filters"], ["id"],
                                                     filter_operator=f["filter_operator"])
            else:
                answers["empty query"][k] = _lib.ask(sg.find, entity_type, f, ["id"])
        answers["date_time"] = {k: matched(sg, "Version", vscope, f, vlabels) for k, f in date_cases()}
        _lib.emit("010_filter_links", answers, env, sg)


if __name__ == "__main__":
    main()
