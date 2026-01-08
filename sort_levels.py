#!/usr/bin/env python
# -*-coding:utf-8 -*-
# Auto updated?
#   Yes
# File:
#   sort_levels.py
# Author:
#   CreativeCodeCat [wayne6324@gmail.com]
# Github:
#   https://github.com/CreativeCodeCat/
#
# Created:
#   Thu 08 January 2026, 02:38:10 PM [GMT]
# Modified:
#   Thu 08 January 2026, 02:40:11 PM [GMT]
#
# Description:
#   - Parse multiple level XML files
#   - Automatically detect and assign level number bases
#   - Sort levels by solution length and modifier priority
#   - Enforce fixed numeric ranges per difficulty tier
#   - Validate and prevent duplicate level numbers
#   - Remove unsupported XML attributes
#   - Pretty-print and write cleaned XML output files
#
# Dependencies:
#   - Python 3.9+
#   - Standard Library only:
#       * os
#       * math
#       * collections
#       * xml.etree.ElementTree
#

import math
import os
import xml.etree.ElementTree as ET
from collections import Counter

# Input files with fallback base numbers
input_files = [
    ("levelsEasy.xml", 0),
    ("levelsMedium.xml", 300),
    ("levelsHard.xml", 600),
    ("levelsCommunity.xml", 900),
]

# Each file is allowed this many levels
LEVEL_RANGE_SIZE = 300

# Allowed attributes
allowed_attributes = {"color", "modifier", "number", "solution"}

# Modifiers to push to the end
special_modifiers = {"B", "w", "x", "a", "s"}


def has_special_modifier(modifier_str):
    return any(char in special_modifiers for char in modifier_str)


def auto_detect_base(levels, fallback_base):
    """
    Detect base by finding the smallest non-zero level number
    and rounding it down to the nearest LEVEL_RANGE_SIZE.
    """
    numbers = [
        int(lvl.get("number"))
        for lvl in levels
        if lvl.get("number", "").isdigit() and int(lvl.get("number")) != 0
    ]

    if not numbers:
        return fallback_base

    detected = min(numbers)
    return (detected // LEVEL_RANGE_SIZE) * LEVEL_RANGE_SIZE


def validate_duplicates(levels, filename):
    numbers = [lvl.get("number") for lvl in levels if lvl.get("number") is not None]

    counts = Counter(numbers)
    duplicates = [num for num, count in counts.items() if count > 1]

    if duplicates:
        raise ValueError(f"Duplicate level numbers found in {filename}: {duplicates}")


for input_file, fallback_base in input_files:
    tree = ET.parse(input_file)
    root = tree.getroot()

    all_levels = root.findall("level")

    # Validate duplicates BEFORE modifying anything
    validate_duplicates(all_levels, input_file)

    # Separate demo levels (number="0") and normal levels
    demo_levels = [lvl for lvl in all_levels if lvl.get("number") == "0"]
    normal_levels = [lvl for lvl in all_levels if lvl.get("number") != "0"]

    # Auto-detect base
    base = auto_detect_base(normal_levels, fallback_base)
    max_allowed = base + LEVEL_RANGE_SIZE - 1

    # Split normal levels by modifier type
    normal_regular = [
        lvl
        for lvl in normal_levels
        if not has_special_modifier(lvl.get("modifier", ""))
    ]
    normal_special = [
        lvl for lvl in normal_levels if has_special_modifier(lvl.get("modifier", ""))
    ]

    # Sort each group by solution length
    normal_regular.sort(key=lambda lvl: len(lvl.get("solution", "")))
    normal_special.sort(key=lambda lvl: len(lvl.get("solution", "")))

    sorted_levels = normal_regular + normal_special

    # Enforce max range
    if base + len(sorted_levels) - 1 > max_allowed:
        raise ValueError(
            f"{input_file} exceeds allowed range "
            f"{base}-{max_allowed} with {len(sorted_levels)} levels"
        )

    # Clear XML
    for lvl in all_levels:
        root.remove(lvl)

    # Re-add demo levels unchanged
    for lvl in demo_levels:
        root.append(lvl)

    # Add sorted levels with new numbering
    for offset, lvl in enumerate(sorted_levels):
        new_number = base + offset + 1
        lvl.set("number", str(new_number))

        # Strip disallowed attributes
        for attr in list(lvl.attrib.keys()):
            if attr not in allowed_attributes:
                lvl.attrib.pop(attr)

        root.append(lvl)

    # Pretty-print (Python 3.9+)
    ET.indent(tree, space="  ", level=0)

    # Write output
    base_name, ext = os.path.splitext(input_file)
    output_file = f"cleaned_{base_name}{ext}"
    tree.write(output_file, encoding="utf-8", xml_declaration=True)

    print(
        f"Processed {input_file} -> {output_file} "
        f"(base={base}, range={base}-{max_allowed})"
    )
