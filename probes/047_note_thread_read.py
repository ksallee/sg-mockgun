"""api3 047: note_thread_read on a Note with replies and attachments, and the entity_fields argument."""
import _lib


def keys_by_type(rows):
    """Sorted keys of the first row of each type, and the order of types in the list."""
    shapes = {}
    for row in rows:
        shapes.setdefault(row.get("type"), sorted(row))
    return shapes


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    note = None
    replies = sg.find("Reply", [["entity", "type_is", "Note"]], ["entity"], limit=200,
                      order=[{"field_name": "id", "direction": "desc"}])
    for note_id in sorted({r["entity"]["id"] for r in replies if r.get("entity")}, reverse=True):
        row = sg.find_one("Note", [["id", "is", note_id], ["attachments", "is_not", None]], ["attachments"])
        if row:
            note = row
            break
    if note is None and replies:
        note = {"type": "Note", "id": replies[0]["entity"]["id"], "attachments": []}
    nid = note["id"]
    plain = sg.note_thread_read(nid)
    wide = sg.note_thread_read(nid, entity_fields={
        "Note": ["subject", "note_links", "created_by.HumanUser.login"],
        "Reply": ["entity", "created_by"],
        "Attachment": ["this_file", "filename", "file_size"],
    })
    answers = {
        "note_has_attachments": len(note.get("attachments") or []),
        "plain_len": len(plain),
        "plain_types_in_order": [r.get("type") for r in plain],
        "plain_created_at_in_order": [str(r.get("created_at")) for r in plain],
        "plain_created_at_python_type": type(plain[0].get("created_at")).__name__ if plain else None,
        "plain_keys": keys_by_type(plain),
        "plain_author_link_keys": {r["type"]: sorted((r.get("created_by") or r.get("user") or {}).keys()) for r in plain},
        "wide_keys": keys_by_type(wide),
        "wide_attachment_this_file_keys": sorted((next((r for r in wide if r["type"] == "Attachment"), {}).get("this_file") or {}).keys()),
        "unknown_field": _lib.ask(sg.note_thread_read, nid, entity_fields={"Note": ["sg_not_a_field"]}),
        "unknown_type_key": _lib.ask(sg.note_thread_read, nid, entity_fields={"Bogus": ["code"]}),
        "missing_note": _lib.ask(sg.note_thread_read, 999999999),
        "note_id_zero": _lib.ask(sg.note_thread_read, 0),
        "note_id_string": _lib.ask(sg.note_thread_read, "abc"),
        "entity_fields_list": _lib.ask(sg.note_thread_read, nid, entity_fields=["subject"]),
        "entity_fields_value_string": _lib.ask(sg.note_thread_read, nid, entity_fields={"Note": "subject"}),
        "raw_rpc_answer_type": type(sg._call_rpc("note_thread_contents", {"note_id": nid, "entity_fields": {}})).__name__,
    }
    _lib.emit("047 note_thread_read", answers, env, sg)


if __name__ == "__main__":
    main()
