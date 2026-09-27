import pytest

from battleship.engine import Game, Ship


def make_ships() -> list[Ship]:
    """A small, known layout: a horizontal Destroyer and a vertical Cruiser."""
    return [
        Ship("Destroyer", frozenset({(0, 0), (0, 1)})),
        Ship("Cruiser", frozenset({(2, 5), (3, 5), (4, 5)})),
    ]


@pytest.fixture
def game() -> Game:
    return Game(ships=make_ships())
