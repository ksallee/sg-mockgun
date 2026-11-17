"""Create contract and refusal messages for record writes. Pure: no I/O, no state.

Every message is what a Flow PT 8.91 site answered over api3 (docs/api3/060 to 063).
"""

from .fields import ruby_inspect

# Types that refuse a create without `project` (finding 012, api3 060).
PROJECT_SCOPED = ("Asset", "Delivery", "Note", "Playlist", "PublishedFile", "Sequence", "Shot", "Task", "Version")

# The identity field a create fills with `New <Type> <id>` when omitted (finding 012, api3 060).
IDENTITY_FIELDS = {
    "Asset": "code", "Delivery": "title", "Playlist": "code", "PublishedFile": "code",
    "Sequence": "code", "Shot": "code", "Task": "content", "Version": "code",
}


def fields_param(data):
    """The `fields` list api3 sends for a create's data."""
    return [{"field_name": k, "value": v} for k, v in data.items()]


def no_fields(entity_type, return_fields=None):
    """The refusal of a create with no fields (api3 060, 061)."""
    params = {"type": entity_type, "fields": [], "return_fields": list(return_fields or ["id"])}
    return "API create() invalid/missing array 'fields':\n%s" % ruby_inspect(params)


def missing_project(data):
    """The refusal of a project-scoped create without `project` (api3 060)."""
    return "API create() missing 'project' attribute:\n%s" % ruby_inspect(fields_param(data))


def empty_identity(entity_type):
    """The refusal of an identity field set to "" or None (api3 060)."""
    return "API create() CRUD ERROR #6: Create failed for [%s]: Cannot set identifier field to empty. (%s)" % (
        entity_type, entity_type)


def bad_status(verb, entity_type, field, value, valid_values):
    """The refusal of a status outside `valid_values`, worded per verb (api3 062)."""
    inner = "Update failed for [%s.%s]: '%s' is not a valid status. Valid statuses: %s." % (
        entity_type, field, value, ", ".join("'%s'" % v for v in valid_values))
    if verb == "create":
        return "API create() CRUD ERROR #6: Invalid field value, update failed [5 - %s]" % inner
    return "API update() CRUD ERROR #5: %s" % inner


def missing_entity(verb, entity_type, entity_id):
    """The refusal of an update or delete of an id that does not exist (api3 063)."""
    return "API %s() CRUD ERROR #3: Entity of type [%s] with id=%s does not exist." % (verb, entity_type, entity_id)


def rolled_back(index, message):
    """A batch refusal: the failing request's index, then its own message (api3 063)."""
    return "API batch() request with index %d failed.  All requests rolled back.\n%s" % (index, message)
