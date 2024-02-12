"""Module for classes used in the application model."""
from typing import Dict, List


class Locatable:
    """Class for objects that have a location in the map."""

    # pylint: disable=too-few-public-methods

    def __init__(
        self,
        lon: float,
        lat: float,
    ):
        self.lon = lon
        self.lat = lat


class Pixel(Locatable):
    """Class for pixels in the map."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        id_pixel: str,
        lon: float,
        lat: float,
        area_surface: float,
        speed_intra_stop: Dict[str, float],
        k: float = 0.57,
    ):  # pylint: disable=too-many-arguments
        Locatable.__init__(
            self,
            lon,
            lat,
        )
        self.id_pixel = id_pixel
        self.area_surface = area_surface
        self.speed_intra_stop = speed_intra_stop
        self.demand_by_period = []
        self.drop_by_period = []
        self.stop_by_period = []
        self.k = k


class Satellite(Locatable):
    """Class for satellites in the map."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        id_satellite: str,
        lon: float,
        lat: float,
        distance_from_dc: float,
        travel_time_from_dc: float,
        travel_time_in_traffic_from_dc: float,
        capacity: Dict[str, float],
        cost_fixed: Dict[str, float],
        cost_operation: Dict[str, List[float]],
        cost_sourcing: float = 0.335
        / 2,  # TODO: Change this to a variable in the future
    ):  # pylint: disable=too-many-arguments
        Locatable.__init__(
            self,
            lon,
            lat,
        )
        self.id_satellite = id_satellite
        self.distance_from_dc = distance_from_dc
        self.travel_time_from_dc = travel_time_from_dc
        self.travel_time_in_traffic_from_dc = travel_time_in_traffic_from_dc
        self.cost_fixed = cost_fixed
        self.cost_operation = cost_operation
        self.cost_sourcing = cost_sourcing
        self.capacity = capacity


class Vehicle:
    """Class for vehicles."""

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        id_vehicle: str,
        type_vehicle: str,
        capacity: float,
        cost_fixed: float,
        time_service: float,
        time_fixed: float,
        time_dispatch: float,
        time_load: float,
        speed_line_haul: float,
        max_time_services: float,
        k: float,
    ):  # pylint: disable=too-many-arguments
        self.id_vehicle = id_vehicle
        self.type_vehicle = type_vehicle
        self.capacity = capacity
        self.cost_fixed = cost_fixed
        self.time_fixed = time_fixed
        self.time_service = time_service
        self.time_dispatch = time_dispatch
        self.time_load = time_load
        self.speed_line_haul = speed_line_haul
        self.max_time_services = max_time_services
        self.k = k
