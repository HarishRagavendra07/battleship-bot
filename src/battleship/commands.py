"""Chat command handling, decoupled from Discord.

:class:`GameManager` turns a raw chat message into a :class:`Reply`.
Keeping this layer platform-agnostic means the whole command flow is
unit-testable without a Discord connection, and a Slack or CLI adapter
could reuse it unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Hashable
from dataclasses import dataclass

from .engine import BOARD_SIZE, Coord, Game, ShotResult
from .render import image_card, text_board

PREFIX = "bb"

HELP_TEXT = f"""\
**Battleship Bot** - sink the hidden fleet in as few shots as you can.

The bot hides 5 ships on a {BOARD_SIZE}x{BOARD_SIZE} grid:
Carrier (5), Battleship (4), Cruiser (3), Submarine (3), Destroyer (2).
Ships sit horizontally or vertically and never overlap.

**Commands**
`bb help` - show these rules
`bb start` - start a new game
`bb shoot r,c` - fire at row `r`, column `c` (1-{BOARD_SIZE}), e.g. `bb shoot 3,7`
`bb surrender` - give up and reveal the fleet

Each player gets their own game per channel."""

_COORD_RE = re.compile(r"^\s*(\d{1,2})\s*[,\s]\s*(\d{1,2})\s*$")


@dataclass(frozen=True)
class Reply:
    text: str
    image: bytes | None = None


def parse_coord(raw: str, size: int = BOARD_SIZE) -> Coord:
    """Parse a 1-based ``"r,c"`` string into a zero-based coordinate."""
    match = _COORD_RE.match(raw)
    if not match:
        raise ValueError(f"I couldn't read `{raw.strip() or ' '}` as a target. Try `bb shoot 3,7`.")
    row, col = int(match[1]), int(match[2])
    if not (1 <= row <= size and 1 <= col <= size):
        raise ValueError(f"`{row},{col}` is off the board - rows and columns go from 1 to {size}.")
    return row - 1, col - 1


class GameManager:
    """Owns one :class:`Game` per player and routes ``bb`` commands."""

    def __init__(
        self,
        board_style: str = "image",
        game_factory: Callable[[], Game] = Game,
    ) -> None:
        if board_style not in ("image", "text"):
            raise ValueError("board_style must be 'image' or 'text'")
        self.board_style = board_style
        self.game_factory = game_factory
        self.games: dict[Hashable, Game] = {}

    def handle(self, player: Hashable, content: str) -> Reply | None:
        """Return a reply for ``content``, or ``None`` if it isn't a bot command."""
        parts = content.strip().split(maxsplit=2)
        if not parts or parts[0].lower() != PREFIX:
            return None

        command = parts[1].lower() if len(parts) > 1 else "help"
        arg = parts[2] if len(parts) > 2 else ""

        handlers = {
            "help": self._help,
            "start": self._start,
            "shoot": self._shoot,
            "surrender": self._surrender,
        }
        handler = handlers.get(command)
        if handler is None:
            return Reply(f"Unknown command `{command}`. Type `bb help` for the list of commands.")
        return handler(player, arg)

    # -- command handlers ---------------------------------------------------

    def _help(self, player: Hashable, arg: str) -> Reply:
        return Reply(HELP_TEXT)

    def _start(self, player: Hashable, arg: str) -> Reply:
        if player in self.games:
            return Reply(
                "You already have a game in progress. Keep shooting, "
                "or `bb surrender` to reveal the fleet and start over."
            )
        game = self.game_factory()
        self.games[player] = game
        return self._with_board(
            game,
            f"New game! {len(game.ships)} ships are hiding on the "
            f"{game.size}x{game.size} grid. Fire with `bb shoot r,c`.",
        )

    def _shoot(self, player: Hashable, arg: str) -> Reply:
        game = self.games.get(player)
        if game is None:
            return Reply("You don't have a game running. Type `bb start` to begin.")
        try:
            coord = parse_coord(arg, game.size)
        except ValueError as exc:
            return Reply(str(exc))

        shot = game.shoot(coord)
        label = f"{coord[0] + 1},{coord[1] + 1}"

        if shot.result is ShotResult.REPEAT:
            return Reply(f"You've already fired at {label}. Pick another target.")
        if shot.result is ShotResult.MISS:
            return self._with_board(game, f"{label}: **Miss.** Just open water.")
        if shot.result is ShotResult.HIT:
            return self._with_board(game, f"{label}: **Hit!**")

        assert shot.ship is not None
        if shot.game_over:
            del self.games[player]
            return self._with_board(
                game,
                f"{label}: **You sank the {shot.ship.name}!**\n"
                f":tada: **Congratulations, the entire fleet is sunk!** "
                f"You won in {game.shots_fired} shots with {game.accuracy:.0%} accuracy. "
                "Type `bb start` to play again.",
                reveal=True,
            )
        return self._with_board(
            game,
            f"{label}: **You sank the {shot.ship.name}!** "
            f"{game.ships_remaining} ship{'s' if game.ships_remaining != 1 else ''} left.",
        )

    def _surrender(self, player: Hashable, arg: str) -> Reply:
        game = self.games.pop(player, None)
        if game is None:
            return Reply("There's no game to surrender. Type `bb start` to begin one.")
        game.surrender()
        return self._with_board(
            game,
            f"You surrendered after {game.shots_fired} shots. Here's where the fleet was hiding. "
            "Type `bb start` for a rematch.",
            reveal=True,
        )

    # -- helpers ------------------------------------------------------------

    def _with_board(self, game: Game, message: str, reveal: bool = False) -> Reply:
        if self.board_style == "image":
            return Reply(message, image_card(game, reveal=reveal))
        return Reply(f"{message}\n```\n{text_board(game, reveal=reveal)}\n```")
