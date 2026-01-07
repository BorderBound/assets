// multi_solver_parallel.js
const { Board, Position, POSITION_NONE } = require("./board");

// Maximum steps constant
const maxSteps = 40;

// ------------------------------
// DFS Solver
// ------------------------------
function dfsSolver(initialBoard, debug = false) {
  let bestSolution = null;
  const visited = new Set();

  function dfs(board) {
    if (board.moveSequence.n > maxSteps) return;
    if (board.isSolved()) {
      if (!bestSolution || board.moveSequence.n < bestSolution.moveSequence.n) {
        bestSolution = board.copy();
      }
      return;
    }

    const boardHash = board.hash();
    if (visited.has(boardHash)) return;
    visited.add(boardHash);

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;

        if (f.onlyReachableFrom !== POSITION_NONE) {
          if (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col) continue;
        }

        const newBoard = board.copy();
        // Always try the move, even if it doesn't change the board
        newBoard.click(r, c);

        if (debug) {
          console.log(`DFS trying move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newBoard.moveSequence.n}`);
        }

        dfs(newBoard);
      }
    }
  }

  dfs(initialBoard);
  return bestSolution;
}

// ------------------------------
// BFS Solver
// ------------------------------
function bfsSolver(initialBoard, debug = false) {
  const queue = [initialBoard];
  const visited = new Set([initialBoard.hash()]);

  while (queue.length) {
    const board = queue.shift();
    if (board.isSolved()) return board;
    if (board.moveSequence.n >= maxSteps) continue;

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;

        if (f.onlyReachableFrom !== POSITION_NONE) {
          if (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col) continue;
        }

        const newBoard = board.copy();
        // Always click
        newBoard.click(r, c);

        const hash = newBoard.hash();
        if (visited.has(hash)) continue;
        visited.add(hash);
        queue.push(newBoard);

        if (debug) {
          console.log(`BFS enqueue move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newBoard.moveSequence.n}`);
        }
      }
    }
  }

  return null;
}

// ------------------------------
// A* / Branch-and-Bound Solver
// ------------------------------
function branchBoundSolver(initialBoard, debug = false) {
  const heap = [];
  const seen = new Set();

  function heuristic(board) {
    return board.fields.flat().filter(f => !f.isCorrect()).length;
  }

  heap.push({ priority: heuristic(initialBoard), moves: 0, board: initialBoard });
  seen.add(initialBoard.hash());

  while (heap.length) {
    heap.sort((a, b) => a.priority - b.priority);
    const { priority, moves, board } = heap.shift();

    if (moves >= maxSteps) continue;
    if (board.isSolved()) return board;

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;

        if (f.onlyReachableFrom !== POSITION_NONE) {
          if (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col) continue;
        }

        const newBoard = board.copy();
        // Always click
        newBoard.click(r, c);

        const hash = newBoard.hash();
        if (seen.has(hash)) continue;
        seen.add(hash);

        const newPriority = newBoard.moveSequence.n + heuristic(newBoard);
        heap.push({ priority: newPriority, moves: newBoard.moveSequence.n, board: newBoard });

        if (debug) {
          console.log(`A* enqueue move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newBoard.moveSequence.n}`);
        }
      }
    }
  }

  return null;
}

// ------------------------------
// Run all solvers in parallel (Promise-based)
// ------------------------------
function solveWithAllStrategiesParallel(board, debug = false) {
  const solvers = [
    { name: "DFS", func: dfsSolver },
    { name: "BFS", func: bfsSolver },
    { name: "A*", func: branchBoundSolver },
  ];

  const promises = solvers.map(s =>
    new Promise(resolve => {
      const result = s.func(board, debug);
      if (result) console.log(`# ${s.name} finished with ${result.moveSequence.n} moves`);
      else console.log(`# ${s.name} finished with no solution`);
      resolve(result);
    })
  );

  return Promise.all(promises).then(solutions => {
    const nonNull = solutions.filter(s => s);
    if (!nonNull.length) {
      console.log("# No solution found by any strategy");
      return null;
    }
    const best = nonNull.reduce((a, b) => (a.moveSequence.n < b.moveSequence.n ? a : b));
    console.log(`# Best solution uses ${best.moveSequence.n} moves`);
    return best;
  });
}

module.exports = {
  dfsSolver,
  bfsSolver,
  branchBoundSolver,
  solveWithAllStrategiesParallel,
};
