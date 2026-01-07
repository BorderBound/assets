// simple_xml.js
const { Board } = require("./board");

class SimpleXml {
	static skipWhitespace(xml, pos) {
		while (pos < xml.length && " \t\n\r".includes(xml[pos])) pos++;
		return pos;
	}

	static consume(token, xml, pos) {
		pos = SimpleXml.skipWhitespace(xml, pos);
		if (!xml.startsWith(token, pos)) {
			throw new Error(`Expected '${token}' at position ${pos}`);
		}
		return pos + token.length;
	}

	static parseLevel(xml, pos) {
		pos = SimpleXml.skipWhitespace(xml, pos);
		pos = SimpleXml.consume("<level", xml, pos);

		const attrs = {};
		while (true) {
			pos = SimpleXml.skipWhitespace(xml, pos);
			if (xml[pos] === ">" || xml[pos] === "/") break;

			// read attribute name
			const start = pos;
			while (pos < xml.length && !" =\t\n\r".includes(xml[pos])) pos++;
			const name = xml.slice(start, pos);

			pos = SimpleXml.skipWhitespace(xml, pos);
			pos = SimpleXml.consume("=", xml, pos);
			pos = SimpleXml.skipWhitespace(xml, pos);

			const quote = xml[pos];
			if (!['"', "'"].includes(quote)) {
				throw new Error(`Expected quote at position ${pos}`);
			}
			pos++;
			const valStart = pos;
			while (xml[pos] !== quote) pos++;
			const value = xml.slice(valStart, pos);
			pos++;
			attrs[name] = value;
		}

		// handle self-closing "/>"
		if (xml.slice(pos, pos + 2) === "/>") {
			pos += 2;
		} else {
			pos = SimpleXml.consume(">", xml, pos);
		}

		return [pos, attrs];
	}

	static parseLevels(xml) {
		let pos = 0;
		pos = SimpleXml.consume("<?xml version='1.0' encoding='utf-8'?>", xml, pos);
		pos = SimpleXml.consume("<levels>", xml, pos);

		const levels = [];

		while (true) {
			pos = SimpleXml.skipWhitespace(xml, pos);
			if (xml.startsWith("</levels>", pos)) {
				pos += "</levels>".length;
				break;
			}
			const [newPos, attrs] = SimpleXml.parseLevel(xml, pos);
			pos = newPos;
			levels.push(attrs);
		}

		return levels;
	}

	static parseBoards(xml) {
		const levels = SimpleXml.parseLevels(xml);
		const boards = [];

		for (const level of levels) {
			const color = (level.color || "").replace(/\s+/g, "");
			const modifier = (level.modifier || "").replace(/\s+/g, "");
			const board = Board.fromStrings(color, modifier);
			boards.push(board);
		}

		return boards;
	}
}

module.exports = { SimpleXml };
