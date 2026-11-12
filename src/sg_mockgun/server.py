"""``sg-mockgun serve``: one mockgun instance behind the api3 JSON protocol, for a real client.

    sg-mockgun serve --port 8080
    shotgun_api3.Shotgun("http://localhost:8080", script_name="any", api_key="any")

Any script name and key are accepted; the script name becomes the event log's user. Calls run one
at a time under a lock, so concurrent clients see a consistent site.
"""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shotgun_api3 import ShotgunError

from . import wire
from .mockgun import Shotgun
from . import schemas

SERVER_VERSION = [8, 91, 0]  # the site the bundled schema and the recorded answers come from


class Site:
    """Dispatches api3 methods onto a mockgun instance."""

    def __init__(self, mock):
        self.mock = mock
        self.lock = threading.Lock()

    def call(self, method, auth, params):
        handler = getattr(self, "m_" + (method or ""), None)
        if handler is None:
            return wire.fault('Error: API method "%s" is not permitted.' % method)
        with self.lock:
            self.mock._event_user["name"] = auth.get("script_name") or auth.get("user_login") or "mockgun"
            try:
                return {"results": wire.to_wire(handler(params or {}))}
            except ShotgunError as e:
                return wire.fault(str(e))

    # values off the wire, typed by the schema
    def _data(self, entity_type, data):
        fields = self.mock._schema.get(entity_type, {})
        return {k: wire.to_python(v, fields.get(k, {}).get("data_type", {}).get("value")) for k, v in data.items()}

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


def make_server(mock, host="127.0.0.1", port=8080):
    site = Site(mock)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            length = int(self.headers.get("content-length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                body = site.call(*wire.split_payload(payload))
            except Exception as e:  # malformed request: answer like a server error, keep serving
                body = wire.fault("API %s" % e)
            data = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

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
