from typing import List
from shapes import Rectangle, Placement


class SimpleNester:
    def __init__(self, config: dict):
        self.default_bin_size = Rectangle(config["bin_width"], config["bin_height"])
        self.bins = [self.default_bin_size]
        self.config = {
            "rotation_steps": config.get("rotation_steps", 4),
            "allow_flip": config.get("allow_flip", True),
            "sort_method": config.get("sort_method", "area"),
            "placement_strategy": config.get("placement_strategy", "bottom_left"),
        }

    def nest(self, shapes: List[Rectangle]) -> List[Placement]:
        sorted_shapes = self.sort_shapes(shapes)
        placements = []
        spaces = [
            [
                Placement(
                    0,
                    0,
                    self.default_bin_size.width,
                    self.default_bin_size.height,
                    0,
                    0,
                )
            ]
        ]

        for shape in sorted_shapes:
            best_placement = None
            best_space_index = -1
            best_bin_index = -1

            for bin_index, bin_spaces in enumerate(spaces):
                for i, space in enumerate(bin_spaces):
                    placement = self.find_best_placement(shape, space)
                    if placement and self.is_better_placement(
                        placement, best_placement
                    ):
                        best_placement = placement
                        best_space_index = i
                        best_bin_index = bin_index

            if best_placement:
                placements.append(best_placement)
                self.update_spaces(
                    spaces[best_bin_index], best_space_index, best_placement
                )
            else:
                new_bin_index = len(self.bins)
                self.bins.append(self.default_bin_size)
                spaces.append(
                    [
                        Placement(
                            0,
                            0,
                            self.default_bin_size.width,
                            self.default_bin_size.height,
                            0,
                            new_bin_index,
                        )
                    ]
                )

                new_placement = self.find_best_placement(
                    shape, spaces[new_bin_index][0]
                )
                if new_placement:
                    placements.append(new_placement)
                    self.update_spaces(spaces[new_bin_index], 0, new_placement)
                else:
                    print(
                        f"Warning: Unable to place shape even in a new bin: {shape.__dict__}"
                    )

        return placements

    def sort_shapes(self, shapes: List[Rectangle]) -> List[Rectangle]:
        if self.config["sort_method"] == "area":
            return sorted(shapes, key=lambda s: s.width * s.height, reverse=True)
        elif self.config["sort_method"] == "height":
            return sorted(shapes, key=lambda s: s.height, reverse=True)
        elif self.config["sort_method"] == "width":
            return sorted(shapes, key=lambda s: s.width, reverse=True)
        elif self.config["sort_method"] == "perimeter":
            return sorted(shapes, key=lambda s: s.width + s.height, reverse=True)

    def find_best_placement(self, shape: Rectangle, space: Placement) -> Placement:
        best_placement = None
        rotations = 360 / self.config["rotation_steps"]

        for r in range(self.config["rotation_steps"]):
            rotation = r * rotations
            flips = [False, True] if self.config["allow_flip"] else [False]

            for flip in flips:
                width = shape.height if flip else shape.width
                height = shape.width if flip else shape.height

                if width <= space.width and height <= space.height:
                    placement = Placement(
                        space.x,
                        space.y,
                        width,
                        height,
                        rotation,  # Remove the "+ 90 if flip" part
                        space.bin_index,
                    )

                    if self.is_better_placement(placement, best_placement):
                        best_placement = placement

        return best_placement

    def is_better_placement(
        self, new_placement: Placement, current_best: Placement
    ) -> bool:
        if not current_best:
            return True

        if self.config["placement_strategy"] == "bottom_left":
            return new_placement.y < current_best.y or (
                new_placement.y == current_best.y and new_placement.x < current_best.x
            )
        elif self.config["placement_strategy"] == "best_short_side":
            new_short_side = min(new_placement.width, new_placement.height)
            current_short_side = min(current_best.width, current_best.height)
            return new_short_side > current_short_side
        elif self.config["placement_strategy"] == "best_long_side":
            new_long_side = max(new_placement.width, new_placement.height)
            current_long_side = max(current_best.width, current_best.height)
            return new_long_side > current_long_side

    def update_spaces(
        self, spaces: List[Placement], used_space_index: int, placement: Placement
    ):
        used_space = spaces.pop(used_space_index)

        # Right space
        if used_space.x + placement.width < used_space.x + used_space.width:
            spaces.append(
                Placement(
                    used_space.x + placement.width,
                    used_space.y,
                    used_space.width - placement.width,
                    placement.height,  # Change this line
                    0,
                    placement.bin_index,
                )
            )

        # Top space
        if used_space.y + placement.height < used_space.y + used_space.height:
            spaces.append(
                Placement(
                    used_space.x,
                    used_space.y + placement.height,
                    placement.width,  # Change this line
                    used_space.height - placement.height,
                    0,
                    placement.bin_index,
                )
            )

        # Sort spaces by area (largest first), then by position
        spaces.sort(key=lambda s: (-s.width * s.height, s.y, s.x))

    def get_bin_count(self) -> int:
        return len(self.bins)

    def get_bin_utilization(self) -> List[float]:
        return [
            self.calculate_used_area(i) / (bin.width * bin.height)
            for i, bin in enumerate(self.bins)
        ]

    def calculate_used_area(self, bin_index: int) -> float:
        return sum(
            p.width * p.height for p in self.nest([]) if p.bin_index == bin_index
        )
