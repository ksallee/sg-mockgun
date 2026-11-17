"""Whether text `is` and list `is` match a value whose case was changed."""
import _lib


def count(sg, entity_type, filters):
    return len(sg.find(entity_type, filters, ["id"]))


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    answers = {}
    shot = sg.find_one("Shot", [["code", "is_not", None]], ["code"], order=[{"field_name": "id", "direction": "asc"}])
    code = shot["code"]
    for label, value in (("as read", code), ("upper", code.upper()), ("swapcase", code.swapcase())):
        answers["Shot.code is, %s" % label] = count(sg, "Shot", [["code", "is", value]])
        answers["Shot.code in, %s" % label] = count(sg, "Shot", [["code", "in", [value]]])
        answers["Shot.code starts_with, %s" % label] = count(sg, "Shot", [["code", "starts_with", value[:4]]])
    note = sg.find_one("Note", [["sg_note_type", "is_not", None]], ["sg_note_type"])
    kind = note["sg_note_type"]
    for label, value in (("as read", kind), ("upper", kind.upper()), ("lower", kind.lower())):
        answers["Note.sg_note_type is, %s" % label] = count(sg, "Note", [["sg_note_type", "is", value]])
        answers["Note.sg_note_type in, %s" % label] = count(sg, "Note", [["sg_note_type", "in", [value]]])
    status = sg.find_one("Version", [["sg_status_list", "is_not", None]], ["sg_status_list"])["sg_status_list"]
    for label, value in (("as read", status), ("upper", status.upper())):
        answers["Version.sg_status_list is, %s" % label] = count(sg, "Version", [["sg_status_list", "is", value]])
    answers["values read"] = {"Shot.code": "<code>", "Note.sg_note_type": kind, "Version.sg_status_list": status}
    _lib.emit("004_case", answers, env, sg)


if __name__ == "__main__":
    main()
