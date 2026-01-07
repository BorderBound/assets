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
// Greedy Best-First Search Solver
// ------------------------------
function gbfsSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS, maxQueueSize = DEFAULT_MAX_QUEUE_SIZE) {
    const seen = new Set();
    const pq = new FastPriorityQueue((a, b) => a.priority < b.priority);

    // Combined heuristic: Manhattan distance + color mismatches
    function heuristic(board) {
        let manhattan = 0;
        let colorMismatch = 0;
        for (let r = 0; r < board.rows; r++) {
            for (let c = 0; c < board.cols; c++) {
                const f = board.fields[r][c];
                if (!f.isCorrect()) {
                    // Manhattan distance to target (for empty / correct position)
                    const targetRow = f.correctRow ?? r;
                    const targetCol = f.correctCol ?? c;
                    manhattan += Math.abs(r - targetRow) + Math.abs(c - targetCol);
                    colorMismatch += f.color !== f.correctColor ? 1 : 0;
                }
            }
        }
        return manhattan + colorMismatch;
    }

    pq.add({ board: initialBoard, priority: heuristic(initialBoard) });
    seen.add(initialBoard.hash() + "|0");

    while (!pq.isEmpty()) {
        const { board } = pq.poll();
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
                if (seen.has(hash)) continue;
                seen.add(hash);

                pq.add({ board: newBoard, priority: heuristic(newBoard) });
                if (pq.size > maxQueueSize) pq.poll();

                if (debug) console.log(`GBFS enqueue move ${String.fromCharCode(65 + c)}${r + 1}`);
            }
        }
    }

    return null;
}

// ------------------------------
// Monte Carlo Tree Search Solver
// ------------------------------
function mctsSolver(
	initialBoard,
	debug = false,
	maxSteps = DEFAULT_MAX_STEPS,
	timeoutMs = DEFAULT_TIMEOUT_MS
) {
	const startTime = Date.now();
	const EXPLORATION = Math.sqrt(2);

	class Node {
		constructor(board, parent = null, move = null) {
			this.board = board;
			this.parent = parent;
			this.move = move;
			this.children = [];
			this.visits = 0;
			this.reward = 0;
			this.untriedMoves = getMoves(board);
		}
	}

	function getMoves(board) {
		const moves = [];
		for (let r = 0; r < board.rows; r++) {
			for (let c = 0; c < board.cols; c++) {
				const f = board.fields[r][c];
				if (!f.isClickable()) continue;
				if (
					f.onlyReachableFrom !== POSITION_NONE &&
					(r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)
				) continue;
				moves.push({ r, c });
			}
		}
		return moves;
	}

	function ucb1(child) {
		return (
			child.reward / (child.visits + 1e-6) +
			EXPLORATION * Math.sqrt(Math.log(child.parent.visits + 1) / (child.visits + 1e-6))
		);
	}

	function select(node) {
		while (node.untriedMoves.length === 0 && node.children.length > 0) {
			node = node.children.reduce((a, b) => (ucb1(a) > ucb1(b) ? a : b));
		}
		return node;
	}

	function expand(node) {
		if (node.untriedMoves.length === 0) return node;
		const move = node.untriedMoves.pop();
		const newBoard = node.board.copy();
		if (!newBoard.click(move.r, move.c)) return node;

		const child = new Node(newBoard, node, move);
		node.children.push(child);
		return child;
	}

	function simulate(board) {
		let depth = 0;
		while (depth < maxSteps) {
			if (board.isSolved()) return 1;

			const moves = getMoves(board);
			if (moves.length === 0) break;

			const m = moves[Math.floor(Math.random() * moves.length)];
			if (!board.click(m.r, m.c)) break;

			depth++;
		}

		// Partial reward: fewer incorrect fields is better
		const incorrect = board.fields.flat().filter(f => !f.isCorrect()).length;
		return 1 / (1 + incorrect);
	}

	function backpropagate(node, reward) {
		while (node) {
			node.visits++;
			node.reward += reward;
			node = node.parent;
		}
	}

	const root = new Node(initialBoard);
	let bestSolved = null;

	while (Date.now() - startTime < timeoutMs) {
		let node = select(root);
		node = expand(node);

		const rolloutBoard = node.board.copy();
		const reward = simulate(rolloutBoard);

		if (rolloutBoard.isSolved()) {
			bestSolved = rolloutBoard.copy();
			break;
		}

		backpropagate(node, reward);
	}

	if (bestSolved) return bestSolved;

	// fallback: best child seen
	const bestChild = root.children.reduce(
		(a, b) => (b.visits > a.visits ? b : a),
		root.children[0]
	);

	return bestChild ? bestChild.board : null;
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
// Enhanced A* / Branch-and-bound Solver with Manhattan distance
// ------------------------------
function enhancedBranchBoundSolver(initialBoard, debug = false, maxSteps = DEFAULT_MAX_STEPS, maxQueueSize = DEFAULT_MAX_QUEUE_SIZE) {
	const seen = new Set();
	const pq = new FastPriorityQueue((a, b) => a.priority < b.priority);

	// Enhanced heuristic: wrong tiles + bombs weighted + Manhattan distance
	function heuristic(board) {
		let score = 0;
		for (let r = 0; r < board.rows; r++) {
			for (let c = 0; c < board.cols; c++) {
				const f = board.fields[r][c];
				if (!f.isCorrect()) {
					score += 1;             // wrong tile
					if (f.isBomb) score += 2; // bomb penalty

					// Manhattan distance from current position to target color cluster
					if (f.targetPosition) {
						const dr = Math.abs(r - f.targetPosition.row);
						const dc = Math.abs(c - f.targetPosition.col);
						score += dr + dc;
					}
				}
			}
		}
		return score;
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
				if (f.onlyReachableFrom !== POSITION_NONE &&
					(r !== f.onlyReachableFrom.row || c !== f.onlyReachableFrom.col)) continue;

				const newBoard = board.copy();
				if (!newBoard.click(r, c)) continue;

				const hash = newBoard.hash() + "|" + newBoard.moveSequence.n;
				if (seen.has(hash)) continue;
				seen.add(hash);

				const newMoves = newBoard.moveSequence.n;
				const priority = newMoves + heuristic(newBoard);
				pq.add({ board: newBoard, moves: newMoves, priority });

				if (pq.size > maxQueueSize) pq.poll();
				if (debug) console.log(`Enhanced A* enqueue move ${String.fromCharCode(65+c)}${r+1}, priority=${priority}`);
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
		GBFS: (b, d) => gbfsSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_MAX_QUEUE_SIZE),
		MCTS: (b, d) => mctsSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_TIMEOUT_MS),
		"A*": (b, d) => branchBoundSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_MAX_QUEUE_SIZE),
		"EA*": (b, d) => enhancedBranchBoundSolver(b, d, DEFAULT_MAX_STEPS, DEFAULT_MAX_QUEUE_SIZE),
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
// Parallel solver (collect up to 4 solutions)
// ------------------------------
async function solveWithAllStrategiesParallel(board, debug = false) {
	const solvers = ["DFS", "BFS","GBFS", "MCTS", "A*", "EA*", "IDA"];
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
					if (results.length >= 4) workers.forEach((w) => w.terminate()); // <-- now 4
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
	return fullySolved.length ? fullySolved.slice(0, 4) : null; // <-- return up to 4
}

// ------------------------------
// Exports
// ------------------------------
module.exports = {
	dfsSolver,
	bfsSolver,
	branchBoundSolver,
	enhancedBranchBoundSolver,
	idaStarSolver,
	solveWithAllStrategiesParallel,
};
