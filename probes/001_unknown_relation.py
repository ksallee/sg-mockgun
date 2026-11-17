"""An unknown relation on one stock field of each data type: the exception and its message (finding 017)."""
import _lib
from _vocab import FIELDS


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    answers = {}
    for entity_type, field, data_type in FIELDS:
        got = sg.schema_field_read(entity_type, field)[field]["data_type"]["value"]
        r = _lib.ask(sg.find, entity_type, [[field, "definitely_not_an_operator", "x"]], ["id"], limit=1)
        answers["%s.%s (%s)" % (entity_type, field, got)] = r
    _lib.emit("001_unknown_relation", answers, env, sg)


if __name__ == "__main__":
    main()
