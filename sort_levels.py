import xml.etree.ElementTree as ET
import os

# List of input files
input_files = [
    "levelsEasy.xml",
    "levelsMedium.xml",
    "levelsHard.xml",
    "levelsCommunity.xml",
]

# The allowed attributes
allowed_attributes = {"color", "modifier", "number", "solution"}

for input_file in input_files:
    # Parse XML
    tree = ET.parse(input_file)
    root = tree.getroot()

    for lvl in root.findall("level"):
        # Remove any attribute not in the allowed list
        for attr in list(lvl.attrib.keys()):
            if attr not in allowed_attributes:
                print(f"Removing attribute '{attr}' from level {lvl.get('number')} in {input_file}")
                lvl.attrib.pop(attr)

    # Prepare output file name
    base, ext = os.path.splitext(input_file)
    output_file = f"cleaned_{base}{ext}"

    # Write back
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Processed {input_file} -> {output_file}")
