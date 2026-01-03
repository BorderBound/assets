# main.py
import sys
from simple_xml import SimpleXml
from board import Board
from multi_solver import solve_with_all_strategies_parallel


# ------------------------------
# Helpers
# ------------------------------
def parse_move(move: str):
    col = ord(move[0].upper()) - ord("A")
    row = int(move[1:]) - 1
    return row, col


def replay_solution(board: Board, solution_str: str):
    b = board.copy()
    for move in solution_str.split(","):
        r, c = parse_move(move)
        changed = b.click(r, c)
        if not changed:
            raise ValueError(f"Invalid move: {move}")
    return b


def count_moves(solution_str: str) -> int:
    return len([m for m in solution_str.split(",") if m])


def try_existing_solution(board: Board, solution_str: str):
    try:
        solved = replay_solution(board, solution_str)
        if solved.is_solved():
            return solved
    except Exception:
        pass
    return None


# ------------------------------
# Main
# ------------------------------
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <levels.xml> [level_number[+]]")
        return

    xml_file = sys.argv[1]
    level_arg = sys.argv[2] if len(sys.argv) >= 3 else None

    level_to_start = None
    continue_after = False

    if level_arg:
        if level_arg.endswith("+"):
            level_to_start = int(level_arg[:-1])
            continue_after = True
        else:
            level_to_start = int(level_arg)

    with open(xml_file, "r", encoding="utf-8") as f:
        xml_data = f.read()

    try:
        levels = SimpleXml.parse_levels(xml_data)
        print(f"Parsed {len(levels)} levels")
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    for level_number, attrs in enumerate(levels):
        if level_to_start is not None:
            if continue_after:
                if level_number < level_to_start:
                    continue
            else:
                if level_number != level_to_start:
                    continue

        print(f"\nFinding Level {level_number} Solution...")

        board = Board.from_strings(attrs["color"], attrs["modifier"])

        # ------------------------------
        # Test existing solution
        # ------------------------------
        existing_solution = attrs.get("solution")
        existing_board = None
        existing_moves = None

        if existing_solution:
            existing_board = try_existing_solution(board, existing_solution)
            if existing_board:
                existing_moves = count_moves(existing_solution)
                print(f"# Existing solution valid ({existing_moves} moves)")
            else:
                print("# Existing solution INVALID")

        # ------------------------------
        # Run solvers
        # ------------------------------
        new_board = solve_with_all_strategies_parallel(board)

        # ------------------------------
        # Choose best
        # ------------------------------
        chosen_board = None

        if new_board and existing_board:
            if new_board.move_sequence.n < existing_moves:
                print("# New solution is better")
                chosen_board = new_board
            else:
                print("# Keeping existing solution")
                chosen_board = existing_board

        elif new_board:
            print("# Using new solution")
            chosen_board = new_board

        elif existing_board:
            print("# Solver failed, keeping existing solution")
            chosen_board = existing_board

        else:
            print("# No solution found")

        # ------------------------------
        # Output
        # ------------------------------
        if chosen_board:
            print(f"Solution: {chosen_board.move_sequence}")
            print("Completed board:")
            chosen_board.display()

        print()
        input("# Press Enter to continue after solution...")


if __name__ == "__main__":
    main()
