"""Module to get data from csv file"""
import json
import logging
import os
import sys
from typing import Dict

import pandas as pd

from src.classes import Pixel, Satellite, Vehicle
from src.constants import (
    PATH_DATA_DISTANCES_FROM_DC,
    PATH_DATA_DISTANCES_FROM_SATELLITES,
    PATH_DATA_PIXEL,
    PATH_DATA_SATELLITE,
    PATH_ROOT_SCENARIO,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Data:
    """Class to get data from csv file"""

    @staticmethod
    def load_satellites(
        show_data: bool = False,
    ) -> Dict[str, Satellite]:
        """Load data from csv file and create a dictionary of satellites"""
        satellites = {}
        if not os.path.isfile(PATH_DATA_SATELLITE):
            logger.error(f"File {PATH_DATA_SATELLITE} not found")
            sys.exit(1)
        logger.info(f"Loading data from satellites from path {PATH_DATA_SATELLITE}")
        df = pd.read_excel(PATH_DATA_SATELLITE)
        if df.empty:
            logger.error(f"File {PATH_DATA_SATELLITE} is empty")
            sys.exit(1)
        logger.info(f"Count of SATELLITES loaded: {len(df.index)}")
        for _, row in df.iterrows():
            id_satellite = str(row["id_satellite"])
            new_satellite = Satellite(
                id_satellite=id_satellite,
                lon=row["lon"],
                lat=row["lat"],
                distance_from_dc=row["distance"],
                travel_time_from_dc=row["travel_time_from_dc"],
                travel_time_in_traffic_from_dc=row["travel_time_in_traffic_from_dc"],
                capacity=json.loads(row["capacity"]),
                cost_fixed=json.loads(row["cost_fixed"]),
                cost_operation=json.loads(row["cost_operation"]),
                cost_sourcing=row["cost_sourcing"],
            )
            satellites[id_satellite] = new_satellite
        if show_data:
            for s in satellites.values():
                logger.info(
                    "-" * 50 + "\n" + json.dumps(s.__dict__, indent=2, default=str)
                )
        logger.info("Loaded OK")
        return satellites

    @staticmethod
    def load_pixels(show_data: bool = False) -> Dict[str, Pixel]:
        """Load data from csv file and create a dictionary of pixels"""
        pixels = {}
        if not os.path.isfile(PATH_DATA_PIXEL):
            logger.error(f"File {PATH_DATA_PIXEL} not found")
            sys.exit(1)
        logger.info(f"Loading data from pixels from path {PATH_DATA_PIXEL}")
        df = pd.read_excel(PATH_DATA_PIXEL)
        if df.empty:
            logger.error(f"File {PATH_DATA_PIXEL} is empty")
            sys.exit(1)
        logger.info(f"Count of PIXELS loaded: {len(df.index)}")
        for _, row in df.iterrows():
            id_pixel = str(row["id_pixel"])
            # create a new pixel
            new_pixel = Pixel(
                id_pixel=id_pixel,
                lon=row["lon"],
                lat=row["lat"],
                area_surface=row["area_surface"],
                speed_intra_stop=json.loads(row["speed_intra_stop"]),
            )
            pixels[id_pixel] = new_pixel
        logger.info("Loaded OK")
        if show_data:
            for p in pixels.values():
                logger.info(
                    "-" * 50 + "\n" + json.dumps(p.__dict__, indent=2, default=str)
                )
        return pixels

    @staticmethod
    def load_matrix_from_satellite() -> Dict[str, Dict]:
        """Load data from csv file and create a dictionary of distances and durations"""
        if not os.path.isfile(PATH_DATA_DISTANCES_FROM_SATELLITES):
            logger.error(f"File {PATH_DATA_DISTANCES_FROM_SATELLITES} not found")
            sys.exit(1)
        logger.info(
            f"Loading data of durations and distance path {PATH_DATA_DISTANCES_FROM_SATELLITES}"
        )
        df = pd.read_excel(PATH_DATA_DISTANCES_FROM_SATELLITES)
        if df.empty:
            logger.error(f"File {PATH_DATA_DISTANCES_FROM_SATELLITES} is empty")
            sys.exit(1)
        distance = {
            (row["id_satellite"], row["id_pixel"]): row["distance"]
            for _, row in df.iterrows()
        }
        travel_time = {
            (row["id_satellite"], row["id_pixel"]): row["travel_time"]
            for _, row in df.iterrows()
        }
        travel_time_in_traffic = {
            (row["id_satellite"], row["id_pixel"]): row["travel_time_in_traffic"]
            for _, row in df.iterrows()
        }
        matrix = {
            "travel_time": travel_time,
            "distance": distance,
            "travel_time_in_traffic": travel_time_in_traffic,
        }
        logger.info("Loaded OK")
        return matrix

    @staticmethod
    def load_matrix_from_dc() -> Dict[str, Dict]:
        """Load data from csv file and create a dictionary of distances and durations"""
        if not os.path.isfile(PATH_DATA_DISTANCES_FROM_DC):
            logger.error(f"File {PATH_DATA_DISTANCES_FROM_DC} not found")
            sys.exit(1)
        logger.info(
            f"Loading data of durations and distance path {PATH_DATA_DISTANCES_FROM_DC}"
        )
        df = pd.read_excel(PATH_DATA_DISTANCES_FROM_DC)
        if df.empty:
            logger.error(f"File {PATH_DATA_DISTANCES_FROM_DC} is empty")
            sys.exit(1)
        distance = {(row["id_pixel"]): row["distance"] for _, row in df.iterrows()}
        travel_time = {
            (row["id_pixel"]): row["travel_time"] for _, row in df.iterrows()
        }
        travel_time_in_traffic = {
            (row["id_pixel"]): row["travel_time_in_traffic"] for _, row in df.iterrows()
        }
        matrix = {
            "travel_time": travel_time,
            "distance": distance,
            "travel_time_in_traffic": travel_time_in_traffic,
        }
        logger.info("Loaded OK")
        return matrix

    @staticmethod
    def load_scenario(id_scenario: str, show_data: bool = False) -> Dict[str, Pixel]:
        """Load data from scenario from csv file and create a dictionary of pixels"""
        base_pixels = Data.load_pixels(show_data)
        scenario_path = PATH_ROOT_SCENARIO + f"scenario_{id_scenario}.xlsx"
        if not os.path.isfile(scenario_path):
            logger.error(f"File {scenario_path} not found")
            sys.exit(1)
        logger.info(f"Loading data from scenario from path {scenario_path}")
        df = pd.read_excel(scenario_path)
        if df.empty:
            logger.error(f"File {scenario_path} is empty")
            sys.exit(1)

        pixels = {}
        for _, row in df.iterrows():
            id_pixel = str(row["id_pixel"])
            demand_by_period = json.loads(row["demand_by_period"])
            drop_by_period = json.loads(row["drop_by_period"])
            stop_by_period = json.loads(row["stop_by_period"])
            pixel = base_pixels.get(id_pixel, None)
            if not pixel is None:
                # update the demand by period
                pixel.demand_by_period = demand_by_period
                pixel.stop_by_period = stop_by_period
                pixel.drop_by_period = drop_by_period
                pixels[id_pixel] = pixel
        logger.info(f"Count of PIXELS loaded from instances: {len(pixels)}")
        if show_data:
            for p in pixels.values():
                logger.info(
                    "-" * 50 + "\n" + json.dumps(p.__dict__, indent=2, default=str)
                )
        return pixels

    @staticmethod
    def load_vehicles() -> Dict[str, Vehicle]:
        """Load data from csv file and create a dictionary of distances and durations"""
        vehicle_small = Vehicle(
            id_vehicle="small",
            type_vehicle="small",
            capacity=115,
            cost_fixed=89,
            time_service=0.01,
            time_fixed=0.05,
            time_dispatch=0.33,
            time_load=0.0071,
            speed_line_haul=30,
            max_time_services=12,
            k=1.3,
        )
        vehicle_large = Vehicle(
            id_vehicle="large",
            type_vehicle="large",
            capacity=460,
            cost_fixed=139,
            time_service=0.02,
            time_fixed=0.05,
            time_dispatch=0.75,
            time_load=0.0071,
            speed_line_haul=25,
            max_time_services=12,
            k=1.3,
        )
        logger.info("Loaded OK")
        logger.info(
            f"Quantity of vehicles loaded: {len([vehicle_small, vehicle_large])}"
        )
        return {"small": vehicle_small, "large": vehicle_large}
