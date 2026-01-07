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
  return solutionStr.split(",").filter(m => m).length;
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
    xmlLines.push(
      `  <level number="${number}" color="${color}" modifier="${modifier}"${solutionAttr} />`
    );
  });
  xmlLines.push("</levels>");
  return xmlLines.join("\n");
}

// ------------------------------
// Main
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
    // Run solver
    // ------------------------------
    const newBoard = await solveWithAllStrategiesParallel(board);

    // ------------------------------
    // Choose best solution
    // ------------------------------
    let chosenBoard = null;
    let solutionStr = "";

    if (newBoard && existingBoard) {
      if (newBoard.moveSequence.n < existingMoves) {
        console.log("# New solution is better");
        chosenBoard = newBoard;
        solutionStr = newBoard.moveSequence.toString();
      } else {
        console.log("# Keeping existing solution");
        chosenBoard = existingBoard;
        solutionStr = existingSolution;
      }
    } else if (newBoard) {
      console.log("# Using new solution");
      chosenBoard = newBoard;
      solutionStr = newBoard.moveSequence.toString();
    } else if (existingBoard) {
      console.log("# Solver failed, keeping existing solution");
      chosenBoard = existingBoard;
      solutionStr = existingSolution;
    } else {
      console.log("# No solution found");
      chosenBoard = null;
      solutionStr = "";
    }

    attrs.solution = solutionStr || ""; // ✅ Ensure string
    updatedLevels.push(attrs);

    // ------------------------------
    // Write updated XML
    // ------------------------------
    const newXml = generateLevels(updatedLevels);
    const outFile = xmlFile.replace(".xml", "_solved.xml");
    fs.writeFileSync(outFile, newXml, "utf-8");
    console.log(`# Updated XML saved to ${outFile}`);

    // ------------------------------
    // Display board
    // ------------------------------
    if (chosenBoard) {
      console.log(`Solution moves: ${solutionStr}`);
      console.log("Completed board:");
      chosenBoard.display();
    }

    // Wait for user
    await new Promise(resolve => {
      process.stdout.write("# Press Enter to continue after solution...");
      process.stdin.once("data", () => resolve());
    });
  }

  console.log("\nAll selected levels processed. Final XML saved.");
  process.exit(0);
}

main().catch(console.error);
