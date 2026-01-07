class Position {
  constructor(row = 0, col = 0) {
    this.row = row;
    this.col = col;
  }

  notEquals(other) {
    return this.row !== other.row || this.col !== other.col;
  }
}

const POSITION_NONE = new Position(15, 15);

class Field {
  constructor(color = "g", modifier = "0") {
    this.color = color;
    this.modifier = modifier;
    this.onlyReachableFrom = POSITION_NONE;
  }

  isColor(c) {
    return "rgbod".includes(c);
  }

  isClickable() {
    return this.isStaticArrow() || this.isRotatingArrow() || "FB".includes(this.modifier);
  }

  isStaticArrow() {
    return "LRUD".includes(this.modifier);
  }

  isRotatingArrow() {
    return "wsax".includes(this.modifier);
  }

  isCorrect() {
    if (!this.isColor(this.color)) return true;
    if (this.isColor(this.modifier)) return this.color === this.modifier;
    return this.modifier !== "0";
  }
}

class MoveSequence {
  constructor() {
    this.moves = [];
    this.n = 0;
  }

  add(row, col) {
    this.moves.push(new Position(row, col));
    this.n++;
  }

  toString() {
    return this.moves.map(m => String.fromCharCode(m.col + 65) + (m.row + 1)).join(",");
  }
}

class Board {
  constructor(rows = 8, cols = 6) {
    this.rows = rows;
    this.cols = cols;
    this.fields = Array.from({ length: rows }, () =>
      Array.from({ length: cols }, () => new Field())
    );
    this.moveSequence = new MoveSequence();
    this.hasBombs = false;
  }

  click(row, col) {
    this.moveSequence.add(row, col);
    const f = this.fields[row][col];

    const fill = (dr, dc, r, c, color) => {
      r += dr; c += dc;
      if (!(0 <= r && r < this.rows && 0 <= c && c < this.cols)) return false;
      let fromColor, toColor;
      const mod = this.fields[r][c].modifier;
      if (mod === color) { fromColor = color; toColor = "0"; }
      else if (mod === "0") { fromColor = "0"; toColor = color; }
      else return false;
      let changed = false;
      while (0 <= r && r < this.rows && 0 <= c && c < this.cols && this.fields[r][c].modifier === fromColor) {
        this.fields[r][c].modifier = toColor;
        r += dr; c += dc;
        changed = true;
      }
      return changed;
    };

    const flood = (r, c, fromColor, toColor) => {
      if (!(0 <= r && r < this.rows && 0 <= c && c < this.cols)) return false;
      if (this.fields[r][c].modifier !== fromColor) return false;
      this.fields[r][c].modifier = toColor;
      let changed = true;
      changed |= flood(r + 1, c, fromColor, toColor);
      changed |= flood(r - 1, c, fromColor, toColor);
      changed |= flood(r, c + 1, fromColor, toColor);
      changed |= flood(r, c - 1, fromColor, toColor);
      return changed;
    };

    const mod = f.modifier;
    switch (mod) {
      case "U": return fill(-1, 0, row, col, f.color);
      case "D": return fill(1, 0, row, col, f.color);
      case "L": return fill(0, -1, row, col, f.color);
      case "R": return fill(0, 1, row, col, f.color);
      case "F":
        let changed = false;
        changed |= flood(row + 1, col, "0", f.color);
        changed |= flood(row - 1, col, "0", f.color);
        changed |= flood(row, col + 1, "0", f.color);
        changed |= flood(row, col - 1, "0", f.color);
        if (!changed) {
          changed |= flood(row + 1, col, f.color, "0");
          changed |= flood(row - 1, col, f.color, "0");
          changed |= flood(row, col + 1, f.color, "0");
          changed |= flood(row, col - 1, f.color, "0");
        }
        return changed;
      case "B":
        for (let dr = 0; dr < 3; dr++) {
          for (let dc = 0; dc < 3; dc++) {
            const r = row - 1 + dr;
            const c = col - 1 + dc;
            if (0 <= r && r < this.rows && 0 <= c && c < this.cols && this.fields[r][c].modifier !== "X") {
              this.fields[r][c].modifier = f.color;
            }
          }
        }
        return true;
      case "w": fill(-1, 0, row, col, f.color); f.modifier = "x"; return true;
      case "s": fill(1, 0, row, col, f.color); f.modifier = "a"; return true;
      case "a": fill(0, -1, row, col, f.color); f.modifier = "w"; return true;
      case "x": fill(0, 1, row, col, f.color); f.modifier = "s"; return true;
      default: console.log("Unknown modifier", mod); return false;
    }
  }

  isSolved() {
    return this.fields.flat().every(f => f.isCorrect());
  }

  static fromStrings(colorStr, modifierStr) {
    // Determine rows/cols from XML
    const colorLines = colorStr.trim().split(/\s+/);
    const modifierLines = modifierStr.trim().split(/\s+/);

    const rows = Math.max(colorLines.length, modifierLines.length);
    const cols = Math.max(...colorLines.map(l => l.length), ...modifierLines.map(l => l.length));

    // Flatten
    const colorClean = colorLines.join("");
    const modifierClean = modifierLines.join("");

    const b = new Board(rows, cols);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const f = b.fields[r][c];
        const idx = r * cols + c;
        if (idx >= colorClean.length || idx >= modifierClean.length) {
          f.color = "0";
          f.modifier = "X";
        } else {
          f.color = colorClean[idx];
          f.modifier = modifierClean[idx];
        }
      }
    }
    return b;
  }

  display() {
    for (let r = 0; r < this.rows; r++) {
      let line = "";
      for (let c = 0; c < this.cols; c++) {
        const f = this.fields[r][c];
        if (f.color === "0") line += "  ";
        else {
          const code = { r: 41, g: 42, b: 44, o: 43, d: 45 }[f.color] || 40;
          line += `\x1b[${code}m  \x1b[0m`;
        }
      }
      console.log(line);
    }
  }

  hash() {
    return JSON.stringify(this.fields.map(r => r.map(f => [f.color, f.modifier])));
  }

  copy() {
    const b = new Board(this.rows, this.cols);
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const fSrc = this.fields[r][c];
        const fDst = b.fields[r][c];
        fDst.color = fSrc.color;
        fDst.modifier = fSrc.modifier;
        fDst.onlyReachableFrom = fSrc.onlyReachableFrom;
      }
    }
    b.moveSequence.moves = this.moveSequence.moves.map(m => new Position(m.row, m.col));
    b.moveSequence.n = this.moveSequence.n;
    b.hasBombs = this.hasBombs;
    return b;
  }
}

module.exports = { Board, Field, MoveSequence, Position, POSITION_NONE };
