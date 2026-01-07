// multiSolver.js
const { Worker, isMainThread, parentPort, workerData } = require("worker_threads");
const FastPriorityQueue = require("fastpriorityqueue");
const { Board, Position, POSITION_NONE } = require("./board");

// ------------------------------
// Default constants
// ------------------------------
const DEFAULT_MAX_STEPS = 100;
const DEFAULT_MAX_QUEUE_SIZE = 100_000;
const DEFAULT_TIMEOUT_MS = 60 * 1000; // 1 minute

// ------------------------------
// Helpers to serialize board
// ------------------------------
function boardToData(board) {
	return {
		rows: board.rows,
		cols: board.cols,
		fields: board.fields.map((r) =>
			r.map((f) => ({
				color: f.color,
				modifier: f.modifier,
				onlyReachableFrom: { row: f.onlyReachableFrom.row, col: f.onlyReachableFrom.col },
			}))
		),
		moves: board.moveSequence.moves.map((m) => ({ row: m.row, col: m.col })),
		hasBombs: board.hasBombs,
	};
}

function boardFromData(data) {
	const b = new Board(data.rows, data.cols);
	for (let r = 0; r < data.rows; r++) {
		for (let c = 0; c < data.cols; c++) {
			const fData = data.fields[r][c];
			const f = b.fields[r][c];
			f.color = fData.color;
			f.modifier = fData.modifier;
			f.onlyReachableFrom = fData.onlyReachableFrom.row === 15 && fData.onlyReachableFrom.col === 15 ? POSITION_NONE : new Position(fData.onlyReachableFrom.row, fData.onlyReachableFrom.col);
		}
	}
	b.moveSequence.moves = data.moves.map((m) => new Position(m.row, m.col));
	b.moveSequence.n = data.moves.length;
	b.hasBombs = data.hasBombs;
	return b;
}

// ------------------------------
// DFS Solver
// ------------------------------
function dfsSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS) {
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
				if (f.onlyReachableFrom !== POSITION_NONE && (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

				const newBoard = board.copy();
				if (!newBoard.click(r, c)) continue;
				if (debug) console.log(`DFS trying move ${String.fromCharCode(65 + c)}${r + 1}`);
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
function bfsSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS, maxQueueSize = DEFAULT_MAX_QUEUE_SIZE) {
	const queue = [initialBoard];
	let head = 0;
	const visited = new Set([initialBoard.hash() + "|0"]);

	while (head < queue.length) {
		const board = queue[head++];
		if (board.isSolved()) return board;
		if (board.moveSequence.n >= maxSteps) continue;

		for (let r = 0; r < board.rows; r++) {
			for (let c = 0; c < board.cols; c++) {
				const f = board.fields[r][c];
				if (!f.isClickable()) continue;
				if (f.onlyReachableFrom !== POSITION_NONE && (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

				const newBoard = board.copy();
				if (!newBoard.click(r, c)) continue;

				const hash = newBoard.hash() + "|" + newBoard.moveSequence.n;
				if (visited.has(hash)) continue;
				visited.add(hash);

				queue.push(newBoard);
				if (queue.length > maxQueueSize) queue.shift();
				if (debug) console.log(`BFS enqueue move ${String.fromCharCode(65 + c)}${r + 1}`);
			}
		}
	}
	return null;
}

// ------------------------------
// A* / Branch-and-bound Solver
// ------------------------------
function branchBoundSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS, maxQueueSize = DEFAULT_MAX_QUEUE_SIZE) {
	const seen = new Set();
	const pq = new FastPriorityQueue((a, b) => a.priority < b.priority);

	function heuristic(board) {
		return board.fields.flat().filter((f) => !f.isCorrect()).length;
	}

	pq.add({ board: initialBoard, moves: 0, priority: heuristic(initialBoard) });
	seen.add(initialBoard.hash() + "|0");

	while (!pq.isEmpty()) {
		const { board, moves } = pq.poll();
		if (moves >= maxSteps) continue;
		if (board.isSolved()) return board;

		for (let r = 0; r < board.rows; r++) {
			for (let c = 0; c < board.cols; c++) {
				const f = board.fields[r][c];
				if (!f.isClickable()) continue;
				if (f.onlyReachableFrom !== POSITION_NONE && (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

				const newBoard = board.copy();
				if (!newBoard.click(r, c)) continue;

				const hash = newBoard.hash() + "|" + newBoard.moveSequence.n;
				if (seen.has(hash)) continue;
				seen.add(hash);

				const newMoves = newBoard.moveSequence.n;
				const priority = newMoves + heuristic(newBoard);
				pq.add({ board: newBoard, moves: newMoves, priority });
				if (pq.size > maxQueueSize) pq.poll();
			}
		}
	}

	return null;
}

// ------------------------------
// IDA* Solver
// ------------------------------
function idaStarSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS, timeoutMs = DEFAULT_TIMEOUT_MS) {
	function heuristic(board) {
		return board.fields.flat().filter((f) => !f.isCorrect()).length;
	}

	let threshold = heuristic(initialBoard);
	if (threshold === 0) return initialBoard;

	let bestSolution = null;
	const startTime = Date.now();

	function search(board, g, bound, pathSet = new Set()) {
		if (Date.now() - startTime > timeoutMs) return -2;

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
				const f = board.fields[r][c];
				if (!f.isClickable()) continue;
				if (f.onlyReachableFrom !== POSITION_NONE && (r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

				const newBoard = board.copy();
				if (!newBoard.click(r, c)) continue;

				const t = search(newBoard, g + 1, bound, pathSet);
				if (t === -1) return -1;
				if (t === -2) return -2;
				if (t < min) min = t;
			}
		}
		pathSet.delete(hash);
		return min;
	}

	while (threshold <= maxSteps) {
		const t = search(initialBoard, 0, threshold);
		if (t === -1) return bestSolution;
		if (t === -2) return null;
		if (t === Infinity) break;
		threshold = t;
	}
	return null;
}

// ------------------------------
// Worker code
// ------------------------------
if (!isMainThread) {
	const { solverName, boardData, debug } = workerData;

	const solverMap = {
		DFS: (b, d) => dfsSolver(b, d, DEFAULT_MAX_STEPS),
		BFS: (b, d) => bfsSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_MAX_QUEUE_SIZE),
		"A*": (b, d) => branchBoundSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_MAX_QUEUE_SIZE),
		IDA: (b, d) => idaStarSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_TIMEOUT_MS),
	};

	const solverFunc = solverMap[solverName];
	try {
		const board = boardFromData(boardData);
		const result = solverFunc(board, debug);
		parentPort.postMessage({
			result: result ? boardToData(result) : null,
			moves: result ? result.moveSequence.n : null,
			solverName,
			solved: result && result.isSolved(),
		});
	} catch (err) {
		parentPort.postMessage({ result: null, moves: null, solverName, solved: false, error: err.message });
	}
	process.exit(0);
}

// ------------------------------
// Parallel solver
// ------------------------------
async function solveWithAllStrategiesParallel(board, debug = false) {
	const solvers = ["DFS", "BFS", "A*", "IDA"];
	const results = [];
	const workers = [];

	function runWorker(solverName) {
		return new Promise((resolve) => {
			const worker = new Worker(__filename, {
				workerData: { solverName, boardData: boardToData(board), debug },
			});

			workers.push(worker);

			worker.on("message", (msg) => {
				if (msg.solved && msg.result) {
					const solvedBoard = boardFromData(msg.result);
					results.push(solvedBoard);
					console.log(`# ${msg.solverName} finished with ${solvedBoard.moveSequence.n} moves`);
					if (results.length >= 2) workers.forEach((w) => w.terminate());
				} else if (msg.error) {
					console.error(`# Worker ${solverName} error:`, msg.error);
				}
			});

			worker.on("exit", () => resolve());
			worker.on("error", (err) => {
				console.error(`# Worker ${solverName} error:`, err);
				resolve();
			});
		});
	}

	await Promise.all(solvers.map(runWorker));

	const fullySolved = results.filter((b) => b.isSolved());
	return fullySolved.length ? fullySolved.slice(0, 2) : null;
}

// ------------------------------
// Exports
// ------------------------------
module.exports = {
	dfsSolver,
	bfsSolver,
	branchBoundSolver,
	idaStarSolver,
	solveWithAllStrategiesParallel,
};
