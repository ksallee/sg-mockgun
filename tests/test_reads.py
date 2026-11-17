"""Pure helpers for find: page size, the echoed read request, LATEST and sort order."""
import datetime

from sg_mockgun import reads


def test_page_size_follows_server_info():
    # api3 020: the client reads api_max_entities_per_page, else 500. The mock defaults to 5000.
    assert reads.page_size({"api_max_entities_per_page": 5000}) == 5000
    assert reads.page_size({}) == 500
    assert reads.page_size(None) == 5000


def test_pp_wraps_a_long_pair_onto_the_next_line():
    # api3 023, the Shot Fault, character for character.
    params = reads.read_params("Shot", [], None, ["id"], False, 5, 1, False,
                               [{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}])
    assert reads.pp(params) == (
        '{"type" => "Shot",\n'
        ' "return_fields" => ["id"],\n'
        ' "filters" => {"logical_operator" => "and", "conditions" => []},\n'
        ' "return_only" => "active",\n'
        ' "paging" => {"entities_per_page" => 5, "current_page" => 1},\n'
        ' "additional_filter_presets" =>\n'
        '  [{"preset_name" => "LATEST", "latest_by" => "ENTITIES_CREATED_AT"}],\n'
        ' "api_return_image_urls" => true,\n'
        ' "return_paging_info_without_counts" => false}'
    )


def test_pp_breaks_nested_values():
    # api3 020: the missing-paging Fault.
    value = {
        "type": "EventLogEntry",
        "return_fields": ["id"],
        "filters": {"logical_operator": "and", "conditions": [
            {"path": "created_at", "relation": "greater_than", "values": ["2026-10-18T18:38:23Z"]}]},
        "return_only": "active",
        "return_paging_info": True,
    }
    assert reads.pp(value) == (
        '{"type" => "EventLogEntry",\n'
        ' "return_fields" => ["id"],\n'
        ' "filters" =>\n'
        '  {"logical_operator" => "and",\n'
        '   "conditions" =>\n'
        '    [{"path" => "created_at",\n'
        '      "relation" => "greater_than",\n'
        '      "values" => ["2026-10-18T18:38:23Z"]}]},\n'
        ' "return_only" => "active",\n'
        ' "return_paging_info" => true}'
    )


def test_read_params_without_limit_asks_for_paging_info():
    params = reads.read_params("PublishedFile", [], None, ["id"], False, 5000, 1, True, [{"preset_name": "NOPE"}])
    assert params["paging"] == {"entities_per_page": 5000, "current_page": 1}
    assert params["return_paging_info_without_counts"] is True


T = datetime.datetime


def test_latest_keeps_the_newest_row_per_group_and_drops_null_groups():
    rows = [
        {"id": 1, "created_at": T(2020, 1, 1), "g": "a"},
        {"id": 2, "created_at": T(2020, 1, 2), "g": "a"},
        {"id": 3, "created_at": T(2020, 1, 1), "g": None},
        {"id": 4, "created_at": T(2020, 1, 3), "g": "b"},
        {"id": 5, "created_at": T(2020, 1, 3), "g": "b"},
    ]
    # api3 023: equal created_at keeps the lower id.
    assert reads.latest_ids(rows, lambda r: (r["g"],), lambda r: ()) == {2, 4}


def test_latest_ranks_by_the_extra_key_first():
    rows = [
        {"id": 1, "created_at": T(2020, 1, 2), "g": "a", "step": 1},
        {"id": 2, "created_at": T(2020, 1, 1), "g": "a", "step": 2},
    ]
    assert reads.latest_ids(rows, lambda r: (r["g"],), lambda r: (r["step"],)) == {2}


def test_sort_puts_none_last_both_ways_ties_by_id():
    # api3 025
    rows = [{"id": 1, "v": "b"}, {"id": 2, "v": None}, {"id": 3, "v": "a"}, {"id": 4, "v": None}]
    get = lambda r, f: r[f]  # noqa: E731
    assert [r["id"] for r in reads.sort_rows(rows, [("v", False)], get)] == [3, 1, 2, 4]
    assert [r["id"] for r in reads.sort_rows(rows, [("v", True)], get)] == [1, 3, 2, 4]
