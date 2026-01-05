# main_add_solutions.py
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
        if not move:
            continue
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


def generate_levels(levels):
    xml_lines = ['<levels>']
    for number, lvl in enumerate(levels):
        color = lvl["color"]
        modifier = lvl["modifier"]
        solution = lvl.get("solution", "")
        solution_attr = f' solution="{solution}"' if solution else ""
        xml_lines.append(f'  <level number="{number}" color="{color}" modifier="{modifier}"{solution_attr} />')
    xml_lines.append('</levels>')
    return "\n".join(xml_lines)


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

    updated_levels = []

    for level_number, attrs in enumerate(levels):
        # Skip levels if starting at a specific level
        if level_to_start is not None:
            if continue_after:
                if level_number < level_to_start:
                    updated_levels.append(attrs)
                    continue
            else:
                if level_number != level_to_start:
                    updated_levels.append(attrs)
                    continue

        print(f"\nSolving Level {level_number}...")

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
        # Run solver
        # ------------------------------
        new_board = solve_with_all_strategies_parallel(board)

        # ------------------------------
        # Choose best solution
        # ------------------------------
        chosen_board = None
        solution_str = None

        if new_board and existing_board:
            if new_board.move_sequence.n < existing_moves:
                print("# New solution is better")
                chosen_board = new_board
                solution_str = str(new_board.move_sequence)
            else:
                print("# Keeping existing solution")
                chosen_board = existing_board
                solution_str = existing_solution
        elif new_board:
            print("# Using new solution")
            chosen_board = new_board
            solution_str = str(new_board.move_sequence)
        elif existing_board:
            print("# Solver failed, keeping existing solution")
            chosen_board = existing_board
            solution_str = existing_solution
        else:
            print("# No solution found")
            chosen_board = None
            solution_str = ""

        # ------------------------------
        # Save solution to level attributes
        # ------------------------------
        attrs["solution"] = solution_str
        updated_levels.append(attrs)

        # ------------------------------
        # Write updated XML after each level
        # ------------------------------
        new_xml = generate_levels(updated_levels)
        out_file = xml_file.replace(".xml", "_solved.xml")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(new_xml)
        print(f"# Updated XML saved to {out_file}")

        # ------------------------------
        # Display
        # ------------------------------
        if chosen_board:
            print(f"Solution moves: {solution_str}")
            print("Completed board:")
            chosen_board.display()

        input("# Press Enter to continue after solution...")

    print("\nAll selected levels processed. Final XML saved.")


if __name__ == "__main__":
    main()
