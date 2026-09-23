#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Auto updated?
#   Yes
# File:
#   sort_levels.py
# Author:
#   CreativeCodeCat [wayne6324@gmail.com]
# Github:
#   https://github.com/CreativeCodeCat/
#
# Description:
#   - Parse multiple level XML files
#   - Use configured level number bases
#   - Automatically detect bases when requested base is None
#   - Sort levels by solution length and modifier priority
#   - Handle levels without a solution
#   - Preserve author information
#   - Remove unsupported XML attributes
#   - Convert multiline color/modifier values to one-line values
#   - Remove excessive whitespace
#   - Use consistent attribute ordering
#   - Validate duplicate level numbers
#   - Validate XML structure
#   - Pretty-print XML output
#
# Python:
#   3.9+
#
# Standard Library only.

import xml.etree.ElementTree as ET
import os
import re
import math
import difflib

from collections import Counter
from copy import deepcopy


# ============================================================
# CONFIGURATION
# ============================================================

DRY_RUN = False
AUTO_EXPAND_RANGES = True
DIFF_LOGGING = False


# ------------------------------------------------------------
# File configuration
#
# The second value is the BASE NUMBER for that file.
# The third value is the normal RANGE SIZE.
#
# Easy:
#   0-299
#
# Medium:
#   300-599
#
# Hard:
#   600-899
#
# Community:
#   900-1199
# ------------------------------------------------------------

input_files = [
    ("levelsEasy.xml", 0, 100),
    ("levelsMedium.xml", 100, 100),
    ("levelsHard.xml", 200, 100),
    ("levelsCommunity.xml", 300, 100),
]


# ============================================================
# ALLOWED ATTRIBUTES
# ============================================================

ALLOWED_ATTRIBUTES = {
    "color",
    "modifier",
    "number",
    "solution",
    "author",
}


# ============================================================
# SPECIAL MODIFIERS
# ============================================================

SPECIAL_MODIFIERS = {
    "B",
    "w",
    "x",
    "a",
    "s",
}


# ============================================================
# CLEANING HELPERS
# ============================================================

def clean_spaces(value):
    """
    Collapse all whitespace into a single space and strip
    leading/trailing whitespace.
    """

    if value is None:
        return None

    return re.sub(r"\s+", " ", value).strip()


def normalise_grid(value):
    """
    Convert multiline color/modifier data into a single line.

    Example:

        abcde
        fghij
        klmno

    becomes:

        abcde fghij klmno
    """

    if value is None:
        return None

    return clean_spaces(value)


def normalise_solution(value):
    """
    Clean solution strings.

    Example:

        A1, B2, C3

    becomes:

        A1,B2,C3
    """

    if value is None:
        return None

    value = clean_spaces(value)

    # Remove spaces around commas
    value = re.sub(r"\s*,\s*", ",", value)

    return value.strip()


def normalise_author(value):
    """
    Clean author names without changing the actual name.
    """

    if value is None:
        return None

    return clean_spaces(value)


def clean_level_attributes(level):
    """
    Remove unsupported attributes and clean all supported
    attributes.
    """

    # --------------------------------------------------------
    # Remove unsupported attributes
    # --------------------------------------------------------

    for attr in list(level.attrib.keys()):
        if attr not in ALLOWED_ATTRIBUTES:
            del level.attrib[attr]

    # --------------------------------------------------------
    # Color
    # --------------------------------------------------------

    if "color" in level.attrib:
        level.attrib["color"] = normalise_grid(
            level.attrib["color"]
        )

    # --------------------------------------------------------
    # Modifier
    # --------------------------------------------------------

    if "modifier" in level.attrib:
        level.attrib["modifier"] = normalise_grid(
            level.attrib["modifier"]
        )

    # --------------------------------------------------------
    # Solution
    # --------------------------------------------------------

    if "solution" in level.attrib:

        solution = normalise_solution(
            level.attrib["solution"]
        )

        # Do not output solution=""
        if solution:
            level.attrib["solution"] = solution
        else:
            del level.attrib["solution"]

    # --------------------------------------------------------
    # Author
    # --------------------------------------------------------

    if "author" in level.attrib:

        author = normalise_author(
            level.attrib["author"]
        )

        if author:
            level.attrib["author"] = author
        else:
            del level.attrib["author"]


# ============================================================
# SORTING HELPERS
# ============================================================

def has_special_modifier(level):
    """
    Return True if the level contains one of the configured
    special modifier characters.
    """

    modifier = level.get("modifier", "")

    return any(
        char in modifier
        for char in SPECIAL_MODIFIERS
    )


def solution_length(level):
    """
    Return the number of moves in the solution.

    Levels without a solution are treated as unsolved.
    """

    solution = level.get("solution")

    if not solution:
        return float("inf")

    if not solution.strip():
        return float("inf")

    moves = [
        move
        for move in solution.split(",")
        if move.strip()
    ]

    return len(moves)


def level_sort_key(item):
    """
    Sorting order:

    1. Solved levels first
    2. Normal modifiers before special modifiers
    3. Shorter solutions first
    4. Original number as tie breaker
    5. Original position as final tie breaker

    Unsolved levels are always last.
    """

    level, original_index = item

    # --------------------------------------------------------
    # Solved / unsolved
    # --------------------------------------------------------

    has_solution = bool(
        level.get("solution", "").strip()
    )

    solution_priority = (
        0 if has_solution else 1
    )

    # --------------------------------------------------------
    # Normal / special modifier
    # --------------------------------------------------------

    modifier_priority = (
        1 if has_special_modifier(level) else 0
    )

    # --------------------------------------------------------
    # Solution length
    # --------------------------------------------------------

    length = solution_length(level)

    # --------------------------------------------------------
    # Original number
    # --------------------------------------------------------

    try:
        original_number = int(
            level.get("number", 0)
        )
    except ValueError:
        original_number = 0

    return (
        solution_priority,
        modifier_priority,
        length,
        original_number,
        original_index,
    )


# ============================================================
# BASE DETECTION
# ============================================================

def get_configured_base(requested_base, levels, range_size):
    """
    Determine the base to use for a file.

    IMPORTANT:

    If a base is explicitly configured in input_files,
    that base ALWAYS wins.

    This means:

        levelsEasy.xml       -> 0
        levelsMedium.xml    -> 300
        levelsHard.xml      -> 600
        levelsCommunity.xml -> 900

    even if the first level inside the file has a number
    such as 100 or 137.

    If requested_base is None, the base is automatically
    calculated from the first level.
    """

    # --------------------------------------------------------
    # Explicitly configured base
    # --------------------------------------------------------

    if requested_base is not None:
        return requested_base

    # --------------------------------------------------------
    # Automatic base detection
    # --------------------------------------------------------

    if not levels:
        return 0

    first_number_text = levels[0].get("number")

    if first_number_text is None:
        return 0

    try:
        first_number = int(first_number_text)
    except ValueError:
        return 0

    return (
        first_number // range_size
    ) * range_size


# ============================================================
# XML ESCAPING
# ============================================================

def escape_xml_attribute(value):
    """
    Escape a value for a double-quoted XML attribute.
    """

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================================
# XML LEVEL FORMATTER
# ============================================================

def format_level(level):
    """
    Format a level using the desired attribute order.

    Example:

        <level color="..."
               modifier="..."
               number="100"
               solution="A1,B2"
               author="Name" />
    """

    preferred_order = [
        "color",
        "modifier",
        "number",
        "solution",
        "author",
    ]

    attributes = []

    # --------------------------------------------------------
    # Preferred attributes
    # --------------------------------------------------------

    for attr in preferred_order:

        if attr in level.attrib:

            attributes.append(
                f'{attr}="'
                f'{escape_xml_attribute(level.attrib[attr])}"'
            )

    # --------------------------------------------------------
    # Any remaining attributes
    # --------------------------------------------------------

    for attr, value in level.attrib.items():

        if attr not in preferred_order:

            attributes.append(
                f'{attr}="'
                f'{escape_xml_attribute(value)}"'
            )

    # --------------------------------------------------------
    # No attributes
    # --------------------------------------------------------

    if not attributes:
        return "    <level />"

    # --------------------------------------------------------
    # Build formatted XML
    # --------------------------------------------------------

    lines = []

    lines.append(
        f"    <level {attributes[0]}"
    )

    for index, attribute in enumerate(
        attributes[1:],
        start=1
    ):

        is_last = (
            index == len(attributes) - 1
        )

        if is_last:

            lines.append(
                f"           {attribute} />"
            )

        else:

            lines.append(
                f"           {attribute}"
            )

    # --------------------------------------------------------
    # Only one attribute
    # --------------------------------------------------------

    if len(attributes) == 1:
        lines[-1] += " />"

    return "\n".join(lines)


# ============================================================
# XML WRITER
# ============================================================

def write_xml(root, output_file):
    """
    Write XML using the custom formatter.
    """

    lines = [
        '<?xml version="1.0" encoding="utf-8" ?>',
        "<levels>",
        "",
    ]

    for child in root:

        if child.tag != "level":
            continue

        lines.append(
            format_level(child)
        )

        lines.append("")

    # Remove final blank line
    if lines and lines[-1] == "":
        lines.pop()

    lines.append("</levels>")

    content = "\n".join(lines) + "\n"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(content)


# ============================================================
# VALIDATION
# ============================================================

def validate_levels(levels, base, range_size):
    """
    Validate:

    - Missing numbers
    - Invalid numbers
    - Duplicate numbers
    - Numbers outside the configured range
    """

    errors = []
    numbers = []

    # --------------------------------------------------------
    # Read numbers
    # --------------------------------------------------------

    for level in levels:

        number_text = level.get("number")

        if number_text is None:

            errors.append(
                "Level is missing a number."
            )

            continue

        try:

            number = int(number_text)

        except ValueError:

            errors.append(
                f"Invalid level number: "
                f"{number_text}"
            )

            continue

        numbers.append(number)

    # --------------------------------------------------------
    # Duplicate numbers
    # --------------------------------------------------------

    duplicates = [
        number
        for number, count
        in Counter(numbers).items()
        if count > 1
    ]

    if duplicates:

        errors.append(
            "Duplicate level numbers: "
            + ", ".join(
                map(str, sorted(duplicates))
            )
        )

    # --------------------------------------------------------
    # Range validation
    # --------------------------------------------------------

    if numbers:

        minimum = min(numbers)
        maximum = max(numbers)

        expected_minimum = base
        expected_maximum = (
            base + range_size - 1
        )

        if minimum < expected_minimum:

            errors.append(
                f"Level number {minimum} "
                f"is below range base "
                f"{expected_minimum}."
            )

        if maximum > expected_maximum:

            errors.append(
                f"Level number {maximum} "
                f"exceeds range maximum "
                f"{expected_maximum}."
            )

    return errors


# ============================================================
# PROCESS FILE
# ============================================================

def process_file(
    input_file,
    requested_base,
    range_size
):
    """
    Load, clean, sort, renumber and write one XML file.
    """

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not os.path.exists(input_file):

        print(
            f"[SKIP] File not found: "
            f"{input_file}"
        )

        return

    print()
    print("=" * 60)
    print(f"Processing: {input_file}")
    print("=" * 60)

    # --------------------------------------------------------
    # Parse XML
    # --------------------------------------------------------

    try:

        tree = ET.parse(input_file)
        root = tree.getroot()

    except ET.ParseError as error:

        print(
            f"[ERROR] Invalid XML: {error}"
        )

        return

    # --------------------------------------------------------
    # Find levels
    # --------------------------------------------------------

    levels = root.findall("level")

    if not levels:

        print(
            "[WARNING] No <level> elements found."
        )

        return

    print(
        f"Found {len(levels)} levels."
    )

    # --------------------------------------------------------
    # Determine base
    # --------------------------------------------------------

    base = get_configured_base(
        requested_base,
        levels,
        range_size
    )

    first_number = levels[0].get(
        "number",
        "unknown"
    )

    print(
        f"First source level : "
        f"{first_number}"
    )

    print(
        f"Configured base    : "
        f"{requested_base}"
    )

    print(
        f"Using base         : "
        f"{base}"
    )

    # --------------------------------------------------------
    # Clean attributes
    # --------------------------------------------------------

    for level in levels:

        clean_level_attributes(
            level
        )

    # --------------------------------------------------------
    # Preserve original order
    # --------------------------------------------------------

    indexed_levels = [
        (level, index)
        for index, level
        in enumerate(levels)
    ]

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    indexed_levels.sort(
        key=level_sort_key
    )

    sorted_levels = [
        level
        for level, _
        in indexed_levels
    ]

    # --------------------------------------------------------
    # Determine required range
    # --------------------------------------------------------

    required_count = len(
        sorted_levels
    )

    required_max = (
        base + required_count - 1
    )

    configured_max = (
        base + range_size - 1
    )

    # --------------------------------------------------------
    # Expand range if necessary
    # --------------------------------------------------------

    if required_max > configured_max:

        if AUTO_EXPAND_RANGES:

            new_range_size = (
                math.ceil(
                    required_count
                    / range_size
                )
                * range_size
            )

            print(
                f"[INFO] Expanding range "
                f"from {range_size} "
                f"to {new_range_size}"
            )

            range_size = (
                new_range_size
            )

        else:

            print(
                "[ERROR] Too many levels "
                "for the configured range."
            )

            return

    # --------------------------------------------------------
    # Renumber levels
    # --------------------------------------------------------

    for index, level in enumerate(
        sorted_levels
    ):

        new_number = (
            base + index
        )

        level.set(
            "number",
            str(new_number)
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    errors = validate_levels(
        sorted_levels,
        base,
        range_size
    )

    if errors:

        print()
        print(
            "[VALIDATION ERRORS]"
        )

        for error in errors:

            print(
                f"  - {error}"
            )

        print()
        print(
            "[ABORTED]"
        )

        return

    # --------------------------------------------------------
    # Build output tree
    # --------------------------------------------------------

    output_root = ET.Element(
        "levels"
    )

    for level in sorted_levels:

        output_root.append(
            deepcopy(level)
        )

    # --------------------------------------------------------
    # Output filename
    # --------------------------------------------------------

    output_file = (
        os.path.splitext(input_file)[0]
        + "_sorted.xml"
    )

    # --------------------------------------------------------
    # Diff logging
    # --------------------------------------------------------

    if (
        DIFF_LOGGING
        and os.path.exists(output_file)
    ):

        with open(
            output_file,
            "r",
            encoding="utf-8"
        ) as file:

            old_text = file.read()

        temp_file = (
            output_file + ".tmp"
        )

        write_xml(
            output_root,
            temp_file
        )

        with open(
            temp_file,
            "r",
            encoding="utf-8"
        ) as file:

            new_text = file.read()

        os.remove(temp_file)

        print()

        diff = difflib.unified_diff(
            old_text.splitlines(True),
            new_text.splitlines(True),
            fromfile=output_file,
            tofile="new",
        )

        print(
            "".join(diff)
        )

    # --------------------------------------------------------
    # Write output
    # --------------------------------------------------------

    if DRY_RUN:

        print()
        print(
            "[DRY RUN] No file written."
        )

        print(
            f"Would write: "
            f"{output_file}"
        )

    else:

        write_xml(
            output_root,
            output_file
        )

        print()
        print(
            f"[OK] Written: "
            f"{output_file}"
        )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    solved = sum(
        1
        for level in sorted_levels
        if level.get("solution")
    )

    unsolved = (
        len(sorted_levels)
        - solved
    )

    special = sum(
        1
        for level in sorted_levels
        if has_special_modifier(level)
    )

    final_min = base
    final_max = (
        base
        + len(sorted_levels)
        - 1
    )

    print()
    print("Statistics:")
    print(
        f"  Total levels : "
        f"{len(sorted_levels)}"
    )

    print(
        f"  Solved       : "
        f"{solved}"
    )

    print(
        f"  Unsolved     : "
        f"{unsolved}"
    )

    print(
        f"  Special      : "
        f"{special}"
    )

    print(
        f"  Base         : "
        f"{base}"
    )

    print(
        f"  Range size   : "
        f"{range_size}"
    )

    print(
        f"  Number range : "
        f"{final_min}-{final_max}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("LEVEL SORTER / CLEANER")
    print("=" * 60)

    for (
        input_file,
        requested_base,
        range_size
    ) in input_files:

        process_file(
            input_file,
            requested_base,
            range_size
        )

    print()
    print("=" * 60)
    print("Finished.")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()