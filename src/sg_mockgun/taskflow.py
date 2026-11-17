"""Task Templates and scheduling applied to a mock's rows: the hooks ``create``, ``update``, ``delete``
and ``revive`` call. The rules are in ``templates`` and ``scheduling``; this module reads and writes rows.

Sources: api3 070 to 074, findings 083, 084, 085, 089, 090, 102.
"""

from shotgun_api3 import Fault

from . import events as _events
from . import scheduling as _sched
from . import templates as _templates
from .fields import ruby_inspect

_DATES = ("start_date", "due_date", "duration")
_EDGE_FIELDS = ("task", "dependent_task", "dependency_type", "offset_days")
_READ_ONLY = (("Task", "dependency_violation"),)  # api3 072


def _ref(row):
    return {"type": row["type"], "id": row["id"]}


def _live(mock, entity_type):
    return dict((i, r) for i, r in mock._db.get(entity_type, {}).items() if not r["__retired"])


def _edge(row):
    return _sched.Edge((row.get("task") or {}).get("id"), (row.get("dependent_task") or {}).get("id"),
                       row.get("dependency_type"), row.get("offset_days"))


def _edges(mock):
    return [(i, _edge(r)) for i, r in _live(mock, "TaskDependency").items()]


def before_update(mock, entity_type, data):
    """Refuse a write to a field the site computes."""
    for read_only_type, field in _READ_ONLY:
        if entity_type == read_only_type and field in data:
            raise Fault("API update() %s.%s is read only:\n%s" % (
                entity_type, field, ruby_inspect({"field_name": field, "value": data[field]})))


def after_create(mock, entity_type, row, data):
    if entity_type == "Task":
        row.update(_sched.own_write(row, data, False, mock.work_week))
    elif entity_type == "TaskDependency":
        if row.get("dependency_type") is None:
            row["dependency_type"] = _sched.DEFAULT_DEPENDENCY_TYPE  # finding 085
        edge = _edge(row)
        _relink(mock, [edge.down, edge.up], log=True)
        _reschedule(mock, [edge.down])
    elif data.get("task_template") and "task_template" in mock._schema[entity_type]:
        _apply_template(mock, row, data["task_template"])


def after_update(mock, entity_type, row, data, before):
    if entity_type == "Task" and (set(data) & set(_DATES + ("pinned",))):
        old = dict(row)
        old.update(before)
        own = _sched.own_write(old, data, bool(row.get("upstream_tasks")), mock.work_week)
        row.update(own)
        targets = [row["id"]] if "pinned" in data or "pinned" in own else []
        if any(row.get(f) != old.get(f) for f in _DATES):
            targets += [t["id"] for t in row.get("downstream_tasks") or []]
        _reschedule(mock, targets)
    elif entity_type == "TaskDependency" and set(data) & set(_EDGE_FIELDS):
        ends = [(before.get(f) or {}).get("id") for f in ("task", "dependent_task") if f in before]
        edge = _edge(row)
        _relink(mock, ends + [edge.down, edge.up])
        _reschedule(mock, [edge.down])
    elif entity_type != "Task" and data.get("task_template") and "task_template" in mock._schema[entity_type]:
        old = before.get("task_template")
        if not old or old["id"] != data["task_template"]["id"]:
            _apply_template(mock, row, data["task_template"])  # api3 071: only a changed value applies


def after_delete(mock, entity_type, row):
    if entity_type == "Task":
        # finding 089: the Task's edges retire with it and revive with it
        for edge_id, edge in _edges(mock):
            if row["id"] in (edge.down, edge.up):
                mock._db["TaskDependency"][edge_id]["__retired_with"] = row["id"]
                mock.delete("TaskDependency", edge_id)
    elif entity_type == "TaskDependency":
        edge = _edge(row)
        _relink(mock, [edge.down, edge.up])
        _reschedule(mock, [edge.down])


def after_revive(mock, entity_type, row):
    if entity_type == "Task":
        for edge_row in list(mock._db.get("TaskDependency", {}).values()):
            if edge_row.get("__retired_with") == row["id"]:
                del edge_row["__retired_with"]
                if edge_row["__retired"]:
                    mock.revive("TaskDependency", edge_row["id"])
        ends = [e.down for _, e in _edges(mock) if e.up == row["id"]] + \
               [e.up for _, e in _edges(mock) if e.down == row["id"]]
        _relink(mock, [row["id"]] + ends)
        _reschedule(mock, [row["id"]] + [t["id"] for t in row.get("downstream_tasks") or []])
    elif entity_type == "TaskDependency":
        edge = _edge(row)
        _relink(mock, [edge.down, edge.up])
        _reschedule(mock, [edge.down])


def _relink(mock, task_ids, log=False):
    """Set ``upstream_tasks`` and ``downstream_tasks`` on these Tasks from the live edges."""
    tasks = _live(mock, "Task")
    computed = _sched.links([e for _, e in _edges(mock)], set(tasks))
    for task_id in set(i for i in task_ids if i in tasks):
        row = tasks[task_id]
        up, down = computed[task_id]
        for field, ids in (("upstream_tasks", up), ("downstream_tasks", down)):
            new = [{"type": "Task", "id": i} for i in ids]
            old = row.get(field) or []
            if new == old:
                continue
            row[field] = new
            if log:  # api3 074: each end of a new edge logs its link change
                added = [mock._named_link(x) for x in new if x not in old]
                removed = [mock._named_link(x) for x in old if x not in new]
                mock._log([_events.links_change(mock._event_user["name"], "Task", task_id, mock._row_name(row),
                                                field, mock._display_name("Task", field), added, removed)], row)


def _reschedule(mock, targets):
    if not targets:
        return
    tasks = _live(mock, "Task")
    state = dict((i, dict((f, r.get(f)) for f in _DATES + ("pinned", "dependency_violation"))) for i, r in tasks.items())
    changes = _sched.reschedule(state, [e for _, e in _edges(mock)], targets, mock.work_week)
    for task_id, fields in changes.items():
        tasks[task_id].update(fields)


def _apply_template(mock, row, template_link):
    """Create the template's missing Tasks on ``row``, re-sync the linked ones, and rewire their edges."""
    template_tasks = dict((i, t) for i, t in sorted(_live(mock, "Task").items())
                          if (t.get("task_template") or {}).get("id") == template_link["id"])
    template_edges = [e for _, e in _edges(mock) if e.down in template_tasks and e.up in template_tasks]
    entity = _ref(row)
    linked = {}
    for task_id, task in sorted(_live(mock, "Task").items()):
        source = (task.get("template_task") or {}).get("id")
        if task.get("entity") == entity and source in template_tasks:
            linked.setdefault(source, task_id)  # finding 106: one Task per template task is re-synced
    fields = _templates.copy_fields(mock._schema["Task"])
    for source, template_task in template_tasks.items():
        if source in linked:
            mock._db["Task"][linked[source]].update(_templates.resync(template_task, mock._db["Task"][linked[source]],
                                                                      fields))
            continue
        made = mock.create("Task", _templates.new_task(template_task, fields, entity, row.get("project")))
        linked[source] = made["id"]
        if "tasks" in row:
            row["tasks"] = list(row["tasks"] or []) + [_ref(made)]  # api3 070
        mock._log([_events.links_change(mock._event_user["name"], row["type"], row["id"], mock._row_name(row),
                                        "tasks", mock._display_name(row["type"], "tasks"),
                                        [mock._named_link(_ref(made))], [], in_create=True)], row)
    targets = set(linked.values())
    create, erase = _templates.edge_plan(
        template_edges, linked, [(i, e) for i, e in _edges(mock) if e.down in targets or e.up in targets])
    # New edges first: an erased row's id is not handed to its replacement.
    for edge in create:
        data = {"task": {"type": "Task", "id": edge.down}, "dependent_task": {"type": "Task", "id": edge.up}}
        if edge.kind != _sched.DEFAULT_DEPENDENCY_TYPE:
            data["dependency_type"] = edge.kind
        if edge.offset is not None:
            data["offset_days"] = edge.offset
        mock.create("TaskDependency", data)
    for edge_id in erase:
        # finding 102: an edge the apply removes is erased, not retired
        edge = _edge(mock._db["TaskDependency"].pop(edge_id))
        _relink(mock, [edge.down, edge.up])
    _reschedule(mock, sorted(targets))
