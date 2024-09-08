from abc import ABC, abstractmethod
import ezdxf
from typing import List, Tuple
import math

import logging

# Configure the logger
logger = logging.getLogger(__name__)


class EntityHandler(ABC):
    @abstractmethod
    def get_points(self, entity) -> List[Tuple[float, float]]:
        pass

    @abstractmethod
    def normalize(self, entity, min_x: float, min_y: float):
        pass

    @abstractmethod
    def copy_and_transform(self, entity, target_layout, placement):
        pass


class LineHandler(EntityHandler):
    def get_points(self, entity):
        return [entity.dxf.start, entity.dxf.end]

    def normalize(self, entity, min_x, min_y):
        entity.dxf.start = (entity.dxf.start[0] - min_x, entity.dxf.start[1] - min_y)
        entity.dxf.end = (entity.dxf.end[0] - min_x, entity.dxf.end[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        start = transform_point(entity.dxf.start, placement)
        end = transform_point(entity.dxf.end, placement)
        return target_layout.add_line(start, end)


class LWPolylineHandler(EntityHandler):
    def get_points(self, entity):
        return entity.get_points()

    def normalize(self, entity, min_x, min_y):
        points = [(p[0] - min_x, p[1] - min_y) for p in entity.get_points()]
        entity.set_points(points)

    def copy_and_transform(self, entity, target_layout, placement):
        points = [transform_point(p, placement) for p in entity.get_points()]
        return target_layout.add_lwpolyline(points)


class CircleHandler(EntityHandler):
    def get_points(self, entity):
        center = entity.dxf.center
        radius = entity.dxf.radius
        return [
            (center[0] - radius, center[1] - radius),
            (center[0] + radius, center[1] + radius),
        ]

    def normalize(self, entity, min_x, min_y):
        entity.dxf.center = (entity.dxf.center[0] - min_x, entity.dxf.center[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        center = transform_point(entity.dxf.center, placement)
        return target_layout.add_circle(center, entity.dxf.radius)


class ArcHandler(EntityHandler):
    def get_points(self, entity):
        return entity.flattening(0.1)  # Approximate arc with line segments

    def normalize(self, entity, min_x, min_y):
        entity.dxf.center = (entity.dxf.center[0] - min_x, entity.dxf.center[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        center = transform_point(entity.dxf.center, placement)
        return target_layout.add_arc(
            center,
            entity.dxf.radius,
            entity.dxf.start_angle + placement.rotation,
            entity.dxf.end_angle + placement.rotation,
        )


class SplineHandler(EntityHandler):
    def get_points(self, entity):
        return entity.get_control_points()

    def normalize(self, entity, min_x, min_y):
        control_points = [
            (p[0] - min_x, p[1] - min_y) for p in entity.get_control_points()
        ]
        entity.set_control_points(control_points)

    def copy_and_transform(self, entity, target_layout, placement):
        control_points = [
            transform_point(p, placement) for p in entity.get_control_points()
        ]
        return target_layout.add_spline(control_points)


class EllipseHandler(EntityHandler):
    def get_points(self, entity):
        return entity.get_points(num=32)  # 32 points approximation

    def normalize(self, entity, min_x, min_y):
        entity.dxf.center = (entity.dxf.center[0] - min_x, entity.dxf.center[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        center = transform_point(entity.dxf.center, placement)
        return target_layout.add_ellipse(center, entity.dxf.radius)


class PointHandler(EntityHandler):
    def get_points(self, entity):
        return [entity.dxf.location]

    def normalize(self, entity, min_x, min_y):
        entity.dxf.location = (
            entity.dxf.location[0] - min_x,
            entity.dxf.location[1] - min_y,
        )

    def copy_and_transform(self, entity, target_layout, placement):
        location = transform_point(entity.dxf.location, placement)
        return target_layout.add_point(location)


class SolidHandler(EntityHandler):
    def get_points(self, entity):
        return entity.get_bbox()

    def normalize(self, entity, min_x, min_y):
        bbox = entity.get_bbox()
        entity.set_bbox(
            (bbox[0] - min_x, bbox[1] - min_y, bbox[2] - min_x, bbox[3] - min_y)
        )

    def copy_and_transform(self, entity, target_layout, placement):
        bbox = entity.get_bbox()
        return target_layout.add_solid(bbox)


class HatchHandler(EntityHandler):
    def get_points(self, entity):
        return entity.get_bbox()

    def normalize(self, entity, min_x, min_y):
        bbox = entity.get_bbox()
        entity.set_bbox(
            (bbox[0] - min_x, bbox[1] - min_y, bbox[2] - min_x, bbox[3] - min_y)
        )

    def copy_and_transform(self, entity, target_layout, placement):
        bbox = entity.get_bbox()
        return target_layout.add_hatch(bbox)


class InsertHandler(EntityHandler):
    def get_points(self, entity):
        insertion = entity.dxf.insert
        return [
            insertion,
            (insertion[0] + entity.dxf.xscale, insertion[1] + entity.dxf.yscale),
        ]

    def normalize(self, entity, min_x, min_y):
        entity.dxf.insert = (entity.dxf.insert[0] - min_x, entity.dxf.insert[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        insertion = transform_point(entity.dxf.insert, placement)
        return target_layout.add_insert(insertion)


class TextHandler(EntityHandler):
    def get_points(self, entity):
        insertion = entity.dxf.insert
        return [insertion, (insertion[0], insertion[1] + entity.dxf.height)]

    def normalize(self, entity, min_x, min_y):
        entity.dxf.insert = (entity.dxf.insert[0] - min_x, entity.dxf.insert[1] - min_y)

    def copy_and_transform(self, entity, target_layout, placement):
        insertion = transform_point(entity.dxf.insert, placement)
        return target_layout.add_text(insertion)


class PolylineHandler(EntityHandler):
    def get_points(self, entity):
        return [vertex.dxf.location for vertex in entity.vertices]

    def normalize(self, entity, min_x, min_y):
        for vertex in entity.vertices:
            vertex.dxf.location = (
                vertex.dxf.location[0] - min_x,
                vertex.dxf.location[1] - min_y,
            )

    def copy_and_transform(self, entity, target_layout, placement):
        points = [transform_point(p, placement) for p in entity.get_points()]
        return target_layout.add_lwpolyline(points)


class DefaultHandler(EntityHandler):
    def get_points(self, entity):
        return []

    def normalize(self, entity, min_x, min_y):
        pass

    def copy_and_transform(self, entity, target_layout, placement):
        raise ValueError(f"Unsupported entity type: {entity.dxftype()}")


def transform_point(point, placement):
    x, y = safe_vector_access(point, 0), safe_vector_access(point, 1)

    # Apply rotation
    rotation_rad = math.radians(placement.rotation)
    x_rot = x * math.cos(rotation_rad) - y * math.sin(rotation_rad)
    y_rot = x * math.sin(rotation_rad) + y * math.cos(rotation_rad)

    # Apply translation
    transformed_point = (x_rot + placement.x, y_rot + placement.y)
    logger.debug(
        f"Transforming point {point} with placement {placement} to {transformed_point}"
    )
    return transformed_point


def safe_vector_access(vector, index, default=0.0):
    try:
        return float(vector[index])
    except (IndexError, TypeError):
        return default


# Dictionary mapping entity types to their handlers
ENTITY_HANDLERS = {
    "LINE": LineHandler(),
    "LWPOLYLINE": LWPolylineHandler(),
    "CIRCLE": CircleHandler(),
    "ARC": ArcHandler(),
    "SPLINE": SplineHandler(),
    "ELLIPSE": EllipseHandler(),
    "POINT": PointHandler(),
    "SOLID": SolidHandler(),
    "HATCH": HatchHandler(),
    "INSERT": InsertHandler(),
    "MTEXT": TextHandler(),
    "TEXT": TextHandler(),
    "POLYLINE": PolylineHandler(),
    "DEFAULT": DefaultHandler(),
}


def get_handler(entity_type: str) -> EntityHandler:
    return ENTITY_HANDLERS.get(entity_type, ENTITY_HANDLERS["DEFAULT"])
