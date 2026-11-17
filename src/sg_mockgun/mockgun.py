"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2017, Shotgun Software Inc

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-----------------------------------------------------------------------------



-----------------------------------------------------------------------------
M O C K G U N
-----------------------------------------------------------------------------

Experimental software ahead!
----------------------------
Disclaimer! Mockgun is in its early stages of development. It is not fully
compatible with the Shotgun API yet and we offer no guarantees at this point
that future versions of Mockgun will be backwards compatible. Consider this
alpha level software and use at your own risk.


What is Mockgun?
----------------
Mockgun is a Shotgun API mocker. It's a class that has got *most* of the same
methods and parameters that the Shotgun API has got. Mockgun is essentially a
Shotgun *emulator* that (for basic operations) looks and feels like Shotgun.

The primary purpose of Mockgun is to drive unit test rigs where it becomes
too slow, cumbersome or non-practical to connect to a real Shotgun. Using a
Mockgun for unit tests means that a test can be rerun over and over again
from exactly the same database state. This can be hard to do if you connect
to a live Shotgun instance.


How do I use Mockgun?
---------------------
First of all, you need a Shotgun schema to run against. This will define
all the fields and entities that mockgun will use. Simply connect to
your Shotgun site and use the generate_schema() method to download
the schema data:

    # connect to your site
    from shotgun_api3 import Shotgun
    sg = Shotgun("https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc")

    # write out schema data to files
    from shotgun_api3.lib import mockgun
    mockgun.generate_schema(sg, "/tmp/schema", "/tmp/entity_schema")

Now that you have a schema, you can tell your mockgun instance about it.
We do this as a class-level operation, so that the consctructor can be
exactly like the real Shotgun one:

    from shotgun_api3.lib import mockgun

    # tell mockgun about the schema
    mockgun.Shotgun.set_schema_paths("/tmp/schema", "/tmp/entity_schema")

    # we are ready to mock!
    # this call will not connect to mysite, but instead create a
    # mockgun instance which is connected to an *empty* shotgun site
    # which has got the same schema as mysite.
    sg = mockgun.Shotgun("https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc")

    # now you can start putting stuff in
    print(sg.create("HumanUser", {"firstname": "John", "login": "john"}))
    # prints {'login': 'john', 'type': 'HumanUser', 'id': 1, 'firstname': 'John'}

    # and find what you have created
    print(sg.find("HumanUser", [["login", "is", "john"]]))
    prints [{'type': 'HumanUser', 'id': 1}]

That's it! Mockgun is used to run the Shotgun Pipeline Toolkit unit test rig.

Mockgun has a 'database' in the form of a dictionary stored in Mockgun._db
By editing this directly, you can modify the database without going through
the API.


What are the limitations?
---------------------
There are many. Don't expect mockgun to be fully featured at this point.
Below is a non-exhaustive list of things that we still need to implement:

- Many find queries won't work
- Methods around session handling and authentication is not implemented
- Attachments and upload is rundimental at best
- Schema modification isn't most most likely will never be supported
- There is no validation or sanitation

"""

import copy
import datetime
import importlib.metadata
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from shotgun_api3 import Fault, ShotgunError, ShotgunFileDownloadError, ShotgunThumbnailNotReady
from shotgun_api3.shotgun import _Config
from shotgun_api3 import Fault, ShotgunError
from shotgun_api3.shotgun import ServerCapabilities, _Config, _translate_filters
from .errors import MockgunError
from .display import display_name
from .schema import SchemaFactory
from . import attention as _attention
from . import events as _events
from . import media as _media
from . import seed as _seed
from . import scheduling as _scheduling
from . import taskflow as _taskflow
from . import writes as _writes
from . import reads as _reads
from . import records as _records
from . import summarize as _summarize
from . import text_search as _text_search
from .site_info import DEFAULT_INFO
from . import wire as _wire
import shotgun_api3.shotgun as _api3
from .filters import (
    CALENDAR, IGNORED, RELATIONS, RELATIVE, calculated_type, client_index_error, filter_refusal, filter_values,
    jsonb_contains, relative_match, unknown_field,
)
from .fields import CREATABLE_TYPES, UPDATABLE_PROPERTIES, field_code, new_field, ruby_inspect, ruby_list, ruby_params

_ALL_RELATIONS = set(r for relations in RELATIONS.values() for r in relations)

def _utc_now():
    """The current time in UTC."""
    return datetime.datetime.now(datetime.timezone.utc)


def _same_link(a, b):
    """Whether two entity links name the same row."""
    return a["type"] == b["type"] and a["id"] == b["id"]


def _link_name(link):
    """The display name of an entity link, empty when the linked row has none."""
    return link.get("name") or ""


class FieldReviveError(ShotgunError):
    """A refused field revive. ``status`` is the HTTP status the REST route answers with."""

    def __init__(self, message, status):
        ShotgunError.__init__(self, message)
        self.status = status


_RETIRED_FIELD = (
    "API schema_field_create() failed, there is a retired field with the same field_name: %s. "
    "Delete the retired field forever from the Trash Page in Shotgun and try again."
)

# ----------------------------------------------------------------------------
# Version
try:
    __version__ = importlib.metadata.version("sg-mockgun")
except importlib.metadata.PackageNotFoundError:
    # Imported from a source tree that was never installed.
    __version__ = "0.0.0"


# ----------------------------------------------------------------------------
# API

class Shotgun(object):
    """
    Mockgun is a mocked Shotgun API, designed for test purposes.
    It generates an object which looks and feels like a normal Shotgun API instance.
    Instead of connecting to a real server, it keeps all its data in memory in a way
    which makes it easy to introspect and test.

    The methods presented in this class reflect the Shotgun API and are therefore
    sparsely documented.

    Please note that this class is built for test purposes only and only creates an
    object which *roughly* resembles the Shotgun API - however, for most common
    use cases, this is enough to be able to perform relevant and straight forward
    testing of code.
    """

    __schema_path = None
    __schema_entity_path = None

    @classmethod
    def set_schema_paths(cls, schema_path, schema_entity_path):
        """
        Set the path where schema files can be found. This is done at the class
        level so all Shotgun instances will share the same schema.
        The responsability to generate and load these files is left to the user
        changing the default value.

        :param schema_path: Directory path where schema files are.
        """
        cls.__schema_path = schema_path
        cls.__schema_entity_path = schema_entity_path

    @classmethod
    def get_schema_paths(cls):
        """
        Returns a tuple with paths to the files which are part of the schema.
        These paths can then be used in generate_schema if needed.

        :returns: A tuple with schema_file_path and schema_entity_file_path
        """
        return (cls.__schema_path, cls.__schema_entity_path)

    def __init__(self,
                 base_url,
                 script_name=None,
                 api_key=None,
                 convert_datetimes_to_utc=True,
                 http_proxy=None,
                 connect=True,
                 ca_certs=None,
                 login=None,
                 password=None,
                 sudo_as_login=None,
                 session_token=None,
                 auth_token=None):

        # emulate the config object in the Shotgun API.
        # these settings won't make sense for mockgun, but
        # having them present means code and get and set them
        # they way they would expect to in the real API.
        self.config = _Config(self)

        self.config.set_server_params(base_url)

        # load in the shotgun schema to associate with this Shotgun
        (schema_path, schema_entity_path) = self.get_schema_paths()

        if schema_path is None or schema_entity_path is None:
            raise MockgunError("Cannot create Mockgun instance because no schema files have been defined. "
                               "Before creating a Mockgun instance, please call Mockgun.set_schema_paths() "
                               "in order to specify which Flow Production Tracking schema Mockgun should operate against.")

        # SchemaFactory caches one schema for every instance; copy it so schema writes stay per instance.
        schema, schema_entity = SchemaFactory.get_schemas(schema_path, schema_entity_path)
        self._schema = copy.deepcopy(schema)
        self._schema_entity = copy.deepcopy(schema_entity)
        # Fields deleted through schema_field_delete: their programmatic names stay taken.
        self._retired_fields = {}

        # initialize the "database"
        self._db = dict((entity, {}) for entity in self._schema)

        # The event log. Like an ApiUser's generate_event_log_entries (sg-groundtruth finding 049), but
        # on by default so a test sees its writes logged unless it says otherwise.
        self.generate_event_log_entries = True
        self._clock = _utc_now
        self._event_user = {"type": "ApiUser", "id": 1, "name": script_name or login or "mockgun"}
        self._column_ids = {}
        self._retired_at = {}
        self._media_state = _media.new_state()
        # The studio work week, Monday first (finding 047). Scheduling counts working days on it.
        self.work_week = _scheduling.DEFAULT_WORK_WEEK
        # The highest id handed out per type, including ids of refused or rolled-back creates (api3 060, 063).
        self._spent_ids = {}
        # What a delete changed on other rows, keyed by the deleted row, for revive to put back (api3 027, 065).
        self._delete_effects = {}
        # Per-project schema values: {(project id, entity type, field): {"visible": bool, "hidden_values": list}}.
        self._project_schema = {}
        # A site refuses a project-scoped create without `project` (api3 060). False lets a test skip it.
        self.require_project = True

        # set some basic public members that exist in the Shotgun API
        self.base_url = base_url

        # bootstrap the event log
        # let's make sure there is at least one event log id in our mock db
        data = {}
        data["event_type"] = "Hello_Mockgun_World"
        data["description"] = "Mockgun was born. Yay."
        self.create("EventLogEntry", data)

        self.finds = 0
        self._info = copy.deepcopy(DEFAULT_INFO)

    ###################################################################################################
    # public API methods

    def set_work_week(self, days):
        """Set the studio work week: seven booleans, Monday first, True for a working day."""
        self.work_week = tuple(bool(d) for d in days)

    def set_clock(self, clock):
        """Make event timestamps deterministic: ``clock`` returns a timezone-aware datetime."""
        self._clock = clock

    def get_session_token(self):
        return "bogus_session_token"

    def schema_read(self):
        return self._schema

    def schema_field_create(self, entity_type, data_type, display_name, properties=None):
        properties = dict(properties or {})
        params = {
            "type": entity_type,
            "data_type": data_type,
            "properties": [{"property_name": "name", "value": display_name}]
            + [{"property_name": k, "value": v} for k, v in properties.items()],
        }
        if entity_type not in self._schema:
            raise Fault(
                "API schema_field_create() invalid/missing string entity 'type':\n%s\nValid entity types:\n%s"
                % (ruby_params(params), ruby_list(sorted(self._schema)))
            )
        if data_type not in CREATABLE_TYPES:
            raise Fault(
                "API schema_field_create() can't create '%s' data type.  Valid data types:\n%s"
                % (data_type, ruby_list(CREATABLE_TYPES))
            )
        if data_type == "calculated":
            # Recorded with no formula. A create that carries one has not been measured.
            raise Fault("API schema_field_create() NoMethodError: undefined method 'strip' for nil")
        if data_type in ("entity", "multi_entity"):
            valid_types = properties.get("valid_types")
            if not valid_types:
                raise Fault("API schema_field_create() missing required 'properties' [\"valid_types\"]")
            if len(valid_types) != 1:
                # REST wording (sg-groundtruth finding 019); the api3 answer has not been recorded.
                raise Fault("API schema_field_create() 'valid_types' value expected Array with one element")
        if data_type == "checkbox" and not isinstance(properties.get("default_value"), bool):
            raise Fault("API schema_field_create() Crud::ParameterError: Only true or false allowed in checkbox")

        live = self._schema[entity_type]
        retired = self._retired_fields.get(entity_type, {})
        base = code = field_code(display_name)
        suffix = 0
        while code in live or code in retired:
            if code in retired:
                raise Fault(_RETIRED_FIELD % code)
            suffix += 1
            code = "%s_%d" % (base, suffix)

        field = new_field(entity_type, data_type, display_name, properties)
        live[code] = field
        default = [] if data_type == "multi_entity" else field["properties"]["default_value"]["value"]
        for row in self._db[entity_type].values():
            row[code] = copy.deepcopy(default)
        column_id = self._column_ids[(entity_type, code)] = len(self._column_ids) + 1
        self._log(_events.field_created(self._event_user["name"], column_id, code))
        return code

    def schema_field_update(self, entity_type, field_name, properties, project_entity=None):
        properties = dict(properties or {})
        params = {
            "type": entity_type,
            "field_name": field_name,
            "properties": [{"property_name": k, "value": v} for k, v in properties.items()],
        }
        if field_name not in self._schema.get(entity_type, {}):
            raise Fault(
                "API schema_field_update() %s.%s doesn't exist:\n%s" % (entity_type, field_name, ruby_params(params))
            )
        if not properties:
            raise Fault("API schema_field_update() can't create/update with no 'properties':\n[]")
        for key, value in properties.items():
            if key not in UPDATABLE_PROPERTIES:
                raise Fault(
                    "API schema_field_update() invalid property '%s':\n%s\nValid property names:\n%s"
                    % (key, ruby_inspect({"property_name": key, "value": value}), ruby_list(UPDATABLE_PROPERTIES))
                )
        field = self._schema[entity_type][field_name]
        old_name = field["name"]["value"]
        for key, value in properties.items():
            if key == "summary_default":
                field["properties"].setdefault("summary_default", {"value": None, "editable": True})["value"] = value
            else:
                field[key]["value"] = value
        if field["name"]["value"] != old_name:
            self._log(_events.field_renamed(
                self._event_user["name"], self._column_id(entity_type, field_name), field_name,
                old_name, field["name"]["value"]))
        return True

    def schema_field_delete(self, entity_type, field_name):
        if field_name not in self._schema.get(entity_type, {}):
            raise Fault(
                "API schema_field_delete() %s.%s doesn't exist:\n%s"
                % (entity_type, field_name, ruby_params({"type": entity_type, "field_name": field_name}))
            )
        field = self._schema[entity_type].pop(field_name)
        self._retired_fields.setdefault(entity_type, {})[field_name] = field
        when = self._retired_at[("field", entity_type, field_name)] = self._clock()
        self._log(_events.field_retired(
            self._event_user["name"], self._column_id(entity_type, field_name), field_name, when))
        return True

    def revive_field(self, entity_type, field_name):
        """Bring a trashed field back as it was retired: original type, name and properties.

        A site offers this over REST only (``POST /schema/<Type>/fields/<field>``, finding 040);
        shotgun_api3 has no call for it. ``sg-mockgun serve`` exposes that route.
        """
        if field_name in self._schema.get(entity_type, {}):
            raise FieldReviveError("Field %s.%s is not retired." % (entity_type, field_name), 400)
        if field_name not in self._retired_fields.get(entity_type, {}):
            raise FieldReviveError("Retired field %s.%s does not exist." % (entity_type, field_name), 404)
        field = self._retired_fields[entity_type].pop(field_name)
        self._schema[entity_type][field_name] = field
        when = self._retired_at.pop(("field", entity_type, field_name), self._clock())
        self._log(_events.field_revived(
            self._event_user["name"], self._column_id(entity_type, field_name), field_name, when))
        return True

    def schema_entity_read(self):
        return self._schema_entity

    def schema_field_read(self, entity_type, field_name=None, project_entity=None):
        self._validate_entity_type(entity_type)
        if field_name is not None and field_name not in self._schema[entity_type]:
            raise Fault(
                "API schema_field_read() %s.%s doesn't exist:\n%s"
                % (entity_type, field_name, ruby_params({"type": entity_type, "field_name": field_name}))
            )
        names = list(self._schema[entity_type]) if field_name is None else [field_name]
        project_id = project_entity.get("id") if isinstance(project_entity, dict) else None
        # api3 064: with a project, `visible` and status `hidden_values` read that project's values.
        overlays = dict(
            (name, self._project_schema[(project_id, entity_type, name)]) for name in names
            if (project_id, entity_type, name) in self._project_schema
        )
        if not overlays:
            if field_name is None:
                return self._schema[entity_type]
            return {field_name: self._schema[entity_type][field_name]}
        out = {}
        for name in names:
            field = self._schema[entity_type][name]
            if name in overlays:
                field = copy.deepcopy(field)
                if "visible" in overlays[name]:
                    field["visible"]["value"] = overlays[name]["visible"]
                if "hidden_values" in overlays[name]:
                    field["properties"]["hidden_values"] = {"value": list(overlays[name]["hidden_values"]),
                                                            "editable": False}
            out[name] = field
        return out

    def set_project_schema(self, project, entity_type, field_name, visible=None, hidden_values=None):
        """Set what ``schema_field_read(project_entity=project)`` reads for one field's ``visible`` and ``hidden_values``."""
        self._validate_entity_fields(entity_type, [field_name])
        overlay = self._project_schema.setdefault((project["id"], entity_type, field_name), {})
        if visible is not None:
            overlay["visible"] = visible
        if hidden_values is not None:
            overlay["hidden_values"] = list(hidden_values)

    def find(
        self, entity_type, filters, fields=None, order=None, filter_operator=None,
        limit=0, retired_only=False, page=0, include_archived_projects=True,
        additional_filter_presets=None,
    ):
        # Argument checks and the limit and page arithmetic follow shotgun_api3.Shotgun.find.
        if not isinstance(limit, int) or limit < 0:
            raise ValueError("limit parameter must be a positive integer")
        if not isinstance(page, int) or page < 0:
            raise ValueError("page parameter must be a positive integer")
        # api3 024: the client copies `column` into `field_name` and fills `direction` with "asc".
        sorts = []
        for sort in order or []:
            sort = dict(sort)
            if "column" in sort:
                sort["field_name"] = sort["column"]
            sort.setdefault("direction", "asc")
            sorts.append({"field_name": sort["field_name"], "direction": sort["direction"]})

        # api3 020: the page size comes from server_info, and limit shrinks it.
        server_info = getattr(self, "server_info", None)
        page_size = _reads.page_size(server_info if isinstance(server_info, dict) else None)
        if limit and limit <= page_size:
            page_size = limit
            page = page or 1

        self.finds += 1

        self._validate_entity_type(entity_type)
        # do not validate custom fields - this makes it hard to mock up a field quickly
        # self._validate_entity_fields(entity_type, fields)

        # FIXME: This should be refactored so that we can use the complex filer
        # style in nested filter operations.
        if isinstance(filters, dict):
            # complex filter style!
            # {'conditions': [{'path': 'id', 'relation': 'is', 'values': [1]}], 'logical_operator': 'and'}

            resolved_filters = []
            for f in filters["conditions"]:

                if f["path"].startswith("$FROM$"):
                    # special $FROM$Task.step.entity syntax
                    # skip this for now
                    continue

                if len(f["values"]) != 1:
                    # {'path': 'id', 'relation': 'in', 'values': [1,2,3]} --> ["id", "in", [1,2,3]]
                    resolved_filters.append([f["path"], f["relation"], f["values"]])
                else:
                    # {'path': 'id', 'relation': 'is', 'values': [3]} --> ["id", "is", 3]
                    resolved_filters.append([f["path"], f["relation"], f["values"][0]])

        else:
            # traditiona style sg filters
            resolved_filters = filters

        # api3 013: validated before the scan.
        self._validate_filters(entity_type, resolved_filters)

        for sort in sorts:
            if sort["direction"] not in ("asc", "desc"):
                # api3 024
                raise Fault("API read() invalid/missing string 'direction':\n%s" % ruby_inspect(sort))

        if additional_filter_presets:
            params = _reads.read_params(
                entity_type, filters, filter_operator, list(fields) if fields else None, retired_only,
                page_size, page or 1, page == 0, additional_filter_presets, include_archived_projects,
            )
            latest_by = self._check_presets(entity_type, additional_filter_presets, params)

        results = [
            # Apply the filters for every single entities for the given entity type.
            row for row in self._db[entity_type].values()
            if self._row_matches_filters(
                entity_type, row, resolved_filters, filter_operator, retired_only
            )
        ]

        if not include_archived_projects:
            # api3 022: rows in an archived project, and archived Project rows, drop out.
            results = [
                row for row in results
                if not self._in_archived_project(row) and not (entity_type == "Project" and row.get("archived"))
            ]

        if additional_filter_presets:
            keep = self._latest_ids(entity_type, latest_by, retired_only)
            results = [row for row in results if row["id"] in keep]

        # finding 026: id ascending is the default order and the last tiebreak.
        results = sorted(results, key=lambda row: row["id"])

        keys = []
        for sort in sorts:
            # finding 026, api3 024: a summary, url or unknown field is ignored.
            try:
                field_type = self._get_field_type(entity_type, sort["field_name"])
            except (KeyError, ShotgunError):
                continue
            if field_type in ("summary", "url"):
                continue
            keys.append((sort["field_name"], sort["direction"] == "desc"))
        if keys:
            results = _reads.sort_rows(results, keys, lambda row, f: self._sort_value(entity_type, row, f))

        if page:
            results = results[(page - 1) * page_size:page * page_size]
        elif limit:
            results = results[:limit]

        if fields is None:
            fields = set(["type", "id"])
        else:
            fields = set(fields) | set(["type", "id"])

        # get the values requested
        val = [dict((field, self._read_field(entity_type, row, field)) for field in fields) for row in results]

        return val

    def find_one(
        self, entity_type, filters, fields=None, order=None, filter_operator=None,
        retired_only=False, include_archived_projects=True, additional_filter_presets=None,
    ):
        results = self.find(
            entity_type, filters, fields=fields,
            order=order, filter_operator=filter_operator, limit=1, retired_only=retired_only,
            include_archived_projects=include_archived_projects,
            additional_filter_presets=additional_filter_presets,
        )
        return results[0] if results else None

    def _check_presets(self, entity_type, presets, params):
        """Raise the site's Fault for a preset it refuses; return the LATEST latest_by value (api3 023)."""
        latest_by = None
        for preset in presets:
            if not isinstance(preset, dict):
                raise Fault("API read() invalid additional filter preset format. It must be a hash:\n%s"
                            % _reads.pp(params))
            if preset.get("preset_name") != "LATEST" or entity_type not in _reads.LATEST_BY:
                raise Fault("API read() Invalid additional filter preset provided: \n%s" % _reads.pp(params))
            if preset.get("latest_by") not in _reads.LATEST_BY[entity_type]:
                raise Fault("API read() CRUD ERROR #10: Read failed for entity type [%s]" % entity_type)
            latest_by = preset["latest_by"]
        return latest_by

    def _latest_ids(self, entity_type, latest_by, retired_only):
        """Ids LATEST keeps among the rows of one retirement state (api3 023)."""
        def link_key(value):
            return (value["type"], value["id"]) if isinstance(value, dict) else value

        if entity_type == "PublishedFile":
            def group(row):
                return tuple(link_key(row.get(f)) for f in _reads.PUBLISHED_FILE_GROUP)
        else:
            def group(row):
                return (link_key(row.get("entity")),)

        def rank(row):
            if latest_by != "BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT":
                return ()
            task = self._db["Task"].get((row.get("sg_task") or {}).get("id"), {})
            step = self._db["Step"].get((task.get("step") or {}).get("id"), {})
            order = step.get("list_order")
            return (-1 if order is None else order,)

        rows = [row for row in self._db[entity_type].values() if row["__retired"] == bool(retired_only)]
        return _reads.latest_ids(rows, group, rank)

    def _sort_value(self, entity_type, row, field):
        """The value a sort compares for one field of a row (api3 024, api3 025)."""
        value = self._get_field_from_row(entity_type, row, field)
        if value is None:
            return None
        field_type = self._get_field_type(entity_type, field)
        if field_type == "status_list" and "." not in field:
            valid = self._schema[entity_type][field]["properties"].get("valid_values", {}).get("value") or []
            return valid.index(value) if value in valid else len(valid)
        if field_type == "entity" and isinstance(value, dict):
            link = self._live_link(value)
            return link["name"] if link else None
        if field_type == "multi_entity" and isinstance(value, list):
            # multi_entity sort order unprobed (sg-mockgun#39)
            return tuple(link["name"] or "" for link in map(self._live_link, value) if link) or None
        return value

    def _in_archived_project(self, row):
        """Return True when the row's project links a Project whose archived is True."""
        project = row.get("project")
        if not isinstance(project, dict) or project.get("type") != "Project":
            return False
        linked = self._db.get("Project", {}).get(project.get("id"))
        return bool(linked and linked.get("archived") is True)

    def batch(self, requests):
        for request in requests:
            if request["request_type"] not in ("create", "update", "delete"):
                raise ShotgunError("Invalid request type %s in request %s" % (request["request_type"], request))
        # api3 063: one failing request rolls back every other one. Ids already handed out stay spent.
        saved = copy.deepcopy((self._db, self._retired_at, self._delete_effects))
        results = []
        for index, request in enumerate(requests):
            try:
                if request["request_type"] == "create":
                    results.append(self.create(request["entity_type"], request["data"]))
                elif request["request_type"] == "update":
                    results.append(self.update(request["entity_type"], request["entity_id"], request["data"],
                                               request.get("multi_entity_update_modes")))
                else:
                    results.append(self.delete(request["entity_type"], request["entity_id"]))
            except ShotgunError as e:
                self._db, self._retired_at, self._delete_effects = saved
                raise Fault(_records.rolled_back(index, str(e)))
        return results

    def create(self, entity_type, data, return_fields=None):

        # special handling of storage fields - if a field value
        # is a dict with a key local_path, then add fields
        # local_path_linux, local_path_windows, local_path_mac
        # as a reflection of this
        for d in data:
            if isinstance(data[d], dict) and "local_path" in data[d]:
                # partly imitate some of the business logic happening on the
                # server side of shotgun when a file/link entity value is created
                if "local_storage" not in data[d]:
                    data[d]["local_storage"] = {"id": 0, "name": "auto_generated_by_mockgun", "type": "LocalStorage"}
                if "local_path_linux" not in data[d]:
                    data[d]["local_path_linux"] = data[d]["local_path"]
                if "local_path_windows" not in data[d]:
                    data[d]["local_path_windows"] = data[d]["local_path"]
                if "local_path_mac" not in data[d]:
                    data[d]["local_path_mac"] = data[d]["local_path"]

        self._validate_entity_type(entity_type)
        self._check_create_contract(entity_type, data, return_fields)
        data = dict(data)
        upload_image = data.pop("image", None)  # api3 035: the client never sends image on create
        data = self._validate_entity_data(entity_type, data, "create")
        data = self._check_status(entity_type, data, "create")
        self._validate_entity_fields(entity_type, return_fields)
        next_id = self._next_id(entity_type)

        row = self._get_new_row(entity_type)

        self._update_row(entity_type, row, data)
        row["id"] = next_id
        now = self._clock()
        server_set = _writes.new_row_values(
            entity_type, self._schema[entity_type], self._event_user, now, display_name(entity_type, row))
        row.update((field, value) for field, value in server_set.items() if field not in data)
        identity = _records.IDENTITY_FIELDS.get(entity_type)
        if identity and identity not in data:
            # finding 012, api3 060
            row[identity] = "New %s %d" % (self._schema_entity[entity_type]["name"]["value"], next_id)

        self._db[entity_type][next_id] = row

        if entity_type != "EventLogEntry":
            changes = [
                (field, self._display_name(entity_type, field), self._get_field_type(entity_type, field), row[field])
                for field in data
                if row.get(field) not in (None, [])
            ]
            self._log(
                _events.entity_created(self._event_user["name"], entity_type, next_id, self._row_name(row), changes),
                row, now=now,
            )
        _taskflow.after_create(self, entity_type, row, data)

        # api3 038: the fields sent, plus the return_fields asked for.
        result = dict((field, self._read_field(entity_type, row, field)) for field in data)
        result.update((field, self._read_field(entity_type, row, field)) for field in return_fields or [])

        result["type"] = row["type"]
        result["id"] = row["id"]

        if upload_image:
            self._client_upload_image(entity_type, row["id"], upload_image, result)
        return result

    def update(self, entity_type, entity_id, data, multi_entity_update_modes=None):
        self._validate_entity_type(entity_type)
        data = dict(data)
        upload_image = data.pop("image") if data.get("image") is not None else None  # api3 035
        dotted = dict((field, data.pop(field)) for field in list(data) if "." in field)
        self._validate_entity_fields(entity_type, dotted.keys())
        data = self._validate_entity_data(entity_type, data)
        data = self._check_status(entity_type, data, "update")
        self._validate_entity_exists(entity_type, entity_id, "update")
        _taskflow.before_update(self, entity_type, data)

        row = self._db[entity_type][entity_id]
        before = dict((field, copy.deepcopy(row.get(field))) for field in data)
        self._update_row(entity_type, row, data, multi_entity_update_modes)
        if entity_type != "EventLogEntry":
            rows = []
            for field in data:
                if row.get(field) != before[field]:
                    rows += [_events.attribute_change(
                        self._event_user["name"], entity_type, entity_id, self._row_name(row), field,
                        self._display_name(entity_type, field), self._get_field_type(entity_type, field),
                        before[field], row.get(field))]
            self._log(rows, row)
        _taskflow.after_update(self, entity_type, row, data, before)

        self._write_through(row, dotted)

        result = dict((field, self._read_field(entity_type, row, field)) for field in data)
        result["type"] = row["type"]
        result["id"] = row["id"]
        result.update(dotted)
        if upload_image:
            self._client_upload_image(entity_type, entity_id, upload_image, result)
        return result

    def delete(self, entity_type, entity_id):
        self._validate_entity_type(entity_type)
        self._validate_entity_exists(entity_type, entity_id, "delete")

        row = self._db[entity_type][entity_id]
        if not row["__retired"]:
            row["__retired"] = True
            if entity_type != "EventLogEntry":
                when = self._retired_at[(entity_type, entity_id)] = self._clock()
                # A delete drops the entity link from every earlier row for it (finding 049).
                link = {"type": entity_type, "id": entity_id}
                for event in self._db.get("EventLogEntry", {}).values():
                    if event.get("entity") == link:
                        event["entity"] = None
                self._log(
                    _events.entity_retired(self._event_user["name"], entity_type, entity_id, self._row_name(row), when),
                    row, linked=False,
                )
            _taskflow.after_delete(self, entity_type, row)
            if entity_type != "EventLogEntry":
                self._apply_delete_effects(entity_type, entity_id)
            return True
        else:
            return False

    def revive(self, entity_type, entity_id):
        self._validate_entity_type(entity_type)
        self._validate_entity_exists(entity_type, entity_id)

        row = self._db[entity_type][entity_id]
        if row["__retired"]:
            row["__retired"] = False
            if entity_type != "EventLogEntry":
                when = self._retired_at.pop((entity_type, entity_id), self._clock())
                self._log(
                    _events.entity_revived(self._event_user["name"], entity_type, entity_id, self._row_name(row), when),
                    row,
                )
                self._undo_delete_effects(entity_type, entity_id)
            _taskflow.after_revive(self, entity_type, row)
            return True
        else:
            return False

    def _write_through(self, row, dotted):
        """Write each `link.Type.field` value to the row the link points at (api3 039)."""
        for path, value in dotted.items():
            link_field, target_type, target_field = path.split(".", 2)
            link = row.get(link_field)
            # A link that is empty or of another type: api3 unprobed (sg-mockgun#39); nothing is written.
            if isinstance(link, dict) and link.get("type") == target_type:
                self.update(target_type, link["id"], {target_field: value})

    def _client_upload_image(self, entity_type, entity_id, path, result):
        """Upload an image the way the client does after its create or update (api3 035)."""
        path = os.path.abspath(os.path.expanduser(path or ""))
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file, got '%s'" % path)
        self.upload_thumbnail(entity_type, entity_id, path)
        result["image"] = self.find_one(entity_type, [["id", "is", entity_id]], ["image"])["image"]

    ###################################################################################################
    # media: upload, thumbnails, download (sg_mockgun.media, api3 053 to 058)

    def upload(self, entity_type, entity_id, path, field_name=None, display_name=None, tag_list=None,
               created_at=None):
        """Store the file's bytes on a new Attachment linked to the entity and return its id (api3 053)."""
        path = self._upload_path(path, created_at)
        if field_name in _media.THUMBNAIL_FIELDS:
            return self._upload_thumbnail(entity_type, entity_id, path, _media.THUMBNAIL_FIELDS[field_name])
        self._check_upload_target(entity_type, entity_id, path)
        if field_name is not None and self._schema[entity_type].get(field_name, {}).get(
                "data_type", {}).get("value") != "url":
            raise ShotgunError(_media.upload_refusal(path, self.config, _media.invalid_column(entity_type, field_name)))
        with open(path, "rb") as f:
            content = f.read()
        filename = os.path.basename(path)
        name = display_name or filename
        entity = self._db[entity_type][entity_id]
        data = {
            "attachment_links": [{"type": entity_type, "id": entity_id}],
            "original_fname": filename,
            "display_name": name,
            "tags": [self._tag_link(tag) for tag in _media.tag_names(tag_list)],
        }
        if isinstance(entity.get("project"), dict):
            data["project"] = {"type": "Project", "id": entity["project"]["id"]}
        if created_at is not None:
            data["created_at"] = created_at
        attachment_id = self.create("Attachment", data)["id"]
        row = self._db["Attachment"][attachment_id]
        url = _media.storage_url(("Attachment", attachment_id), filename)
        row["filename"] = filename
        row["cached_display_name"] = name
        row["this_file"] = _media.this_file(url, name, filename, attachment_id)
        self._media_state["files"][attachment_id] = content
        self._media_state["urls"][url] = attachment_id
        if field_name is not None:
            entity[field_name] = copy.deepcopy(row["this_file"])
            if _media.makes_thumbnail(filename):
                # api3 053: a media upload makes a thumbnail, for the Attachment and the entity.
                final = _media.storage_url(("Attachment", attachment_id, "image"), _media.thumbnail_name(filename))
                row["image_source_entity"] = {"type": "Attachment", "id": attachment_id}
                row["processing_status"] = _media.PENDING_STATUS
                self._set_pending("Attachment", attachment_id, "image", final)
                if "image" in self._schema[entity_type]:
                    self._set_pending(entity_type, entity_id, "image", final)
        return attachment_id

    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Set the entity's image, transient until ``finalize_thumbnails``; return a thumbnail id (api3 055)."""
        return self.upload(entity_type, entity_id, path, field_name="thumb_image", **kwargs)

    def upload_filmstrip_thumbnail(self, entity_type, entity_id, path, **kwargs):
        """Set the entity's filmstrip_image at once; return a thumbnail id (api3 055)."""
        return self.upload(entity_type, entity_id, path, field_name="filmstrip_thumb_image", **kwargs)

    def finalize_thumbnails(self):
        """Mock only: end every pending transcode, so each transient image reads its final URL."""
        for (entity_type, entity_id, field), final in self._media_state["pending"].items():
            row = self._db.get(entity_type, {}).get(entity_id)
            if row is not None and row.get(field) == _media.transient_url(self.config):
                row[field] = final
        self._media_state["pending"] = {}

    def share_thumbnail(self, entities, thumbnail_path=None, source_entity=None, filmstrip_thumbnail=False,
                        **kwargs):
        """Point the entities' image at the source's thumbnail and return its id (api3 058)."""
        # The client's own checks, word for word.
        if not isinstance(entities, list) or len(entities) == 0:
            raise ShotgunError("'entities' parameter must be a list of entity hashes and may not be empty")
        for e in entities:
            if not isinstance(e, dict) or "id" not in e or "type" not in e:
                raise ShotgunError("'entities' parameter must be a list of entity hashes with at least "
                                   "'type' and 'id' keys.\nInvalid entity: %s" % e)
        if (not thumbnail_path and not source_entity) or (thumbnail_path and source_entity):
            raise ShotgunError("You must supply either thumbnail_path OR source_entity.")
        if thumbnail_path:
            source_entity = entities.pop(0)
            upload = self.upload_filmstrip_thumbnail if filmstrip_thumbnail else self.upload_thumbnail
            thumb_id = upload(source_entity["type"], source_entity["id"], thumbnail_path, **kwargs)
            if len(entities) == 0:
                return thumb_id
        elif not isinstance(source_entity, dict) or "id" not in source_entity or "type" not in source_entity:
            raise ShotgunError("'source_entity' parameter must be a dict with at least 'type' and 'id' keys."
                               "\nGot: %s (%s)" % (source_entity, type(source_entity)))
        field = "filmstrip_image" if filmstrip_thumbnail else "image"
        for e in entities:
            if e["id"] not in self._db.get(e["type"], {}):
                raise ShotgunError(_media.share_missing(e["type"], e["id"]))
        source = self._db[source_entity["type"]][source_entity["id"]]
        image = source.get(field)
        if image == _media.transient_url(self.config):
            raise ShotgunThumbnailNotReady(_media.NOT_READY)
        for e in entities:
            self._db[e["type"]][e["id"]][field] = image
        if image is None:
            return None
        return self._media_state["thumbnail_ids"].get((source_entity["type"], source_entity["id"]))

    def get_attachment_download_url(self, attachment):
        """The URL download_attachment fetches; client-side, no request (api3 057)."""
        return _media.attachment_download_url(self.config, attachment)

    def download_attachment(self, attachment=False, file_path=None, attachment_id=None):
        """Return an uploaded file's bytes, or write them to ``file_path`` and return it (api3 056)."""
        if attachment is False:
            if type(attachment_id) == int:
                attachment = attachment_id
            else:
                raise TypeError("Missing parameter 'attachment'. Expected a dict, int, NoneType value or"
                                "an int for parameter attachment_id")
        fp = open(file_path, "wb") if file_path else None
        try:
            url = self.get_attachment_download_url(attachment)
            if url is None:
                return None
            content = self._stored_bytes(url)
            if fp is None:
                return content
            fp.write(content)
            return file_path
        finally:
            if fp is not None:
                fp.close()

    def _upload_path(self, path, created_at):
        """The client's checks on the local file, before any request."""
        path = os.path.abspath(os.path.expanduser(path or ""))
        if not os.path.isfile(path):
            raise ShotgunError("Path must be a valid file, got '%s'" % path)
        if os.path.getsize(path) == 0:
            raise ShotgunError("Path cannot be an empty file: '%s'" % path)
        if created_at is not None and not isinstance(created_at, datetime.datetime):
            raise ShotgunError("created_at must be a datetime.datetime instance, got '%s'" % type(created_at))
        return path

    def _check_upload_target(self, entity_type, entity_id, path):
        if entity_type not in self._schema:
            raise ShotgunError(_media.upload_refusal(path, self.config, _media.invalid_class(entity_type)))
        row = self._db[entity_type].get(entity_id)
        if row is None or row["__retired"]:
            raise ShotgunError(_media.upload_refusal(path, self.config, _media.entity_not_found(entity_type, entity_id)))

    def _upload_thumbnail(self, entity_type, entity_id, path, field):
        """api3 055: no Attachment; the id comes from a sequence of its own."""
        self._check_upload_target(entity_type, entity_id, path)
        thumb_id = self._media_state["next_thumbnail_id"]
        self._media_state["next_thumbnail_id"] += 1
        filename = os.path.basename(path)
        if field in self._schema[entity_type]:
            if field == "image":
                final = _media.storage_url((entity_type, entity_id, thumb_id), _media.thumbnail_name(filename))
                self._set_pending(entity_type, entity_id, field, final)
                self._media_state["thumbnail_ids"][(entity_type, entity_id)] = thumb_id
            else:
                # A filmstrip is not transcoded: it reads the uploaded file at once.
                self._db[entity_type][entity_id][field] = _media.storage_url((entity_type, entity_id, thumb_id), filename)
        return thumb_id

    def _set_pending(self, entity_type, entity_id, field, final):
        self._db[entity_type][entity_id][field] = _media.transient_url(self.config)
        self._media_state["pending"][(entity_type, entity_id, field)] = final

    def _tag_link(self, name):
        """A link to the Tag of that name, created when missing (api3 053)."""
        tag = self.find_one("Tag", [["name", "is", name]])
        if tag is None:
            tag = self.create("Tag", {"name": name})
        return {"type": "Tag", "id": tag["id"]}

    def _stored_bytes(self, url):
        """The bytes a download URL serves; ShotgunFileDownloadError when nothing is stored there."""
        if url.startswith("file://"):
            # The client opens a local link's file:// URL with a urllib opener and wraps URLError.
            try:
                with urllib.request.build_opener().open(urllib.request.Request(url)) as response:
                    return response.read()
            except urllib.error.URLError as e:
                raise ShotgunFileDownloadError("Failed to open %s\n%s" % (url, e))
        attachment_id = _media.attachment_id_of(self.config, self._media_state, url)
        row = self._db["Attachment"].get(attachment_id)
        if row is None or row["__retired"] or attachment_id not in self._media_state["files"]:
            raise ShotgunFileDownloadError(_media.download_failure(url))
        return self._media_state["files"][attachment_id]

    def add_user_agent(self, agent):
        pass

    def set_session_uuid(self, session_uuid):
        pass

    ###################################################################################################
    # internal methods and members

    def _log(self, rows, source=None, linked=True, now=None):
        """Append event rows, filling id, entity, project, user and created_at."""
        if not rows or not self.generate_event_log_entries or "EventLogEntry" not in self._db:
            return
        table = self._db["EventLogEntry"]
        now = now or self._clock()
        for partial in rows:
            event = self._get_new_row("EventLogEntry")
            event.update(partial)
            event_id = max(table) + 1 if table else 1
            event["id"] = event_id
            event["user"] = dict(self._event_user)
            event["created_at"] = now
            if source is not None:
                event["entity"] = {"type": source["type"], "id": source["id"]} if linked else None
                project = source.get("project")
                event["project"] = {"type": project["type"], "id": project["id"]} if project else None
            table[event_id] = event

    def _column_id(self, entity_type, field_name):
        key = (entity_type, field_name)
        if key not in self._column_ids:
            self._column_ids[key] = len(self._column_ids) + 1
        return self._column_ids[key]

    def _display_name(self, entity_type, field):
        try:
            return self._schema[entity_type][field]["name"]["value"]
        except KeyError:
            return field

    @staticmethod
    def _row_name(row):
        for field in ("code", "name", "content", "title"):
            if row.get(field):
                return row[field]
        return None

    def _validate_entity_type(self, entity_type):
        if entity_type not in self._schema:
            raise ShotgunError("%s is not a valid entity" % entity_type)

    def _validate_entity_data(self, entity_type, data, verb="update"):
        """Raise ShotgunError on a value the site refuses; return data with each value as stored."""
        if "id" in data or "type" in data:
            raise ShotgunError("Can't set id or type on create or update")

        fields = self._schema[entity_type]
        for field, item in data.items():
            if "." in field:
                self._validate_entity_fields(entity_type, [field])
            elif field not in fields:
                raise _writes.unknown_field(verb, entity_type, field, item)  # api3 039

        stored = dict(data)
        for field, item in data.items():
            if field not in fields:
                continue
            field_info = fields[field]
            sg_type = field_info["data_type"]["value"]
            editable = field_info.get("editable", {}).get("value", False)
            item = stored[field] = _writes.check_value(verb, entity_type, field, sg_type, item, editable)

            if item is None or (entity_type, field) == ("Task", "splits"):
                continue
            if sg_type in _writes.RULES and sg_type not in ("multi_entity", "serializable"):
                continue

            if field_info["data_type"]["value"] == "multi_entity":
                if not isinstance(item, list):
                    raise ShotgunError(
                        "%s.%s is of type multi_entity, but data %s is not a list" %
                        (entity_type, field, item)
                    )
                elif item and any(not isinstance(sub_item, dict) for sub_item in item):
                    raise ShotgunError(
                        "%s.%s is of type multi_entity, but data %s contains a non-dictionary" %
                        (entity_type, field, item)
                    )
                elif item and any("id" not in sub_item or "type" not in sub_item for sub_item in item):
                    raise ShotgunError(
                        "%s.%s is of type multi-entity, but an item in data %s does not contain 'type' and 'id'" %
                        (entity_type, field, item)
                    )
                elif item and any(
                    sub_item["type"] not in field_info["properties"]["valid_types"]["value"] for sub_item in item
                ):
                    raise ShotgunError(
                        "%s.%s is of multi-type entity, but an item in data %s has an invalid type (expected one of %s)"
                        % (entity_type, field, item, field_info["properties"]["valid_types"]["value"])
                    )

            elif field_info["data_type"]["value"] == "entity":
                if not isinstance(item, dict):
                    raise ShotgunError(
                        "%s.%s is of type entity, but data %s is not a dictionary" %
                        (entity_type, field, item)
                    )
                elif "id" not in item or "type" not in item:
                    raise ShotgunError(
                        "%s.%s is of type entity, but data %s does not contain 'type' and 'id'"
                        % (entity_type, field, item)
                    )
                # elif item["type"] not in field_info["properties"]["valid_types"]["value"]:
                #    raise ShotgunError(
                #        "%s.%s is of type entity, but data %s has an invalid type (expected one of %s)" %
                #        (entity_type, field, item, field_info["properties"]["valid_types"]["value"])
                #    )

            else:
                try:
                    sg_type = field_info["data_type"]["value"]
                    python_type = {"number": int,
                                   "float": float,
                                   "checkbox": bool,
                                   "percent": int,
                                   "text": str,
                                   "serializable": dict,
                                   "entity_type": str,
                                   "date": str,
                                   "date_time": datetime.datetime,
                                   "duration": int,
                                   "list": str,
                                   "status_list": str,
                                   "url": dict}[sg_type]
                except KeyError:
                    raise ShotgunError(
                        "Field %s.%s: Handling for Flow Production Tracking type %s is not implemented" %
                        (entity_type, field, sg_type)
                    )

                if not isinstance(item, python_type):
                    raise ShotgunError(
                        "%s.%s is of type %s, but data %s is not of type %s" %
                        (entity_type, field, type(item), sg_type, python_type)
                    )

                # TODO: add check for correct timezone

        return stored

    def _validate_entity_fields(self, entity_type, fields):
        self._validate_entity_type(entity_type)
        if fields is not None:
            valid_fields = set(self._schema[entity_type].keys())
            for field in fields:
                try:
                    field2, entity_type2, field3 = field.split(".", 2)
                    self._validate_entity_fields(entity_type2, [field3])
                except ValueError:
                    if field not in valid_fields and field not in ("type", "id"):
                        raise ShotgunError("%s is not a valid field for entity %s" % (field, entity_type))

    def _get_default_value(self, entity_type, field):
        """Return the value a new row reads for this field."""
        field_info = self._schema[entity_type][field]
        field_type = field_info["data_type"]["value"]
        default_value = field_info["properties"]["default_value"]["value"]
        if field_type == "multi_entity":
            return []  # field_types/multi_entity
        if field_type == "checkbox":
            return bool(default_value)  # field_types/checkbox: never None
        if field_type == "password":
            return "*******"  # field_types/password
        if field_type == "pivot_column":
            return None  # field_types/pivot_column
        if field_type in ("text", "date") and default_value == "":
            return None  # field_types/text, field_types/date
        if field_type in ("number", "percent", "duration", "timecode") and isinstance(default_value, str):
            # entity_types/Playlist: a "0" default reads 0.
            return int(default_value) if default_value else None
        if field_type == "float" and isinstance(default_value, str):
            return float(default_value) if default_value else None
        return default_value

    def _get_new_row(self, entity_type):
        row = {"type": entity_type, "__retired": False}
        for field in self._schema[entity_type]:
            row[field] = self._get_default_value(entity_type, field)
        return row

    def _compare(self, field_type: str, lval: Any, operator: str, rval: Any) -> bool:
        """
        Compares a field using the operator and value provide by the filter.

        :param str field_type: Type of the field we are operating on.
        :param lval: Value inside that field. Can be of any type: datetime, date, int, str, bool, etc.
        :param str operator: Name of the operator to use.
        :param rval: The value following the operator in a filter.

        :returns: The result of the operator that was applied.
        :rtype: bool
        """
        # A list of scalar values comes from a dotted path through a multi_entity field.
        # A jsonb array is one value.
        if isinstance(lval, list) and field_type not in ("multi_entity", "jsonb"):
            # No linked row of the named type reads null (api3 012).
            if not lval:
                return self._compare(field_type, None, operator, rval)
            # Compare each one. If one matches the predicate we're good!
            return any((self._compare(field_type, sub_val, operator, rval)) for sub_val in lval)

        if field_type == "checkbox":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
        elif field_type in ("float", "number", "percent", "duration", "timecode", "date", "date_time"):
            is_date = field_type in ("date", "date_time")
            # api3 014
            if is_date and (operator in RELATIVE or operator in CALENDAR):
                return relative_match(lval, operator, filter_values(rval), self._clock(), field_type == "date")
            if is_date and operator in ("in", "not_in") and not isinstance(rval, list):
                rval = [rval]
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            # Comparisons exclude null rows; negations include them (field_types/number, field_types/date).
            elif operator == "less_than":
                return lval is not None and rval is not None and lval < rval
            elif operator == "greater_than":
                return lval is not None and rval is not None and lval > rval
            elif operator == "between":
                low, high = rval
                if lval is None or low is None or high is None:
                    return False
                # A date range is order-insensitive (field_types/date).
                if is_date and low > high:
                    low, high = high, low
                return low <= lval <= high
            elif operator == "in":
                return lval in rval
            elif operator == "not_in":
                return lval not in rval
        elif field_type in ("list", "status_list", "entity_type", "color", "uuid"):
            # A bare scalar stands for a one-element list, and "" for None (field_types/list, field_types/uuid).
            if operator in ("in", "not_in"):
                rval = rval if isinstance(rval, list) else [rval]
                rval = [None if val == "" else val for val in rval]
            elif rval == "":
                rval = None
            # List and status_list match case-insensitively, as text does (field_types/list).
            if field_type in ("list", "status_list"):
                lval = lval.lower() if isinstance(lval, str) else lval
                if isinstance(rval, list):
                    rval = [val.lower() if isinstance(val, str) else val for val in rval]
                elif isinstance(rval, str):
                    rval = rval.lower()
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "in":
                return lval in rval
            elif operator == "not_in":
                return lval not in rval
        elif field_type == "image":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
        elif field_type == "jsonb":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "contains":
                return jsonb_contains(lval, rval)
            elif operator == "not_contains":
                return not jsonb_contains(lval, rval)
        elif field_type == "text":
            # Some operations expect a list but can deal with a single value
            if operator in ("in", "not_in") and not isinstance(rval, list):
                rval = [rval]
            # A "" write stores null, and `is ""` matches the null rows (api3 030).
            elif operator in ("is", "is_not") and rval == "":
                rval = None
            # Some operation expect a string but can deal with None
            elif operator in ("starts_with", "ends_with", "contains", "not_contains"):
                lval = lval or ''
                rval = rval or ''
            # Shotgun string comparison is case insensitive
            lval = lval.lower() if lval is not None else None
            if isinstance(rval, list):
                rval = [val.lower() if val is not None else None for val in rval]
            else:
                rval = rval.lower() if rval is not None else None

            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "in":
                return lval in rval
            elif operator == "contains":
                return rval in lval
            elif operator == "not_contains":
                return rval not in lval
            elif operator == "starts_with":
                return lval.startswith(rval)
            elif operator == "ends_with":
                return lval.endswith(rval)
            elif operator == "not_in":
                return lval not in rval
        elif field_type == "entity":
            # field_types/entity
            if operator in ("in", "not_in") and isinstance(rval, dict):
                rval = [rval]
            if operator == "is":
                if lval is None or rval is None:
                    return lval == rval
                return lval["type"] == rval["type"] and lval["id"] == rval["id"]
            elif operator == "is_not":
                if lval is None or rval is None:
                    return lval != rval
                return lval["type"] != rval["type"] or lval["id"] != rval["id"]
            # `type_is None` means unset; unset rows match every negation (api3 010).
            elif operator == "type_is" and rval is None:
                return lval is None
            elif operator == "type_is_not" and rval is None:
                return lval is not None
            elif lval is None and operator in ("in", "type_is", "name_is", "name_contains"):
                return False
            elif lval is None and operator in ("not_in", "type_is_not", "name_not_contains"):
                return True
            elif operator == "in":
                return any(_same_link(lval, sub_rval) for sub_rval in rval)
            elif operator == "not_in":
                return not any(_same_link(lval, sub_rval) for sub_rval in rval)
            elif operator == "type_is":
                return lval["type"] == rval
            elif operator == "type_is_not":
                return lval["type"] != rval
            elif operator == "name_is":
                return _link_name(lval) == rval
            elif operator == "name_contains":
                return rval in _link_name(lval)
            elif operator == "name_not_contains":
                return rval not in _link_name(lval)
        elif field_type == "multi_entity":
            # field_types/multi_entity
            # filter_refusal has refused any other list length and an empty `in` list.
            if operator == "is" and isinstance(rval, list):
                rval = rval[0]
            if operator in ("in", "not_in") and isinstance(rval, dict):
                rval = [rval]
            if operator == "is":
                if rval is None:
                    return len(lval) == 0
                return any(_same_link(sub_lval, rval) for sub_lval in lval)
            elif operator == "is_not":
                if rval is None:
                    return len(lval) != 0
                return not any(_same_link(sub_lval, rval) for sub_lval in lval)
            elif operator == "in":
                return any(_same_link(sub_lval, sub_rval) for sub_lval in lval for sub_rval in rval)
            elif operator == "not_in":
                return not any(_same_link(sub_lval, sub_rval) for sub_lval in lval for sub_rval in rval)
            # `type_is None` means no links; empty rows match every negation (api3 011).
            elif operator == "type_is" and rval is None:
                return len(lval) == 0
            elif operator == "type_is_not" and rval is None:
                return len(lval) != 0
            elif operator == "type_is":
                return any(sub_lval["type"] == rval for sub_lval in lval)
            elif operator == "type_is_not":
                return not any(sub_lval["type"] == rval for sub_lval in lval)
            elif operator == "name_is":
                return any(_link_name(sub_lval) == rval for sub_lval in lval)
            elif operator == "name_contains":
                return any(rval in _link_name(sub_lval) for sub_lval in lval)
            elif operator == "name_not_contains":
                return not any(rval in _link_name(sub_lval) for sub_lval in lval)

        raise ShotgunError("mockgun does not implement the '%s' relation on the '%s' data type" % (operator, field_type))

    def _get_field_from_row(self, entity_type, row, field):
        # split dotted form fields
        try:
            # is it something like sg_sequence.Sequence.code ?
            field2, entity_type2, field3 = field.split(".", 2)

            if field2 in row:

                field_value = row[field2]

                # If we have a list of links, retrieve the subfields one by one.
                if isinstance(field_value, list):
                    values = []
                    for linked_row in field_value:
                        # Make sure we're actually iterating on links.
                        if not isinstance(linked_row, dict):
                            raise ShotgunError("Invalid deep query field %s.%s" % (entity_type, field))

                        # Skips entities that are not of the requested type.
                        if linked_row["type"] != entity_type2:
                            continue

                        entity = self._db[linked_row["type"]][linked_row["id"]]

                        sub_field_value = self._get_field_from_row(entity_type2, entity, field3)
                        values.append(sub_field_value)
                    return values
                # The field is not set, so return None.
                elif field_value is None:
                    return None
                # not multi entity, must be entity.
                elif not isinstance(field_value, dict):
                    raise ShotgunError("Invalid deep query field %s.%s" % (entity_type, field))

                # A link to another type reads the path as null (field_types/entity).
                if entity_type2 != field_value["type"]:
                    return None

                # ok so looks like the value is an entity link
                # e.g. db contains: {"sg_sequence": {"type":"Sequence", "id": 123 } }
                linked_row = self._db[field_value["type"]][field_value["id"]]

                return self._get_field_from_row(entity_type2, linked_row, field3)
            else:
                # sg returns none for unknown stuff
                return None

        except ValueError:
            # this is not a deep-linked field - just something like "code"
            if field in row:
                return row[field]
            else:
                # sg returns none for unknown stuff
                return None

    def _get_field_type(self, entity_type, field):
        """Return the data type of a field or of the last field of a dotted path."""
        parts = field.split(".")
        if len(parts) < 3:
            return self._schema[entity_type][field]["data_type"]["value"]
        # Each named type must have the field after it, whatever the link's valid_types (finding 016).
        for i in range(1, len(parts) - 1, 2):
            fields = self._schema.get(parts[i], {})
            if parts[i + 1] not in fields:
                # REST wording; api3 unprobed (sg-mockgun#39)
                raise ShotgunError("%s.%s doesn't exist." % (entity_type, field))
        return fields[parts[-1]]["data_type"]["value"]

    def _row_matches_filter(self, entity_type, row, sg_filter, retired_only):

        try:
            field, operator, rval = sg_filter
        except ValueError:
            raise ShotgunError("Filters must be in the form [lval, operator, rval]")

        # Special case, field is None when we have a filter operator.
        if field is None:
            if operator in ["any", "all"]:
                return self._row_matches_filters(entity_type, row, rval, operator, retired_only)
            else:
                raise ShotgunError("Unknown filter_operator type: %s" % operator)
        else:

            lval = self._get_field_from_row(entity_type, row, field)

            field_type = self._get_field_type(entity_type, field)

            # A link to a retired row reads None, or drops out of the list (api3 027).
            if field_type == "entity" and isinstance(lval, dict) and self._is_retired_link(lval):
                lval = None
            elif field_type == "multi_entity" and isinstance(lval, list):
                lval = [link for link in lval if not self._is_retired_link(link)]
            elif field_type == "calculated":
                field_type = calculated_type(self._field_properties(entity_type, field))

            # Name operators compare the display name `find` returns, on copies of the stored links (finding 060).
            if field_type == "entity" and isinstance(lval, dict):
                lval = self._named_link(lval)
            elif field_type == "multi_entity" and operator.startswith("name_") and isinstance(lval, list):
                lval = [self._named_link(link) for link in lval]

            if (entity_type, field) in IGNORED:
                return True
            return self._compare(field_type, lval, operator, rval)

    def _is_retired_link(self, link):
        row = self._db.get(link.get("type"), {}).get(link.get("id"))
        return bool(row and row.get("__retired"))

    def _field_properties(self, entity_type, path):
        """The schema properties of a field, or of the last field of a dotted path."""
        parts = path.split(".")
        return self._schema[parts[-2] if len(parts) > 1 else entity_type][parts[-1]].get("properties", {})

    def _filter_field_type(self, entity_type, path):
        """The data type a filter path ends on, or None when a hop names no field (api3 013)."""
        parts = path.split(".")
        if len(parts) % 2 == 0:
            return None
        fields = self._schema.get(entity_type, {})
        for i in range(0, len(parts) - 1, 2):
            if parts[i] not in fields:
                return None
            fields = self._schema.get(parts[i + 1], {})
        if parts[-1] not in fields:
            return None
        return fields[parts[-1]]["data_type"]["value"]

    def _validate_filters(self, entity_type, filters):
        """Raise what the api3 client raises building ``filters``, then the site's refusal of any of them."""
        disabled = _api3.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION
        for field, operator, rval in self._flat_filters(filters):
            if client_index_error(field, operator, rval, disabled):
                # api3 011, api3 015: the client's `values[0]` on an empty list.
                raise IndexError("list index out of range")
        for field, operator, rval in self._flat_filters(filters):
            field_type = self._filter_field_type(entity_type, field)
            if field_type is None:
                raise Fault(unknown_field(entity_type, field, operator, rval))
            last_type, last_field = entity_type, field
            while last_field.count(".") >= 2:
                _, last_type, last_field = last_field.split(".", 2)
            if (last_type, last_field) in IGNORED:
                continue
            if field_type == "calculated":
                # api3 002, api3 006
                if operator in ("in", "not_in") and None in filter_values(rval):
                    raise Fault("API read() CRUD ERROR #10: Read failed for entity type [%s]" % last_type)
                field_type = calculated_type(self._field_properties(entity_type, field))
            refusal = filter_refusal(last_type, last_field, field_type, operator, rval, path=field)
            if refusal:
                raise Fault(refusal)

    def _flat_filters(self, filters):
        """Each ``[field, operator, value]`` in ``filters``, nested groups included."""
        for sg_filter in self._rearrange_filters(filters):
            if len(sg_filter) != 3:
                continue
            field, operator, rval = sg_filter
            if field is None:
                if operator in ("any", "all"):
                    for nested in self._flat_filters(rval):
                        yield nested
                continue
            yield field, operator, rval

    def _rearrange_filters(self, filters: list) -> None:
        """
        Modifies the filter syntax to turn it into a list of three items regardless
        of the actual filter. Most of the filters are list of three elements, so this doesn't change much.

        The filter_operator syntax uses a dictionary with two keys, "filters" and
        "filter_operator". Filters using this syntax will be turned into
        [None, filter["filter_operator"], filter["filters"]]

        Filters of the form [field, operator, values....] will be turned into
        [field, operator, [values...]].

        :param list filters: List of filters to rearrange.

        :returns: A list of three items.
        """
        rearranged_filters = []

        # now translate ["field", "in", 2,3,4] --> ["field", "in", [2, 3, 4]]
        for f in filters:
            if isinstance(f, list):
                if len(f) > 3:
                    # ["field", "in", 2,3,4] --> ["field", "in", [2, 3, 4]]
                    new_filter = [f[0], f[1], f[2:]]

                elif f[1] == "in" and not isinstance(f[2], list):
                    # ["field", "in", 2] --> ["field", "in", [2]]
                    new_filter = [f[0], f[1], [f[2]]]

                else:
                    new_filter = f
            elif isinstance(f, dict):
                if "filter_operator" not in f or "filters" not in f:
                    raise ShotgunError(
                        "Bad filter operator, requires keys 'filter_operator' and 'filters', "
                        "found %s" % ", ".join(f.keys())
                    )
                new_filter = [None, f["filter_operator"], f["filters"]]
            else:
                raise ShotgunError(
                    "Filters can only be lists or dictionaries, not %s." % type(f).__name__
                )

            rearranged_filters.append(new_filter)

        return rearranged_filters

    def _row_matches_filters(self, entity_type, row, filters, filter_operator, retired_only):
        filters = self._rearrange_filters(filters)

        if retired_only and not row["__retired"] or not retired_only and row["__retired"]:
            # ignore retired rows unless the retired_only flag is set
            # ignore live rows if the retired_only flag is set
            return False
        elif filter_operator in ("all", None):
            return all(self._row_matches_filter(entity_type, row, filter, retired_only) for filter in filters)
        elif filter_operator == "any":
            return any(self._row_matches_filter(entity_type, row, filter, retired_only) for filter in filters)
        else:
            raise ShotgunError("%s is not a valid filter operator" % filter_operator)

    def _update_row(self, entity_type, row, data, multi_entity_update_modes=None):
        for field in data:
            field_type = self._get_field_type(entity_type, field)
            if field_type == "entity" and data[field]:
                row[field] = {"type": data[field]["type"], "id": data[field]["id"]}
            elif field_type == "multi_entity":
                update_mode = multi_entity_update_modes.get(field, "set") if multi_entity_update_modes else "set"

                if update_mode == "add":
                    for item in data[field]:
                        new_item = {"type": item["type"], "id": item["id"]}
                        if new_item not in row[field]:
                            row[field].append(new_item)
                elif update_mode == "remove":
                    row[field] = [
                        item
                        for item in row[field]
                        for new_item in data[field]
                        if item["id"] != new_item["id"]
                        or item["type"] != new_item["type"]
                    ]
                elif update_mode == "set":
                    row[field] = [{"type": item["type"], "id": item["id"]} for item in data[field]]
            elif field_type == "text" and isinstance(data[field], str):
                # field_types/text: both ends stripped, and an empty string is stored as None.
                row[field] = data[field].strip() or None
            else:
                row[field] = data[field]

    def _read_field(self, entity_type, row, field):
        """Return a field as a site returns it, with entity links named (finding 060)."""
        value = self._get_field_from_row(entity_type, row, field)
        try:
            field_type = self._get_field_type(entity_type, field)
        except KeyError:
            return value
        if field_type not in ("entity", "multi_entity"):
            return value
        if isinstance(value, list):
            links = [self._live_link(item) for item in value]
            links = [link for link in links if link is not None]
            if entity_type == "Note" and field == "tasks":
                # api3 026: Note.tasks elements add the Task's template_task id.
                for link in links:
                    task = self._db["Task"].get(link["id"], {})
                    link["template_task_id"] = (task.get("template_task") or {}).get("id")
            return links
        return self._live_link(value)

    def _live_link(self, link):
        """A named link, or None when its target is retired (api3 027)."""
        if isinstance(link, dict) and "type" in link and "id" in link:
            target = self._db.get(link["type"], {}).get(link["id"])
            if target is not None and target.get("__retired"):
                return None
        return self._named_link(link)

    def _named_link(self, link):
        """Return an entity link as {type, id, name}, where name is the target's cached_display_name."""
        if not isinstance(link, dict) or "type" not in link or "id" not in link:
            # A dotted path through a multi_entity returns nested lists.
            return [self._named_link(item) for item in link] if isinstance(link, list) else link
        target = self._db.get(link["type"], {}).get(link["id"])
        name = display_name(link["type"], target) if target is not None else link.get("name")
        return {"type": link["type"], "id": link["id"], "name": name}

    def _validate_entity_exists(self, entity_type, entity_id, verb=None):
        if entity_id not in self._db[entity_type]:
            if verb in ("update", "delete"):
                raise Fault(_records.missing_entity(verb, entity_type, entity_id))  # api3 063
            raise ShotgunError("No entity of type %s exists with id %s" % (entity_type, entity_id))

    def _next_id(self, entity_type):
        """Hand out the next id for a type, past every id already in the table or spent."""
        next_id = max(max(self._db[entity_type], default=0), self._spent_ids.get(entity_type, 0)) + 1
        self._spent_ids[entity_type] = next_id
        return next_id

    def _check_create_contract(self, entity_type, data, return_fields):
        """Raise the Fault a site answers for a create with no fields, no project or an empty identity."""
        if not data:
            raise Fault(_records.no_fields(entity_type, return_fields))  # api3 060, 061
        if self.require_project and entity_type in _records.PROJECT_SCOPED and "project" not in data:
            raise Fault(_records.missing_project(data))  # api3 060
        identity = _records.IDENTITY_FIELDS.get(entity_type)
        if identity in data and data[identity] in ("", None):
            self._next_id(entity_type)  # api3 060: the refused create spends an id.
            raise Fault(_records.empty_identity(entity_type))

    def _check_status(self, entity_type, data, verb):
        """Refuse a status outside ``valid_values``; return data with "" stored as None (api3 062)."""
        out = dict(data)
        for field, value in data.items():
            info = self._schema[entity_type].get(field)
            if not info or info["data_type"]["value"] != "status_list":
                continue
            if value in ("", None):
                out[field] = None
                continue
            valid = info["properties"]["valid_values"]["value"]
            if value not in valid:
                raise Fault(_records.bad_status(verb, entity_type, field, value, valid))
        return out

    def _apply_delete_effects(self, entity_type, entity_id):
        """Null entity links to a deleted row and retire Versions it is the `entity` of (api3 027, 065)."""
        link = {"type": entity_type, "id": entity_id}
        cleared, retired = [], []
        for other_type, rows in self._db.items():
            if other_type == "EventLogEntry":
                continue
            fields = [f for f, info in self._schema[other_type].items() if info["data_type"]["value"] == "entity"]
            for row in rows.values():
                for field in fields:
                    value = row.get(field)
                    if row["__retired"] or not isinstance(value, dict) or not _same_link(value, link):
                        continue
                    if other_type == "Version" and field == "entity":
                        retired.append(row["id"])
                    else:
                        row[field] = None
                        cleared.append((other_type, row["id"], field))
        for version_id in retired:
            self.delete("Version", version_id)
        self._delete_effects[(entity_type, entity_id)] = (cleared, retired)

    def _undo_delete_effects(self, entity_type, entity_id):
        """Put back what deleting a row changed on other rows, where nothing has set them since."""
        cleared, retired = self._delete_effects.pop((entity_type, entity_id), ([], []))
        for version_id in retired:
            self.revive("Version", version_id)
        for other_type, other_id, field in cleared:
            row = self._db[other_type].get(other_id)
            if row is not None and row.get(field) is None:
                row[field] = {"type": entity_type, "id": entity_id}

    ###################################################################################################
    # summarize, text_search, info (sg_mockgun.summarize, sg_mockgun.text_search, sg_mockgun.site_info)

    def summarize(self, entity_type, filters, summary_fields, filter_operator=None, grouping=None,
                  include_archived_projects=True):
        """Summarize the rows ``filters`` selects, optionally grouped (api3 040 to 042)."""
        # Client-side checks and translation follow shotgun_api3.Shotgun.summarize.
        if not isinstance(grouping, list) and grouping is not None:
            raise ValueError("summarize() 'grouping' parameter must be a list or None")
        if isinstance(filters, (list, tuple)):
            filters = _translate_filters(filters, filter_operator)
        params = {"type": entity_type, "summaries": summary_fields, "filters": filters}
        if include_archived_projects is False:
            params["include_archived_projects"] = False
        if grouping is not None:
            params["grouping"] = grouping
        field_type = lambda field: self._field_type_or_none(entity_type, field)  # noqa: E731
        _summarize.check_request(entity_type, params, self._schema, field_type)
        python_filters, operator = _wire.filters_from_wire(filters)
        fields = [s["field"] for s in summary_fields] + [g["field"] for g in grouping or []]
        rows = self.find(entity_type, python_filters, fields, filter_operator=operator,
                         include_archived_projects=include_archived_projects)
        return _summarize.summarize(rows, summary_fields, grouping, field_type, self._status_order(entity_type))

    def text_search(self, text, entity_types, project_ids=None, limit=None):
        """Search the names of rows of ``entity_types`` for every word of ``text`` (api3 043 to 045)."""
        # Client-side checks and translation follow shotgun_api3.Shotgun.text_search.
        if not isinstance(entity_types, dict):
            raise ValueError("entity_types parameter must be a dictionary")
        api_entity_types = {}
        for entity_type, filter_list in entity_types.items():
            if not isinstance(filter_list, (list, tuple)):
                raise ValueError("value of entity_types['%s'] must be a list or tuple." % entity_type)
            api_entity_types[entity_type] = _translate_filters(filter_list, filter_operator=None)
        params = {"text": text, "entity_types": api_entity_types, "project_ids": project_ids or [],
                  "max_results": limit}
        _text_search.check_request(params, self._schema)
        _text_search.row_limit(limit)
        # api3 045: no entity type searches every type.
        searched = api_entity_types or dict((t, {"logical_operator": "and", "conditions": []}) for t in self._db)
        rows = []
        for entity_type, node in searched.items():
            node = self._searchable_conditions(entity_type, node)
            python_filters, operator = _wire.filters_from_wire(node)
            for found in self.find(entity_type, python_filters, filter_operator=operator):
                match = self._search_match(entity_type, self._db[entity_type][found["id"]])
                if match["name"] is None:
                    continue  # unprobed: a row with no display name, an EventLogEntry, is not searched
                if not params["project_ids"] or match["project_id"] in params["project_ids"]:
                    rows.append(match)
        return _text_search.search(text, rows, limit)

    def info(self):
        """The site's API metadata. It needs no credentials (api3 046)."""
        return copy.deepcopy(self._info)

    def set_info(self, **values):
        """Change keys of the payload ``info()`` answers, e.g. ``set_info(version=[8, 92, 0])``."""
        self._info.update(copy.deepcopy(values))

    def connect(self):
        """Do what the client's connect does: read ``info()``, return None (api3 046)."""
        self.info()

    def close(self):
        """Do what the client's close does when no connection is open: nothing."""

    @property
    def server_info(self):
        """The ``info()`` payload."""
        return self.server_caps.server_info

    @property
    def server_caps(self):
        """The client's ``ServerCapabilities`` built from ``info()``, as ``shotgun_api3`` builds it."""
        return ServerCapabilities(self.config.server, self.info())

    def _field_type_or_none(self, entity_type, field):
        if not isinstance(field, str):
            return None
        try:
            return self._get_field_type(entity_type, field)
        except (KeyError, ShotgunError):
            return None

    def _status_order(self, entity_type):
        def order(field):
            try:
                return list(self._schema[entity_type][field]["properties"]["valid_values"]["value"])
            except KeyError:
                return []
        return order

    def _searchable_conditions(self, entity_type, node):
        """Drop conditions on fields the type lacks, and refuse a relation no data type has (api3 045)."""
        kept = []
        for condition in node.get("conditions", []):
            if "conditions" in condition:
                kept.append(self._searchable_conditions(entity_type, condition))
                continue
            if self._field_type_or_none(entity_type, condition["path"]) is None:
                continue
            if condition["relation"] not in _ALL_RELATIONS:
                raise Fault("Uncaught exception! No condition node type matches <%s> for column %s a.%s"
                            % (condition["relation"], entity_type, condition["path"]))
            kept.append(condition)
        return dict(node, conditions=kept)

    def _search_match(self, entity_type, row):
        """One row as ``text_search`` returns it (api3 043)."""
        link = row.get("entity")
        links = ["", ""]
        if isinstance(link, dict) and link.get("type") in self._db:
            target = self._db[link["type"]].get(link["id"])
            if target is not None:
                links = [link["type"], display_name(link["type"], target) or ""]
        project = row.get("project")
        return {
            "id": row["id"], "type": entity_type, "name": display_name(entity_type, row),
            "project_id": project.get("id") if isinstance(project, dict) else None,
            "links": links, "status": row.get("sg_status_list"), "image": row.get("image"),
        }

    ###################################################################################################
    # seeding and snapshots (sg_mockgun.seed)

    def load(self, source):
        """Add the records in a seed file, or an already parsed dict, without event log rows."""
        _seed.load(self, source)

    def snapshot(self):
        """A copy of this instance's records and schema, for ``restore``."""
        return _seed.snapshot(self)

    def restore(self, state):
        """Put this instance's records and schema back to a ``snapshot``."""
        _seed.restore(self, state)

    ###################################################################################################
    # attention, navigation and site reads (sg_mockgun.attention, api3 047 to 052)

    def note_thread_read(self, note_id, entity_fields=None):
        """Return a Note, its Replies and its Attachments, oldest first."""
        entity_fields = entity_fields or {}
        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")
        return _attention.note_thread_contents(self, note_id, entity_fields)

    def activity_stream_read(self, entity_type, entity_id, entity_fields=None, min_id=None, max_id=None, limit=None):
        """Return the ``create`` updates on a record and on the rows linked to it, newest first."""
        entity_fields = entity_fields or {}
        if not isinstance(entity_fields, dict):
            raise ValueError("entity_fields parameter must be a dictionary")
        return _attention.activity_stream(self, entity_type, entity_id, entity_fields, min_id, max_id, limit)

    def followers(self, entity):
        """Return the HumanUsers following ``entity``."""
        return _attention.followers(self, entity)

    def following(self, user, project=None, entity_type=None):
        """Return the ``{type, id}`` of every record ``user`` follows."""
        params = {"user": user}
        if project:
            params["project"] = project
        if entity_type:
            params["entity_type"] = entity_type
        return _attention.following(self, params)

    def set_following(self, user, entities):
        """Make ``user`` (a HumanUser link) follow exactly ``entities``."""
        _attention.state(self)["follows"][user["id"]] = [{"type": e["type"], "id": e["id"]} for e in entities]

    def nav_expand(self, path, seed_entity_field=None, entity_fields=None):
        """Return the navigation node at ``path`` with its children."""
        return _attention.nav_expand(self, path, seed_entity_field, entity_fields)

    def nav_search_string(self, root_path, search_string, seed_entity_field=None):
        """Return the navigation rows under ``root_path`` whose label contains ``search_string``."""
        return _attention.nav_search(self, root_path, {"search_string": search_string})

    def nav_search_entity(self, root_path, entity, seed_entity_field=None):
        """Return the navigation row of ``entity`` under ``root_path``."""
        return _attention.nav_search(self, root_path, {"entity": entity})

    def preferences_read(self, prefs=None):
        """Return the site preferences, or only those named in ``prefs``."""
        return _attention.preferences_read(self, prefs or [])

    def set_preferences(self, values):
        """Change site preferences for ``preferences_read``."""
        _attention.state(self)["preferences"].update(values)

    def work_schedule_read(self, start_date, end_date, project=None, user=None):
        """Return the work day rule of each date from ``start_date`` to ``end_date`` inclusive."""
        if not isinstance(start_date, str) or not isinstance(end_date, str):
            raise ShotgunError("The start_date and end_date arguments must be strings in YYYY-MM-DD format")
        return _attention.work_schedule_read(
            self, {"start_date": start_date, "end_date": end_date, "project": project, "user": user})

    def set_work_schedule(self, week=None, exceptions=None):
        """Set the studio week (seven booleans, Monday first) and per-date rules for ``work_schedule_read``."""
        state = _attention.state(self)
        if week is not None:
            state["work_week"] = list(week)
        if exceptions is not None:
            state["work_exceptions"] = dict(exceptions)

    def user_subscriptions_read(self):
        """Return the subscription of each HumanUser, keyed by the user id as a string."""
        return dict(_attention.state(self)["subscriptions"])

    def set_user_subscriptions(self, subscriptions):
        """Set what ``user_subscriptions_read`` returns."""
        _attention.state(self)["subscriptions"] = dict(subscriptions)

    def export_page(self, page_id, format, layout_name=None):
        """Refuse a page export the way a site with no exportable page does."""
        return _attention.export_page(self, {"format": format, "page_id": page_id, "layout_name": layout_name})
