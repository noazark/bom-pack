from typing import List, Tuple, Optional
from shapes import Rectangle, Placement, Bin
import logging

# Configure logging
logger = logging.getLogger(__name__)


class SkylineNode:
    def __init__(self, x: float, y: float, width: float):
        self.x = x
        self.y = y
        self.width = width


class SkylineNester:
    def __init__(self, config: dict):
        self.default_bin_size = Rectangle(config["bin_width"], config["bin_height"])
        self.config = {
            "rotation_steps": config.get("rotation_steps", 4),
            "allow_flip": config.get("allow_flip", True),
            "sort_method": config.get("sort_method", "area"),
        }

    def nest(self, shapes: List[Rectangle]) -> List[Bin]:
        indexed_shapes = list(enumerate(shapes))  # Preserve original indices
        sorted_shapes = self.sort_shapes(indexed_shapes)
        bins: List[Bin] = []

        for original_index, shape in sorted_shapes:
            placed = False
            for bin in bins:
                placement = self.find_best_placement_in_bin(shape, bin)
                if placement:
                    placement.shape_index = original_index  # Use original index
                    bin.placements.append(placement)
                    self.update_skyline(bin, placement)
                    placed = True
                    break

            if not placed:
                new_bin = Bin(self.default_bin_size.width, self.default_bin_size.height)
                new_bin.skyline = [SkylineNode(0, 0, new_bin.width)]
                placement = self.find_best_placement_in_bin(shape, new_bin)
                if placement:
                    placement.shape_index = original_index  # Use original index
                    new_bin.placements.append(placement)
                    self.update_skyline(new_bin, placement)
                    bins.append(new_bin)
                else:
                    logger.warning(
                        f"Unable to place shape even in a new bin: {shape.__dict__}"
                    )

        return bins

    def find_best_placement_in_bin(
        self, shape: Rectangle, bin: Bin
    ) -> Optional[Placement]:
        best_placement = None
        min_waste = float("inf")

        rotations = 360 / self.config["rotation_steps"]
        for r in range(self.config["rotation_steps"]):
            rotation = r * rotations
            flips = [False, True] if self.config["allow_flip"] else [False]

            for flip in flips:
                width = shape.height if flip else shape.width
                height = shape.width if flip else shape.height

                for i, node in enumerate(bin.skyline):
                    if width > node.width:
                        continue

                    y = self.find_min_y(bin.skyline, i, width)
                    if y + height > bin.height:
                        continue

                    waste = (y - node.y) * width
                    if waste < min_waste:
                        min_waste = waste
                        best_placement = Placement(node.x, y, width, height, rotation)

        return best_placement

    def find_min_y(self, skyline: List[SkylineNode], index: int, width: float) -> float:
        min_y = skyline[index].y
        width_left = width
        i = index

        while width_left > 0:
            min_y = max(min_y, skyline[i].y)
            width_left -= skyline[i].width
            i += 1
            if i >= len(skyline):
                break

        return min_y

    def update_skyline(self, bin: Bin, placement: Placement):
        new_skyline = []
        i = 0

        # Nodes before the placement
        while i < len(bin.skyline) and bin.skyline[i].x < placement.x:
            new_skyline.append(bin.skyline[i])
            i += 1

        # Add new node for the placement
        new_node = SkylineNode(
            placement.x, placement.y + placement.height, placement.width
        )
        new_skyline.append(new_node)

        # Update or add nodes after the placement
        while i < len(bin.skyline):
            node = bin.skyline[i]
            if node.x >= placement.x + placement.width:
                new_skyline.append(node)
            elif node.x + node.width > placement.x + placement.width:
                new_width = node.x + node.width - (placement.x + placement.width)
                new_skyline.append(
                    SkylineNode(placement.x + placement.width, node.y, new_width)
                )
            i += 1

        # Merge adjacent nodes with the same height
        bin.skyline = [new_skyline[0]]
        for node in new_skyline[1:]:
            if bin.skyline[-1].y == node.y:
                bin.skyline[-1].width += node.width
            else:
                bin.skyline.append(node)

    def sort_shapes(
        self, indexed_shapes: List[Tuple[int, Rectangle]]
    ) -> List[Tuple[int, Rectangle]]:
        if self.config["sort_method"] == "area":
            return sorted(
                indexed_shapes, key=lambda x: x[1].width * x[1].height, reverse=True
            )
        elif self.config["sort_method"] == "height":
            return sorted(indexed_shapes, key=lambda x: x[1].height, reverse=True)
        elif self.config["sort_method"] == "width":
            return sorted(indexed_shapes, key=lambda x: x[1].width, reverse=True)
        elif self.config["sort_method"] == "perimeter":
            return sorted(
                indexed_shapes, key=lambda x: x[1].width + x[1].height, reverse=True
            )
