"""Pure scheduling rules: working days, a Task's own writes, the dependency cascade."""

from sg_mockgun import scheduling as S

WEEK = S.DEFAULT_WORK_WEEK


def task(start=None, due=None, duration=None, pinned=False):
    return {"start_date": start, "due_date": due, "duration": duration, "pinned": pinned}


def test_default_week_is_monday_to_friday():
    # finding 047: STUDIO_WORK_WEEK, Mon..Fri working
    assert WEEK == (True, True, True, True, True, False, False)


def test_duration_counts_working_days_at_480_minutes():
    # api3 072: 03-02..03-03 reads 960, 03-02..03-05 reads 1920, 03-02..03-02 reads 480
    assert S.duration_between("2026-03-02", "2026-03-03", WEEK) == 960
    assert S.duration_between("2026-03-02", "2026-03-05", WEEK) == 1920
    assert S.duration_between("2026-03-02", "2026-03-02", WEEK) == 480
    assert S.duration_between("2026-03-05", "2026-03-13", WEEK) == 3360


def test_due_from_start_and_duration_skips_weekends():
    # api3 072: up duration 2880 from 03-02 ends 03-09
    assert S.due_from("2026-03-02", 2880, WEEK) == "2026-03-09"
    assert S.due_from("2026-03-10", 3360, WEEK) == "2026-03-18"


def test_shift_moves_working_days_both_ways():
    assert S.shift("2026-03-06", 1, WEEK) == "2026-03-09"
    assert S.shift("2026-03-09", -1, WEEK) == "2026-03-06"
    assert S.shift("2026-03-06", 0, WEEK) == "2026-03-06"


def test_own_write_due_recomputes_duration_and_does_not_pin():
    # api3 072, finding 093: a due_date write resizes
    old = task("2026-03-05", "2026-03-10", 1920)
    assert S.own_write(old, {"due_date": "2026-03-13"}, True, WEEK) == {"duration": 3360}


def test_own_write_duration_moves_due_and_does_not_pin():
    # api3 072, finding 100
    old = task("2026-03-03", "2026-03-04", 960)
    assert S.own_write(old, {"duration": 1920}, True, WEEK) == {"due_date": "2026-03-06"}


def test_own_write_start_on_a_dependent_pins_and_holds_duration():
    # api3 072, finding 093
    old = task("2026-03-10", "2026-03-18", 3360)
    assert S.own_write(old, {"start_date": "2026-03-04"}, True, WEEK) == {"due_date": "2026-03-12", "pinned": True}


def test_own_write_of_the_stored_start_does_not_pin():
    # finding 093; live conformance run: a write of the stored start_date leaves pinned False
    old = task("2026-03-04", "2026-03-05", 960)
    assert S.own_write(old, {"start_date": "2026-03-04"}, True, WEEK) == {}


def test_own_write_start_null_pins_and_keeps_due():
    # finding 093
    old = task("2026-03-04", "2026-03-05", 960)
    assert S.own_write(old, {"start_date": None}, True, WEEK) == {"pinned": True}


def test_own_write_start_without_upstream_never_pins():
    # finding 097
    old = task("2026-03-02", "2026-03-03", 960)
    assert S.own_write(old, {"start_date": "2026-03-09", "due_date": "2026-03-10"}, False, WEEK) == {}


def test_own_write_both_dates_recompute_duration():
    assert S.own_write(task(), {"start_date": "2026-03-02", "due_date": "2026-03-05"}, False, WEEK) == {"duration": 1920}


def test_placement_per_dependency_type():
    # finding 085: U runs 03-02..03-06, D two working days
    up = task("2026-03-02", "2026-03-06", 2400)
    dn = task("2026-02-16", "2026-02-17", 960)
    for kind, offset, want in [
        ("finish-to-start-next-day", None, ("2026-03-09", "2026-03-10")),
        ("finish-to-start-next-day", 2, ("2026-03-11", "2026-03-12")),
        ("finish-to-start-next-day", -1, ("2026-03-06", "2026-03-09")),
        ("start-to-start", None, ("2026-03-02", "2026-03-03")),
        ("start-to-start", 2, ("2026-03-04", "2026-03-05")),
        ("finish-to-finish", None, ("2026-03-05", "2026-03-06")),
        ("finish-to-finish", -1, ("2026-03-04", "2026-03-05")),
        ("start-to-finish-next-day", None, ("2026-02-26", "2026-02-27")),
        ("start-to-finish-next-day", 2, ("2026-03-02", "2026-03-03")),
    ]:
        edges = [S.Edge(down=2, up=1, kind=kind, offset=offset)]
        changes = S.reschedule({1: up, 2: dn}, edges, [2], WEEK)
        assert (changes[2]["start_date"], changes[2]["due_date"]) == want, (kind, offset)


def test_cascade_moves_unpinned_later_and_earlier():
    # api3 072
    tasks = {1: task("2026-03-02", "2026-03-05", 1920), 2: task("2026-03-04", "2026-03-05", 960)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None)]
    assert S.reschedule(tasks, edges, [2], WEEK)[2] == {"start_date": "2026-03-06", "due_date": "2026-03-09"}
    tasks[1]["due_date"] = "2026-03-02"
    assert S.reschedule(tasks, edges, [2], WEEK)[2] == {"start_date": "2026-03-03", "due_date": "2026-03-04"}


def test_cascade_reaches_every_depth():
    tasks = {1: task("2026-03-02", "2026-03-03", 960), 2: task("2026-03-02", "2026-03-03", 960),
             3: task("2026-03-02", "2026-03-03", 960)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None), S.Edge(3, 2, "finish-to-start-next-day", None)]
    changes = S.reschedule(tasks, edges, [2], WEEK)
    assert changes[3] == {"start_date": "2026-03-06", "due_date": "2026-03-09"}


def test_pinned_holds_and_flags_violation_while_broken():
    # api3 072
    tasks = {1: task("2026-03-02", "2026-03-10", 3360), 2: task("2026-03-04", "2026-03-12", 3360, pinned=True)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None)]
    assert S.reschedule(tasks, edges, [2], WEEK) == {2: {"dependency_violation": True}}
    tasks[1]["due_date"] = "2026-03-02"
    assert S.reschedule(tasks, edges, [2], WEEK) == {2: {"dependency_violation": False}}


def test_pinned_null_start_is_no_violation():
    # finding 093
    tasks = {1: task("2026-03-09", "2026-03-10", 960), 2: task(None, None, 960, pinned=True)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None)]
    assert S.reschedule(tasks, edges, [2], WEEK) == {2: {"dependency_violation": False}}


def test_unpin_refills_null_dates_from_duration():
    # finding 093
    tasks = {1: task("2026-03-09", "2026-03-10", 960), 2: task(None, None, 960)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None)]
    assert S.reschedule(tasks, edges, [2], WEEK)[2] == {"start_date": "2026-03-11", "due_date": "2026-03-12"}


def test_undated_upstream_moves_nothing():
    # finding 097, api3 070: undated template Tasks stay undated
    tasks = {1: task(), 2: task("2026-03-04", "2026-03-05", 960)}
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None)]
    assert S.reschedule(tasks, edges, [2], WEEK) == {}


def test_links_need_both_ends_live():
    # api3 073: a revived edge with a retired end links nothing
    edges = [S.Edge(2, 1, "finish-to-start-next-day", None), S.Edge(3, 9, "start-to-start", None)]
    assert S.links(edges, {1, 2, 3}) == {1: ([], [2]), 2: ([1], []), 3: ([], [])}
