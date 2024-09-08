import logging
import os
from typing import List, Dict, Tuple
import ezdxf
from bom_packer.shapes import Shape, Part
from bom_packer.nesters.rect import RectNester
from bom_packer.nesters.utils import get_bin_utilization, get_bin_count
from bom_packer.dxf.io import extract_boundary_from_dxf, write_packed_shapes_to_dxf
from bom_packer.bom_utils import read_bom_csv

logger = logging.getLogger(__name__)


def process_bom(
    bom_file: str,
    output_file: str,
    sheet_width: float,
    sheet_height: float,
    allow_flip: bool,
    draw_boundaries: bool,
    margin: float,
) -> None:
    logger.info(f"Processing BOM file: {bom_file}")
    nester_config = {
        "bin_width": sheet_width,
        "bin_height": sheet_height,
        "allow_rotate": allow_flip,
    }

    parts = read_bom_csv(bom_file)
    all_shapes, error_summary = process_parts(parts, margin)

    if not all_shapes:
        logger.error("No valid shapes found. Exiting.")
        log_error_summary(error_summary)
        return

    bins = nest_shapes(all_shapes, nester_config)
    log_nesting_results(bins, all_shapes)  # Pass all_shapes here
    write_output_files(bins, all_shapes, output_file, draw_boundaries)


def process_parts(
    parts: List[Part], margin: float
) -> Tuple[List[Shape], Dict[str, List[str]]]:
    all_shapes: List[Shape] = []
    error_summary: Dict[str, List[str]] = {
        "file_not_found": [],
        "dxf_structure_error": [],
        "no_valid_entities": [],
        "processing_errors": [],
    }

    for part in parts:
        try:
            rectangle, entities, summary = extract_boundary_from_dxf(
                part.file_path, margin
            )
            if rectangle is None:
                error_summary["no_valid_entities"].append(
                    f"{part.name} ({part.file_path})"
                )
                continue
            for _ in range(part.quantity):
                all_shapes.append(Shape(part, rectangle, entities))
            if summary["errors"]:
                error_summary["processing_errors"].extend(
                    [
                        f"{part.name} ({part.file_path}): {error}"
                        for error in summary["errors"]
                    ]
                )
        except ezdxf.DXFStructureError:
            error_summary["dxf_structure_error"].append(
                f"{part.name} ({part.file_path})"
            )
        except FileNotFoundError:
            error_summary["file_not_found"].append(f"{part.name} ({part.file_path})")

    return all_shapes, error_summary


def nest_shapes(all_shapes: List[Shape], nester_config: Dict) -> List:
    nester = RectNester(nester_config)
    return nester.nest([shape.rectangle for shape in all_shapes])


def log_nesting_results(bins: List, all_shapes: List[Shape]):
    logger.info("Packing complete. Results:")
    for bin_index, bin in enumerate(bins):
        logger.info(f"Bin {bin_index}:")
        for placement in bin.placements:
            shape = all_shapes[placement.shape_index]
            logger.info(f"  Shape {placement.shape_index} ({shape.part.name}):")
            logger.info(f"    Position: ({placement.x}, {placement.y})")
            logger.info(f"    Rotation: {placement.rotation}")

    logger.info(f"Total bins used: {get_bin_count(bins)}")
    logger.info(
        f"Bin utilization: {', '.join(f'{u*100:.2f}%' for u in get_bin_utilization(bins))}"
    )


def write_output_files(
    bins: List, all_shapes: List[Shape], output_file: str, draw_boundaries: bool
):
    base_name, ext = os.path.splitext(output_file)
    for bin_index, bin in enumerate(bins):
        output_file = f"{base_name}-{bin_index + 1}{ext}"
        write_packed_shapes_to_dxf(bin, all_shapes, output_file, draw_boundaries)
        logger.info(f"Packed shapes for Bin {bin_index} written to {output_file}")


def log_error_summary(error_summary: Dict[str, List[str]]):
    logger.error("Detailed error summary:")
    for error_type, errors in error_summary.items():
        if errors:
            logger.error(f"{error_type.replace('_', ' ').title()}:")
            for error in errors:
                logger.error(f"  - {error}")
    logger.error(
        "Please check the BOM file and ensure all referenced DXF files exist and contain supported entities."
    )
