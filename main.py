import argparse
import logging
import ezdxf
import os
from typing import List, Dict

from nesters.genetic import GeneticNester
from nesters.rect import RectNester
from nesters.simple import SimpleNester
from nesters.skyline import SkylineNester
from nesters.utils import get_bin_utilization, get_bin_count
from shapes import Shape, Bin, Rectangle
from dxf_utils import extract_boundary_from_dxf, write_packed_shapes_to_dxf
from bom_utils import read_bom_csv


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
        "--rotation-steps", type=int, default=4, help="Number of rotation steps"
    )
    parser.add_argument(
        "--allow-flip", action="store_true", help="Allow flipping shapes"
    )
    parser.add_argument(
        "--sort-method",
        choices=["area", "height", "width", "perimeter"],
        default="area",
        help="Method to sort shapes",
    )
    parser.add_argument(
        "--placement-strategy",
        choices=["bottom_left", "best_short_side", "best_long_side"],
        default="bottom_left",
        help="Strategy for placing shapes",
    )
    parser.add_argument("--material", type=str, help="Material of the sheet")
    parser.add_argument("--thickness", type=float, help="Thickness of the sheet")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode (draw boundaries)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    args = parser.parse_args()

    # Configure logging
    logger = configure_logger(args.log_level)

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
                part.file_path, args.verbose
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

    if args.material:
        logger.info(f"Material: {args.material}")
    if args.thickness:
        logger.info(f"Thickness: {args.thickness} mm")

    # Write one DXF file per bin
    base_name, ext = os.path.splitext(args.output_file)
    for bin_index, bin in enumerate(bins):
        output_file = f"{base_name}-{bin_index + 1}{ext}"
        write_packed_shapes_to_dxf(bin, all_shapes, output_file, args.debug)
        logger.info(f"Packed shapes for Bin {bin_index} written to {output_file}")

    if any(error_summary.values()):
        logger.warning(
            "Warning: Some files were skipped or partially processed due to errors. See summary below:"
        )
        for error_type, errors in error_summary.items():
            if errors:
                logger.warning(f"  - {len(errors)} {error_type.replace('_', ' ')}(s)")
        logger.warning("Use the --verbose flag for more detailed information.")


if __name__ == "__main__":
    main()
