import argparse
import logging
from bom_packer.core import process_bom


def configure_logger(verbosity: int) -> None:
    log_level = max(logging.ERROR - verbosity * 10, logging.DEBUG)
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("bom-packer")
    logger.setLevel(log_level)


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

    configure_logger(args.verbose)

    process_bom(
        args.bom_file,
        args.output_file,
        args.sheet_width,
        args.sheet_height,
        args.allow_flip,
        args.draw_boundaries,
        args.margin,
    )


if __name__ == "__main__":
    main()
