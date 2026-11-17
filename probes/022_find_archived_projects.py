"""022: is any project archived, and does include_archived_projects=False change a find."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
projects = sg.find("Project", [], ["archived", "is_template", "is_demo"])
archived = [p for p in projects if p.get("archived")]
answers = {
    "projects": len(projects),
    "archived True": len(archived),
    "archived values": sorted({repr(p.get("archived")) for p in projects}),
    "find Project include_archived_projects=False": len(sg.find("Project", [], ["id"], include_archived_projects=False)),
    "find Project archived is True": len(sg.find("Project", [["archived", "is", True]], ["id"])),
    "find Version limit 50, False vs True": [
        len(sg.find("Version", [], ["id"], limit=50, include_archived_projects=False)),
        len(sg.find("Version", [], ["id"], limit=50)),
    ],
    "summarize Version count, include_archived_projects=False": sg.summarize(
        "Version", [], [{"field": "id", "type": "count"}], include_archived_projects=False)["summaries"],
    "summarize Version count, default": sg.summarize("Version", [], [{"field": "id", "type": "count"}])["summaries"],
}
_lib.emit("022_find_archived_projects", answers, env, sg)
