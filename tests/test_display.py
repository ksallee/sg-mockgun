"""The `name` of an entity link, derived per target type (finding 060)."""

from sg_mockgun.display import display_name


def test_code_types_read_code():
    # finding 060: Asset, Shot, Sequence and the other code types mirror `code`.
    for entity_type in ("Shot", "Asset", "Sequence", "Version", "Playlist", "CustomEntity01"):
        assert display_name(entity_type, {"code": "sh010"}) == "sh010"


def test_task_reads_content_or_dash():
    # entity_types/Task
    assert display_name("Task", {"content": "comp"}) == "comp"
    assert display_name("Task", {"content": None}) == "-"


def test_note_joins_subject_and_content():
    # entity_types/Note
    assert display_name("Note", {"subject": "s", "content": None}) == "s"
    assert display_name("Note", {"subject": "s", "content": "c"}) == "s - c"
    assert display_name("Note", {"subject": None, "content": None}) == ""


def test_delivery_prefixes_the_number():
    # entity_types/Delivery, finding 060
    assert display_name("Delivery", {"id": 68, "title": "zzprobe_060_delivery"}) == "#68: zzprobe_060_delivery"


def test_cut_appends_the_revision():
    # entity_types/Cut
    assert display_name("Cut", {"code": "reel1", "revision_number": 2}) == "reel1 v002"
    assert display_name("Cut", {"code": "reel1", "revision_number": None}) == "reel1"


def test_identity_field_per_type():
    assert display_name("Project", {"name": "sandbox", "code": "sbx"}) == "sandbox"  # entity_types/Project
    assert display_name("HumanUser", {"name": "Ann Lee", "login": "ann"}) == "Ann Lee"  # finding 020
    assert display_name("Reply", {"content": "ok"}) == "ok"  # entity_types/Reply
    assert display_name("TimeLog", {"description": "work"}) == "work"  # entity_types/TimeLog


def test_type_without_identity_reads_none():
    assert display_name("Booking", {"id": 1}) is None
