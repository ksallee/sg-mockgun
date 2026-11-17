"""EventLogEntry rows a script's writes add, as recorded over api3 in docs/api3-probe-2026-11-12.md."""

import pytest

API3 = "docs/api3-probe-2026-11-12.md"
FIELDS = ["event_type", "attribute_name", "meta", "entity", "description"]


def head(site):
    return site.find_one("EventLogEntry", [], ["id"], order=[{"field_name": "id", "direction": "desc"}])["id"]


def events(site, start, entity_type, entity_id):
    """Rows after ``start`` about one entity, matched on meta.entity_id, which a delete leaves in place."""
    rows = site.find("EventLogEntry", [["id", "greater_than", start], ["event_type", "starts_with", "Shotgun_%s_" % entity_type]],
                     FIELDS, order=[{"field_name": "id", "direction": "asc"}])
    rows = [r for r in rows if (r["meta"] or {}).get("entity_id") == entity_id]
    if not rows:
        pytest.skip("No events logged. The script's ApiUser has generate_event_log_entries off (finding 049).")
    return rows


@pytest.mark.finding("049", api3=API3)
def test_create_logs_new_then_a_change_per_field(site, made, sandbox, run_token):
    start = head(site)
    code = "zzconf_%s_log_create" % run_token
    v = made.create("Version", {"code": code, "description": "probe", "project": sandbox})
    rows = events(site, start, "Version", v["id"])
    assert rows[0]["event_type"] == "Shotgun_Version_New"
    assert rows[0]["meta"]["type"] == "new_entity" and rows[0]["meta"]["entity_type"] == "Version"
    assert rows[0]["description"].endswith(" created new Version ")
    by_field = dict((r["attribute_name"], r) for r in rows[1:])
    assert set(r["event_type"] for r in rows[1:]) == {"Shotgun_Version_Change"}
    meta = by_field["code"]["meta"]
    assert (meta["in_create"], meta["old_value"], meta["new_value"], meta["field_data_type"]) == (True, None, code, "text")


@pytest.mark.finding("025", api3=API3)
def test_update_logs_only_changed_fields(site, made, sandbox, run_token):
    v = made.create("Version", {"code": "zzconf_%s_log_update" % run_token, "description": "probe",
                                "sg_status_list": "rev", "project": sandbox})
    start = head(site)
    made.update("Version", v["id"], {"description": "probe 2", "sg_status_list": "rev"})
    rows = events(site, start, "Version", v["id"])
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [("Shotgun_Version_Change", "description")]
    assert (rows[0]["meta"]["old_value"], rows[0]["meta"]["new_value"]) == ("probe", "probe 2")
    assert "in_create" not in rows[0]["meta"]


@pytest.mark.finding("049", api3=API3)
def test_delete_and_revive(site, made, sandbox, run_token):
    code = "zzconf_%s_log_retire" % run_token
    v = made.create("Version", {"code": code, "project": sandbox})
    start = head(site)
    made.delete("Version", v["id"])
    made.revive("Version", v["id"])
    rows = events(site, start, "Version", v["id"])
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [
        ("Shotgun_Version_Change", "retirement_date"),
        ("Shotgun_Version_Retirement", None),
        ("Shotgun_Version_Change", "retirement_date"),
        ("Shotgun_Version_Revival", None),
    ]
    assert rows[0]["meta"]["old_value"] is None and rows[0]["meta"]["new_value"]
    assert rows[1]["meta"]["type"] == "entity_retirement" and rows[1]["meta"]["display_name"] == code
    assert rows[1]["description"] == ' retired Version "%s"' % code
    assert rows[2]["meta"]["new_value"] is None
    assert rows[3]["meta"]["type"] == "entity_revival" and rows[3]["description"] == ' revived Version "%s"' % code


@pytest.mark.finding("049", api3=API3)
def test_delete_drops_the_entity_link_from_earlier_rows(site, made, sandbox, run_token):
    start = head(site)
    v = made.create("Version", {"code": "zzconf_%s_log_orphan" % run_token, "project": sandbox})
    made.delete("Version", v["id"])
    assert events(site, start, "Version", v["id"])
    link = {"type": "Version", "id": v["id"]}
    assert site.find("EventLogEntry", [["id", "greater_than", start], ["entity", "is", link]], ["id"]) == []


@pytest.mark.finding("049", api3=API3)
def test_batch_logs_as_single_writes_do(site, made, sandbox, run_token):
    start = head(site)
    code = "zzconf_%s_log_batch" % run_token
    v = made.batch([{"request_type": "create", "entity_type": "Version", "data": {"code": code, "project": sandbox}}])[0]
    rows = events(site, start, "Version", v["id"])
    assert rows[0]["event_type"] == "Shotgun_Version_New"
    assert "code" in [r["attribute_name"] for r in rows[1:]]


@pytest.mark.finding("025", api3=API3)
@pytest.mark.cell("schema_field_update", "-", "text")
def test_schema_writes_log_display_column_rows(site, fields, run_token):
    start = head(site)
    name = "zzprobe mockgun %s log" % run_token
    code = fields.create("Version", "text", name)
    fields.update("Version", code, {"name": name + " renamed"})
    fields.delete("Version", code)
    rows = site.find("EventLogEntry", [["id", "greater_than", start], ["event_type", "starts_with", "Shotgun_DisplayColumn_"]],
                     FIELDS, order=[{"field_name": "id", "direction": "asc"}])
    rows = [r for r in rows if code in (r["description"] or "") and r["attribute_name"] != "properties"]
    if not rows:
        pytest.skip("No events logged. The script's ApiUser has generate_event_log_entries off (finding 049).")
    assert [(r["event_type"], r["attribute_name"]) for r in rows] == [
        ("Shotgun_DisplayColumn_New", None),
        ("Shotgun_DisplayColumn_Change", "human_name"),
        ("Shotgun_DisplayColumn_Change", "retirement_date"),
        ("Shotgun_DisplayColumn_Retirement", None),
    ]
    assert rows[0]["description"].endswith(" created new Field %s" % code)
    assert (rows[1]["meta"]["old_value"], rows[1]["meta"]["new_value"]) == (name, name + " renamed")
    assert rows[3]["meta"]["display_name"] == code
