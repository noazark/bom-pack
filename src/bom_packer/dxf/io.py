import ezdxf
import math
import logging
from typing import List, Tuple, Dict, Any
from ..shapes import Rectangle, Shape, Placement, Bin
from .entity_handlers import get_handler
from .utils import transform_point, safe_vector_access

# Configure the logger
logger = logging.getLogger(__name__)


def extract_boundary_from_dxf(
    filename: str, margin: float = 0.0
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
        handler = get_handler(entity_type)
        try:
            points = handler.get_points(entity)
            all_points.extend(points)
            if points:
                summary["supported"][entity_type] = (
                    summary["supported"].get(entity_type, 0) + 1
                )
            else:
                summary["unsupported"][entity_type] = (
                    summary["unsupported"].get(entity_type, 0) + 1
                )
        except Exception as e:
            summary["errors"].append(str(e))

    # Calculate the bounding rectangle with margin
    min_x = min(p[0] for p in all_points) - margin
    min_y = min(p[1] for p in all_points) - margin
    max_x = max(p[0] for p in all_points) + margin
    max_y = max(p[1] for p in all_points) + margin
    boundary = Rectangle(max_x - min_x, max_y - min_y)

    # Normalize the entities to the origin, considering the margin
    normalized_entities = normalize_entities(all_entities, min_x, min_y)

    return boundary, normalized_entities, summary


def normalize_entities(entities, min_x, min_y):
    return [get_handler(e.dxftype()).normalize(e, min_x, min_y) or e for e in entities]


def write_packed_shapes_to_dxf(
    bin: Bin,
    shapes: List[Shape],
    output_file: str,
    debug: bool = False,
):
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Set units to millimeters
    doc.header["$INSUNITS"] = 4

    # Group shapes by part name
    shape_groups = {}
    for placement in bin.placements:
        shape = shapes[placement.shape_index]
        part_name = shape.part.name
        if part_name not in shape_groups:
            shape_groups[part_name] = []
        shape_groups[part_name].append((shape, placement))

    # Process each group of shapes
    for part_name, group in shape_groups.items():
        # Add entities for each instance of this part type
        for i, (shape, placement) in enumerate(group, start=1):
            # Create a layer name for this specific instance
            layer_name = f"{part_name}_{i}"
            doc.layers.new(name=layer_name)

            for entity in shape.entities:
                new_entity = copy_and_transform_entity(entity, msp, placement)
                new_entity.dxf.layer = layer_name

            if debug:
                draw_boundary(msp, shape.rectangle, placement, layer_name)

    doc.saveas(output_file)


def copy_and_transform_entity(entity, target_layout, placement):
    handler = get_handler(entity.dxftype())
    try:
        return handler.copy_and_transform(entity, target_layout, placement)
    except ValueError as e:
        logger.warning(f"Skipping unsupported entity: {str(e)}")
        return None


def draw_boundary(msp, rectangle: Rectangle, placement: Placement, layer_name: str):
    points = [
        (0, 0),
        (rectangle.width, 0),
        (rectangle.width, rectangle.height),
        (0, rectangle.height),
    ]

    transformed_points = [transform_point(p, placement) for p in points]
    logger.debug(f"Drawing boundary with transformed points: {transformed_points}")

    msp.add_lwpolyline(
        transformed_points + [transformed_points[0]],
        dxfattribs={
            "layer": f"DEBUG_{layer_name}",
            "color": 1,  # 1 is the AutoCAD color code for red
        },
    )
