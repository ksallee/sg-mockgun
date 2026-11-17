"""Defaults on create, text writes and entity link shape in returned rows."""

import pytest

from sg_mockgun import Shotgun, schemas


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="x", api_key="y")


@pytest.fixture
def project(sg):
    return sg.create("Project", {"name": "sandbox"})


def read(sg, entity_type, entity_id, fields):
    return sg.find_one(entity_type, [["id", "is", entity_id]], fields)


# Defaults on create


def test_untouched_checkbox_reads_false(sg, project):
    # field_types/checkbox: the bundled schema stores None, the site reads False.
    v = sg.create("Version", {"code": "v001", "project": project})
    assert read(sg, "Version", v["id"], ["flagged"])["flagged"] is False
    assert read(sg, "Project", project["id"], ["archived"])["archived"] is False


def test_unset_scalars_read_none(sg, project):
    # field_types/text, number, date
    v = sg.create("Version", {"code": "v001", "project": project})
    row = read(sg, "Version", v["id"], ["sg_department", "frame_count"])
    assert row["sg_department"] is None
    assert row["frame_count"] is None
    t = sg.create("Task", {"content": "comp", "project": project})
    assert read(sg, "Task", t["id"], ["due_date"])["due_date"] is None


def test_empty_text_default_reads_none(sg):
    # field_types/text: the schema stores "" on HumanUser.email.
    u = sg.create("HumanUser", {"name": "Ann", "login": "ann"})
    assert read(sg, "HumanUser", u["id"], ["email"])["email"] is None


def test_numeric_string_default_reads_int(sg, project):
    # entity_types/Playlist: a create reads external_share_count 0, the schema stores "0".
    p = sg.create("Playlist", {"code": "dailies", "project": project})
    assert read(sg, "Playlist", p["id"], ["external_share_count"])["external_share_count"] == 0


def test_password_reads_the_mask(sg):
    # field_types/password
    u = sg.create("HumanUser", {"name": "Ann", "login": "ann"})
    assert read(sg, "HumanUser", u["id"], ["password_proxy"])["password_proxy"] == "*******"


def test_pivot_column_reads_none(sg, project):
    # field_types/pivot_column
    s = sg.create("Shot", {"code": "sh010", "project": project})
    assert read(sg, "Shot", s["id"], ["step_0"])["step_0"] is None


def test_multi_entity_reads_empty_list(sg, project):
    # field_types/multi_entity
    v = sg.create("Version", {"code": "v001", "project": project})
    assert read(sg, "Version", v["id"], ["notes"])["notes"] == []


# Text writes


def test_empty_text_is_stored_as_none(sg, project):
    # field_types/text
    v = sg.create("Version", {"code": "v001", "project": project, "sg_department": ""})
    assert read(sg, "Version", v["id"], ["sg_department"])["sg_department"] is None
    sg.update("Version", v["id"], {"sg_department": "   "})
    assert read(sg, "Version", v["id"], ["sg_department"])["sg_department"] is None


def test_text_is_stripped_at_both_ends(sg, project):
    # field_types/text
    v = sg.create("Version", {"code": "v001", "project": project, "description": "  padded  "})
    assert v["description"] == "padded"
    sg.update("Version", v["id"], {"description": " line1\nline2 "})
    assert read(sg, "Version", v["id"], ["description"])["description"] == "line1\nline2"


# Result shape


def test_entity_link_has_the_target_name(sg, project):
    # finding 060
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    task = sg.create("Task", {"content": "comp", "project": project})
    v = sg.create("Version", {"code": "v001", "project": project, "entity": shot, "sg_task": task})
    row = read(sg, "Version", v["id"], ["entity", "sg_task", "project"])
    assert row["entity"] == {"type": "Shot", "id": shot["id"], "name": "sh010"}
    assert row["sg_task"] == {"type": "Task", "id": task["id"], "name": "comp"}
    assert row["project"] == {"type": "Project", "id": project["id"], "name": "sandbox"}


def test_multi_entity_links_have_the_target_name(sg, project):
    # finding 060, field_types/multi_entity
    note = sg.create("Note", {"subject": "fix edge", "project": project})
    v = sg.create("Version", {"code": "v001", "project": project, "notes": [note]})
    assert read(sg, "Version", v["id"], ["notes"])["notes"] == [
        {"type": "Note", "id": note["id"], "name": "fix edge"}
    ]


def test_link_name_follows_a_rename(sg, project):
    # finding 060: `name` is the target's current cached_display_name.
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    v = sg.create("Version", {"code": "v001", "project": project, "entity": shot})
    sg.update("Shot", shot["id"], {"code": "sh020"})
    assert read(sg, "Version", v["id"], ["entity"])["entity"]["name"] == "sh020"


def test_dotted_path_to_a_link_has_the_name(sg, project):
    # finding 060
    seq = sg.create("Sequence", {"code": "sq01", "project": project})
    shot = sg.create("Shot", {"code": "sh010", "project": project, "sg_sequence": seq})
    v = sg.create("Version", {"code": "v001", "project": project, "entity": shot})
    row = read(sg, "Version", v["id"], ["entity.Shot.sg_sequence"])
    assert row["entity.Shot.sg_sequence"] == {"type": "Sequence", "id": seq["id"], "name": "sq01"}


def test_create_and_update_return_links_with_names(sg, project):
    # finding 024: every relationship comes back as {id, name, type}.
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    v = sg.create("Version", {"code": "v001", "project": project, "entity": shot})
    assert v["entity"] == {"type": "Shot", "id": shot["id"], "name": "sh010"}
    assert v["project"] == {"type": "Project", "id": project["id"], "name": "sandbox"}
    updated = sg.update("Version", v["id"], {"entity": shot})[0]
    assert updated["entity"] == {"type": "Shot", "id": shot["id"], "name": "sh010"}


def test_link_is_stored_without_name(sg, project):
    # finding 060: the name is derived on read, so a stored link stays {type, id}.
    shot = sg.create("Shot", {"code": "sh010", "project": project})
    v = sg.create("Version", {"code": "v001", "project": project, "entity": dict(shot, name="stale")})
    assert sg._db["Version"][v["id"]]["entity"] == {"type": "Shot", "id": shot["id"]}
