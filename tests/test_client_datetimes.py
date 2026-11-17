"""Naive datetimes in writes and filters, read as the client sends them (shotgun_api3 _transform_outbound)."""

import datetime

import pytest
from shotgun_api3.shotgun import SG_TIMEZONE

from sg_mockgun import Shotgun, schemas
from sg_mockgun.wire import client_datetime

NAIVE = datetime.datetime(2026, 3, 1, 10, 30)
LOCAL = NAIVE.replace(tzinfo=SG_TIMEZONE.local)


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
    sg.require_project = False
    return sg


def test_client_datetime_reads_a_naive_value_as_local_time():
    assert client_datetime(NAIVE, True) == LOCAL
    assert client_datetime(NAIVE, True).tzinfo is not None


def test_client_datetime_reads_a_naive_value_as_utc_when_conversion_is_off():
    assert client_datetime(NAIVE, False) == NAIVE.replace(tzinfo=datetime.timezone.utc)


def test_client_datetime_leaves_aware_values_and_other_types():
    aware = datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc)
    assert client_datetime(aware, True) is aware
    assert client_datetime(None, True) is None
    assert client_datetime(datetime.date(2026, 3, 1), True) == datetime.date(2026, 3, 1)


def test_a_naive_write_stores_an_aware_value(sg):
    shot = sg.create("Shot", {"code": "a", "created_at": NAIVE})
    stored = sg.find_one("Shot", [["id", "is", shot["id"]]], ["created_at"])["created_at"]
    assert stored == LOCAL and stored.tzinfo is not None


def test_order_mixes_written_and_server_set_datetimes(sg):
    sg.create("Shot", {"code": "old", "created_at": NAIVE})
    sg.create("Shot", {"code": "new"})
    rows = sg.find("Shot", [], ["code"], order=[{"field_name": "created_at", "direction": "desc"}])
    assert [r["code"] for r in rows] == ["new", "old"]


def test_a_naive_filter_value_matches_a_naive_write(sg):
    sg.create("Shot", {"code": "a", "created_at": NAIVE})
    assert len(sg.find("Shot", [["created_at", "is", NAIVE]])) == 1
    later = NAIVE + datetime.timedelta(hours=1)
    assert len(sg.find("Shot", [["created_at", "less_than", later]])) == 1
    assert len(sg.find("Shot", [["created_at", "between", [NAIVE, later]]])) == 1


def test_order_reads_a_naive_value_stored_straight_in_the_table(sg):
    # Upstream mockgun callers write rows into _db directly.
    old = sg.create("Shot", {"code": "old"})
    sg._db["Shot"][old["id"]]["created_at"] = NAIVE
    sg.create("Shot", {"code": "new"})
    rows = sg.find("Shot", [], ["code"], order=[{"field_name": "created_at", "direction": "asc"}])
    assert [r["code"] for r in rows] == ["old", "new"]
