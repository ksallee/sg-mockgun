"""``sg-mockgun serve --seed``."""

import os

from sg_mockgun import Shotgun, schemas
from sg_mockgun.server import build_mock, parse_args

SMALL = os.path.join(os.path.dirname(__file__), "fixtures", "seed", "small.json")


def test_seed_is_an_option_of_serve():
    args = parse_args(["serve", "--seed", SMALL])
    assert args.seed == SMALL


def test_build_mock_loads_the_seed():
    mock = build_mock("fpt_8_91", SMALL)
    assert mock.find_one("Shot", [["id", "is", 1001]], ["code"])["code"] == "sh010"


def test_build_mock_without_a_seed_is_empty():
    mock = build_mock("fpt_8_91", None)
    assert mock.find("Shot", []) == []
