"""Module to define the configuration of the CA"""
import logging
import math
from typing import Any, Dict, Tuple

from src.classes import Pixel, Satellite, Vehicle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ContinuousApproximationConfig:
    """Class to define the configuration of the CA"""

    def __init__(
        self,
        periods: int,
        small_vehicle: Vehicle,
        large_vehicle: Vehicle,
    ) -> None:
        self.periods = periods
        self.small_vehicle = small_vehicle
        self.large_vehicle = large_vehicle

    def __avg_fleet_size(
        self, pixel: Pixel, vehicle: Vehicle, t: int, distance: float
    ) -> Dict[str, float]:
        """Calculate the average fleet size for a pixel in a period of time"""
        if (
            pixel.drop_by_period[t] <= 0
            or pixel.stop_by_period[t] <= 0
            or pixel.demand_by_period[t] <= 0
        ):
            logger.warning(
                f"[CA] Pixel {pixel.id_pixel} in period {t} has no demand or no stops or no drops"
            )
            return {
                "fleet_size": 0,
                "avg_tour_time": 0,
                "fully_loaded_tours": 0,
                "effective_capacity": 0,
                "demand_served": pixel.demand_by_period[t],
                "avg_drop": pixel.drop_by_period[t],
                "avg_stop": pixel.stop_by_period[t],
                "avg_time": 0,
                "avg_time_dispatch": 0,
                "avg_time_line_haul": 0,
            }

        # effective vehicle capacity
        effective_vehicle_capacity = vehicle.capacity / pixel.drop_by_period[t]

        # time services
        time_services = (
            vehicle.time_fixed + vehicle.time_service * pixel.drop_by_period[t]
        )

        # time intra stop
        time_intra_stop = (vehicle.k * pixel.k) / (
            pixel.speed_intra_stop[vehicle.type_vehicle]
            * math.sqrt(pixel.drop_by_period[t] / pixel.area_surface)
        )

        # average tour time
        avg_tour_time = effective_vehicle_capacity * (time_services + time_intra_stop)

        # time preparing
        time_preparing_dispatch = (
            vehicle.time_dispatch
            + effective_vehicle_capacity * pixel.drop_by_period[t] * vehicle.time_load
        )

        # time line_haul
        time_line_haul = 2 * (distance * vehicle.k / vehicle.speed_line_haul)

        # number of fully loaded tours
        beta = vehicle.max_time_services / (
            avg_tour_time + time_preparing_dispatch + time_line_haul
        )
        avg_time = avg_tour_time + time_preparing_dispatch + time_line_haul

        # average fleet size
        numerador = pixel.stop_by_period[t]
        denominador = beta * effective_vehicle_capacity
        v = (numerador / denominador) if denominador > 0 else 0.0

        return {
            "fleet_size": v,
            "avg_tour_time": avg_tour_time,
            "fully_loaded_tours": beta,
            "effective_capacity": effective_vehicle_capacity,
            "demand_served": pixel.demand_by_period[t],
            "avg_drop": pixel.drop_by_period[t],
            "avg_stop": pixel.stop_by_period[t],
            "avg_time": avg_time,
            "avg_time_dispatch": time_preparing_dispatch,
            "avg_time_line_haul": time_line_haul,
        }

    def calculate_avg_fleet_size_from_satellites(
        self,
        pixels: Dict[str, Pixel],
        distances_line_haul: Dict[Any, float],
        satellites: Dict[str, Satellite],
    ) -> Dict[Any, float]:
        """Calculate the average fleet size for a pixel in a period of time"""
        logger.info("[CA] Estimation of fleet size running for satellites")
        fleet_size = dict(
            [
                (
                    (s, k, t),
                    self.__avg_fleet_size(
                        pixel, self.small_vehicle, t, distances_line_haul[(s, k)]
                    ),
                )
                for t in range(self.periods)
                for s in satellites.keys()
                for k, pixel in pixels.items()
            ]
        )
        return fleet_size

    def calculate_avg_fleet_size_from_dc(
        self,
        pixels: Dict[str, Pixel],
        distances_line_haul: Dict[str, float],
    ) -> Dict[Any, float]:
        """Calculate the average fleet size for a pixel in a period of time"""
        logger.info("[CA] Estimation of fleet size running for DC")
        fleet_size = dict(
            [
                (
                    (k, t),
                    self.__avg_fleet_size(
                        pixel, self.large_vehicle, t, distances_line_haul[k]
                    ),
                )
                for t in range(self.periods)
                for k, pixel in pixels.items()
            ]
        )
        return fleet_size


def cost_satellite_to_pixel(
    satellites: Dict[str, Satellite],
    pixels: Dict[str, Pixel],
    vehicle: Vehicle,
    periods: int,
    fleet_size_required: Dict[Tuple[str, str], float],
) -> Dict[Tuple[str, str, int], float]:
    """Calculate the cost from satellite to pixel by period"""
    costs = {}
    for t in range(periods):
        for k, pixel in pixels.items():
            for s, satellite in satellites.items():
                cost_first_level = satellite.cost_sourcing * pixel.demand_by_period[t]
                cost_shipping = 0  # TODO cost_shipping_satellite[(s, k)] * pixel.demand_by_period[t]
                cost_vehicles = (
                    vehicle.cost_fixed * fleet_size_required[(s, k, t)]["fleet_size"]
                )

                total_cost = cost_first_level + cost_shipping + cost_vehicles
                costs[(s, k, t)] = {
                    "total": total_cost,
                    "first_level": cost_first_level,
                    "shipping": cost_shipping,
                    "vehicles": cost_vehicles,
                }
    return costs


def cost_dc_to_pixel(
    pixels: Dict[str, Pixel],
    periods: int,
    vehicle: Vehicle,
    fleet_size_required: Dict[str, dict],
) -> Dict[Any, float]:
    """Calculate the cost from DC to pixel by period"""
    costs = {}
    for t in range(periods):
        for k in pixels.keys():
            cost_shipping = 0  # TODO cost_shipping_dc[k] * pixel.demand_by_period[t]
            cost_vehicles = (
                vehicle.cost_fixed * fleet_size_required[(k, t)]["fleet_size"]
            )

            total_cost = cost_shipping + cost_vehicles
            costs[(k, t)] = {
                "total": total_cost,
                "shipping": cost_shipping,
                "vehicles": cost_vehicles,
            }
    return costs


def get_cost_from_continuous_approximation(
    pixels: Dict[str, Pixel],
    satellites: Dict[str, Satellite],
    vehicles: Dict[str, Vehicle],
    fleet_size_required: Dict[Any, Dict],
    periods: int,
) -> Dict[str, Dict]:
    """
    Calculate the cost of serving a pixel by period
    ----
    returns:
    - Dict[str, Dict]
        the cost of serving a pixel by period, where the key is the echelon dc or satellite
    """
    cost_satellite_to_pixel_period = cost_satellite_to_pixel(
        satellites=satellites,
        pixels=pixels,
        vehicle=vehicles["small"],
        periods=periods,
        fleet_size_required=fleet_size_required["satellite"],
    )
    cost_dc_to_pixel_period = cost_dc_to_pixel(
        pixels=pixels,
        periods=periods,
        vehicle=vehicles["large"],
        fleet_size_required=fleet_size_required["dc"],
    )
    return {
        "dc": cost_dc_to_pixel_period,
        "satellite": cost_satellite_to_pixel_period,
    }
