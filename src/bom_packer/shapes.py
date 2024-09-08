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
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rotation = rotation


class Part(NamedTuple):
    name: str
    file_path: str
    quantity: int


class Shape(NamedTuple):
    part: Part
    rectangle: Rectangle
    entities: List[ezdxf.entities.DXFEntity]


class Bin:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.placements: List[Placement] = []
