"""Module of class instances."""
import logging
from typing import Dict, List

from src.classes import Pixel
from src.etl import Data

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Instance:
    """Class to define Instance"""

    def __init__(
        self,
        N: int,
        capacity_satellites: List[int],
        is_continuous_X: bool,
        alpha: float,
        beta: float,
        type_of_flexibility: str,
        scenarios: List[int],
        folder_path: str,
        periods: int = 12,
        M: int = 20,
        N_testing: int = 100,
    ):  # pylint: disable=too-many-arguments
        self.N_testing = N_testing
        self.capacity_satellites = capacity_satellites
        self.is_continuous_X = is_continuous_X
        self.alpha = alpha
        self.beta = beta
        self.type_of_flexibility = type_of_flexibility
        self.periods = periods
        self.N = N
        self.M = M
        self.folder_path = folder_path

        self.scenarios = scenarios
        self.satellites = self.__read_satellites()
        self.vehicles = self.__read_vehicles()
        self.pixels_by_scenarios = {
            str(id_scenario): self.__read_pixels(id_scenario)
            for id_scenario in scenarios
        }
        self.costs_by_scenarios = {
            str(id_scenario): self.__calculate_costs(
                self.pixels_by_scenarios[str(id_scenario)]
            )
            for id_scenario in scenarios
        }

    def __str__(self):
        return (
            f"Capacity of satellites: {self.capacity_satellites}\n"
            f"Is continuous X: {self.is_continuous_X}\n"
            f"Alpha: {self.alpha}\n"
            f"Beta: {self.beta}\n"
            f"Type of flexibility: {self.type_of_flexibility}\n"
            f"Periods: {self.periods}\n"
            f"M: {self.M}\n"
            f"Folder path: {self.folder_path}\n"
        )

    def __read_satellites(self) -> Dict:
        """Reads the satellites from the file."""
        try:
            satellites = Data.load_satellites()
        except FileNotFoundError as error:
            logger.error(f"[read satellites] File not found: {error}")
            raise error
        return satellites

    def __read_vehicles(self) -> Dict:
        """Reads the vehicles from the file."""
        try:
            vehicles = Data.load_vehicles()
        except FileNotFoundError as error:
            logger.error(f"[read vehicles] File not found: {error}")
            raise error
        return vehicles

    def __read_pixels(self, id_scenario: int) -> Dict:
        """Reads the pixels from the file."""
        try:
            pixels = Data.load_scenario(id_scenario=id_scenario)
        except FileNotFoundError as error:
            logger.error(f"[read pixels] File not found: {error}")
            raise error
        return pixels

    def __calculate_costs(self, pixels: Pixel) -> Dict:
        """Calculates the costs of the instance."""
        # TODO - implement the calculation of the costs
        try:
            costs = Data.load_costs()
        except FileNotFoundError as error:
            logger.error(f"[calculate costs] File not found: {error}")
            raise error
        return costs
