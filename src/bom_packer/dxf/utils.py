import ezdxf
import math
import logging

# Configure the logger
logger = logging.getLogger(__name__)


def safe_vector_access(vector, index, default=0.0):
    try:
        return float(vector[index])
    except (IndexError, TypeError):
        return default


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
