"""api3 052: export_page on pages the script can read. update_project_last_accessed is a write and is not sent."""
import collections

import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    pages = sg.find("Page", [], ["page_type", "entity_type"], limit=20,
                    order=[{"field_name": "id", "direction": "asc"}])
    canvas = next((p for p in pages if p.get("page_type") == "canvas"), pages[0])
    pid = canvas["id"]
    results = collections.Counter()
    for p in pages:
        a = _lib.ask(sg.export_page, p["id"], "csv")
        results["ok" if "ok" in a else a["message"].replace(str(p["id"]), "<id>")] += 1
    answers = {
        "pages_tried": len(pages),
        "page_types_tried": dict(collections.Counter(p.get("page_type") for p in pages)),
        "csv_by_answer": dict(results),
        "csv": _lib.ask(sg.export_page, pid, "csv"),
        "csv_layout_0": _lib.ask(sg.export_page, pid, "csv", layout_name="layout_0"),
        "csv_layout_unknown": _lib.ask(sg.export_page, pid, "csv", layout_name="zzprobe_052_not_a_view"),
        "json": _lib.ask(sg.export_page, pid, "json"),
        "format_bogus": _lib.ask(sg.export_page, pid, "bogus"),
        "format_none": _lib.ask(sg.export_page, pid, None),
        "missing_page": _lib.ask(sg.export_page, 999999999, "csv"),
        "page_id_zero": _lib.ask(sg.export_page, 0, "csv"),
        "page_id_string": _lib.ask(sg.export_page, "abc", "csv"),
        "page_id_none": _lib.ask(sg.export_page, None, "csv"),
    }
    _lib.emit("052 export_page", answers, env, sg)


if __name__ == "__main__":
    main()
