"""Module to define Sub Problem and Cut Generator"""
import logging
import sys
import time
from typing import Dict

import numpy as np
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

    def __init__(self, instance: Instance, period: int, scenario: Dict):
        Cuts.SP = SubProblem(instance, period, scenario)
        Cuts.instance: Instance = instance
        Cuts.period: int = period
        Cuts.satellites: Dict[str, Satellite] = instance.satellites
        Cuts.vehicles: Dict[str, Vehicle] = instance.vehicles

        Cuts.pixels: Dict[str, Pixel] = scenario["pixels"]
        Cuts.costs: Dict = scenario["costs"]
        Cuts.id_scenario: int = scenario["id"]

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

        subproblem_run_time, subproblem_cost = Cuts.SP.solve_model(Y, False)
        Cuts.subproblem_solved += 1
        total_cost = model._total_cost.getValue() + subproblem_cost

        # update upper bound and best solution found so far
        if total_cost < Cuts.upper_bound:
            Cuts.upper_bound = total_cost
            Cuts.best_solution = Y
            Cuts.time_best_solution_found = round(time.time() - Cuts.start_time, 3)
            Cuts.upper_bound_updated += 1
            model.cbSetSolution(model._Y, Y)
            model.cbSetSolution(
                model._θ, subproblem_cost
            )  # TODO: check if this is correct
            model.cbUseSolution()

        if θ[(Cuts.period, Cuts.id_scenario)] < subproblem_cost:
            # Create the activation function:
            act_functon = Cuts.get_activation_function(model, Y, subproblem_cost)

            # Add the optimality cut:
            model.cbLazy(θ[(Cuts.period, Cuts.id_scenario)] <= act_functon)
            Cuts.optimality_cuts += 1

    @staticmethod
    def get_activation_function(model, Y, subproblem_cost):
        """Get the activation function"""
        activation = (
            quicksum(
                model._Y[(s, q)]
                for s, satellite in Cuts.satellites.items()
                for q in satellite.capacity.keys()
                if Y[(s, q)] > 0
            )
            - len(
                [
                    1
                    for s, satellite in Cuts.satellites.items()
                    for q in satellite.capacity.keys()
                    if Y[(s, q)] > 0
                ]
            )
            + 1
        )
        L = np.sum(
            [
                np.min(
                    [
                        Cuts.costs["satellite"][(s, k, Cuts.period)]["total"]
                        for s in Cuts.satellites.keys()
                        if Y[(s, k)] > 0
                    ]
                )
                for k in Cuts.pixels.keys()
            ]
        )
        activation_function = L + (subproblem_cost - L) * activation

        return activation_function
