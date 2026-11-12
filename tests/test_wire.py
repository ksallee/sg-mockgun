import datetime

from sg_mockgun import wire


def test_split_payload_with_and_without_auth():
    assert wire.split_payload({"method_name": "read", "params": [{"script_name": "s", "script_key": "k"}, {"type": "Shot"}]}) == (
        "read", {"script_name": "s", "script_key": "k"}, {"type": "Shot"})
    assert wire.split_payload({"method_name": "info", "params": []}) == ("info", {}, {})


def test_filters_from_wire_nested():
    node = {"logical_operator": "and", "conditions": [
        {"path": "code", "relation": "is", "values": ["a"]},
        {"path": "id", "relation": "in", "values": [1, 2]},
        {"path": "sg_cut_in", "relation": "between", "values": [1, 9]},
        {"logical_operator": "or", "conditions": [{"path": "code", "relation": "starts_with", "values": ["s"]}]},
    ]}
    filters, op = wire.filters_from_wire(node)
    assert op == "all"
    assert filters == [
        ["code", "is", "a"], ["id", "in", [1, 2]], ["sg_cut_in", "between", [1, 9]],
        {"filter_operator": "any", "filters": [["code", "starts_with", "s"]]},
    ]


def test_fields_and_properties_from_wire():
    assert wire.fields_from_wire([{"field_name": "code", "value": "a"},
                                  {"field_name": "assets", "value": [], "multi_entity_update_mode": "add"}]) == (
        {"code": "a", "assets": []}, {"assets": "add"})
    assert wire.properties_from_wire([{"property_name": "name", "value": "X"}]) == {"name": "X"}


def test_datetimes_both_ways():
    utc = datetime.timezone.utc
    assert wire.to_python("2026-11-12T21:54:08Z", "date_time") == datetime.datetime(2026, 11, 12, 21, 54, 8, tzinfo=utc)
    assert wire.to_python("2026-11-12T21:54:08Z", "text") == "2026-11-12T21:54:08Z"
    assert wire.to_wire({"at": datetime.datetime(2026, 11, 12, 21, 54, 8, tzinfo=utc)}) == {"at": "2026-11-12T21:54:08Z"}


def test_page():
    out = wire.page(list(range(23)), {"entities_per_page": 10, "current_page": 3})
    assert out["entities"] == [20, 21, 22]
    assert out["paging_info"] == {"entity_count": 23, "current_page": 3, "page_count": 3, "has_next_page": False}
