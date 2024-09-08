import csv
import os
from typing import List
from bom_packer.shapes import Part


def read_bom_csv(filename: str) -> List[Part]:
    parts = []
    base_path = os.path.dirname(os.path.abspath(filename))
    with open(filename, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert relative path to absolute path
            file_path = os.path.join(base_path, row["file_path"])
            parts.append(
                Part(name=row["name"], file_path=file_path, quantity=int(row["qty"]))
            )
    return parts
