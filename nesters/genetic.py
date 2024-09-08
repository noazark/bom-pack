import random
from typing import List, Tuple, Optional
import logging
import multiprocessing as mp

from shapes import Rectangle, Placement, Bin

logger = logging.getLogger(__name__)


class GeneticNester:
    def __init__(self, config: dict):
        self.default_bin_size = Rectangle(config["bin_width"], config["bin_height"])
        self.config = {
            "population_size": config.get("population_size", 50),
            "generations": config.get("generations", 100),
            "mutation_rate": config.get("mutation_rate", 0.1),
            "rotation_steps": config.get("rotation_steps", 4),
            "allow_flip": config.get("allow_flip", True),
            "num_processes": config.get("num_processes", mp.cpu_count()),
        }

    def nest(self, shapes: List[Rectangle]) -> List[Bin]:
        self.shapes = shapes
        population = self.initialize_population(len(shapes))
        best_solution = None
        best_fitness = 0
        best_bin_count = float("inf")

        logger.info(f"Starting genetic algorithm with {len(shapes)} shapes")
        logger.info(f"Population size: {self.config['population_size']}")
        logger.info(f"Number of generations: {self.config['generations']}")
        logger.info(f"Mutation rate: {self.config['mutation_rate']}")
        logger.info(f"Number of processes: {self.config['num_processes']}")

        with mp.Pool(processes=self.config["num_processes"]) as pool:
            for generation in range(self.config["generations"]):
                fitness_scores = pool.map(self.calculate_fitness, population)
                current_best = max(fitness_scores)
                current_best_index = fitness_scores.index(current_best)
                current_best_solution = population[current_best_index]
                current_bin_count = len(
                    self.create_bins_from_solution(current_best_solution)
                )

                if current_best > best_fitness or (
                    current_best == best_fitness and current_bin_count < best_bin_count
                ):
                    best_solution = current_best_solution
                    best_fitness = current_best
                    best_bin_count = current_bin_count

                logger.info(
                    f"Generation {generation + 1}/{self.config['generations']}:"
                )
                logger.info(f"  Best fitness: {best_fitness:.4f}")
                logger.info(f"  Best bin count: {best_bin_count}")
                logger.info(f"  Current best fitness: {current_best:.4f}")
                logger.info(f"  Current best bin count: {current_bin_count}")

                new_population = [best_solution]  # Elitism
                while len(new_population) < self.config["population_size"]:
                    parent1, parent2 = pool.map(
                        self.select_parent, [(population, fitness_scores)] * 2
                    )
                    child = self.crossover(parent1, parent2)
                    if random.random() < self.config["mutation_rate"]:
                        child = self.mutate(child)
                    new_population.append(child)

                population = new_population

        logger.info("Genetic algorithm completed")
        logger.info(f"Final best fitness: {best_fitness:.4f}")
        logger.info(f"Final best bin count: {best_bin_count}")

        return self.create_bins_from_solution(best_solution)

    def initialize_population(
        self, num_shapes: int
    ) -> List[List[Tuple[int, float, bool]]]:
        return [
            [(i, 0, False) for i in range(num_shapes)]
            for _ in range(self.config["population_size"])
        ]

    def calculate_fitness(self, solution: List[Tuple[int, float, bool]]) -> float:
        bins = self.create_bins_from_solution(solution)
        total_area = sum(bin.width * bin.height for bin in bins)
        used_area = sum(sum(p.width * p.height for p in bin.placements) for bin in bins)
        return used_area / total_area

    def select_parent(
        self, args: Tuple[List[List[Tuple[int, float, bool]]], List[float]]
    ) -> List[Tuple[int, float, bool]]:
        population, fitness_scores = args
        total_fitness = sum(fitness_scores)
        pick = random.uniform(0, total_fitness)
        current = 0
        for solution, fitness in zip(population, fitness_scores):
            current += fitness
            if current > pick:
                return solution
        return population[-1]

    def crossover(
        self,
        parent1: List[Tuple[int, float, bool]],
        parent2: List[Tuple[int, float, bool]],
    ) -> List[Tuple[int, float, bool]]:
        crossover_point = random.randint(0, len(parent1) - 1)
        return parent1[:crossover_point] + parent2[crossover_point:]

    def mutate(
        self, solution: List[Tuple[int, float, bool]]
    ) -> List[Tuple[int, float, bool]]:
        index = random.randint(0, len(solution) - 1)
        shape_index, rotation, flip = solution[index]

        if self.config["rotation_steps"] > 1 and random.random() < 0.5:
            new_rotation = random.randint(0, self.config["rotation_steps"] - 1) * (
                360 / self.config["rotation_steps"]
            )
            solution[index] = (shape_index, new_rotation, flip)
        elif self.config["allow_flip"]:
            solution[index] = (shape_index, rotation, not flip)

        return solution

    def create_bins_from_solution(
        self, solution: List[Tuple[int, float, bool]]
    ) -> List[Bin]:
        bins = [Bin(self.default_bin_size.width, self.default_bin_size.height)]

        for shape_index, rotation, flip in solution:
            shape = self.shapes[shape_index]
            width = shape.height if flip else shape.width
            height = shape.width if flip else shape.height

            placed = False
            for bin in bins:
                placement = self.find_best_placement_in_bin(
                    width, height, rotation, bin
                )
                if placement:
                    placement.shape_index = shape_index
                    bin.placements.append(placement)
                    placed = True
                    break

            if not placed:
                new_bin = Bin(self.default_bin_size.width, self.default_bin_size.height)
                placement = Placement(0, 0, width, height, rotation)
                placement.shape_index = shape_index
                new_bin.placements.append(placement)
                bins.append(new_bin)

        return bins

    def find_best_placement_in_bin(
        self, width: float, height: float, rotation: float, bin: Bin
    ) -> Optional[Placement]:
        best_placement = None
        min_y = float("inf")
        min_x = float("inf")

        for y in range(0, int(bin.height), max(1, int(height / 2))):
            for x in range(0, int(bin.width), max(1, int(width / 2))):
                placement = Placement(x, y, width, height, rotation)
                if self.is_valid_placement(bin, placement):
                    if y < min_y or (y == min_y and x < min_x):
                        best_placement = placement
                        min_y = y
                        min_x = x
                    return best_placement  # Return the first valid placement found

        return best_placement

    def is_valid_placement(self, bin: Bin, placement: Placement) -> bool:
        if (
            placement.x + placement.width > bin.width
            or placement.y + placement.height > bin.height
        ):
            return False
        for existing_placement in bin.placements:
            if self.overlaps(placement, existing_placement):
                return False
        return True

    def overlaps(self, a: Placement, b: Placement) -> bool:
        return (
            a.x < b.x + b.width
            and a.x + a.width > b.x
            and a.y < b.y + b.height
            and a.y + a.height > b.y
        )
