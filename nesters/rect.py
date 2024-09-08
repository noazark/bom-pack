from typing import List
from shapes import Rectangle, Placement, Bin
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA
import logging

logger = logging.getLogger(__name__)


class RectNester:
    def __init__(self, config: dict):
        self.default_bin_size = Rectangle(config["bin_width"], config["bin_height"])
        self.config = {
            "allow_rotate": config.get("allow_rotate", False),
            "sort_algo": config.get("sort_algo", SORT_AREA),
        }

    def nest(self, shapes: List[Rectangle]) -> List[Bin]:
        packer = newPacker(
            mode=PackingMode.Offline,
            sort_algo=self.config["sort_algo"],
            rotation=self.config["allow_rotate"],
        )

        # Add initial bin
        packer.add_bin(
            self.default_bin_size.width,
            self.default_bin_size.height,
            count=float("inf"),
        )

        # Add rectangles to the packer
        for i, shape in enumerate(shapes):
            packer.add_rect(shape.width, shape.height, rid=i)

        # Start packing
        packer.pack()

        bins = []
        for abin in packer:
            if not abin:
                continue
            new_bin = Bin(self.default_bin_size.width, self.default_bin_size.height)
            for rect in abin:
                original_shape = shapes[rect.rid]
                is_rotated = (
                    rect.width != original_shape.width
                    or rect.height != original_shape.height
                )
                print(rect.rid, rect.x, rect.y, is_rotated)
                placement = Placement(
                    rect.x,
                    rect.y,
                    rect.width,
                    rect.height,
                    0,
                )
                placement.shape_index = rect.rid
                new_bin.placements.append(placement)
            bins.append(new_bin)

        if len(shapes) != sum(len(bin.placements) for bin in bins):
            logger.warning(
                f"Not all shapes were packed. Packed {sum(len(bin.placements) for bin in bins)} out of {len(shapes)} shapes."
            )
            unpacked_shapes = set(range(len(shapes))) - set(
                p.shape_index for bin in bins for p in bin.placements
            )
            logger.warning(f"Unpacked shapes: {unpacked_shapes}")

        return bins
