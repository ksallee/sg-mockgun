"""Pure Task scheduling rules: working days, a Task's own date writes, and the dependency cascade.

Dates are ``YYYY-MM-DD`` strings as api3 returns them. A duration is in minutes, 480 per working
day. A work week is seven booleans, Monday first. Sources: api3 072, findings 047, 085, 087, 092,
093, 097, 100.
"""

import collections
import datetime

DEFAULT_WORK_WEEK = (True, True, True, True, True, False, False)  # finding 047: STUDIO_WORK_WEEK
MINUTES_PER_DAY = 480

DEFAULT_DEPENDENCY_TYPE = "finish-to-start-next-day"  # finding 085: an omitted type is stored as this

# One TaskDependency: ``down`` is the row's ``task``, ``up`` its ``dependent_task`` (finding 085).
Edge = collections.namedtuple("Edge", "down up kind offset")


def _day(text):
    return datetime.date(*(int(part) for part in text.split("-")))


def shift(date, days, week):
    """The date ``days`` working days after ``date``, or before it when negative."""
    if not days:
        return date
    day, step, left = _day(date), (1 if days > 0 else -1), abs(days)
    while left:
        day += datetime.timedelta(days=step)
        if week[day.weekday()]:
            left -= 1
    return day.isoformat()


def _days(duration):
    return max(-(-duration // MINUTES_PER_DAY), 1)


def duration_between(start, due, week):
    """The minutes of working days from ``start`` to ``due``, both included."""
    day, end, count = _day(start), _day(due), 0
    while day <= end:
        count += week[day.weekday()]
        day += datetime.timedelta(days=1)
    return count * MINUTES_PER_DAY


def due_from(start, duration, week):
    """The due date of a Task that starts on ``start`` and lasts ``duration`` minutes."""
    return shift(start, _days(duration) - 1, week)


def start_from(due, duration, week):
    """The start date of a Task that ends on ``due`` and lasts ``duration`` minutes."""
    return shift(due, 1 - _days(duration), week)


def own_write(old, data, has_upstream, week):
    """The fields the site sets beside ``data`` on a Task write, other than the sent ones.

    A ``start_date`` write that changes the value pins a Task with an upstream, null or real
    (finding 093); nothing else pins (finding 097, 100). A ``due_date`` write resizes, a ``start_date`` or ``duration`` write
    moves ``due_date`` and keeps ``duration``.
    """
    merged = dict(old)
    merged.update(data)
    start, due, duration = merged.get("start_date"), merged.get("due_date"), merged.get("duration")
    changes = {}
    if "start_date" in data and "due_date" in data:
        if start and due:
            changes["duration"] = duration_between(start, due, week)
    elif "start_date" in data or "duration" in data:
        if start and duration is not None:
            changes["due_date"] = due_from(start, duration, week)
    elif "due_date" in data:
        if start and due:
            changes["duration"] = duration_between(start, due, week)
    if "start_date" in data and data["start_date"] != old.get("start_date") and has_upstream and "pinned" not in data:
        changes["pinned"] = True
    return dict((k, v) for k, v in changes.items() if merged.get(k) != v)


def links(edges, live):
    """``{task id: (upstream ids, downstream ids)}`` for each id in ``live``, from edges with both ends live."""
    out = dict((task_id, (set(), set())) for task_id in live)
    for edge in edges:
        if edge.down in live and edge.up in live:
            out[edge.down][0].add(edge.up)
            out[edge.up][1].add(edge.down)
    return dict((k, (sorted(up), sorted(down))) for k, (up, down) in out.items())


def _own_duration(task, week):
    if task.get("duration") is not None:
        return task["duration"]
    if task.get("start_date") and task.get("due_date"):
        return duration_between(task["start_date"], task["due_date"], week)
    return None


def _required_start(task, ups, week):
    """The start each upstream edge places the Task at, latest first; None when no upstream is dated."""
    duration = _own_duration(task, week)
    starts = []
    for edge, up in ups:
        offset = edge.offset or 0
        if edge.kind == "start-to-start" and up.get("start_date"):
            starts.append(shift(up["start_date"], offset, week))
        elif edge.kind == "finish-to-finish" and up.get("due_date") and duration is not None:
            starts.append(start_from(shift(up["due_date"], offset, week), duration, week))
        elif edge.kind == "start-to-finish-next-day" and up.get("start_date") and duration is not None:
            starts.append(start_from(shift(up["start_date"], offset - 1, week), duration, week))
        elif edge.kind == "finish-to-start-next-day" and up.get("due_date"):
            starts.append(shift(up["due_date"], offset + 1, week))
    return max(starts) if starts else None


def reschedule(tasks, edges, targets, week):
    """Place ``targets`` behind their upstream Tasks and cascade downstream.

    ``tasks`` maps id to ``start_date``, ``due_date``, ``duration``, ``pinned`` and, when known,
    ``dependency_violation``. Returns ``{id: {field: new value}}`` for the fields that change.

    An unpinned Task snaps to its latest constraint, later or earlier, ``duration`` held (findings
    085, 087). A pinned Task holds and reads ``dependency_violation`` true while it starts before its
    constraint; a null start is no violation (finding 093). An undated upstream places nothing
    (finding 097). Several upstream edges place the Task at the latest constraint: unmeasured.
    """
    state = dict((k, dict(v)) for k, v in tasks.items())
    ups = collections.defaultdict(list)
    downs = collections.defaultdict(list)
    for edge in edges:
        if edge.down in state and edge.up in state:
            ups[edge.down].append(edge)
            downs[edge.up].append(edge.down)
    changes = {}
    queue = collections.deque(targets)
    budget = 100 * (len(state) + 1)
    while queue and budget:
        budget -= 1
        task_id = queue.popleft()
        task = state.get(task_id)
        if task is None:
            continue
        required = _required_start(task, [(e, state[e.up]) for e in ups[task_id]], week)
        new = {}
        if task.get("pinned"):
            violation = bool(required and task.get("start_date") and task["start_date"] < required)
            if task.get("dependency_violation") != violation:
                new["dependency_violation"] = violation
        else:
            if task.get("dependency_violation"):
                new["dependency_violation"] = False
            duration = _own_duration(task, week)
            if required and duration is not None:
                due = due_from(required, duration, week)
                if task.get("start_date") != required:
                    new["start_date"] = required
                if task.get("due_date") != due:
                    new["due_date"] = due
        if new:
            task.update(new)
            changes.setdefault(task_id, {}).update(new)
            if "start_date" in new or "due_date" in new:
                queue.extend(downs[task_id])
    return changes
