"""Every relation in the union of the REST `Valid relations` lists, on one stock field per data type."""
import _lib
from _vocab import EXTRA, FIELDS, UNION, value_for


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    answers = {}
    for entity_type, field, data_type in FIELDS:
        row = {"accepted": [], "refused": [], "value_refused": {}}
        for relation in UNION + EXTRA:
            r = _lib.ask(sg.find, entity_type, [[field, relation, value_for(relation, data_type)]], ["id"], limit=1)
            if "ok" in r:
                row["accepted"].append(relation)
            elif "doesn't support" in r["message"] or "cannot be used in a filter" in r["message"]:
                row["refused"].append(relation)
            else:
                row["value_refused"][relation] = r["message"][:300]
        answers["%s.%s (%s)" % (entity_type, field, data_type)] = row
    _lib.emit("002_relations_per_type", answers, env, sg)


if __name__ == "__main__":
    main()
