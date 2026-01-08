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

for input_file in input_files:
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Separate demo levels (number="0") and normal levels
    demo_levels = [lvl for lvl in root.findall("level") if lvl.get("number") == "0"]
    normal_levels = [lvl for lvl in root.findall("level") if lvl.get("number") != "0"]

    # Sort normal levels by length of solution (shortest first)
    normal_levels.sort(key=lambda lvl: len(lvl.get("solution", "")))

    # Clear all levels from XML
    for lvl in root.findall("level"):
        root.remove(lvl)

    # Add demo levels first (keep number="0" as-is)
    for lvl in demo_levels:
        root.append(lvl)

    # Add sorted normal levels and renumber starting from 1
    for new_number, lvl in enumerate(normal_levels, start=1):
        lvl.set("number", str(new_number))  # renumber starting at 1

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
