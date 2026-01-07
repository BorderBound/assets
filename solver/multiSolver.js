// multiSolver_optimized_safe.js
const { Board, Position, POSITION_NONE } = require("./board");
const FastPriorityQueue = require("fastpriorityqueue"); // npm install fastpriorityqueue

const maxSteps = 100;
const MAX_QUEUE_SIZE = 100_000; // prevent heap blowup
const TIMEOUT_MS = 3 * 60 * 1000; // 3 minutes

// ------------------------------
// DFS Solver (no undo, uses copy)
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

    const hash = board.hash();
    if (visited.has(hash)) return;
    visited.add(hash);

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;
        if (f.onlyReachableFrom !== POSITION_NONE &&
            (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

        const newBoard = board.copy();
        if (!newBoard.click(r, c)) continue; // skip no-op

        if (debug) console.log(`DFS trying move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newBoard.moveSequence.n}`);
        dfs(newBoard);
      }
    }
  }

  dfs(initialBoard);
  return bestSolution;
}

// ------------------------------
// BFS Solver (O(1) queue + copy + capped queue)
function bfsSolver(initialBoard, debug = false) {
  const queue = [initialBoard];
  let head = 0;
  const visited = new Set([initialBoard.hash() + '|0']); // include move sequence

  while (head < queue.length) {
    const board = queue[head++];
    if (board.isSolved()) return board;
    if (board.moveSequence.n >= maxSteps) continue;

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;
        if (f.onlyReachableFrom !== POSITION_NONE &&
            (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

        const newBoard = board.copy();
        if (!newBoard.click(r, c)) continue;

        const hash = newBoard.hash() + '|' + newBoard.moveSequence.n;
        if (visited.has(hash)) continue;
        visited.add(hash);

        queue.push(newBoard);
        if (queue.length > MAX_QUEUE_SIZE) queue.shift(); // cap queue

        if (debug) console.log(`BFS enqueue move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newBoard.moveSequence.n}`);
      }
    }
  }

  return null;
}

// ------------------------------
// A* Solver (FastPriorityQueue + copy + capped heap)
function branchBoundSolver(initialBoard, debug = false) {
  const seen = new Set();
  const pq = new FastPriorityQueue((a, b) => a.priority < b.priority);

  function heuristic(board) {
    return board.fields.flat().filter(f => !f.isCorrect()).length;
  }

  pq.add({ board: initialBoard, moves: 0, priority: heuristic(initialBoard) });
  seen.add(initialBoard.hash() + '|0');

  while (!pq.isEmpty()) {
    const { board, moves } = pq.poll();

    if (moves >= maxSteps) continue;
    if (board.isSolved()) return board;

    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const f = board.fields[r][c];
        if (!f.isClickable()) continue;
        if (f.onlyReachableFrom !== POSITION_NONE &&
            (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

        const newBoard = board.copy();
        if (!newBoard.click(r, c)) continue;

        const hash = newBoard.hash() + '|' + newBoard.moveSequence.n;
        if (seen.has(hash)) continue;
        seen.add(hash);

        const newMoves = newBoard.moveSequence.n;
        const priority = newMoves + heuristic(newBoard);
        pq.add({ board: newBoard, moves: newMoves, priority });

        if (pq.size > MAX_QUEUE_SIZE) pq.poll(); // cap heap

        if (debug) console.log(`A* enqueue move ${String.fromCharCode(65 + c)}${r + 1}, depth ${newMoves}`);
      }
    }
  }

  return null;
}

// ------------------------------
// IDA* Solver (new addition)
function idaStarSolver(initialBoard, debug = false) {
  function heuristic(board) {
    return board.fields.flat().filter(f => !f.isCorrect()).length;
  }

  let threshold = heuristic(initialBoard);
  if (threshold === 0) return initialBoard;

  let bestSolution = null;
  const startTime = Date.now();

  function search(board, g, bound, pathSet = new Set()) {
    if (Date.now() - startTime > TIMEOUT_MS) return -2; // timeout

    const f = g + heuristic(board);
    if (f > bound) return f;
    if (board.isSolved()) {
      bestSolution = board.copy();
      return -1;
    }

    const hash = board.hash();
    if (pathSet.has(hash)) return Infinity;
    pathSet.add(hash);

    let min = Infinity;
    for (let r = 0; r < board.rows; r++) {
      for (let c = 0; c < board.cols; c++) {
        const field = board.fields[r][c];
        if (!field.isClickable()) continue;
        if (field.onlyReachableFrom !== POSITION_NONE &&
            (r !== field.onlyReachableFrom.row || c !== field.onlyReachableFrom.col)) continue;

        const newBoard = board.copy();
        if (!newBoard.click(r, c)) continue;

        if (debug) console.log(`IDA* trying move ${String.fromCharCode(65 + c)}${r + 1}, g=${g + 1}, f=${g + 1 + heuristic(newBoard)}`);

        const t = search(newBoard, g + 1, bound, pathSet);
        if (t === -1) return -1; // solution found
        if (t === -2) return -2; // timeout
        if (t < min) min = t;
      }
    }

    pathSet.delete(hash);
    return min;
  }

  while (threshold <= maxSteps) {
    const t = search(initialBoard, 0, threshold);
    if (t === -1) return bestSolution;
    if (t === -2) return null; // timeout
    if (t === Infinity) break;
    threshold = t;
  }

  return null;
}

// ------------------------------
// Run all solvers in parallel with timeout
async function solveWithAllStrategiesParallel(board, debug = false) {
  const solvers = [
    { name: "DFS", func: dfsSolver },
    { name: "BFS", func: bfsSolver },
    { name: "A*", func: branchBoundSolver },
    { name: "IDA*", func: idaStarSolver }, // new optimal solver added
  ];

  const results = await Promise.all(
    solvers.map(s =>
      new Promise(resolve => {
        const startTime = Date.now();
        const res = s.func(board, debug);
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

        if (res) console.log(`# ${s.name} finished with ${res.moveSequence.n} moves in ${elapsed}s`);
        else console.log(`# ${s.name} finished with no solution after ${elapsed}s`);
        resolve(res);
      })
    )
  );

  const nonNull = results.filter(r => r);
  if (!nonNull.length) {
    console.log("# No solution found by any strategy");
    return null;
  }

  const best = nonNull.reduce((a, b) => (a.moveSequence.n < b.moveSequence.n ? a : b));
  console.log(`# Best solution uses ${best.moveSequence.n} moves`);
  return best;
}

module.exports = {
  dfsSolver,
  bfsSolver,
  branchBoundSolver,
  idaStarSolver,
  solveWithAllStrategiesParallel,
};
