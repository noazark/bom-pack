import argparse
import logging
import ezdxf
import os
from typing import List, Dict

from .nesters.rect import RectNester
from .nesters.utils import get_bin_utilization, get_bin_count
from .shapes import Shape, Bin, Rectangle
from .dxf.io import extract_boundary_from_dxf, write_packed_shapes_to_dxf
from .bom_utils import read_bom_csv


def configure_logger(log_level: str):
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("bom-packer")
    logger.setLevel(log_level)
    return logger


def main():
    parser = argparse.ArgumentParser(
        description="Pack shapes from DXF files listed in a BOM CSV into rectangles."
    )
    parser.add_argument("bom_file", help="Input BOM CSV file")
    parser.add_argument("output_file", help="Base name for output DXF files")
    parser.add_argument(
        "-W", "--sheet-width", type=float, required=True, help="Sheet width"
    )
    parser.add_argument(
        "-H", "--sheet-height", type=float, required=True, help="Sheet height"
    )
    parser.add_argument(
        "--allow-flip", action="store_true", help="Allow flipping shapes"
    )
    parser.add_argument(
        "--draw-boundaries",
        action="store_true",
        help="Enable debug mode (draw boundaries)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times, e.g. -vvv)",
    )
    parser.add_argument(
        "-m",
        "--margin",
        type=float,
        default=0.125,
        help="Margin/kerf to apply around each shape (default: 0.125)",
    )

    args = parser.parse_args()

    # Map verbosity count to logging level
    verbosity_to_log_level = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }

    # Get the log level, defaulting to WARNING if verbosity is higher than expected
    log_level = verbosity_to_log_level.get(args.verbose, logging.DEBUG)

    # Configure logging
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("bom-packer")
    logger.setLevel(log_level)

    logger.info(f"Processing BOM file: {args.bom_file}")
    nester_config = {
        "bin_width": args.sheet_width,
        "bin_height": args.sheet_height,
        "allow_rotate": args.allow_flip,
    }

    parts = read_bom_csv(args.bom_file)
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
                part.file_path, args.margin
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

    if not all_shapes:
        logger.error("No valid shapes found. Exiting.")
        logger.error("Detailed error summary:")
        for error_type, errors in error_summary.items():
            if errors:
                logger.error(f"{error_type.replace('_', ' ').title()}:")
                for error in errors:
                    logger.error(f"  - {error}")
        logger.error(
            "Please check the BOM file and ensure all referenced DXF files exist and contain supported entities."
        )
        return

    nester = RectNester(nester_config)
    bins = nester.nest([shape.rectangle for shape in all_shapes])

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

    # Write one DXF file per bin
    base_name, ext = os.path.splitext(args.output_file)
    for bin_index, bin in enumerate(bins):
        output_file = f"{base_name}-{bin_index + 1}{ext}"
        write_packed_shapes_to_dxf(bin, all_shapes, output_file, args.draw_boundaries)
        logger.info(f"Packed shapes for Bin {bin_index} written to {output_file}")

    if any(error_summary.values()):
        logger.warning(
            "Warning: Some files were skipped or partially processed due to errors. See summary below:"
        )
        for error_type, errors in error_summary.items():
            if errors:
                logger.warning(f"  - {len(errors)} {error_type.replace('_', ' ')}(s)")


if __name__ == "__main__":
    main()
