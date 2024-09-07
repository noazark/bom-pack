from typing import List, Tuple, Optional
from shapes import Rectangle, Placement, Bin
import logging

logger = logging.getLogger(__name__)


class SimpleNester:
    def __init__(self, config: dict):
        self.default_bin_size = Rectangle(config["bin_width"], config["bin_height"])
        self.config = {
            "rotation_steps": config.get("rotation_steps", 4),
            "allow_flip": config.get("allow_flip", True),
            "sort_method": config.get("sort_method", "area"),
            "placement_strategy": config.get("placement_strategy", "bottom_left"),
        }

    def nest(self, shapes: List[Rectangle]) -> List[Bin]:
        indexed_shapes = list(enumerate(shapes))
        sorted_shapes = self.sort_shapes(indexed_shapes)
        bins: List[Bin] = []

        for original_index, shape in sorted_shapes:
            placed = False
            for bin in bins:
                placement = self.find_best_placement_in_bin(shape, bin)
                if placement:
                    placement.shape_index = original_index
                    bin.placements.append(placement)
                    self.update_spaces(bin, placement)
                    placed = True
                    break

            if not placed:
                new_bin = Bin(self.default_bin_size.width, self.default_bin_size.height)
                new_bin.spaces = [Placement(0, 0, new_bin.width, new_bin.height, 0)]
                placement = self.find_best_placement_in_bin(shape, new_bin)
                if placement:
                    placement.shape_index = original_index
                    new_bin.placements.append(placement)
                    self.update_spaces(new_bin, placement)
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
        for space in bin.spaces:
            placement = self.find_best_placement(shape, space)
            if placement and self.is_valid_placement(bin, placement):
                if not best_placement or self.is_better_placement(
                    placement, best_placement
                ):
                    best_placement = placement
        return best_placement

    def find_best_placement(
        self, shape: Rectangle, space: Placement
    ) -> Optional[Placement]:
        best_placement = None
        rotations = 360 / self.config["rotation_steps"]

        for r in range(self.config["rotation_steps"]):
            rotation = r * rotations
            flips = [False, True] if self.config["allow_flip"] else [False]

            for flip in flips:
                width = shape.height if flip else shape.width
                height = shape.width if flip else shape.height

                if width <= space.width and height <= space.height:
                    placement = Placement(space.x, space.y, width, height, rotation)
                    if not best_placement or self.is_better_placement(
                        placement, best_placement
                    ):
                        best_placement = placement

        return best_placement

    def is_valid_placement(self, bin: Bin, placement: Placement) -> bool:
        if (
            placement.x + placement.width > bin.width
            or placement.y + placement.height > bin.height
        ):
            return False
        for existing_placement in bin.placements:
            if self.overlaps(placement, existing_placement):
                return False
        return True

    def update_spaces(self, bin: Bin, placement: Placement):
        new_spaces = []
        for space in bin.spaces:
            if self.overlaps(space, placement):
                # Right space
                if space.x + space.width > placement.x + placement.width:
                    new_spaces.append(
                        Placement(
                            placement.x + placement.width,
                            space.y,
                            space.x + space.width - (placement.x + placement.width),
                            space.height,
                            0,
                        )
                    )
                # Top space
                if space.y + space.height > placement.y + placement.height:
                    new_spaces.append(
                        Placement(
                            space.x,
                            placement.y + placement.height,
                            space.width,
                            space.y + space.height - (placement.y + placement.height),
                            0,
                        )
                    )
            else:
                new_spaces.append(space)

        bin.spaces = sorted(new_spaces, key=lambda s: (s.y, s.x))

    def overlaps(self, a: Placement, b: Placement) -> bool:
        return (
            a.x < b.x + b.width
            and a.x + a.width > b.x
            and a.y < b.y + b.height
            and a.y + a.height > b.y
        )

    def is_better_placement(self, new: Placement, current: Optional[Placement]) -> bool:
        if not current:
            return True
        if self.config["placement_strategy"] == "bottom_left":
            return new.y < current.y or (new.y == current.y and new.x < current.x)
        elif self.config["placement_strategy"] == "best_short_side":
            new_short = min(new.width, new.height)
            current_short = min(current.width, current.height)
            return new_short > current_short
        elif self.config["placement_strategy"] == "best_long_side":
            new_long = max(new.width, new.height)
            current_long = max(current.width, current.height)
            return new_long > current_long

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
