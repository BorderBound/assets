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
    tree = ET.parse(input_file)
    root = tree.getroot()

    for index, lvl in enumerate(root.findall("level")):
        # Reset number starting from 0
        lvl.set("number", str(index))

        # Remove any attribute not in the allowed list
        for attr in list(lvl.attrib.keys()):
            if attr not in allowed_attributes:
                print(
                    f"Removing attribute '{attr}' from level {index} in {input_file}"
                )
                lvl.attrib.pop(attr)

    # Prepare output file name
    base, ext = os.path.splitext(input_file)
    output_file = f"cleaned_{base}{ext}"

    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Processed {input_file} -> {output_file}")
