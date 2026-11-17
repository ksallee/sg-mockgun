"""Pure helpers for find: page size, the read request a Fault echoes, LATEST and sort order."""
import functools

from shotgun_api3.shotgun import _translate_filters

from .fields import ruby_inspect

WIDTH = 80

# api3 023: the latest_by values each type accepts.
LATEST_BY = {
    "PublishedFile": ("ENTITIES_CREATED_AT",),
    "Version": ("ENTITIES_CREATED_AT", "BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT"),
}

# api3 023: the fields that group PublishedFile rows for LATEST.
PUBLISHED_FILE_GROUP = ("entity", "task", "published_file_type", "name")


def page_size(server_info):
    """Rows in one page, as the client reads it from server_info (api3 020)."""
    if server_info is None:
        return 5000
    return server_info.get("api_max_entities_per_page") or 500


def read_params(entity_type, filters, filter_operator, fields, retired_only, per_page, current_page,
                paging_info, presets, include_archived_projects=True):
    """The `read` request the client sends, in its key order."""
    params = {
        "type": entity_type,
        "return_fields": fields or ["id"],
        "filters": _translate_filters(filters, filter_operator) if isinstance(filters, (list, tuple)) else filters,
        "return_only": "retired" if retired_only else "active",
        "paging": {"entities_per_page": per_page, "current_page": current_page},
    }
    if presets:
        params["additional_filter_presets"] = presets
    if include_archived_projects is False:
        params["include_archived_projects"] = False
    params["api_return_image_urls"] = True
    params["return_paging_info_without_counts"] = paging_info
    return params


def pp(value, col=0, trail=0):
    """Ruby ``pp`` of a value starting at column ``col``, with ``trail`` characters after it."""
    flat = ruby_inspect(value)
    if col + len(flat) + trail <= WIDTH or not isinstance(value, (dict, list, tuple)) or not value:
        return flat
    if isinstance(value, dict):
        items = list(value.items())
        render = lambda item, c, t: _pp_pair(item[0], item[1], c, t)  # noqa: E731
        opening, closing = "{", "}"
    else:
        items = list(value)
        render = lambda item, c, t: pp(item, c, t)  # noqa: E731
        opening, closing = "[", "]"
    parts = []
    for i, item in enumerate(items):
        last = i == len(items) - 1
        parts.append(render(item, col + 1, trail + 1 if last else 1))
    return opening + (",\n" + " " * (col + 1)).join(parts) + closing


def _pp_pair(key, value, col, trail):
    head = ruby_inspect(key) + " =>"
    flat = head + " " + ruby_inspect(value)
    if col + len(flat) + trail <= WIDTH:
        return flat
    return head + "\n" + " " * (col + 1) + pp(value, col + 1, trail)


def latest_ids(rows, group, rank):
    """Ids of the newest row per group; a group key with None in it drops the row (api3 023).

    ``rank`` orders rows before ``created_at``. Equal ranks keep the lower id.
    """
    best = {}
    for row in rows:
        key = group(row)
        if any(k is None for k in key):
            continue
        order = (rank(row), _sortable(row.get("created_at")), -row["id"])
        if key not in best or order > best[key][0]:
            best[key] = (order, row["id"])
    return {entry[1] for entry in best.values()}


def _sortable(value):
    return (value is not None, value)


def sort_rows(rows, keys, get):
    """Rows sorted by ``keys``, a list of (field, descending).

    None sorts last in both directions and ties keep id ascending (api3 025).
    """
    def compare(a, b):
        for field, descending in keys:
            x, y = get(a, field), get(b, field)
            if x == y:
                continue
            if x is None:
                return 1
            if y is None:
                return -1
            result = -1 if x < y else 1
            return -result if descending else result
        return -1 if a["id"] < b["id"] else (1 if a["id"] > b["id"] else 0)

    return sorted(rows, key=functools.cmp_to_key(compare))
