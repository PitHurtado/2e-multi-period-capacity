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
        self.instance = instance

        # Params
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.pixels_by_scenarios: Dict = instance.pixels_by_scenarios
        self.costs_by_scenarios: Dict = instance.costs_by_scenarios
        self.fleet_size_required_by_scenarios: Dict = (
            instance.fleet_size_required_by_scenarios
        )
        self.vehicles: Dict[str, Vehicle] = instance.vehicles
        self.periods = instance.periods

        # Scenarios to evaluate
        self.scenarios_to_evalute: Dict = instance.get_scenarios_evaluation()

        # config params
        self.objective_value = 0
        self.initial_upper_bound = 0
        self.run_time = 0
        self.optimality_gap = 0
        self.best_bound_value = 0

    def solve(self, max_run_time, warm_start):
        """Solve the Branch and Cut algorithm"""
        # (1) Create master problem:
        # self.MP.create_model(warm_start) # TODO - check if this is necessary

        # (2) Define Gurobi parameters and optimize:
        logger.info("[BRANCH AND CUT] Start Branch and Cut algorithm")
        self.MP.model.setParam("Timelimit", max_run_time)
        self.MP.model.Params.lazyConstraints = 1
        self.MP.model.setParam("Heuristics", 0)
        self.MP.model.setParam("MIPGap", 0.001)
        self.MP.model.setParam("Threads", 12)
        start_time = time.time()
        self.MP.set_start_time(start_time)
        self.Cuts.set_start_time(start_time)
        self.MP.model.optimize(Cuts.add_cuts)
        logger.info("[BRANCH AND CUT] End Branch and Cut algorithm")

        # (3) Save metrics:
        logger.info("[BRANCH AND CUT] Save metrics")
        self.run_time = round(time.time() - start_time, 3)
        self.optimality_gap = round(100 * self.MP.model.MIPGap, 3)
        self.objective_value = round(self.MP.get_objective_value(), 3)
        self.initial_upper_bound = round(self.MP.get_initial_upper_bound(), 3)
        self.MP.model.dispose()

    def get_metrics_from_fixed_solution(self, folder_path):
        """Get metrics from fixed solution"""
        best_solution = self.Cuts.best_solution
        subproblem_solution = []

        metrics = {
            "run_time": self.run_time,
            "optimality_gap": self.optimality_gap,
            "objective_value": self.objective_value,
            "best_bound_value": self.best_bound_value,
            "initial_upper_bound": self.initial_upper_bound,
        }

        # (1) Create subproblems:
        for i, scenario in enumerate(self.scenarios_to_evalute):
            for period in range(self.periods):
                solver = SubProblem(
                    instance=self.instance, period=period, scenario=scenario
                )
                (
                    subproblem_run_time,
                    subproblem_cost,
                    subproblem_solution,
                ) = solver.solve_model(best_solution, True)
                logger.info(
                    f"[BRANCH AND CUT] Subproblem X - Period {period} - Run time: {subproblem_run_time}"
                )

                # Save subproblem metrics
                subproblem_metrics = {
                    "run_time": subproblem_run_time,
                    "subproblem_cost": subproblem_cost,
                    "subproblem_solution": subproblem_solution,
                }
                file_name = (
                    folder_path
                    + "/individual/"
                    + str(i)
                    + "scenario_evaluation"
                    + ".json"
                )
                with open(file_name, "w") as json_file:
                    json.dump(subproblem_metrics, json_file, indent=4)

                # Save metrics
                metrics.update(
                    {
                        "satellites_used": best_solution,
                        "sp_total_cost": subproblem_cost["sp_total_cost"],
                        "sp_cost_served_from_dc": subproblem_cost[
                            "sp_cost_served_from_dc"
                        ],
                        "sp_cost_served_from_satellite": subproblem_cost[
                            "sp_cost_served_from_satellite"
                        ],
                        "sp_cost_operating_satellites": subproblem_cost[
                            "sp_cost_operating_satellites"
                        ],
                    }
                )

        return metrics
