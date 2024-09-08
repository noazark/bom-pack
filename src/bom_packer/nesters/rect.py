from typing import List
import logging

from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA

from bom_packer.shapes import Part, Placement, Bin

logger = logging.getLogger(__name__)


class RectNester:
    def __init__(self, config: dict):
        self.default_bin_size = (config["bin_width"], config["bin_height"])
        self.config = {
            "allow_rotate": config.get("allow_rotate", True),
            "sort_algo": config.get("sort_algo", SORT_AREA),
        }

    def nest(self, parts: List[Part]) -> List[Bin]:
        packer = newPacker(
            mode=PackingMode.Offline,
            sort_algo=self.config["sort_algo"],
            rotation=self.config["allow_rotate"],
        )

        # Add initial bin
        packer.add_bin(*self.default_bin_size, count=float("inf"))

        # Add rectangles to the packer
        for i, part in enumerate(parts):
            packer.add_rect(part.width, part.height, rid=i)

        # Start packing
        packer.pack()

        bins = []
        for abin in packer:
            if not abin:
                continue
            new_bin = Bin(*self.default_bin_size)
            for rect in abin:
                original_part = parts[rect.rid]
                placement = Placement(
                    rect.x,
                    rect.y,
                    90 if rect.width != original_part.width else 0,
                    original_part,
                )
                new_bin.placements.append(placement)
            bins.append(new_bin)

        if len(parts) != sum(len(bin.placements) for bin in bins):
            logger.warning(
                f"Not all parts were packed. Packed {sum(len(bin.placements) for bin in bins)} out of {len(parts)} parts."
            )
            unpacked_parts = set(range(len(parts))) - set(
                p.part.name for bin in bins for p in bin.placements
            )
            logger.warning(f"Unpacked parts: {unpacked_parts}")

        return bins
