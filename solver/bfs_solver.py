from board import ROWS, COLS


def solve_bfs(level_nr, initial_board):
    queue = [initial_board]
    seen = set()

    while queue:
        board = queue.pop(0)
        for r in range(ROWS):
            for c in range(COLS):
                if not board.fields[r][c].is_clickable():
                    continue
                new_board = board.copy()
                new_board.click(r, c)
                if new_board.is_solved():
                    return new_board
                h = new_board.hash()
                if h not in seen:
                    seen.add(h)
                    queue.append(new_board)
    return None
