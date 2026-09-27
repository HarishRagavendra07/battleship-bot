"""Core Battleship game logic, independent of any chat platform.

Coordinates inside the engine are zero-based ``(row, col)`` tuples.
The presentation layer is responsible for translating to/from the
one-based coordinates players type.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

BOARD_SIZE = 10

# Classic Milton Bradley fleet, largest first so random placement packs well.
FLEET: dict[str, int] = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}

Coord = tuple[int, int]


class ShotResult(Enum):
    MISS = "miss"
    HIT = "hit"
    SUNK = "sunk"
    REPEAT = "repeat"


@dataclass
class Ship:
    name: str
    cells: frozenset[Coord]
    hits: set[Coord] = field(default_factory=set)

    @property
    def size(self) -> int:
        return len(self.cells)

    @property
    def sunk(self) -> bool:
        return len(self.hits) == len(self.cells)


@dataclass(frozen=True)
class Shot:
    coord: Coord
    result: ShotResult
    ship: Ship | None = None
    game_over: bool = False


class GameOverError(RuntimeError):
    """Raised when a shot is fired at a finished game."""


def place_fleet(
    size: int = BOARD_SIZE,
    fleet: dict[str, int] = FLEET,
    rng: random.Random | None = None,
) -> list[Ship]:
    """Randomly place every ship in ``fleet`` without overlaps."""
    rng = rng or random.Random()
    occupied: set[Coord] = set()
    ships: list[Ship] = []

    for name, length in fleet.items():
        if length > size:
            raise ValueError(f"{name} (length {length}) does not fit on a {size}x{size} board")
        for _ in range(10_000):
            horizontal = rng.random() < 0.5
            row = rng.randrange(size if horizontal else size - length + 1)
            col = rng.randrange(size - length + 1 if horizontal else size)
            cells = frozenset(
                (row, col + i) if horizontal else (row + i, col) for i in range(length)
            )
            if not cells & occupied:
                occupied |= cells
                ships.append(Ship(name, cells))
                break
        else:
            raise ValueError("Could not place fleet; board is too crowded")

    return ships


class Game:
    """A single-player game: the bot hides a fleet, the player hunts it."""

    def __init__(
        self,
        size: int = BOARD_SIZE,
        ships: list[Ship] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.size = size
        self.ships = ships if ships is not None else place_fleet(size, rng=rng)
        self.hits: set[Coord] = set()
        self.misses: set[Coord] = set()
        self.surrendered = False

        self._ship_at: dict[Coord, Ship] = {}
        for ship in self.ships:
            for cell in ship.cells:
                if not self.in_bounds(cell):
                    raise ValueError(f"{ship.name} is off the board at {cell}")
                if cell in self._ship_at:
                    raise ValueError(f"{ship.name} overlaps {self._ship_at[cell].name} at {cell}")
                self._ship_at[cell] = ship

    def in_bounds(self, coord: Coord) -> bool:
        row, col = coord
        return 0 <= row < self.size and 0 <= col < self.size

    def ship_at(self, coord: Coord) -> Ship | None:
        return self._ship_at.get(coord)

    @property
    def won(self) -> bool:
        return all(ship.sunk for ship in self.ships)

    @property
    def over(self) -> bool:
        return self.won or self.surrendered

    @property
    def shots_fired(self) -> int:
        return len(self.hits) + len(self.misses)

    @property
    def accuracy(self) -> float:
        return len(self.hits) / self.shots_fired if self.shots_fired else 0.0

    @property
    def ships_remaining(self) -> int:
        return sum(not ship.sunk for ship in self.ships)

    def shoot(self, coord: Coord) -> Shot:
        if self.over:
            raise GameOverError("This game is already over")
        if not self.in_bounds(coord):
            raise ValueError(f"{coord} is outside the {self.size}x{self.size} board")
        if coord in self.hits or coord in self.misses:
            return Shot(coord, ShotResult.REPEAT)

        ship = self._ship_at.get(coord)
        if ship is None:
            self.misses.add(coord)
            return Shot(coord, ShotResult.MISS)

        ship.hits.add(coord)
        self.hits.add(coord)
        if ship.sunk:
            return Shot(coord, ShotResult.SUNK, ship, game_over=self.won)
        return Shot(coord, ShotResult.HIT, ship)

    def surrender(self) -> None:
        self.surrendered = True
