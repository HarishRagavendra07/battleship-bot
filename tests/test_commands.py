import pytest
from conftest import make_ships

from battleship.commands import GameManager, parse_coord
from battleship.engine import Game

PLAYER = ("channel", "user")


@pytest.fixture
def manager() -> GameManager:
    return GameManager(board_style="text", game_factory=lambda: Game(ships=make_ships()))


@pytest.mark.parametrize("message", ["hello", "", "bbq time", "please bb start"])
def test_ignores_non_commands(manager, message):
    assert manager.handle(PLAYER, message) is None


@pytest.mark.parametrize("message", ["bb help", "BB HELP", "bb"])
def test_help(manager, message):
    assert "bb shoot r,c" in manager.handle(PLAYER, message).text


def test_unknown_command(manager):
    assert "Unknown command" in manager.handle(PLAYER, "bb dance").text


def test_start_shows_board(manager):
    reply = manager.handle(PLAYER, "bb start")
    assert "New game" in reply.text
    assert "```" in reply.text


def test_start_twice_keeps_existing_game(manager):
    manager.handle(PLAYER, "bb start")
    manager.handle(PLAYER, "bb shoot 1,1")
    reply = manager.handle(PLAYER, "bb start")
    assert "already have a game" in reply.text
    assert manager.games[PLAYER].shots_fired == 1


def test_shoot_without_game(manager):
    assert "bb start" in manager.handle(PLAYER, "bb shoot 1,1").text


@pytest.mark.parametrize("arg", ["", "a,b", "1", "0,1", "11,1", "1,11"])
def test_bad_coordinates(manager, arg):
    manager.handle(PLAYER, "bb start")
    reply = manager.handle(PLAYER, f"bb shoot {arg}")
    assert "```" not in reply.text  # no board, just an error
    assert manager.games[PLAYER].shots_fired == 0


def test_shot_outcomes(manager):
    manager.handle(PLAYER, "bb start")
    assert "Miss" in manager.handle(PLAYER, "bb shoot 10,10").text
    assert "Hit" in manager.handle(PLAYER, "bb shoot 1,1").text
    assert "already fired" in manager.handle(PLAYER, "bb shoot 1,1").text
    sunk = manager.handle(PLAYER, "bb shoot 1,2").text
    assert "sank the Destroyer" in sunk and "1 ship left" in sunk


def test_full_game_ends_with_congratulations(manager):
    manager.handle(PLAYER, "bb start")
    for target in ["1,1", "1,2", "3,6", "4,6"]:
        manager.handle(PLAYER, f"bb shoot {target}")
    reply = manager.handle(PLAYER, "bb shoot 5,6")
    assert "Congratulations" in reply.text
    assert "5 shots" in reply.text
    assert PLAYER not in manager.games


def test_surrender_reveals_fleet(manager):
    manager.handle(PLAYER, "bb start")
    reply = manager.handle(PLAYER, "bb surrender")
    assert "surrendered" in reply.text
    assert "#" in reply.text
    assert PLAYER not in manager.games


def test_surrender_without_game(manager):
    assert "no game" in manager.handle(PLAYER, "bb surrender").text


def test_players_have_separate_games(manager):
    other = ("channel", "someone-else")
    manager.handle(PLAYER, "bb start")
    assert "bb start" in manager.handle(other, "bb shoot 1,1").text


def test_image_mode_attaches_png():
    manager = GameManager(board_style="image", game_factory=lambda: Game(ships=make_ships()))
    reply = manager.handle(PLAYER, "bb start")
    assert reply.image is not None and reply.image.startswith(b"\x89PNG")
    assert "```" not in reply.text


@pytest.mark.parametrize(
    "raw, expected", [("3,7", (2, 6)), (" 3 , 7 ", (2, 6)), ("3 7", (2, 6)), ("10,10", (9, 9))]
)
def test_parse_coord(raw, expected):
    assert parse_coord(raw) == expected
