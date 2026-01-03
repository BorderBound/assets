# simple_xml.py
from board import Board


class SimpleXml:

    @staticmethod
    def skip_whitespace(xml: str, pos: int) -> int:
        while pos < len(xml) and xml[pos] in " \t\n\r":
            pos += 1
        return pos

    @staticmethod
    def consume(token: str, xml: str, pos: int) -> int:
        pos = SimpleXml.skip_whitespace(xml, pos)
        if not xml.startswith(token, pos):
            raise ValueError(f"Expected '{token}' at position {pos}")
        return pos + len(token)

    @staticmethod
    def parse_level(xml: str, pos: int):
        pos = SimpleXml.skip_whitespace(xml, pos)
        pos = SimpleXml.consume("<level", xml, pos)

        attrs = {}
        while True:
            pos = SimpleXml.skip_whitespace(xml, pos)
            if xml[pos] in (">", "/"):
                break

            # read attribute name
            start = pos
            while pos < len(xml) and xml[pos] not in " =\t\n\r":
                pos += 1
            name = xml[start:pos]

            pos = SimpleXml.skip_whitespace(xml, pos)
            pos = SimpleXml.consume("=", xml, pos)
            pos = SimpleXml.skip_whitespace(xml, pos)

            quote = xml[pos]
            if quote not in ('"', "'"):
                raise ValueError(f"Expected quote at position {pos}")
            pos += 1
            start = pos
            while xml[pos] != quote:
                pos += 1
            value = xml[start:pos]
            pos += 1
            attrs[name] = value

        # handle self-closing tag "/>"
        if xml[pos : pos + 2] == "/>":
            pos += 2
        else:
            pos = SimpleXml.consume(">", xml, pos)

        return pos, attrs

    @staticmethod
    def parse_levels(xml: str):
        pos = 0
        pos = SimpleXml.consume("<?xml version='1.0' encoding='utf-8'?>", xml, pos)
        pos = SimpleXml.consume("<levels>", xml, pos)

        levels = []

        while True:
            pos = SimpleXml.skip_whitespace(xml, pos)
            if xml.startswith("</levels>", pos):
                pos += len("</levels>")
                break
            pos, attrs = SimpleXml.parse_level(xml, pos)
            levels.append(attrs)

        return levels

    @staticmethod
    def parse_boards(xml: str):
        levels = SimpleXml.parse_levels(xml)
        boards = []
        for level in levels:
            color = level["color"].replace(" ", "")
            modifier = level["modifier"].replace(" ", "")
            board = Board.from_strings(color, modifier)
            boards.append(board)
        return boards
