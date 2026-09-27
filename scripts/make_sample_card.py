"""Generate docs/sample-board.png for the README."""

import random
from pathlib import Path

from battleship.engine import Game
from battleship.render import image_card

rng = random.Random(7)
game = Game(rng=rng)

# Sink two ships outright, wing a third, and scatter some misses.
for ship in game.ships[3:]:
    for cell in ship.cells:
        game.shoot(cell)
game.shoot(sorted(game.ships[0].cells)[1])
water = [(r, c) for r in range(game.size) for c in range(game.size) if game.ship_at((r, c)) is None]
for coord in rng.sample(water, 14):
    game.shoot(coord)

out = Path(__file__).resolve().parent.parent / "docs" / "sample-board.png"
out.write_bytes(image_card(game))
print(f"wrote {out}")
