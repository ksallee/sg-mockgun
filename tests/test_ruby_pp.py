"""Ruby ``pp`` layout for Fault bodies. Expected strings are api3 answers 042 and 045."""

from sg_mockgun.fields import Sym, ruby_pp


def test_short_values_stay_on_one_line():
    assert ruby_pp({"field": "id", "type": "maximum"}) == '{"field" => "id", "type" => "maximum"}'
    assert ruby_pp([Sym(s) for s in ("record_count", "count", "sum", "maximum", "minimum", "average")]) == (
        "[:record_count, :count, :sum, :maximum, :minimum, :average]")


def test_a_long_symbol_list_breaks_one_per_line():  # api3 042
    kinds = ("exact", "tens", "hundreds", "thousands", "tensofthousands", "hundredsofthousands", "millions")
    assert ruby_pp([Sym(s) for s in kinds]) == (
        "[:exact,\n :tens,\n :hundreds,\n :thousands,\n :tensofthousands,\n :hundredsofthousands,\n :millions]")


def test_a_hash_value_too_long_for_its_line_moves_under_its_key():  # api3 045
    request = {
        "text": "ab",
        "entity_types": {"Shot": {"logical_operator": "and", "conditions": []}},
        "project_ids": [1180],
        "max_results": None,
    }
    assert ruby_pp(request) == (
        '{"text" => "ab",\n "entity_types" =>\n  {"Shot" => {"logical_operator" => "and", "conditions" => []}},\n'
        ' "project_ids" => [1180],\n "max_results" => nil}')


def test_nested_groups_indent_by_level():  # api3 042
    request = {
        "type": "NotAType",
        "summaries": [{"field": "id", "type": "count"}],
        "filters": {"logical_operator": "and", "conditions": [
            {"path": "project", "relation": "is", "values": [{"id": 1180, "type": "Project"}]}]},
    }
    assert ruby_pp(request) == (
        '{"type" => "NotAType",\n "summaries" => [{"field" => "id", "type" => "count"}],\n "filters" =>\n'
        '  {"logical_operator" => "and",\n   "conditions" =>\n    [{"path" => "project",\n'
        '      "relation" => "is",\n      "values" => [{"id" => 1180, "type" => "Project"}]}]}}')


def test_two_keys_break_between_pairs():  # api3 040
    assert ruby_pp({"filter_operator": "all", "filters": [["project", "is", {"type": "Project", "id": 1180}]]}) == (
        '{"filter_operator" => "all",\n "filters" => [["project", "is", {"type" => "Project", "id" => 1180}]]}')
