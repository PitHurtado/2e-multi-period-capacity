"""Module to solve the Branch and Cut algorithm"""
import time
from typing import Any, Dict

import numpy as np
from matplotlib import pyplot as plt

from src.classes import Satellite
from src.instance.instance import Instance
from src.instance.scenario import Scenario
from src.model.cuts import Cuts
from src.model.master_problem import MasterProblem
from src.model.sub_problem import SubProblem
from src.utils import LOGGER as logger


class Branch_and_Cut:
    """Class to define the Branch and Cut algorithm"""

    def __init__(self, instance: Instance):
        # solvers
        self.MP = MasterProblem(instance)
        self.Cuts = Cuts(instance, self.MP.LB)

        # Params
        self.instance: Instance = instance
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.scenarios: Dict[str, Scenario] = instance.scenarios
        self.periods = instance.periods

        # config params
        self.objective_value = 0
        self.initial_upper_bound = 0
        self.run_time = 0
        self.optimality_gap = 0
        self.best_bound_value = 0

    def solve(self, max_run_time: int, warm_start: bool = False) -> None:
        """Solve the Branch and Cut algorithm"""
        # (1) Create master problem:
        # self.MP.create_model(warm_start) # TODO - check if this is necessary

        # (2) Define Gurobi parameters and optimize:
        logger.info(
            "[BRANCH AND CUT] Start Branch and Cut algorithm - id instance: %s",
            self.instance.id_instance,
        )
        logger.info(f"[BRANCH AND CUT] Instance: \n {self.instance}")
        self.MP.build()
        self.MP.model.setParam("Timelimit", max_run_time)
        self.MP.model.Params.lazyConstraints = 1
        self.MP.model.setParam("Heuristics", 0)
        self.MP.model.setParam("MIPGap", 0.001)
        self.MP.model.setParam("Threads", 10)
        start_time = time.time()
        self.MP.set_start_time(start_time)
        self.Cuts.set_start_time(start_time)
        # turn off presolve
        # self.MP.model.setParam("Presolve", 0)
        self.MP.model.optimize(Cuts.add_cuts)
        # self.MP.model.update()
        logger.info(
            "[BRANCH AND CUT] End Branch and Cut algorithm - id instance: %s",
            self.instance.id_instance,
        )
        values_times_subproblems = Cuts.run_times
        plt.hist(values_times_subproblems, bins=50)
        plt.yscale("log")
        plt.show()

        # (3) Save metrics:
        logger.info("[BRANCH AND CUT] Save metrics")
        try:
            self.run_time = round(time.time() - start_time, 3)
            self.optimality_gap = round(100 * self.MP.model.MIPGap, 3)
            self.objective_value = round(self.MP.get_objective_value(), 3)
            print("Objective value: ", self.objective_value)
            # self.MP.model.dispose()
        except AttributeError:
            logger.error(
                "[BRANCH AND CUT] Error while saving metrics - id instance: %s",
                self.instance.id_instance,
            )

    def get_best_solution_allocation(self):
        """Get the best solution allocation"""
        return self.Cuts.best_solution

    def get_metrics_evaluation(self):
        """Get metrics of the evaluation"""
        metrics = {
            "id_instance": self.instance.id_instance,
            "cost_installed_satellites": self.MP.model._cost_allocation_satellites.getValue(),
            "run_time": self.run_time,
            "optimality_gap": self.optimality_gap,
            "objective_value": self.objective_value,
            "best_bound_value": self.best_bound_value,
            "solution": self.Cuts.best_solution,
        }
        return metrics

    def __solve_subproblem(
        self, scenario: Scenario, t: int, solution: Dict[Any, float]
    ) -> float:
        """Solve the subproblem and return the total cost of the solution"""
        # (1) create subproblem
        sub_problem = SubProblem(self.instance, t, scenario)
        sp_run_time, sp_total_cost, sp_solution = sub_problem.solve_model(
            solution, True
        )
        return sp_total_cost["sp_total_cost"]

    def solve_evaluation(self, solution: Dict[Any, float]) -> float:
        """Solve the subproblem for the evaluation"""
        # (1) compute cost installed satellites
        cost_installed_satellites = np.sum(
            [
                satellite.cost_fixed[q] * solution[(s, q)]
                for s, satellite in self.satellites.items()
                for q in satellite.capacity.keys()
            ]
        )

        # (2) create subproblem N * T times and solve
        cost_second_echeleon = 0
        for scenario in self.scenarios.values():
            for t in range(self.periods):
                cost_second_echeleon += self.__solve_subproblem(scenario, t, solution)

        # (3) compute total cost of the evaluation
        total_cost = (
            cost_installed_satellites + (1 / len(self.scenarios)) * cost_second_echeleon
        )
        return total_cost
