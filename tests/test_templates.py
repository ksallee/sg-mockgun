"""Pure Task Template rules: what a generated Task copies, what a re-sync overwrites, which edges change."""

from sg_mockgun import templates as T
from sg_mockgun.scheduling import Edge

FIELDS = ["content", "step", "duration", "est_in_mins", "sg_status_list", "start_date", "due_date",
          "task_assignees", "task_reviewers", "milestone"]
STEP = {"type": "Step", "id": 3}


def test_copy_fields_are_editable_and_not_links_to_the_entity():
    schema = {
        "content": {"editable": {"value": True}},
        "created_at": {"editable": {"value": False}},
        "entity": {"editable": {"value": True}},
        "template_task": {"editable": {"value": True}},
        "pinned": {"editable": {"value": True}},
        "upstream_tasks": {"editable": {"value": True}},
    }
    assert T.copy_fields(schema) == ["content"]


def test_new_task_copies_set_fields_and_links_the_template_task():
    # api3 070, finding 083: template_task set, task_template left null
    tt = {"type": "Task", "id": 9, "content": "Comp", "step": STEP, "duration": 3360, "est_in_mins": None,
          "milestone": False, "sg_status_list": "wtg", "task_assignees": []}
    shot, project = {"type": "Shot", "id": 1}, {"type": "Project", "id": 2}
    assert T.new_task(tt, FIELDS, shot, project) == {
        "project": project, "entity": shot, "template_task": {"type": "Task", "id": 9},
        "content": "Comp", "step": STEP, "duration": 3360, "sg_status_list": "wtg"}


def test_resync_overwrites_set_values_and_keeps_status():
    # api3 071, finding 102
    tt = {"content": "Comp", "step": STEP, "sg_status_list": "wtg", "est_in_mins": 0, "milestone": False}
    task = {"content": "renamed", "step": {"type": "Step", "id": 4}, "sg_status_list": "ip", "est_in_mins": 60,
            "milestone": True}
    assert T.resync(tt, task, FIELDS) == {"content": "Comp", "step": STEP, "est_in_mins": 0}


def test_resync_fills_dates_and_assignees_only_when_empty():
    # finding 102
    group = [{"type": "Group", "id": 5}]
    tt = {"start_date": "2026-03-02", "due_date": "2026-03-04", "task_assignees": group, "task_reviewers": group}
    kept = {"start_date": "2026-05-04", "due_date": "2026-05-08", "task_assignees": [{"type": "Group", "id": 6}],
            "task_reviewers": [{"type": "Group", "id": 6}]}
    assert T.resync(tt, kept, FIELDS) == {"task_reviewers": group}
    empty = {"start_date": None, "due_date": None, "task_assignees": [], "task_reviewers": []}
    assert T.resync(tt, empty, FIELDS) == tt


def test_resync_duration_only_on_an_undated_task():
    # findings 102, 108
    tt = {"duration": 960}
    assert T.resync(tt, {"duration": 2400, "start_date": "2026-05-04", "due_date": "2026-05-08"}, FIELDS) == {}
    assert T.resync(tt, {"duration": None, "start_date": "2026-05-04", "due_date": None}, FIELDS) == {}
    assert T.resync(tt, {"duration": 1920, "start_date": None, "due_date": None}, FIELDS) == {"duration": 960}


def test_edge_plan_creates_missing_and_replaces_different():
    # api3 071, findings 102, 105
    template = [Edge(2, 1, "finish-to-start-next-day", None), Edge(3, 2, "start-to-start", 2)]
    linked = {1: 11, 2: 12, 3: 13}
    live = [(100, Edge(13, 12, "finish-to-finish", 5)), (101, Edge(13, 11, "finish-to-start-next-day", None)),
            (102, Edge(99, 11, "finish-to-start-next-day", None))]
    create, erase = T.edge_plan(template, linked, live)
    assert create == [Edge(12, 11, "finish-to-start-next-day", None), Edge(13, 12, "start-to-start", 2)]
    assert erase == [100, 101]


def test_edge_plan_keeps_an_equal_edge_and_tells_null_from_zero():
    # finding 105
    template = [Edge(2, 1, "finish-to-start-next-day", None), Edge(3, 1, "finish-to-start-next-day", 0)]
    linked = {1: 11, 2: 12, 3: 13}
    live = [(100, Edge(12, 11, "finish-to-start-next-day", None)), (101, Edge(13, 11, "finish-to-start-next-day", None))]
    assert T.edge_plan(template, linked, live) == ([Edge(13, 11, "finish-to-start-next-day", 0)], [101])
