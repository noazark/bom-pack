# bom-packer

bom-packer is a lightweight, efficient tool designed to pack DXF part files onto material sheets for laser cutting projects. It's perfect for hobbyists and makers who want to optimize their material usage without the complexity and cost of commercial nesting software.

## Key Features

- Supports DXF file format for parts
- Designed for integration into headless pipelines, enabling automated workflows
- Open-source and free to use

## Ideal For

- Hobby laser cutting projects
- Makers and DIY enthusiasts
- Small-scale production runs
- Anyone looking for a straightforward, no-frills nesting solution

## Why bom-packer?

Unlike expensive, complex, or outdated alternatives, bom-packer offers a streamlined approach to part nesting. It's built with automated workflows in mind, allowing for easy integration into your existing processes without the need for a graphical interface.

## Potential Future Features

- Support for additional file formats (e.g., SVG)
- Advanced optimization algorithms for minimizing material waste:
  - Genetic algorithms for evolving optimal nesting arrangements
  - Simulated annealing for finding near-optimal solutions in large search
    spaces
  - No-fit polygon techniques for handling irregular shapes more efficiently
  - Heuristic approaches like bottom-left fill with various sorting criteria
  - Constraint programming for complex nesting problems with multiple
    constraints
- Support for different units of measurement, currently only millimeters are
  supported
- Integration with CAD software

## Installation

bom-packer is currently not distributed on PyPI or other package repositories. To use it, you'll need to clone the repository and install it locally. This method ensures you have the latest development version and allows for easy updates.

### Prerequisites

- [asdf](https://asdf-vm.com/) version manager

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/noazark/bom-packer.git
   cd bom-packer
   ```

2. Install Python and pdm using asdf:
   ```
   asdf install
   ```

3. Install project dependencies:
   ```
   pdm install
   ```

4. Test bom-packer on the example files:
   ```
   bom examples/bom.csv examples/output.dxf --sheet-width 300 --sheet-height 300
   ```

This command will process the example BOM file, arrange the parts on a 300x300mm sheet, and output the result to `examples/output-1.dxf`.

