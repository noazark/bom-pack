from typing import List, NamedTuple, Optional
import ezdxf


class Part(NamedTuple):
    name: str
    file_path: str
    quantity: int
    width: Optional[float] = None
    height: Optional[float] = None
    entities: Optional[List[ezdxf.entities.DXFEntity]] = None


class Placement:
    def __init__(self, x: float, y: float, rotation: float, part: Part):
        self.x = x
        self.y = y
        self.rotation = rotation
        self.part = part


class Bin:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.placements: List[Placement] = []
