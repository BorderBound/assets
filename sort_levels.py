import os
import xml.etree.ElementTree as ET

# List of input files
input_files = [
    "levelsEasy.xml",
    "levelsMedium.xml",
    "levelsHard.xml",
    "levelsCommunity.xml",
]

# Allowed attributes
allowed_attributes = {"color", "modifier", "number", "solution"}

# Modifiers to push to the end
special_modifiers = {"B", "w", "x", "a", "s"}


# Function to check if a modifier string contains any special modifier
def has_special_modifier(modifier_str):
    return any(char in special_modifiers for char in modifier_str)


for input_file in input_files:
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Separate demo levels (number="0") and normal levels
    demo_levels = [lvl for lvl in root.findall("level") if lvl.get("number") == "0"]
    normal_levels = [lvl for lvl in root.findall("level") if lvl.get("number") != "0"]

    # Split normal levels into two groups:
    # 1. Levels without special modifiers
    # 2. Levels with special modifiers
    normal_regular = [lvl for lvl in normal_levels if not has_special_modifier(lvl.get("modifier", ""))]
    normal_special = [lvl for lvl in normal_levels if has_special_modifier(lvl.get("modifier", ""))]

    # Sort each group by length of solution (shortest first)
    normal_regular.sort(key=lambda lvl: len(lvl.get("solution", "")))
    normal_special.sort(key=lambda lvl: len(lvl.get("solution", "")))

    # Combine the two groups: regular first, special later
    sorted_levels = normal_regular + normal_special

    # Clear all levels from XML
    for lvl in root.findall("level"):
        root.remove(lvl)

    # Add demo levels first (number="0" stays as-is)
    for lvl in demo_levels:
        root.append(lvl)

    # Add sorted normal levels and renumber starting from 1
    for new_number, lvl in enumerate(sorted_levels, start=1):
        lvl.set("number", str(new_number))  # reset number after sorting

        # Remove any attribute not allowed
        for attr in list(lvl.attrib.keys()):
            if attr not in allowed_attributes:
                print(
                    f"Removing attribute '{attr}' from level {new_number} in {input_file}"
                )
                lvl.attrib.pop(attr)

        root.append(lvl)

    # Prepare output file name
    base, ext = os.path.splitext(input_file)
    output_file = f"cleaned_{base}{ext}"

    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Processed {input_file} -> {output_file}")
