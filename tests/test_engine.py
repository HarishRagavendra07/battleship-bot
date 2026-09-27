import random

import pytest

from battleship.engine import BOARD_SIZE, FLEET, Game, GameOverError, Ship, ShotResult, place_fleet


def test_miss(game):
    shot = game.shoot((9, 9))
    assert shot.result is ShotResult.MISS
    assert game.misses == {(9, 9)}
    assert game.shots_fired == 1


def test_hit_then_sunk(game):
    assert game.shoot((0, 0)).result is ShotResult.HIT
    shot = game.shoot((0, 1))
    assert shot.result is ShotResult.SUNK
    assert shot.ship.name == "Destroyer"
    assert not shot.game_over
    assert game.ships_remaining == 1


def test_repeat_shot_is_not_counted(game):
    game.shoot((5, 5))
    assert game.shoot((5, 5)).result is ShotResult.REPEAT
    assert game.shots_fired == 1


def test_sinking_last_ship_wins(game):
    for coord in [(0, 0), (0, 1), (2, 5), (3, 5)]:
        game.shoot(coord)
    shot = game.shoot((4, 5))
    assert shot.result is ShotResult.SUNK
    assert shot.game_over
    assert game.won and game.over
    assert game.accuracy == 1.0


def test_cannot_shoot_after_game_over(game):
    game.surrender()
    with pytest.raises(GameOverError):
        game.shoot((0, 0))


@pytest.mark.parametrize("coord", [(-1, 0), (0, -1), (10, 0), (0, 10)])
def test_out_of_bounds_rejected(game, coord):
    with pytest.raises(ValueError):
        game.shoot(coord)


def test_overlapping_ships_rejected():
    ships = [Ship("A", frozenset({(0, 0), (0, 1)})), Ship("B", frozenset({(0, 1), (1, 1)}))]
    with pytest.raises(ValueError, match="overlaps"):
        Game(ships=ships)


def test_off_board_ship_rejected():
    with pytest.raises(ValueError, match="off the board"):
        Game(ships=[Ship("A", frozenset({(9, 9), (9, 10)}))])


@pytest.mark.parametrize("seed", range(200))
def test_random_fleet_is_valid(seed):
    ships = place_fleet(rng=random.Random(seed))
    assert sorted(s.size for s in ships) == sorted(FLEET.values())

    all_cells = [cell for s in ships for cell in s.cells]
    assert len(all_cells) == len(set(all_cells)), "ships overlap"
    assert all(0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE for r, c in all_cells)

    for ship in ships:
        rows = {r for r, _ in ship.cells}
        cols = {c for _, c in ship.cells}
        assert len(rows) == 1 or len(cols) == 1, f"{ship.name} is not straight"
        line = sorted(cols) if len(rows) == 1 else sorted(rows)
        assert line == list(range(line[0], line[0] + ship.size)), f"{ship.name} has gaps"


def test_same_seed_same_layout():
    a = place_fleet(rng=random.Random(42))
    b = place_fleet(rng=random.Random(42))
    assert [s.cells for s in a] == [s.cells for s in b]
