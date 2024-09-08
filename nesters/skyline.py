from typing import List, Tuple, Optional
from shapes import Rectangle, Placement, Bin
import logging
import copy

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
            "placement_strategy": config.get("placement_strategy", "best_fit"),
            "look_ahead": config.get("look_ahead", 3),  # Number of shapes to look ahead
        }

    def nest(self, shapes: List[Rectangle]) -> List[Bin]:
        indexed_shapes = list(enumerate(shapes))  # Preserve original indices
        sorted_shapes = self.sort_shapes(indexed_shapes)
        bins: List[Bin] = []

        while sorted_shapes:
            current_shape_index, current_shape = sorted_shapes.pop(0)
            look_ahead_shapes = sorted_shapes[: self.config["look_ahead"]]

            placed = False
            for bin in bins:
                placement = self.find_best_placement_with_lookahead(
                    current_shape, bin, look_ahead_shapes
                )
                if placement:
                    placement.shape_index = current_shape_index
                    bin.placements.append(placement)
                    self.update_skyline(bin, placement)
                    placed = True
                    break

            if not placed:
                new_bin = Bin(self.default_bin_size.width, self.default_bin_size.height)
                new_bin.skyline = [SkylineNode(0, 0, new_bin.width)]
                placement = self.find_best_placement_with_lookahead(
                    current_shape, new_bin, look_ahead_shapes
                )
                if placement:
                    placement.shape_index = current_shape_index
                    new_bin.placements.append(placement)
                    self.update_skyline(new_bin, placement)
                    bins.append(new_bin)
                else:
                    logger.warning(
                        f"Unable to place shape even in a new bin: {current_shape.__dict__}"
                    )

        return bins

    def find_best_placement_with_lookahead(
        self, shape: Rectangle, bin: Bin, look_ahead_shapes: List[Tuple[int, Rectangle]]
    ) -> Optional[Placement]:
        best_placement = None
        best_score = float("inf")

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

                    placement = Placement(node.x, y, width, height, rotation)
                    score = self.calculate_placement_score(placement, bin)

                    # Look ahead
                    temp_bin = copy.deepcopy(bin)
                    temp_bin.placements.append(placement)
                    self.update_skyline(temp_bin, placement)

                    for _, look_ahead_shape in look_ahead_shapes:
                        look_ahead_placement = self.find_best_placement_in_bin(
                            look_ahead_shape, temp_bin
                        )
                        if look_ahead_placement:
                            score += self.calculate_placement_score(
                                look_ahead_placement, temp_bin
                            )
                            self.update_skyline(temp_bin, look_ahead_placement)
                        else:
                            score += (
                                self.default_bin_size.width
                                * self.default_bin_size.height
                            )  # Penalty for not placing

                    if score < best_score:
                        best_score = score
                        best_placement = placement

        return best_placement

    def find_best_placement_in_bin(
        self, shape: Rectangle, bin: Bin
    ) -> Optional[Placement]:
        best_placement = None
        best_score = float("inf")

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

                    placement = Placement(node.x, y, width, height, rotation)
                    score = self.calculate_placement_score(placement, bin)
                    if score < best_score:
                        best_score = score
                        best_placement = placement

        return best_placement

    def calculate_placement_score(self, placement: Placement, bin: Bin) -> float:
        if self.config["placement_strategy"] == "best_fit":
            # Calculate the perimeter touching other shapes or bin edges
            touching_perimeter = 0
            if placement.x == 0:
                touching_perimeter += placement.height
            if placement.x + placement.width == bin.width:
                touching_perimeter += placement.height
            if placement.y == 0:
                touching_perimeter += placement.width

            for node in bin.skyline:
                if (
                    node.x < placement.x + placement.width
                    and node.x + node.width > placement.x
                ):
                    touching_perimeter += min(
                        node.x + node.width, placement.x + placement.width
                    ) - max(node.x, placement.x)

            return (
                -touching_perimeter
            )  # Negative because we want to maximize touching perimeter
        else:
            # Default to waste minimization
            return (placement.y - bin.skyline[0].y) * placement.width

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
        bin.skyline = self.merge_skyline(new_skyline)

    def merge_skyline(self, skyline: List[SkylineNode]) -> List[SkylineNode]:
        if not skyline:
            return skyline

        merged = [skyline[0]]
        for node in skyline[1:]:
            if merged[-1].y == node.y:
                merged[-1].width += node.width
            else:
                merged.append(node)

        return merged

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
