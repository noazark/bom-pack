import argparse
import ezdxf
from typing import List, Dict

from nester import SimpleNester
from shapes import Shape, Rectangle, Part
from dxf_utils import extract_boundary_from_dxf, write_packed_shapes_to_dxf
from bom_utils import read_bom_csv


def main():
    parser = argparse.ArgumentParser(
        description="Pack shapes from DXF files listed in a BOM CSV into rectangles."
    )
    parser.add_argument("bom_file", help="Input BOM CSV file")
    parser.add_argument("output_file", help="Output DXF file")
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
    args = parser.parse_args()

    nester_config = {
        "bin_width": args.sheet_width,
        "bin_height": args.sheet_height,
        "rotation_steps": args.rotation_steps,
        "allow_flip": args.allow_flip,
        "sort_method": args.sort_method,
        "placement_strategy": args.placement_strategy,
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
        print("Error: No valid shapes found. Exiting.")
        print("\nDetailed error summary:")
        for error_type, errors in error_summary.items():
            if errors:
                print(f"\n{error_type.replace('_', ' ').title()}:")
                for error in errors:
                    print(f"  - {error}")
        print(
            "\nPlease check the BOM file and ensure all referenced DXF files exist and contain supported entities."
        )
        return

    nester = SimpleNester(nester_config)
    placements = nester.nest([shape.rectangle for shape in all_shapes])

    print("\nPacking complete. Results:")
    for i, (shape, placement) in enumerate(zip(all_shapes, placements)):
        print(f"Shape {i} ({shape.part.name}):")
        print(f"  Bin: {placement.bin_index}")
        print(f"  Position: ({placement.x}, {placement.y})")
        print(f"  Rotation: {placement.rotation}")

    print(f"\nTotal bins used: {nester.get_bin_count()}")
    print(
        f"Bin utilization: {', '.join(f'{u*100:.2f}%' for u in nester.get_bin_utilization())}"
    )

    if args.material:
        print(f"Material: {args.material}")
    if args.thickness:
        print(f"Thickness: {args.thickness} mm")

    write_packed_shapes_to_dxf(all_shapes, placements, args.output_file, args.debug)
    print(f"\nPacked shapes written to {args.output_file}")

    if any(error_summary.values()):
        print(
            "\nWarning: Some files were skipped or partially processed due to errors. See summary below:"
        )
        for error_type, errors in error_summary.items():
            if errors:
                print(f"  - {len(errors)} {error_type.replace('_', ' ')}(s)")
        print("Use the --verbose flag for more detailed information.")


if __name__ == "__main__":
    main()
