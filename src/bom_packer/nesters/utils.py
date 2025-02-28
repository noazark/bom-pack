from typing import List
from bom_packer.shapes import Bin


def get_bin_count(bins: List[Bin]) -> int:
    return len(bins)


def get_bin_utilization(bins: List[Bin]) -> List[float]:
    return [calculate_used_area(bin) / (bin.width * bin.height) for bin in bins]


def calculate_used_area(bin: Bin) -> float:
    return sum(p.part.width * p.part.height for p in bin.placements)
