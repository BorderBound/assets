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
#   - Automatically detect and assign level number bases
#   - Sort levels by solution length and modifier priority
#   - Handle levels without a solution
#   - Preserve author information
#   - Remove unsupported XML attributes
#   - Convert multiline color/modifier values to one-line values
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

input_files = [
    ("levelsEasy.xml", 0, 300),
    ("levelsMedium.xml", 300, 300),
    ("levelsHard.xml", 600, 300),
    ("levelsCommunity.xml", 900, 300),
]

# Attributes allowed to remain on <level>
ALLOWED_ATTRIBUTES = {
    "color",
    "modifier",
    "number",
    "solution",
    "author",
}

# Modifiers containing one of these characters are treated
# as "special" modifiers and sorted after normal modifiers.
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
    Clean multiline color/modifier data.

    Example:

        "  abcde
           fghij
           klmno "

    becomes:

        "abcde fghij klmno"
    """
    if value is None:
        return None

    return clean_spaces(value)


def normalise_solution(value):
    """
    Clean solution strings.

    Removes unnecessary whitespace around commas and
    collapses any other whitespace.
    """
    if value is None:
        return None

    value = clean_spaces(value)
    value = re.sub(r"\s*,\s*", ",", value)

    return value.strip()


def normalise_author(value):
    """
    Clean author names without changing their actual text.
    """
    if value is None:
        return None

    return clean_spaces(value)


def clean_level_attributes(level):
    """
    Remove unsupported attributes and clean the attributes
    that we keep.
    """

    # Remove attributes that are not supported
    for attr in list(level.attrib.keys()):
        if attr not in ALLOWED_ATTRIBUTES:
            del level.attrib[attr]

    # Clean color
    if "color" in level.attrib:
        level.attrib["color"] = normalise_grid(level.attrib["color"])

    # Clean modifier
    if "modifier" in level.attrib:
        level.attrib["modifier"] = normalise_grid(level.attrib["modifier"])

    # Clean solution
    if "solution" in level.attrib:
        solution = normalise_solution(level.attrib["solution"])

        # Don't leave empty solution attributes behind
        if solution:
            level.attrib["solution"] = solution
        else:
            del level.attrib["solution"]

    # Clean author
    if "author" in level.attrib:
        author = normalise_author(level.attrib["author"])

        if author:
            level.attrib["author"] = author
        else:
            del level.attrib["author"]


# ============================================================
# SORTING HELPERS
# ============================================================

def has_special_modifier(level):
    """
    Return True if the modifier contains one of the special
    modifier characters.
    """

    modifier = level.get("modifier", "")

    for char in SPECIAL_MODIFIERS:
        if char in modifier:
            return True

    return False


def solution_length(level):
    """
    Return the number of moves in the solution.

    Missing solutions are treated as unsolved.
    """

    solution = level.get("solution")

    if not solution:
        return float("inf")

    if not solution.strip():
        return float("inf")

    return len([
        move for move in solution.split(",")
        if move.strip()
    ])


def level_sort_key(item):
    """
    Sorting order:

    1. Solved levels first
    2. Normal modifiers before special modifiers
    3. Shorter solutions first
    4. Original number as final tie breaker

    Unsolved levels are always placed at the end.
    """

    level, original_index = item

    has_solution = bool(
        level.get("solution", "").strip()
    )

    # Unsolved levels go last
    solution_priority = 0 if has_solution else 1

    # Normal modifiers before special modifiers
    modifier_priority = 1 if has_special_modifier(level) else 0

    # Solution length
    length = solution_length(level)

    # Original number for deterministic ordering
    try:
        original_number = int(level.get("number", 0))
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
# RANGE / BASE DETECTION
# ============================================================

def detect_base_from_first_level(levels, range_size):
    """
    Determine the intended range base from the FIRST level
    in the file.

    Example:

        first number = 901
        range size  = 300

        901 // 300 = 3
        3 * 300 = 900

    Therefore the detected base is 900.

    This deliberately does NOT use min(numbers), because a
    file can begin at 901 while also containing older or
    out-of-order levels such as 137, 138, etc.
    """

    if not levels:
        return 0

    first_number_text = levels[0].get("number")

    if first_number_text is None:
        return 0

    try:
        first_number = int(first_number_text)
    except ValueError:
        return 0

    return (first_number // range_size) * range_size


# ============================================================
# XML FORMATTING
# ============================================================

def escape_xml_attribute(value):
    """
    Escape a value for use inside a double-quoted XML attribute.
    """

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_level(level):
    """
    Format a <level> element in the desired style.

    Example:

        <level color="..."
               modifier="..."
               number="901"
               solution="A1,B2"
               author="Name" />
    """

    # Desired attribute order
    preferred_order = [
        "color",
        "modifier",
        "number",
        "solution",
        "author",
    ]

    attributes = []

    for attr in preferred_order:
        if attr in level.attrib:
            attributes.append(
                f'{attr}="{escape_xml_attribute(level.attrib[attr])}"'
            )

    # Include any unexpected remaining attributes just in case
    for attr, value in level.attrib.items():
        if attr not in preferred_order:
            attributes.append(
                f'{attr}="{escape_xml_attribute(value)}"'
            )

    if not attributes:
        return "    <level />"

    lines = []

    # First attribute sits after <level
    lines.append(f"    <level {attributes[0]}")

    # Remaining attributes align underneath
    for index, attribute in enumerate(attributes[1:], start=1):
        if index == len(attributes) - 1:
            lines.append(f'           {attribute} />')
        else:
            lines.append(f'           {attribute}')

    # If there was only one attribute, close it here
    if len(attributes) == 1:
        lines[-1] += " />"

    return "\n".join(lines)


def write_xml(root, output_file):
    """
    Write XML using our own formatter so multiline attributes
    are cleaned and formatted consistently.
    """

    lines = [
        '<?xml version="1.0" encoding="utf-8" ?>',
        "<levels>",
        "",
    ]

    for child in root:
        if child.tag != "level":
            continue

        lines.append(format_level(child))
        lines.append("")

    # Remove the final blank line
    if lines and lines[-1] == "":
        lines.pop()

    lines.append("</levels>")

    content = "\n".join(lines) + "\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# VALIDATION
# ============================================================

def validate_levels(levels, base, range_size):
    """
    Validate the resulting level numbers.
    """

    errors = []

    numbers = []

    for level in levels:
        number_text = level.get("number")

        if number_text is None:
            errors.append("Level is missing a number.")
            continue

        try:
            number = int(number_text)
        except ValueError:
            errors.append(
                f"Invalid level number: {number_text}"
            )
            continue

        numbers.append(number)

    # Duplicate numbers
    duplicates = [
        number
        for number, count in Counter(numbers).items()
        if count > 1
    ]

    if duplicates:
        errors.append(
            "Duplicate level numbers: "
            + ", ".join(map(str, sorted(duplicates)))
        )

    # Range check
    if numbers:
        minimum = min(numbers)
        maximum = max(numbers)

        expected_minimum = base
        expected_maximum = base + range_size - 1

        if minimum < expected_minimum:
            errors.append(
                f"Level number {minimum} is below "
                f"range base {expected_minimum}."
            )

        if maximum > expected_maximum:
            errors.append(
                f"Level number {maximum} exceeds "
                f"range maximum {expected_maximum}."
            )

    return errors


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(input_file, requested_base, range_size):
    """
    Load, clean, sort and renumber one XML file.
    """

    if not os.path.exists(input_file):
        print(f"[SKIP] File not found: {input_file}")
        return

    print()
    print("=" * 60)
    print(f"Processing: {input_file}")
    print("=" * 60)

    # --------------------------------------------------------
    # Load XML
    # --------------------------------------------------------

    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[ERROR] Invalid XML: {e}")
        return

    # Only direct <level> elements
    levels = root.findall("level")

    if not levels:
        print("[WARNING] No <level> elements found.")
        return

    print(f"Found {len(levels)} levels.")

    # --------------------------------------------------------
    # Detect base
    # --------------------------------------------------------

    detected_base = detect_base_from_first_level(
        levels,
        range_size
    )

    # Use detected base rather than min(number)
    base = detected_base

    print(f"First level number: {levels[0].get('number')}")
    print(f"Detected base: {base}")

    # --------------------------------------------------------
    # Clean attributes
    # --------------------------------------------------------

    for level in levels:
        clean_level_attributes(level)

    # --------------------------------------------------------
    # Preserve original order for tie-breaking
    # --------------------------------------------------------

    indexed_levels = [
        (level, index)
        for index, level in enumerate(levels)
    ]

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    indexed_levels.sort(key=level_sort_key)

    sorted_levels = [
        level
        for level, _ in indexed_levels
    ]

    # --------------------------------------------------------
    # Renumber
    # --------------------------------------------------------

    # Keep the existing range base.

    required_count = len(sorted_levels)

    required_max = base + required_count - 1

    if required_max > base + range_size - 1:

        if AUTO_EXPAND_RANGES:
            new_range_size = (
                math.ceil(required_count / range_size)
                * range_size
            )

            print(
                f"[INFO] Expanding range from "
                f"{range_size} to {new_range_size}"
            )

            range_size = new_range_size

        else:
            print(
                "[ERROR] Too many levels for the configured range."
            )
            return

    for index, level in enumerate(sorted_levels):
        level.set("number", str(base + index))

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
        print("[VALIDATION ERRORS]")

        for error in errors:
            print(f"  - {error}")

        print()
        print("[ABORTED]")
        return

    # --------------------------------------------------------
    # Build output tree
    # --------------------------------------------------------

    output_root = ET.Element("levels")

    for level in sorted_levels:
        output_root.append(deepcopy(level))

    # --------------------------------------------------------
    # Output filename
    # --------------------------------------------------------

    output_file = os.path.splitext(input_file)[0] + "_sorted.xml"

    # --------------------------------------------------------
    # Diff logging
    # --------------------------------------------------------

    if DIFF_LOGGING and os.path.exists(output_file):

        old_text = open(
            output_file,
            "r",
            encoding="utf-8"
        ).read()

        temp_file = output_file + ".tmp"

        write_xml(output_root, temp_file)

        new_text = open(
            temp_file,
            "r",
            encoding="utf-8"
        ).read()

        os.remove(temp_file)

        print()
        print("".join(
            difflib.unified_diff(
                old_text.splitlines(True),
                new_text.splitlines(True),
                fromfile=output_file,
                tofile="new",
            )
        ))

    # --------------------------------------------------------
    # Write output
    # --------------------------------------------------------

    if DRY_RUN:
        print()
        print("[DRY RUN] No file written.")
        print(f"Would write: {output_file}")
    else:
        write_xml(
            output_root,
            output_file
        )

        print()
        print(f"[OK] Written: {output_file}")

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    solved = sum(
        1
        for level in sorted_levels
        if level.get("solution")
    )

    unsolved = len(sorted_levels) - solved

    special = sum(
        1
        for level in sorted_levels
        if has_special_modifier(level)
    )

    print()
    print("Statistics:")
    print(f"  Total levels : {len(sorted_levels)}")
    print(f"  Solved       : {solved}")
    print(f"  Unsolved     : {unsolved}")
    print(f"  Special      : {special}")
    print(f"  Base         : {base}")
    print(f"  Range size   : {range_size}")
    print(
        f"  Number range : "
        f"{base}-{base + len(sorted_levels) - 1}"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("LEVEL SORTER / CLEANER")
    print("=" * 60)

    for input_file, requested_base, range_size in input_files:
        process_file(
            input_file,
            requested_base,
            range_size
        )

    print()
    print("=" * 60)
    print("Finished.")
    print("=" * 60)


if __name__ == "__main__":
    main()
