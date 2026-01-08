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
#   Thu 08 January 2026, 02:55:34 PM [GMT]
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
# Features:
#   - Dry-run mode
#   - Auto-detect level bases
#   - Per-file custom range sizes
#   - Automatic range expansion
#   - Duplicate level validation
#   - XML structural validation (stdlib-safe)
#   - Diff-style logging
#   - Pretty-printed output
#
# Dependencies:
#   - Python 3.9+
#   - Standard Library only:
#       * os
#       * math
#       * collections
#       * xml.etree.ElementTree
#

import difflib
import math
import os
import xml.etree.ElementTree as ET
from collections import Counter
from copy import deepcopy

# ==========================
# CONFIGURATION
# ==========================

DRY_RUN = False  # True = no files written
AUTO_EXPAND_RANGES = True  # Expand range instead of error
DIFF_LOGGING = False  # Print before/after diffs

# Input files:
# (filename, fallback_base, range_size)
input_files = [
    ("levelsEasy.xml", 0, 300),
    ("levelsMedium.xml", 300, 300),
    ("levelsHard.xml", 600, 300),
    ("levelsCommunity.xml", 900, 300),
]

allowed_attributes = {"color", "modifier", "number", "solution"}
special_modifiers = {"B", "w", "x", "a", "s"}


# ==========================
# HELPERS
# ==========================


def has_special_modifier(modifier_str):
    return any(c in special_modifiers for c in modifier_str or "")


def auto_detect_base(levels, fallback_base, range_size):
    numbers = [
        int(lvl.get("number"))
        for lvl in levels
        if lvl.get("number", "").isdigit() and int(lvl.get("number")) > 0
    ]
    if not numbers:
        return fallback_base
    return (min(numbers) // range_size) * range_size


def validate_duplicates(levels, filename):
    numbers = [lvl.get("number") for lvl in levels if lvl.get("number")]
    dupes = [n for n, c in Counter(numbers).items() if c > 1]
    if dupes:
        raise ValueError(f"[ERROR] Duplicate level numbers in {filename}: {dupes}")


def validate_structure(levels, filename):
    """
    Stdlib-safe XML validation:
    - Required attributes exist
    - Number is numeric
    """
    for lvl in levels:
        if "number" not in lvl.attrib or "solution" not in lvl.attrib:
            raise ValueError(f"[ERROR] Invalid level in {filename}: missing attributes")

        if not lvl.get("number").isdigit():
            raise ValueError(
                f"[ERROR] Invalid number in {filename}: {lvl.get('number')}"
            )


def xml_to_string(elem):
    return ET.tostring(elem, encoding="unicode")


# ==========================
# PROCESS FILES
# ==========================

for input_file, fallback_base, range_size in input_files:
    print(f"\n=== Processing {input_file} ===")

    tree = ET.parse(input_file)
    root = tree.getroot()

    original_root = deepcopy(root)

    all_levels = root.findall("level")

    validate_structure(all_levels, input_file)
    validate_duplicates(all_levels, input_file)

    demo_levels = [lvl for lvl in all_levels if lvl.get("number") == "0"]
    normal_levels = [lvl for lvl in all_levels if lvl.get("number") != "0"]

    base = auto_detect_base(normal_levels, fallback_base, range_size)

    normal_regular = [
        lvl for lvl in normal_levels if not has_special_modifier(lvl.get("modifier"))
    ]
    normal_special = [
        lvl for lvl in normal_levels if has_special_modifier(lvl.get("modifier"))
    ]

    normal_regular.sort(key=lambda l: len(l.get("solution", "")))
    normal_special.sort(key=lambda l: len(l.get("solution", "")))

    sorted_levels = normal_regular + normal_special

    required_max = base + len(sorted_levels)

    if required_max > base + range_size:
        if AUTO_EXPAND_RANGES:
            old_size = range_size
            range_size = math.ceil(len(sorted_levels) / range_size) * range_size
            print(f"[INFO] Auto-expanded range {old_size} → {range_size}")
        else:
            raise ValueError(f"[ERROR] {input_file} exceeds allowed range")

    # Clear XML
    for lvl in all_levels:
        root.remove(lvl)

    for lvl in demo_levels:
        root.append(lvl)

    for i, lvl in enumerate(sorted_levels, start=1):
        lvl.set("number", str(base + i))

        for attr in list(lvl.attrib):
            if attr not in allowed_attributes:
                lvl.attrib.pop(attr)

        root.append(lvl)

    # Pretty-print
    ET.indent(tree, space="  ", level=0)

    # ==========================
    # DIFF LOGGING
    # ==========================

    if DIFF_LOGGING:
        before = xml_to_string(original_root).splitlines()
        after = xml_to_string(root).splitlines()
        diff = difflib.unified_diff(
            before,
            after,
            fromfile=f"{input_file} (before)",
            tofile=f"{input_file} (after)",
            lineterm="",
        )
        print("\n".join(diff))

    # ==========================
    # WRITE OUTPUT
    # ==========================

    if DRY_RUN:
        print("[DRY-RUN] No file written.")
        continue

    base_name, ext = os.path.splitext(input_file)
    output_file = f"cleaned_{base_name}{ext}"

    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"[OK] Written {output_file} (base={base}, range={range_size})")
