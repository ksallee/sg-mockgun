import pickle

from sg_mockgun import Shotgun, schemas


def test_bundled_schema_loads_and_round_trips_a_shot():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    project = sg.create("Project", {"name": "Demo"})
    shot = sg.create("Shot", {"code": "sh010", "project": project, "sg_cut_in": 1001})
    found = sg.find_one("Shot", [["code", "is", "sh010"]], ["sg_cut_in", "project"])
    assert found["id"] == shot["id"] and found["sg_cut_in"] == 1001


def test_bundled_schema_carries_what_upstream_lacks():
    schema = pickle.load(open(schemas.paths()[0], "rb"))
    types = {f["data_type"]["value"] for fields in schema.values() for f in fields.values()}
    assert {"calculated", "summary", "jsonb"} <= types  # stock query and timecode fields are all custom
    assert all("visible" in f for fields in schema.values() for f in fields.values())


def test_bundled_schema_has_no_probe_or_app_fields():
    schema = pickle.load(open(schemas.paths()[0], "rb"))
    names = [f for fields in schema.values() for f in fields]
    assert not [n for n in names if "zzprobe" in n or "fp_test" in n or n.startswith("sg_ai_")]


def test_upstream_schema_is_bundled_too():
    Shotgun.set_schema_paths(*schemas.paths("upstream_3_10_5"))
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    code = sg.schema_field_create("Version", "entity", "Shot Link", {"valid_types": ["Shot"]})
    shot = sg.create("Shot", {"code": "sh010"})
    v = sg.create("Version", {"code": "v1", code: shot})
    assert sg.find_one("Version", [["id", "is", v["id"]]], [code])[code]["id"] == shot["id"]
