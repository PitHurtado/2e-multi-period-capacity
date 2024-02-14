"""Module to define Sub Problem and Cut Generator"""
import logging
import sys
import time
from typing import Any, Dict, List

from gurobipy import GRB, quicksum

from classes import Pixel, Satellite, Vehicle
from src.instance.instance import Instance
from src.model.sub_problem import SubProblem

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Cuts:
    """Class to define the Cut Generator"""

    def __init__(self, instance: Instance):
        Cuts.SPs: Dict[Any, SubProblem] = self.__create_subproblems(instance)
        Cuts.periods: int = instance.periods
        Cuts.satellites: Dict[str, Satellite] = instance.satellites
        Cuts.vehicles: Dict[str, Vehicle] = instance.vehicles

        Cuts.pixels_by_scenario: Dict[
            str, Dict[str, Pixel]
        ] = instance.pixels_by_scenarios
        Cuts.costs_by_scenario: Dict[
            str, Dict[str, Dict[str, Dict[str, float]]]
        ] = instance.costs_by_scenarios
        Cuts.id_scenarios: List[int] = instance.id_scenarios

        Cuts.optimality_cuts = 0
        Cuts.LBF_cuts = 0
        Cuts.best_solution = {}
        Cuts.upper_bound_updated = 0
        Cuts.upper_bound = sys.maxsize
        Cuts.subproblem_solved = 0
        Cuts.start_time = 0
        Cuts.time_best_solution_found = 0

    @staticmethod
    def add_cuts(model, where) -> None:
        """Add optimality cuts and LBF cuts"""
        if where == GRB.Callback.MIPSOL:
            Cuts.add_cut_integer_solution(model)
        logger.info(f"Optimality cuts: {Cuts.optimality_cuts}")
        logger.info(f"LBF cuts: {Cuts.LBF_cuts}")

    @staticmethod
    def add_cut_integer_solution(model) -> None:
        """Add optimality cuts and LBF cuts"""
        # retrieve current solution
        Y = model.cbGetSolution(model._Y)
        θ = model.cbGetSolution(model._θ)
        current_solution_cost = model._total_cost.getValue()

        for t in range(Cuts.periods):
            for n in Cuts.id_scenarios:
                subproblem_run_time, subproblem_cost = Cuts.SPs[(t, n)].solve_model(
                    Y, False
                )
                Cuts.subproblem_solved += 1
                current_solution_cost += subproblem_cost

                if θ[(t, n)] < subproblem_cost:
                    # Create the activation function:
                    act_functon = Cuts.get_activation_function(
                        model, Y, subproblem_cost, n, t
                    )

                    # Add the optimality cut:
                    model.cbLazy(
                        θ[(t, n)]
                        >= model.LB + (subproblem_cost - model.LB) * act_functon
                    )
                    Cuts.optimality_cuts += 1

        # update upper bound and best solution found so far
        if current_solution_cost < Cuts.upper_bound:
            Cuts.upper_bound = current_solution_cost
            Cuts.best_solution = Y
            Cuts.time_best_solution_found = round(time.time() - Cuts.start_time, 3)
            Cuts.upper_bound_updated += 1
            model.cbSetSolution(model._Y, Y)
            model.cbSetSolution(model._θ, subproblem_cost)
            model.cbUseSolution()

    @staticmethod
    def get_activation_function(model, Y):
        """Get the activation function"""
        activation = (
            quicksum(
                model._Y[(s, q)]
                for s, satellite in Cuts.satellites.items()
                for q in satellite.capacity.keys()
                if Y[(s, q)] > 0.5
            )
            - len(
                [
                    1
                    for s, satellite in Cuts.satellites.items()
                    for q in satellite.capacity.keys()
                    if Y[(s, q)] > 0.5
                ]
            )
            + 1
        )
        return activation

    def __create_subproblems(self, instance: Instance) -> Dict[Any, SubProblem]:
        """Create the subproblems"""
        subproblems = {}
        for t in range(instance.periods):
            for n in instance.id_scenarios:
                scenario = {
                    "pixels": instance.pixels_by_scenarios[str(n)],
                    "costs": instance.costs_by_scenarios[str(n)],
                }
                subproblems[(t, n)] = SubProblem(instance, t, scenario)
        return subproblems

    @staticmethod
    def set_start_time(start_time):
        """Set start time"""
        Cuts.start_time = start_time
