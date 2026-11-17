"""find with each text operator of finding 017, on Shot.code."""

import pytest

pytestmark = pytest.mark.finding("017")

SUFFIXES = ["sh010_0010", "sh010_0020", "sh020_0010"]


@pytest.fixture
def shots(made, sandbox, run_token):
    """Three Shots in the sandbox, coded zzconf_<token>_<suffix>, and the filter that scopes a find to them."""
    prefix = "zzconf_%s_" % run_token
    for suffix in SUFFIXES:
        made.create("Shot", {"code": prefix + suffix, "project": sandbox})
    scope = [["project", "is", sandbox], ["code", "starts_with", prefix]]
    return prefix, scope


def codes(site, scope, sg_filter):
    return sorted(r["code"] for r in site.find("Shot", scope + [sg_filter], ["code"]))


@pytest.mark.cell("find", "is", "text")
def test_is(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "is", prefix + "sh010_0010"]) == [prefix + "sh010_0010"]
    assert codes(site, scope, ["code", "is", prefix + "nope"]) == []


@pytest.mark.cell("find", "is_not", "text")
def test_is_not(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "is_not", prefix + "sh010_0010"]) == [prefix + "sh010_0020", prefix + "sh020_0010"]


@pytest.mark.cell("find", "contains", "text")
def test_contains(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "contains", "010_00"]) == [prefix + "sh010_0010", prefix + "sh010_0020"]
    assert codes(site, scope, ["code", "contains", "zzznope"]) == []


@pytest.mark.cell("find", "not_contains", "text")
def test_not_contains(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "not_contains", "sh010"]) == [prefix + "sh020_0010"]


@pytest.mark.cell("find", "starts_with", "text")
def test_starts_with(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "starts_with", prefix + "sh01"]) == [prefix + "sh010_0010", prefix + "sh010_0020"]
    assert codes(site, scope, ["code", "starts_with", "zzznope"]) == []


@pytest.mark.cell("find", "ends_with", "text")
def test_ends_with(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "ends_with", "0010"]) == [prefix + "sh010_0010", prefix + "sh020_0010"]
    assert codes(site, scope, ["code", "ends_with", "zzznope"]) == []


@pytest.mark.cell("find", "in", "text")
def test_in(site, shots):
    prefix, scope = shots
    wanted = [prefix + "sh010_0010", prefix + "sh020_0010"]
    assert codes(site, scope, ["code", "in", wanted]) == wanted
    assert codes(site, scope, ["code", "in", ["ZZZNOPE1", "ZZZNOPE2"]]) == []


@pytest.mark.cell("find", "not_in", "text")
def test_not_in(site, shots):
    prefix, scope = shots
    assert codes(site, scope, ["code", "not_in", [prefix + "sh010_0010", prefix + "sh020_0010"]]) == [prefix + "sh010_0020"]
