import io

from PIL import Image

from battleship.render import HIT, MISS, SHIP, SUNK, UNKNOWN, image_card, text_board


def grid_rows(board: str) -> list[list[str]]:
    lines = board.split("\n\n")[0].splitlines()[1:]  # drop header and legend
    return [line.split()[1:] for line in lines]


def test_text_board_is_10x10(game):
    rows = grid_rows(text_board(game))
    assert len(rows) == 10
    assert all(len(row) == 10 for row in rows)
    assert all(cell == UNKNOWN for row in rows for cell in row)


def test_text_board_marks_shots(game):
    game.shoot((9, 9))
    game.shoot((2, 5))
    game.shoot((0, 0))
    game.shoot((0, 1))
    rows = grid_rows(text_board(game))
    assert rows[9][9] == MISS
    assert rows[2][5] == HIT
    assert rows[0][0] == rows[0][1] == SUNK


def test_text_board_hides_ships_until_revealed(game):
    assert SHIP not in "".join(sum(grid_rows(text_board(game)), []))
    rows = grid_rows(text_board(game, reveal=True))
    assert rows[3][5] == SHIP


def test_image_card_is_valid_png(game):
    game.shoot((0, 0))
    game.shoot((5, 5))
    img = Image.open(io.BytesIO(image_card(game, reveal=True)))
    assert img.format == "PNG"
    assert img.width > 400 and img.height > 400
