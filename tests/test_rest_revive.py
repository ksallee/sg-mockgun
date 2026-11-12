"""REST token + field revive next to api3, answers from sg-groundtruth (finding 040, endpoint cards
post_auth_access_token, post_schema_type_fields_field) and docs/api3-probe-2026-11-12.md."""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest
import shotgun_api3

from sg_mockgun import Shotgun as Mockgun, schemas
from sg_mockgun.server import make_server


@pytest.fixture
def site():
    Mockgun.set_schema_paths(*schemas.paths())
    mock = Mockgun("https://mock.example.com", script_name="server", api_key="x")
    server = make_server(mock, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % server.server_address[1]
    yield url, shotgun_api3.Shotgun(url, script_name="pipeline", api_key="key")
    server.shutdown()


def call(url, method, path, body=None, form=False, bearer=None, content_type=None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
        headers["Content-Type"] = content_type or ("application/x-www-form-urlencoded" if form else "application/json")
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(url + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def token(url, **form):
    status, body = call(url, "POST", "/api/v1/auth/access_token", form, form=True)
    assert status == 200, body
    return body["access_token"]


def trashed(sg, data_type="entity", name="Shot Link"):
    props = {"valid_types": ["Shot"]} if data_type == "entity" else None
    code = sg.schema_field_create("Version", data_type, name, props)
    sg.schema_field_delete("Version", code)
    return code


def test_token_from_script_credentials(site):
    url, _ = site
    status, body = call(url, "POST", "/api/v1/auth/access_token",
                        {"grant_type": "client_credentials", "client_id": "pipeline", "client_secret": "key"}, form=True)
    assert status == 200
    assert body["token_type"] == "Bearer" and body["expires_in"] == 600
    assert body["access_token"] and body["refresh_token"]


def test_token_from_an_api3_session(site):
    url, sg = site
    session = sg.get_session_token()
    assert session
    assert token(url, grant_type="session_token", session_token=session)


def test_token_endpoint_refusals(site):
    url, _ = site
    status, body = call(url, "POST", "/api/v1/auth/access_token", {"grant_type": "client_credentials"})
    assert status == 415
    assert body == {"errors": [{"status": 415, "code": 103,
                                "title": "Unsupported Content-Type 'application/json'",
                                "source": {"content_type": "Content-Type must be one of: 'application/x-www-form-urlencoded'"}}]}
    status, body = call(url, "POST", "/api/v1/auth/access_token", {"grant_type": "authorization_code"}, form=True)
    assert status == 400 and body["errors"][0]["title"] == "Unsupported grant_type"
    status, body = call(url, "POST", "/api/v1/auth/access_token", {"grant_type": "client_credentials", "client_id": "x"}, form=True)
    assert status == 400 and body["errors"][0]["title"] == "Missing or invalid authentication arguments"


def test_revive_brings_back_the_original_type(site):
    url, sg = site
    code = trashed(sg)
    bearer = token(url, grant_type="client_credentials", client_id="pipeline", client_secret="key")
    status, body = call(url, "POST", "/api/v1/schema/Version/fields/%s" % code, {"revive": True}, bearer=bearer)
    assert (status, body) == (204, None)
    field = sg.schema_field_read("Version", code)[code]
    assert field["data_type"]["value"] == "entity"
    assert field["properties"]["valid_types"]["value"] == ["Shot"]
    assert field["name"]["value"] == "Shot Link"


def test_revive_by_query_parameter(site):
    url, sg = site
    code = trashed(sg)
    bearer = token(url, grant_type="client_credentials", client_id="pipeline", client_secret="key")
    status, _ = call(url, "POST", "/api/v1/schema/Version/fields/%s?revive=true" % code, bearer=bearer)
    assert status == 204


def test_revive_refusals(site):
    url, sg = site
    code = trashed(sg)
    live = sg.schema_field_create("Version", "text", "Live One")
    bearer = token(url, grant_type="client_credentials", client_id="pipeline", client_secret="key")
    path = "/api/v1/schema/Version/fields/"
    assert call(url, "POST", path + code, {}, bearer=bearer) == (
        400, {"errors": [{"status": 400, "code": 103, "source": {"revive": ["revive is missing"]}}]})
    status, body = call(url, "POST", path + code, {"revive": False}, bearer=bearer)
    assert status == 400 and body["errors"][0]["source"] == {"revive": ["revive must be true"]}
    status, body = call(url, "POST", path + live, {"revive": True}, bearer=bearer)
    assert status == 400 and body["errors"][0]["title"] == "Field Version.%s is not retired." % live
    status, body = call(url, "POST", path + "sg_never_used", {"revive": True}, bearer=bearer)
    assert status == 404 and body["errors"][0]["title"] == "Retired field Version.sg_never_used does not exist."


def test_revive_needs_a_bearer(site):
    url, sg = site
    code = trashed(sg)
    status, body = call(url, "POST", "/api/v1/schema/Version/fields/%s" % code, {"revive": True})
    assert status == 401 and body["errors"][0]["title"] == "Request rejected due to invalid credentials."
    status, _ = call(url, "POST", "/api/v1/schema/Version/fields/%s" % code, {"revive": True}, bearer="nope")
    assert status == 401


def test_revive_is_logged(site):
    url, sg = site
    code = trashed(sg)
    bearer = token(url, grant_type="client_credentials", client_id="pipeline", client_secret="key")
    call(url, "POST", "/api/v1/schema/Version/fields/%s" % code, {"revive": True}, bearer=bearer)
    rows = sg.find("EventLogEntry", [["event_type", "starts_with", "Shotgun_DisplayColumn"]],
                   ["event_type", "attribute_name", "meta", "description"], order=[{"field_name": "id", "direction": "asc"}])
    assert [(r["event_type"], r["attribute_name"]) for r in rows][-2:] == [
        ("Shotgun_DisplayColumn_Change", "retirement_date"), ("Shotgun_DisplayColumn_Revival", None)]
    assert rows[-2]["meta"]["new_value"] is None and rows[-2]["meta"]["old_value"]
    assert rows[-1]["meta"]["type"] == "entity_revival" and rows[-1]["meta"]["display_name"] == code
    assert rows[-1]["description"] == ' revived DisplayColumn "%s"' % code


def test_create_after_revive_suffixes_again(site):
    url, sg = site
    code = trashed(sg, "text", "Plain")
    bearer = token(url, grant_type="client_credentials", client_id="pipeline", client_secret="key")
    call(url, "POST", "/api/v1/schema/Version/fields/%s" % code, {"revive": True}, bearer=bearer)
    assert sg.schema_field_create("Version", "text", "Plain") == code + "_1"
