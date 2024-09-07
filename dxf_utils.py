import ezdxf
import math
from typing import List, Tuple, Dict, Any
from shapes import Rectangle, Shape, Placement


def safe_vector_access(vector, index, default=0.0):
    try:
        return float(vector[index])
    except (IndexError, TypeError):
        return default


def extract_boundary_from_dxf(
    filename: str, verbose: bool = False
) -> Tuple[Rectangle, List[ezdxf.entities.DXFEntity], Dict[str, Any]]:
    doc = ezdxf.readfile(filename)
    msp = doc.modelspace()
    all_entities = list(msp)
    all_points = []
    summary = {
        "supported": {},
        "unsupported": {},
        "total_entities": len(all_entities),
        "errors": [],
    }

    for entity in all_entities:
        entity_type = entity.dxftype()
        try:
            if entity_type in ["LINE", "LWPOLYLINE", "CIRCLE", "ARC"]:
                points = get_entity_points(entity)
                all_points.extend(points)
                summary["supported"][entity_type] = (
                    summary["supported"].get(entity_type, 0) + 1
                )
            else:
                summary["unsupported"][entity_type] = (
                    summary["unsupported"].get(entity_type, 0) + 1
                )
        except Exception as e:
            summary["errors"].append(str(e))

    # Calculate the bounding rectangle
    min_x = min(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_x = max(p[0] for p in all_points)
    max_y = max(p[1] for p in all_points)
    boundary = Rectangle(max_x - min_x, max_y - min_y)

    return boundary, all_entities, summary


def get_entity_points(entity):
    if entity.dxftype() == "LINE":
        return [
            (
                safe_vector_access(entity.dxf.start, 0),
                safe_vector_access(entity.dxf.start, 1),
            ),
            (
                safe_vector_access(entity.dxf.end, 0),
                safe_vector_access(entity.dxf.end, 1),
            ),
        ]
    elif entity.dxftype() == "LWPOLYLINE":
        return [
            (safe_vector_access(vertex, 0), safe_vector_access(vertex, 1))
            for vertex in entity.get_points()
        ]
    elif entity.dxftype() == "CIRCLE":
        center = (
            safe_vector_access(entity.dxf.center, 0),
            safe_vector_access(entity.dxf.center, 1),
        )
        radius = entity.dxf.radius
        return [
            (center[0] + radius, center[1]),
            (center[0] - radius, center[1]),
            (center[0], center[1] + radius),
            (center[0], center[1] - radius),
        ]
    elif entity.dxftype() == "ARC":
        center = (
            safe_vector_access(entity.dxf.center, 0),
            safe_vector_access(entity.dxf.center, 1),
        )
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        start_point = (
            center[0] + radius * math.cos(start_angle),
            center[1] + radius * math.sin(start_angle),
        )
        end_point = (
            center[0] + radius * math.cos(end_angle),
            center[1] + radius * math.sin(end_angle),
        )
        return [start_point, end_point, center]


def write_packed_shapes_to_dxf(
    shapes: List[Shape],
    placements: List[Placement],
    output_file: str,
    debug: bool = False,
):
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Group shapes by part name
    shape_groups = {}
    for shape, placement in zip(shapes, placements):
        part_name = shape.part.name
        if part_name not in shape_groups:
            shape_groups[part_name] = []
        shape_groups[part_name].append((shape, placement))

    # Process each group of shapes
    for part_name, group in shape_groups.items():
        # Add entities for each instance of this part type
        for i, (shape, placement) in enumerate(group, start=1):
            # Create a layer name for this specific instance
            layer_name = f"{part_name} #{i}"
            doc.layers.new(name=layer_name)

            for entity in shape.entities:
                new_entity = copy_entity(entity, msp)
                transform_entity(new_entity, placement)
                new_entity.dxf.layer = layer_name

            if debug:
                draw_boundary(msp, shape.rectangle, placement, layer_name)

    doc.saveas(output_file)


def copy_entity(entity, target_layout):
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        return target_layout.add_line(
            start=(
                safe_vector_access(entity.dxf.start, 0),
                safe_vector_access(entity.dxf.start, 1),
            ),
            end=(
                safe_vector_access(entity.dxf.end, 0),
                safe_vector_access(entity.dxf.end, 1),
            ),
        )
    elif dxftype == "LWPOLYLINE":
        return target_layout.add_lwpolyline(entity.get_points())
    elif dxftype == "CIRCLE":
        return target_layout.add_circle(
            center=(
                safe_vector_access(entity.dxf.center, 0),
                safe_vector_access(entity.dxf.center, 1),
            ),
            radius=entity.dxf.radius,
        )
    elif dxftype == "ARC":
        return target_layout.add_arc(
            center=(
                safe_vector_access(entity.dxf.center, 0),
                safe_vector_access(entity.dxf.center, 1),
            ),
            radius=entity.dxf.radius,
            start_angle=entity.dxf.start_angle,
            end_angle=entity.dxf.end_angle,
        )
    else:
        raise ValueError(f"Unsupported entity type: {dxftype}")


def transform_entity(entity, placement):
    rotation_rad = math.radians(placement.rotation)
    cos_rot = math.cos(rotation_rad)
    sin_rot = math.sin(rotation_rad)

    if entity.dxftype() == "LINE":
        entity.dxf.start = transform_point(
            entity.dxf.start, placement, cos_rot, sin_rot
        )
        entity.dxf.end = transform_point(entity.dxf.end, placement, cos_rot, sin_rot)
    elif entity.dxftype() == "LWPOLYLINE":
        new_points = [
            transform_point(p, placement, cos_rot, sin_rot) for p in entity.get_points()
        ]
        entity.set_points(new_points)
    elif entity.dxftype() in ["CIRCLE", "ARC"]:
        entity.dxf.center = transform_point(
            entity.dxf.center, placement, cos_rot, sin_rot
        )
        if entity.dxftype() == "ARC":
            entity.dxf.start_angle += placement.rotation
            entity.dxf.end_angle += placement.rotation


def transform_point(point, placement, cos_rot, sin_rot):
    x, y = safe_vector_access(point, 0), safe_vector_access(point, 1)
    x_rot = x * cos_rot - y * sin_rot
    y_rot = x * sin_rot + y * cos_rot
    return (x_rot + placement.x, y_rot + placement.y)


def draw_boundary(msp, rectangle: Rectangle, placement: Placement, layer_name: str):
    points = [
        (0, 0),
        (rectangle.width, 0),
        (rectangle.width, rectangle.height),
        (0, rectangle.height),
        (0, 0),
    ]

    transformed_points = [
        transform_point(
            p,
            placement,
            math.cos(math.radians(placement.rotation)),
            math.sin(math.radians(placement.rotation)),
        )
        for p in points
    ]

    msp.add_lwpolyline(transformed_points, dxfattribs={"layer": f"DEBUG_{layer_name}"})
