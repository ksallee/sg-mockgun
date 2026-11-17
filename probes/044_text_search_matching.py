"""api3 044: what a text_search() word is matched against: case, prefix or substring, several words, links."""
import _lib

TEXTS = [
    "sq010", "SQ010", "Sq010",
    "010", "h01", "q01", "0_s",
    "sq010_sh020", "_sh0",
    "sq010 sh020", "sh020 sq010", "sq010  sh020", "  sq010  ",
    "sq010 kitchen", "sq010 zzznotaword",
    "kitchen", "itche", "KITCHEN",
    "flickers", "banister", "matte painting",
    "sq010 x", "sq0*", "sq0%", "demo-01", "demo 01",
]


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    pid = [project["id"]]
    answers = {}
    for text in TEXTS:
        r = _lib.ask(sg.text_search, text, {"Shot": [], "Asset": []}, project_ids=pid, limit=100)
        if "ok" in r:
            answers[repr(text)] = {"terms": r["ok"]["terms"], "names": [m["name"] for m in r["ok"]["matches"]]}
        else:
            answers[repr(text)] = r
    # A row matches on the name of the row it links to (finding 053).
    for text, types in (("sbx_charA", {"Version": [], "Task": []}), ("charA", {"Task": []})):
        r = _lib.ask(sg.text_search, text, types, project_ids=pid, limit=100)
        answers["%r over %s" % (text, sorted(types))] = r if "ok" not in r else [
            {"type": m["type"], "own_name_holds_text": text.lower() in m["name"].lower(), "links": m["links"]}
            for m in r["ok"]["matches"]]
    _lib.emit("044_text_search_matching", answers, env, sg)


if __name__ == "__main__":
    main()
