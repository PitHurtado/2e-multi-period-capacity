"""Module of class instances."""
import logging
import sys
from typing import Dict, List

from src.classes import Pixel, Satellite
from src.continuous_approximation.fleet_size import ContinuousApproximationConfig
from src.etl import Data

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

FEE_COST_FROM_DC = 0.264
FEE_COST_FROM_SATELLITE = 0.264


class Instance:
    """Class to define Instance"""

    def __init__(
        self,
        id_instance: str,
        N: int,
        capacity_satellites: List[int],
        is_continuous_X: bool,
        alpha: float,
        beta: float,
        type_of_flexibility: str,
        id_scenarios: List[int],
        folder_path: str,
        periods: int = 12,
        M: int = 20,
        N_testing: int = 100,
    ):  # pylint: disable=too-many-arguments
        self.id_instance = id_instance
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

        self.id_scenarios = id_scenarios
        self.satellites: Dict[str, Satellite] = self.__read_satellites()
        self.vehicles = self.__read_vehicles()

        # create instance of continuous approximation
        self.computer_fleet_size = ContinuousApproximationConfig(
            periods=12,
            small_vehicle=self.vehicles["small"],
            large_vehicle=self.vehicles["large"],
        )

        # read pixels and calculate fleet size required
        self.pixels_by_scenarios = {
            str(id_scenario): self.__read_pixels(id_scenario)
            for id_scenario in id_scenarios
        }
        self.fleet_size_required_by_scenarios = {
            str(id_scenario): self.__calculate_fleet_size_required(
                self.pixels_by_scenarios[str(id_scenario)]
            )
            for id_scenario in id_scenarios
        }
        self.costs_shipping_by_scenarios = {
            str(id_scenario): self.__calculate_costs_shipping(
                self.pixels_by_scenarios[str(id_scenario)],
            )
            for id_scenario in id_scenarios
        }
        self.costs_by_scenarios = {
            str(id_scenario): self.__calculate_costs(
                self.pixels_by_scenarios[str(id_scenario)],
                self.fleet_size_required_by_scenarios[str(id_scenario)],
                self.costs_shipping_by_scenarios[str(id_scenario)],
            )
            for id_scenario in id_scenarios
        }
        self.periods = 12

        self.__update_instance()

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

    def __calculate_fleet_size_required(self, pixels: Pixel) -> Dict:
        """Calculates the fleet size required for the instance."""
        try:
            matrix_satellite_pixels = Data.load_matrix_from_satellite()
            matrix_dc_pixels = Data.load_matrix_from_dc()

            # compute fleet size required from satellite to pixel
            fleet_size_from_satellites = (
                self.computer_fleet_size.calculate_avg_fleet_size_from_satellites(
                    pixels=pixels,
                    distances_line_haul=matrix_satellite_pixels["distance"],
                    satellites=self.satellites,
                )
            )
            fleet_size_from_dc = (
                self.computer_fleet_size.calculate_avg_fleet_size_from_dc(
                    pixels=pixels,
                    distances_line_haul=matrix_dc_pixels["distance"],
                )
            )
        except FileNotFoundError as error:
            logger.error(f"[calculate fleet size required] File not found: {error}")
            raise error
        fleet_size_required = {
            "small": fleet_size_from_satellites,
            "large": fleet_size_from_dc,
        }
        return fleet_size_required

    def __calculate_costs(
        self, pixels: Pixel, fleet_size_required: Dict, cost_shipping: Dict
    ) -> Dict:
        """Calculates the costs of the instance."""
        try:
            costs = self.computer_fleet_size.cost_serving(
                pixels=pixels,
                satellites=self.satellites,
                vehicles_required=fleet_size_required,
                cost_shipping=cost_shipping,
            )
        except Exception as error:
            logger.error(f"[calculate costs] File not found: {error}")
            raise error
        return costs

    def __calculate_costs_shipping(self, pixels: Pixel) -> Dict:
        """Calculates the costs of the instance."""

        def calculate_avg_distance_from_dc(matrix_distance, pixels) -> dict:
            distance_average_from_dc = {}
            min_distances, max_distances = sys.maxsize, -sys.maxsize - 1
            for k in pixels.keys():
                min_distances = (
                    min_distances
                    if matrix_distance["distance"][(k)] > min_distances
                    else matrix_distance["distance"][(k)]
                )
                max_distances = (
                    max_distances
                    if matrix_distance["distance"][(k)] < max_distances
                    else matrix_distance["distance"][(k)]
                )
            distance_average_from_dc = {
                "min": min_distances,
                "max": max_distances,
                "interval": max_distances - min_distances,
                "cost": 0.389 - 0.264,
            }
            return distance_average_from_dc

        def calculate_avg_distance_from_satellites(
            matrix_distance, satellites, pixels
        ) -> dict:
            distance_average_from_satellites = {}
            for s in satellites.keys():
                min_distances, max_distances = sys.maxsize, -sys.maxsize - 1
                for k in pixels.keys():
                    min_distances = (
                        min_distances
                        if matrix_distance["distance"][(s, k)] > min_distances
                        else matrix_distance["distance"][(s, k)]
                    )
                    max_distances = (
                        max_distances
                        if matrix_distance["distance"][(s, k)] < max_distances
                        else matrix_distance["distance"][(s, k)]
                    )
                distance_average_from_satellites[s] = {
                    "min": min_distances,
                    "max": max_distances,
                    "interval": max_distances - min_distances,
                    "cost": 0.421 - 0.335,
                }
            return distance_average_from_satellites

        def calculate_cost_shipping_from_satellites(
            matrix_distance, satellites, pixels, fee_cost_from_satellites
        ) -> dict:
            distance_average_from_satellites = calculate_avg_distance_from_satellites(
                matrix_distance, satellites, pixels
            )
            cost_shipping_from_satellites = dict(
                [
                    (
                        (s, k),
                        distance_average_from_satellites[(s)]["cost"]
                        / distance_average_from_satellites[(s)]["interval"]
                        * (
                            matrix_distance["distance"][(s, k)]
                            - distance_average_from_satellites[(s)]["min"]
                        )
                        + fee_cost_from_satellites,
                    )
                    for s in satellites.keys()
                    for k in pixels.keys()
                ]
            )
            return cost_shipping_from_satellites

        def calculate_cost_shipping_from_dc(
            matrix_distance, pixels, fee_cost_from_dc
        ) -> dict:
            distance_average_from_dc = calculate_avg_distance_from_dc(
                matrix_distance, pixels
            )
            cost_shipping_from_dc = dict(
                [
                    (
                        k,
                        distance_average_from_dc["cost"]
                        / distance_average_from_dc["interval"]
                        * (
                            matrix_distance["distance"][(k)]
                            - distance_average_from_dc["min"]
                        )
                        + fee_cost_from_dc,
                    )
                    for k in pixels.keys()
                ]
            )
            return cost_shipping_from_dc

        try:
            matrix_dc_pixels = Data.load_matrix_from_dc()
            cost_shipping_from_dc = calculate_cost_shipping_from_dc(
                matrix_distance=matrix_dc_pixels,
                pixels=pixels,
                fee_cost_from_dc=FEE_COST_FROM_DC,
            )
            matrix_satellite_pixels = Data.load_matrix_from_satellite()
            cost_shipping_from_satellites = calculate_cost_shipping_from_satellites(
                matrix_distance=matrix_satellite_pixels,
                satellites=self.satellites,
                pixels=pixels,
                fee_cost_from_satellites=FEE_COST_FROM_SATELLITE,
            )
        except Exception as error:
            logger.error(f"[calculate costs shipping] File not found: {error}")
            raise error
        return {"dc": cost_shipping_from_dc, "satellite": cost_shipping_from_satellites}

    def get_scenarios(self) -> Dict:
        """Get the scenarios."""
        scenarios = {}
        for id_scenario in self.id_scenarios:
            scenarios[str(id_scenario)] = dict(
                {
                    "pixels": self.pixels_by_scenarios[str(id_scenario)],
                    "costs": self.costs_by_scenarios[str(id_scenario)],
                }
            )
        return scenarios

    def __update_instance(self):
        """Update the instance."""

        # (1) Update the capacity of the satellites:
        for satellite in self.satellites.values():
            satellite.capacity = {
                str(capacity): capacity for capacity in self.capacity_satellites
            }

        # (2) Update the costs of the pixels (ALPHA):

        # (3) Update the costs of the satellites (BETA):
