"""Module to solve the Branch and Cut algorithm"""
import json
import logging
import time
from typing import Dict

from src.classes import Satellite, Vehicle
from src.instance.instance import Instance
from src.model.cuts import Cuts
from src.model.master_problem import MasterProblem
from src.model.sub_problem import SubProblem

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Branch_and_Cut:
    """Class to define the Branch and Cut algorithm"""

    def __init__(self, instance: Instance):
        self.MP = MasterProblem(instance)
        self.Cuts = Cuts(instance)

        # Params
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.pixels_by_scenarios: Dict = instance.pixels_by_scenarios
        self.costs_by_scenarios: Dict = instance.costs_by_scenarios
        self.vehicles: Dict[str, Vehicle] = instance.vehicles
        self.periods = instance.periods

        # config params
        self.objective_value = 0
        self.initial_upper_bound = 0
        self.run_time = 0
        self.optimality_gap = 0
        self.best_bound_value = 0

    def solve(self, max_run_time, warm_start):
        # (1) Create master problem:
        # self.MP.create_model(warm_start) # TODO - check if this is necessary

        # (2) Define Gurobi parameters and optimize:
        self.MP.model.setParam("Timelimit", max_run_time)
        self.MP.model.Params.lazyConstraints = 1
        self.MP.model.setParam("Heuristics", 0)
        self.MP.model.setParam("MIPGap", 0.001)
        self.MP.model.setParam("Threads", 12)
        start_time = time.time()
        self.MP.set_start_time(start_time)
        self.Cuts.set_start_time(start_time)
        self.MP.model.optimize(Cuts.add_cuts)

        # (3) Save metrics:
        self.run_time = round(time.time() - start_time, 3)
        self.optimality_gap = round(100 * self.MP.model.MIPGap, 3)
        self.objective_value = round(self.MP.get_objective_value(), 3)
        self.best_bound_value = round(self.MP.get_best_bound_value(), 3)
        self.initial_upper_bound = round(self.MP.get_initial_upper_bound(), 3)
        self.MP.model.dispose()

    def get_metrics(self, folder_path):
        pass
