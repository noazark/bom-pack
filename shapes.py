from typing import List, NamedTuple
import ezdxf


class Rectangle:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height


class Placement:
    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float,
        bin_index: int,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rotation = rotation
        self.bin_index = bin_index


class Part(NamedTuple):
    name: str
    file_path: str
    quantity: int


class Shape(NamedTuple):
    part: Part
    rectangle: Rectangle
    entities: List[ezdxf.entities.DXFEntity]
