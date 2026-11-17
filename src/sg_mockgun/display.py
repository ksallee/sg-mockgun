"""The display name a site returns as `name` in an entity link, derived from the target row."""

# Types whose identity field is not `code`. entity_types/<Type> per row; finding 020 for HumanUser.
IDENTITY = {
    "Project": "name",  # entity_types/Project
    "HumanUser": "name",  # finding 020: the display name is not unique, `login` is
    "ClientUser": "name",
    "Reply": "content",  # entity_types/Reply
    "TimeLog": "description",  # entity_types/TimeLog
    "Attachment": "display_name",  # entity_types/Attachment
    "ActionMenuItem": "title",
    "Icon": "name",
    "Page": "name",
    "Tag": "name",
}

# Tried in order on a type with no rule above and no `code` field.
FALLBACK = ("code", "name", "title", "content", "subject")


def display_name(entity_type, row):
    """Return the target's `cached_display_name` for an entity link (finding 060)."""
    if entity_type == "Task":
        # entity_types/Task: a copy of `content`, "-" when it is null.
        return row.get("content") or "-"
    if entity_type == "Note":
        # entity_types/Note: `subject` alone, or "<subject> - <content>" when both are set.
        return " - ".join(part for part in (row.get("subject"), row.get("content")) if part)
    if entity_type == "Delivery":
        # entity_types/Delivery: "#<delivery_number>: <title>", where delivery_number is the id.
        return "#%s: %s" % (row.get("id"), row.get("title") or "")
    if entity_type == "Cut":
        # entity_types/Cut: `code`, plus " v001" when `revision_number` is set.
        code = row.get("code") or ""
        revision = row.get("revision_number")
        return code if revision is None else "%s v%03d" % (code, revision)
    if entity_type in IDENTITY:
        return row.get(IDENTITY[entity_type])
    for field in FALLBACK:
        if field in row:
            return row[field]
    return None
