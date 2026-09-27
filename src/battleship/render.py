"""Turn a :class:`Game` into something a human can look at.

Two renderers are provided:

* :func:`text_board` - a monospace grid for a Discord code block.
* :func:`image_card` - a PNG "card" drawn with Pillow (the bonus feature).
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from .engine import Game

# --- Text ------------------------------------------------------------------

UNKNOWN, MISS, HIT, SUNK, SHIP = ".", "o", "x", "X", "#"

TEXT_LEGEND = f"{MISS} miss   {HIT} hit   {SUNK} sunk   {UNKNOWN} unexplored"


def _cell_symbol(game: Game, coord: tuple[int, int], reveal: bool) -> str:
    ship = game.ship_at(coord)
    if coord in game.misses:
        return MISS
    if coord in game.hits:
        return SUNK if ship and ship.sunk else HIT
    if reveal and ship:
        return SHIP
    return UNKNOWN


def text_board(game: Game, reveal: bool = False) -> str:
    """Render the board as a fixed-width grid with 1-based labels."""
    header = "    " + "".join(f"{c + 1:>3}" for c in range(game.size))
    rows = [header]
    for r in range(game.size):
        cells = "".join(f"{_cell_symbol(game, (r, c), reveal):>3}" for c in range(game.size))
        rows.append(f"{r + 1:>3} {cells}")
    legend = TEXT_LEGEND + (f"   {SHIP} ship" if reveal else "")
    return "\n".join(rows) + "\n\n" + legend


# --- Image -----------------------------------------------------------------

CELL = 44
LABEL = 32
PAD = 24
HEADER = 76
FOOTER = 56

BG = (11, 29, 51)
WATER = (26, 72, 115)
GRID = (45, 106, 163)
LABEL_FG = (156, 190, 222)
TITLE_FG = (240, 246, 252)
MISS_FG = (226, 236, 245)
HIT_FG = (239, 83, 80)
SUNK_BG = (110, 28, 36)
SHIP_BG = (96, 110, 128)


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no sized default font
        return ImageFont.load_default()


def image_card(game: Game, reveal: bool = False, title: str = "BATTLESHIP") -> bytes:
    """Render the board as a PNG and return the encoded bytes."""
    grid_px = CELL * game.size
    width = PAD * 2 + LABEL + grid_px
    height = HEADER + LABEL + grid_px + FOOTER + PAD

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    title_font, stat_font, label_font = _font(26), _font(15), _font(15)

    # Header: title + running stats.
    draw.text((PAD, 18), title, font=title_font, fill=TITLE_FG)
    stats = (
        f"Shots {game.shots_fired}   Hits {len(game.hits)}   "
        f"Accuracy {game.accuracy:.0%}   Ships left {game.ships_remaining}/{len(game.ships)}"
    )
    draw.text((PAD, 52), stats, font=stat_font, fill=LABEL_FG)

    ox, oy = PAD + LABEL, HEADER + LABEL

    # Axis labels.
    for i in range(game.size):
        centre = CELL * i + CELL // 2
        draw.text((ox + centre, oy - LABEL // 2), str(i + 1), font=label_font, fill=LABEL_FG, anchor="mm")
        draw.text((ox - LABEL // 2, oy + centre), str(i + 1), font=label_font, fill=LABEL_FG, anchor="mm")

    # Cells.
    for r in range(game.size):
        for c in range(game.size):
            x0, y0 = ox + c * CELL, oy + r * CELL
            x1, y1 = x0 + CELL, y0 + CELL
            ship = game.ship_at((r, c))
            fill = WATER
            if (r, c) in game.hits and ship and ship.sunk:
                fill = SUNK_BG
            elif reveal and ship and (r, c) not in game.hits:
                fill = SHIP_BG
            draw.rectangle((x0, y0, x1, y1), fill=fill, outline=GRID, width=1)

            cx, cy = x0 + CELL // 2, y0 + CELL // 2
            if (r, c) in game.misses:
                rad = CELL // 7
                draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=MISS_FG)
            elif (r, c) in game.hits:
                rad = CELL // 3
                draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=HIT_FG)
                arm = CELL // 6
                draw.line((cx - arm, cy - arm, cx + arm, cy + arm), fill=TITLE_FG, width=3)
                draw.line((cx - arm, cy + arm, cx + arm, cy - arm), fill=TITLE_FG, width=3)

    # Legend.
    ly = oy + grid_px + 22
    lx = PAD
    legend = [("miss", MISS_FG, "dot"), ("hit", HIT_FG, "hit"), ("sunk", SUNK_BG, "box")]
    if reveal:
        legend.append(("ship", SHIP_BG, "box"))
    for label, colour, kind in legend:
        if kind == "dot":
            draw.ellipse((lx + 5, ly + 5, lx + 13, ly + 13), fill=colour)
        elif kind == "hit":
            draw.ellipse((lx, ly, lx + 18, ly + 18), fill=colour)
        else:
            draw.rectangle((lx, ly, lx + 18, ly + 18), fill=colour, outline=GRID)
        draw.text((lx + 26, ly + 9), label, font=label_font, fill=LABEL_FG, anchor="lm")
        lx += 90

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
