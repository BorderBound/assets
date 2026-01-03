# board.py
from typing import List

rows = 8
cols = 6
max_steps = 40


class Position:
    def __init__(self, row=0, col=0):
        self.row = row
        self.col = col

    def __ne__(self, other):
        return self.row != other.row or self.col != other.col


POSITION_NONE = Position(15, 15)


class Field:
    def __init__(self, color="g", modifier="0"):
        self.color = color
        self.modifier = modifier
        self.onlyReachableFrom = POSITION_NONE

    def is_color(self, c):
        return c in "rgbod"

    def is_clickable(self):
        return (
            self.is_static_arrow() or self.is_rotating_arrow() or self.modifier in "FB"
        )

    def is_static_arrow(self):
        return self.modifier in "LRUD"

    def is_rotating_arrow(self):
        return self.modifier in "wsax"

    def is_correct(self):
        if not self.is_color(self.color):
            return True
        if self.is_color(self.modifier):
            return self.color == self.modifier
        return self.modifier != "0"


class MoveSequence:
    def __init__(self):
        self.moves: List[Position] = []
        self.n = 0

    def add(self, row, col):
        self.moves.append(Position(row, col))
        self.n += 1

    def __str__(self):
        return ",".join(f"{chr(m.col + ord('A'))}{m.row + 1}" for m in self.moves)


class Board:
    def __init__(self):
        self.fields = [[Field() for _ in range(cols)] for _ in range(rows)]
        self.move_sequence = MoveSequence()
        self.has_bombs = False

    def click(self, row, col):
        self.move_sequence.add(row, col)
        f = self.fields[row][col]

        # Arrow moves
        def fill(dr, dc, r, c, color):
            r += dr
            c += dc
            if not (0 <= r < rows and 0 <= c < cols):
                return False
            from_color = None
            to_color = None
            if self.fields[r][c].modifier == color:
                from_color, to_color = color, "0"
            elif self.fields[r][c].modifier == "0":
                from_color, to_color = "0", color
            else:
                return False
            changed = False
            while (
                0 <= r < rows
                and 0 <= c < cols
                and self.fields[r][c].modifier == from_color
            ):
                self.fields[r][c].modifier = to_color
                r += dr
                c += dc
                changed = True
            return changed

        # Flood fill
        def flood(r, c, from_color, to_color):
            if not (0 <= r < rows and 0 <= c < cols):
                return False
            if self.fields[r][c].modifier != from_color:
                return False
            self.fields[r][c].modifier = to_color
            changed = True
            changed |= flood(r + 1, c, from_color, to_color)
            changed |= flood(r - 1, c, from_color, to_color)
            changed |= flood(r, c + 1, from_color, to_color)
            changed |= flood(r, c - 1, from_color, to_color)
            return changed

        mod = f.modifier
        if mod == "U":
            return fill(-1, 0, row, col, f.color)
        elif mod == "D":
            return fill(1, 0, row, col, f.color)
        elif mod == "L":
            return fill(0, -1, row, col, f.color)
        elif mod == "R":
            return fill(0, 1, row, col, f.color)
        elif mod == "F":
            changed = False
            changed |= flood(row + 1, col, "0", f.color)
            changed |= flood(row - 1, col, "0", f.color)
            changed |= flood(row, col + 1, "0", f.color)
            changed |= flood(row, col - 1, "0", f.color)
            if not changed:
                changed |= flood(row + 1, col, f.color, "0")
                changed |= flood(row - 1, col, f.color, "0")
                changed |= flood(row, col + 1, f.color, "0")
                changed |= flood(row, col - 1, f.color, "0")
            return changed
        elif mod == "B":
            for dr in range(3):
                for dc in range(3):
                    r, c = row - 1 + dr, col - 1 + dc
                    if (
                        0 <= r < rows
                        and 0 <= c < cols
                        and self.fields[r][c].modifier != "X"
                    ):
                        self.fields[r][c].modifier = f.color
            return True
        elif mod == "w":
            fill(-1, 0, row, col, f.color)
            f.modifier = "x"
            return True
        elif mod == "s":
            fill(1, 0, row, col, f.color)
            f.modifier = "a"
            return True
        elif mod == "a":
            fill(0, -1, row, col, f.color)
            f.modifier = "w"
            return True
        elif mod == "x":
            fill(0, 1, row, col, f.color)
            f.modifier = "s"
            return True
        else:
            print("Unknown modifier", mod)
        return False

    def is_solved(self):
        return all(f.is_correct() for row in self.fields for f in row)

    @classmethod
    def from_strings(cls, color_str, modifier_str):
        color_str = color_str.replace(" ", "")
        modifier_str = modifier_str.replace(" ", "")
        b = cls()
        small_board = len(color_str) == 5 * 6
        for r in range(rows):
            for c in range(cols):
                f = b.fields[r][c]
                if small_board and (r >= 6 or c >= 5):
                    f.color = "0"
                    f.modifier = "X"
                    continue
                idx = r * (5 if small_board else 6) + c
                if idx >= len(color_str) or idx >= len(modifier_str):
                    f.color = "0"
                    f.modifier = "X"
                else:
                    f.color = color_str[idx]
                    f.modifier = modifier_str[idx]
        return b

    def display(self):
        for row in range(rows):
            for col in range(cols):
                f = self.fields[row][col]

                if f.color == "0":
                    # Transparent: just print spaces
                    print("  ", end="")
                else:
                    color_code = {
                        "r": 41,  # Red
                        "g": 42,  # Green
                        "b": 44,  # Blue
                        "o": 43,  # Yellow/Orange
                        "d": 45,  # Magenta/Purple
                    }.get(f.color, 40)
                    print(f"\033[{color_code}m  \033[0m", end="")
            print()

    def hash(self):
        """
        Compute a hash of the board’s current state using colors and modifiers.
        """
        flat = []
        for row in self.fields:
            for field in row:
                flat.append((field.color, field.modifier))
        return hash(tuple(flat))

    def copy(self):
        new_board = Board()
        for r in range(rows):
            for c in range(cols):
                f_src = self.fields[r][c]
                f_dst = new_board.fields[r][c]
                f_dst.color = f_src.color
                f_dst.modifier = f_src.modifier
                f_dst.onlyReachableFrom = f_src.onlyReachableFrom
        new_board.move_sequence = MoveSequence()
        for m in self.move_sequence.moves:
            new_board.move_sequence.add(m.row, m.col)
        new_board.has_bombs = self.has_bombs
        return new_board
