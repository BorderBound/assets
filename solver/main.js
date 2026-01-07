// main.js
const fs = require("fs");
const { SimpleXml } = require("./simpleXml");
const { Board } = require("./board");
const { solveWithAllStrategiesParallel } = require("./multiSolver");

// ------------------------------
// Helpers
// ------------------------------
function parseMove(move) {
	const col = move[0].toUpperCase().charCodeAt(0) - 65;
	const row = parseInt(move.slice(1), 10) - 1;
	return [row, col];
}

function replaySolution(board, solutionStr) {
	const b = board.copy();
	for (const move of solutionStr.split(",")) {
		if (!move) continue;
		const [r, c] = parseMove(move);
		const changed = b.click(r, c);
		if (!changed) throw new Error(`Invalid move: ${move}`);
	}
	return b;
}

function countMoves(solutionStr) {
	return solutionStr.split(",").filter((m) => m).length;
}

function tryExistingSolution(board, solutionStr) {
	try {
		const solved = replaySolution(board, solutionStr);
		if (solved.isSolved()) return solved;
	} catch (_) {}
	return null;
}

function generateLevels(levels) {
	const xmlLines = ["<levels>"];
	levels.forEach((lvl, number) => {
		const color = lvl.color || "";
		const modifier = lvl.modifier || "";
		const solution = (lvl.solution || "").toString();
		const solutionAttr = solution ? ` solution="${solution}"` : "";
		xmlLines.push(`  <level number="${number}" color="${color}" modifier="${modifier}"${solutionAttr} />`);
	});
	xmlLines.push("</levels>");
	return xmlLines.join("\n");
}

// ------------------------------
// Main function
// ------------------------------
async function main() {
	const args = process.argv.slice(2);
	if (args.length < 1) {
		console.log(`Usage: node ${process.argv[1]} <levels.xml> [level_number[+]]`);
		return;
	}

	const xmlFile = args[0];
	const levelArg = args[1]?.trim();

	let levelToStart = null;
	let continueAfter = false;
	if (levelArg) {
		if (levelArg.endsWith("+")) {
			levelToStart = parseInt(levelArg.slice(0, -1), 10);
			continueAfter = true;
		} else {
			levelToStart = parseInt(levelArg, 10);
		}
	}

	const xmlData = fs.readFileSync(xmlFile, "utf-8");
	let levels;
	try {
		levels = SimpleXml.parseLevels(xmlData);
		console.log(`Parsed ${levels.length} levels`);
	} catch (e) {
		console.error("Error parsing XML:", e);
		return;
	}

	const updatedLevels = [];

	for (let levelNumber = 0; levelNumber < levels.length; levelNumber++) {
		const attrs = levels[levelNumber];

		if (levelToStart !== null) {
			if (continueAfter && levelNumber < levelToStart) {
				updatedLevels.push(attrs);
				continue;
			} else if (!continueAfter && levelNumber !== levelToStart) {
				updatedLevels.push(attrs);
				continue;
			}
		}

		console.log(`\nSolving Level ${levelNumber}...`);

		const board = Board.fromStrings(attrs.color, attrs.modifier);

		// ------------------------------
		// Test existing solution
		// ------------------------------
		const existingSolution = attrs.solution;
		let existingBoard = existingSolution ? tryExistingSolution(board, existingSolution) : null;
		let existingMoves = existingBoard ? countMoves(existingSolution) : null;

		if (existingBoard) console.log(`# Existing solution valid (${existingMoves} moves)`);
		else if (existingSolution) console.log("# Existing solution INVALID");

		// ------------------------------
        // Run parallel solver (DFS, BFS, A*, IDA*)
        const solvedBoards = await solveWithAllStrategiesParallel(board, false); // debug=false

        let chosenBoard = null;
        let solutionStr = "";
        let updatedXml = false;

        if (solvedBoards && solvedBoards.length) {
            // Only keep fully solved boards
            const fullySolved = solvedBoards.filter(b => b.isSolved());

            if (fullySolved.length > 0) {
                // Pick the board with fewest moves
                chosenBoard = fullySolved.reduce((a, b) =>
                    a.moveSequence.n < b.moveSequence.n ? a : b
                );

                solutionStr = chosenBoard.moveSequence.moves
                    .map(m => String.fromCharCode(m.col + 65) + (m.row + 1))
                    .join(",");

                // Determine if it's better than existing solution
                if (existingBoard && chosenBoard.moveSequence.n >= existingMoves) {
                    console.log("# Keeping existing solution");
                    chosenBoard = existingBoard;
                    solutionStr = existingSolution;
                } else if (!existingBoard) {
                    console.log("# Using new solution");
                    updatedXml = true;
                } else {
                    console.log("# New solution is better");
                    updatedXml = true;
                }
            } else if (existingBoard) {
                console.log("# Solver failed, keeping existing solution");
                chosenBoard = existingBoard;
                solutionStr = existingSolution;
            } else {
                console.log("# No solution found");
                chosenBoard = null;
                solutionStr = "";
            }
        } else if (existingBoard) {
            console.log("# Solver failed, keeping existing solution");
            chosenBoard = existingBoard;
            solutionStr = existingSolution;
        } else {
            console.log("# No solution found");
            chosenBoard = null;
            solutionStr = "";
        }

		attrs.solution = solutionStr || ""; // ensure string
		updatedLevels.push(attrs);

		// ------------------------------
		// Write updated XML ONLY if a new/better solution exists
		// ------------------------------
		if (updatedXml) {
			const newXml = generateLevels(updatedLevels);
			const outFile = xmlFile.replace(".xml", "_solved.xml");
			fs.writeFileSync(outFile, newXml, "utf-8");
			console.log(`# Updated XML saved to ${outFile}`);
		}

		// ------------------------------
		// Display board and moves
		// ------------------------------
		if (chosenBoard) {
			console.log(`Solution moves: ${solutionStr}`);
			console.log("Completed board:");
			chosenBoard.display();
		}

		// ------------------------------
		// Wait for user input
		// ------------------------------
		await new Promise((resolve) => {
			process.stdout.write("# Press Enter to continue after solution...");
			process.stdin.once("data", () => resolve());
		});
	}

	console.log("\nAll selected levels processed. Final XML saved.");
	process.exit(0);
}

// ------------------------------
// Run main
// ------------------------------
main().catch(console.error);
