"""``sg-mockgun serve``: one mockgun instance behind the api3 JSON protocol, for a real client.

    sg-mockgun serve --port 8080
    shotgun_api3.Shotgun("http://localhost:8080", script_name="any", api_key="any")

Any script name and key are accepted; the script name becomes the event log's user. Calls run one
at a time under a lock, so concurrent clients see a consistent site.

Next to api3, the two REST routes a site needs for reviving a trashed field, which api3 cannot do:
``POST /api/v1/auth/access_token`` (``client_credentials``, ``session_token``, ``refresh_token``)
and ``POST /api/v1/schema/<Type>/fields/<field>`` with ``revive``. Answers from sg-groundtruth
finding 040 and the endpoint cards post_auth_access_token and post_schema_type_fields_field.
"""

import argparse
import json
import re
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shotgun_api3 import ShotgunError

from . import wire
from .mockgun import FieldReviveError, Shotgun
from . import schemas

SERVER_VERSION = [8, 91, 0]  # the site the bundled schema and the recorded answers come from


class Site:
    """Dispatches api3 methods onto a mockgun instance."""

    def __init__(self, mock):
        self.mock = mock
        self.lock = threading.Lock()
        self.sessions = {}  # api3 session token -> script name
        self.bearers = {}  # REST access token -> script name
        self.refresh = {}  # REST refresh token -> script name

    def _who(self, auth):
        return (auth.get("script_name") or self.sessions.get(auth.get("session_token"))
                or auth.get("user_login") or "mockgun")

    def call(self, method, auth, params):
        handler = getattr(self, "m_" + (method or ""), None)
        if handler is None:
            return wire.fault('Error: API method "%s" is not permitted.' % method)
        with self.lock:
            self._caller = self._who(auth)
            self.mock._event_user["name"] = self._caller
            try:
                return {"results": wire.to_wire(handler(params or {}))}
            except ShotgunError as e:
                return wire.fault(str(e))

    # values off the wire, typed by the schema
    def _data(self, entity_type, data):
        fields = self.mock._schema.get(entity_type, {})
        return {k: wire.to_python(v, fields.get(k, {}).get("data_type", {}).get("value")) for k, v in data.items()}

    def m_get_session_token(self, params):
        token = secrets.token_hex(16)
        self.sessions[token] = self._caller
        return {"session_id": token}

    # REST: token endpoint and field revive. Each returns (status, body or None).
    def rest_token(self, content_type, raw):
        if not content_type.startswith("application/x-www-form-urlencoded"):
            return 415, {"errors": [{"status": 415, "code": 103,
                                     "title": "Unsupported Content-Type '%s'" % content_type.split(";")[0],
                                     "source": {"content_type": "Content-Type must be one of: "
                                                                "'application/x-www-form-urlencoded'"}}]}
        form = dict(urllib.parse.parse_qsl(raw.decode("utf-8")))
        grant = form.get("grant_type")
        with self.lock:
            if grant == "client_credentials":
                if not form.get("client_id") or not form.get("client_secret"):
                    return 400, rest_error(400, "Missing or invalid authentication arguments")
                who = form["client_id"]
            elif grant == "session_token":
                who = self.sessions.get(form.get("session_token"))
                if not who:
                    return 400, rest_error(400, "Missing or invalid authentication arguments")
            elif grant == "refresh_token":
                who = self.refresh.get(form.get("refresh_token"))
                if not who:
                    return 400, rest_error(400, "Missing or invalid authentication arguments")
            else:
                return 400, rest_error(400, "Unsupported grant_type")
            access, refresh = secrets.token_hex(16), secrets.token_hex(16)
            self.bearers[access], self.refresh[refresh] = who, who
        return 200, {"token_type": "Bearer", "access_token": access, "expires_in": 600, "refresh_token": refresh}

    def rest_revive(self, bearer, entity_type, field_name, query, raw):
        with self.lock:
            who = self.bearers.get(bearer)
        if not who:
            return 401, rest_error(401, "Request rejected due to invalid credentials.")
        body = json.loads(raw or b"{}") if raw else {}
        revive = body.get("revive") if isinstance(body, dict) and "revive" in body else query.get("revive")
        if revive is None:
            return 400, {"errors": [{"status": 400, "code": 103, "source": {"revive": ["revive is missing"]}}]}
        if revive not in (True, "true", "1", 1):
            return 400, {"errors": [{"status": 400, "code": 103, "source": {"revive": ["revive must be true"]}}]}
        with self.lock:
            self.mock._event_user["name"] = who
            try:
                self.mock.revive_field(entity_type, field_name)
            except FieldReviveError as e:
                return e.status, rest_error(e.status, str(e))
        return 204, None

    def m_info(self, params):
        return {"version": SERVER_VERSION, "s3_uploads_enabled": False, "totango_site_id": None}

    def m_read(self, params):
        filters, operator = wire.filters_from_wire(params.get("filters") or {"conditions": []})
        entity_type = params["type"]
        fields = self.mock._schema.get(entity_type, {})
        filters = self._typed_filters(filters, fields)
        order = [{"field_name": s["field_name"], "direction": s.get("direction", "asc")} for s in params.get("sorts") or []]
        records = self.mock.find(
            entity_type, filters, fields=params.get("return_fields"), order=order or None,
            filter_operator=operator, retired_only=params.get("return_only") == "retired",
        )
        return wire.page(records, params.get("paging"))

    def _typed_filters(self, filters, fields):
        out = []
        for f in filters:
            if isinstance(f, dict):
                out.append({"filter_operator": f["filter_operator"], "filters": self._typed_filters(f["filters"], fields)})
                continue
            data_type = fields.get(f[0], {}).get("data_type", {}).get("value")
            out.append([f[0], f[1]] + [
                [wire.to_python(x, data_type) for x in v] if isinstance(v, list) else wire.to_python(v, data_type)
                for v in f[2:]
            ])
        return out

    def m_create(self, params):
        data, _ = wire.fields_from_wire(params.get("fields"))
        # The client sends return_fields ["id"] by default; a site answers with what was written too.
        returned = list(data) + [f for f in params.get("return_fields") or [] if f not in data]
        return self.mock.create(params["type"], self._data(params["type"], data), returned)

    def m_update(self, params):
        data, modes = wire.fields_from_wire(params.get("fields"))
        return self.mock.update(params["type"], params["id"], self._data(params["type"], data), modes or None)[0]

    def m_delete(self, params):
        return self.mock.delete(params["type"], params["id"])

    def m_revive(self, params):
        return self.mock.revive(params["type"], params["id"])

    def m_batch(self, params):
        results = []
        for request in params:
            kind = request["request_type"]
            if kind == "create":
                results.append(self.m_create(request))
            elif kind == "update":
                results.append(self.m_update(request))
            elif kind == "delete":
                results.append(self.m_delete(request))
            else:
                raise ShotgunError("Invalid request type %s in request %s" % (kind, request))
        return results

    def m_schema_read(self, params):
        return self.mock.schema_read()

    def m_schema_entity_read(self, params):
        return self.mock.schema_entity_read()

    def m_schema_field_read(self, params):
        return self.mock.schema_field_read(params["type"], params.get("field_name"))

    def m_schema_field_create(self, params):
        props = wire.properties_from_wire(params.get("properties"))
        name = props.pop("name", None)
        return self.mock.schema_field_create(params["type"], params["data_type"], name, props)

    def m_schema_field_update(self, params):
        return self.mock.schema_field_update(
            params["type"], params["field_name"], wire.properties_from_wire(params.get("properties")))

    def m_schema_field_delete(self, params):
        return self.mock.schema_field_delete(params["type"], params["field_name"])


def rest_error(status, title):
    # Status and title are recorded; the site's numeric "code" for these is not, so it is left out.
    return {"errors": [{"status": status, "title": title}]}


_FIELD_PATH = re.compile(r"^/api/v1(?:\.1)?/schema/([^/]+)/fields/([^/]+)$")


def make_server(mock, host="127.0.0.1", port=8080):
    site = Site(mock)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status, body):
            data = b"" if body is None else json.dumps(body).encode("utf-8")
            self.send_response(status)
            if body is not None:
                self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b""
            parsed = urllib.parse.urlsplit(self.path)
            path, query = parsed.path, dict(urllib.parse.parse_qsl(parsed.query))
            if path.startswith("/api/v1"):
                if path.rstrip("/").endswith("/auth/access_token"):
                    return self._send(*site.rest_token(self.headers.get("content-type", ""), raw))
                m = _FIELD_PATH.match(path)
                if m:
                    auth = self.headers.get("authorization", "")
                    bearer = auth[7:] if auth.lower().startswith("bearer ") else ""
                    return self._send(*site.rest_revive(bearer, m.group(1), m.group(2), query, raw))
                # Only the revive route is served; the rest of REST is out of scope for this mock.
                return self._send(404, rest_error(404, "Not served by sg-mockgun: %s" % path))
            try:
                body = site.call(*wire.split_payload(json.loads(raw or b"{}")))
            except Exception as e:  # malformed request: answer like a server error, keep serving
                body = wire.fault("API %s" % e)
            self._send(200, body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    server.site = site
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sg-mockgun")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="serve a mock site over the api3 JSON protocol")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--schema", default="fpt_8_91", help="a bundled schema name")
    args = parser.parse_args(argv)
    Shotgun.set_schema_paths(*schemas.paths(args.schema))
    mock = Shotgun("https://mock.example.com", script_name="mockgun", api_key="mockgun")
    server = make_server(mock, args.host, args.port)
    print("serving api3 on http://%s:%d" % server.server_address[:2], flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
