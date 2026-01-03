# multi_solver_parallel.py
from board import Board, Position, rows, cols, max_steps
from multiprocessing import Pool, Manager
import itertools
import copy
from collections import deque
import heapq
import time


# ------------------------------
# DFS Solver
# ------------------------------
def dfs_solver(initial_board: Board):
    best_solution = None
    visited = set()

    def dfs(board: Board):
        nonlocal best_solution
        if board.move_sequence.n > max_steps:
            return

        if board.is_solved():
            if (
                best_solution is None
                or board.move_sequence.n < best_solution.move_sequence.n
            ):
                best_solution = copy.deepcopy(board)
            return

        board_hash = board.hash()
        if board_hash in visited:
            return
        visited.add(board_hash)

        for r in range(rows):
            for c in range(cols):
                f = board.fields[r][c]
                if not f.is_clickable():
                    continue

                if f.onlyReachableFrom != Position(15, 15):
                    if r != f.onlyReachableFrom.row or c != f.onlyReachableFrom.col:
                        continue

                new_board = copy.deepcopy(board)
                changed = new_board.click(r, c)
                if changed:
                    dfs(new_board)

    dfs(initial_board)
    return best_solution


# ------------------------------
# BFS Solver
# ------------------------------
def bfs_solver(initial_board: Board):
    queue = deque()
    visited = set()

    queue.append(initial_board)
    visited.add(initial_board.hash())

    while queue:
        board = queue.popleft()
        if board.is_solved():
            return board
        if board.move_sequence.n >= max_steps:
            continue

        for r in range(rows):
            for c in range(cols):
                f = board.fields[r][c]
                if not f.is_clickable():
                    continue

                if f.onlyReachableFrom != Position(15, 15):
                    if r != f.onlyReachableFrom.row or c != f.onlyReachableFrom.col:
                        continue

                new_board = copy.deepcopy(board)
                changed = new_board.click(r, c)
                if not changed:
                    continue

                h = new_board.hash()
                if h in visited:
                    continue
                visited.add(h)
                queue.append(new_board)
    return None


# ------------------------------
# A* / Branch-and-Bound Solver
# ------------------------------
def branch_bound_solver(initial_board: Board):
    heap = []
    counter = itertools.count()
    seen = set()

    def heuristic(board: Board):
        return sum(1 for row in board.fields for f in row if not f.is_correct())

    heapq.heappush(heap, (heuristic(initial_board), 0, next(counter), initial_board))
    seen.add(initial_board.hash())

    while heap:
        priority, moves_count, _, board = heapq.heappop(heap)
        if moves_count >= max_steps:
            continue
        if board.is_solved():
            return board

        for r in range(rows):
            for c in range(cols):
                f = board.fields[r][c]
                if not f.is_clickable():
                    continue

                if f.onlyReachableFrom != Position(15, 15):
                    if r != f.onlyReachableFrom.row or c != f.onlyReachableFrom.col:
                        continue

                new_board = copy.deepcopy(board)
                changed = new_board.click(r, c)
                if not changed:
                    continue

                h = new_board.hash()
                if h in seen:
                    continue
                seen.add(h)

                new_priority = new_board.move_sequence.n + heuristic(new_board)
                heapq.heappush(
                    heap,
                    (new_priority, new_board.move_sequence.n, next(counter), new_board),
                )

    return None


# ------------------------------
# Parallel solver with timeout after first solution
# ------------------------------
def _solver_worker(board, solver_func, solver_name, return_dict):
    solution = solver_func(board)
    if solution:
        print(f"# {solver_name} finished with {solution.move_sequence.n} moves")
        return_dict[solver_name] = solution
    else:
        print(f"# {solver_name} finished with no solution")
    return solution


def solve_with_all_strategies_parallel(board: Board, wait_after_first=300):
    """
    Runs DFS, BFS, and A* in parallel.
    Returns the shortest solution found.
    If a solution is found, waits up to wait_after_first seconds
    for possibly better solutions, then cancels remaining solvers
    and returns the best solution so far.
    """
    solvers = [("DFS", dfs_solver), ("BFS", bfs_solver), ("A*", branch_bound_solver)]
    manager = Manager()
    return_dict = manager.dict()

    pool = Pool(processes=len(solvers))
    results = []
    try:
        for name, func in solvers:
            r = pool.apply_async(_solver_worker, args=(board, func, name, return_dict))
            results.append((name, r))

        first_solution_time = None
        while True:
            # Check if any solver has finished and record first solution time
            if return_dict and first_solution_time is None:
                first_solution_time = time.time()

            # Timeout reached after first solution
            if first_solution_time is not None:
                elapsed = time.time() - first_solution_time
                if elapsed >= wait_after_first:
                    print(
                        f"# Timeout reached ({wait_after_first}s) after first solution"
                    )
                    # Cancel all remaining tasks
                    pool.terminate()
                    pool.join()
                    break

            # All solvers finished naturally
            if all(r[1].ready() for r in results):
                pool.close()
                pool.join()
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        pool.terminate()
        pool.join()
        raise

    # Collect solutions from return_dict
    solutions = list(return_dict.values())
    if not solutions:
        print("# No solution found by any strategy")
        return None

    # Pick the shortest move sequence
    best = min(solutions, key=lambda b: b.move_sequence.n)
    print(f"# Best solution uses {best.move_sequence.n} moves")
    return best
