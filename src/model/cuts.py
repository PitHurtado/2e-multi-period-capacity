"""Module to define Sub Problem and Cut Generator"""
import sys
import time
from typing import Any, Dict

import numpy as np
from gurobipy import GRB, quicksum

from src.classes import Satellite
from src.instance.instance import Instance
from src.model.master_problem import MasterProblem
from src.model.sub_problem import SubProblem
from src.utils import LOGGER as logger


class Cuts:
    """Class to define the Cut Generator"""

    def __init__(self, instance: Instance, lower_bound_from_mp: Dict[Any, float]):
        # solver SP
        Cuts.SPs: Dict[Any, SubProblem] = self.__create_subproblems(instance)
        Cuts.LB = lower_bound_from_mp

        # parameters
        Cuts.periods: int = instance.periods
        Cuts.satellites: Dict[str, Satellite] = instance.satellites
        Cuts.instance = instance

        # configs parameters
        Cuts.optimality_cuts = 0
        Cuts.best_solution = {}
        Cuts.upper_bound_updated = 0
        Cuts.upper_bound = sys.maxsize
        Cuts.subproblem_solved = 0
        Cuts.start_time = 0
        Cuts.time_best_solution_found = 0
        Cuts.run_times = []

    @staticmethod
    def add_cuts(model, where) -> None:
        """Add optimality cuts and LBF cuts"""
        if where == GRB.Callback.MIPSOL:
            Cuts.add_cut_integer_solution(model)
            logger.info(f"[CUT] Optimality cuts: {Cuts.optimality_cuts}")

    @staticmethod
    def add_cut_integer_solution(model: MasterProblem) -> None:
        """Add optimality cuts and LBF cuts"""
        # retrieve current solution
        Y = model.cbGetSolution(model._Y)
        θ = model.cbGetSolution(model._θ)

        # solve subproblems
        total_subproblem_cost = 0
        new_θ = {}
        for t in range(Cuts.periods):
            for n in Cuts.instance.scenarios.keys():
                logger.info(f"[CUT] Subproblem: {n} - {t}")
                subproblem_runtime, subproblem_cost = Cuts.SPs[(n, t)].solve_model(
                    Y, False
                )
                Cuts.subproblem_solved += 1
                new_θ[(n, t)] = subproblem_cost
                total_subproblem_cost += subproblem_cost
                Cuts.run_times.append(subproblem_runtime)

        logger.info(f"[CUT] Subproblems solved: {Cuts.subproblem_solved}")

        total_cost = (
            np.sum(
                [
                    satellite.cost_fixed[q] * Y[(s, q)]
                    for s, satellite in Cuts.instance.satellites.items()
                    for q in satellite.capacity.keys()
                ]
            )
            + (1 / (len(Cuts.instance.scenarios))) * total_subproblem_cost
        )

        # update upper bound and best solution found so far
        if total_cost < Cuts.upper_bound + 1:
            Cuts.upper_bound = total_cost
            Cuts.best_solution = Y
            Cuts.time_best_solution_found = round(time.time() - Cuts.start_time, 3)
            Cuts.upper_bound_updated += 1
            model.cbSetSolution(model._Y, Y)
            model.cbSetSolution(model._θ, new_θ)
            model.cbUseSolution()

        # add optimality cuts
        epsilon = 1e-6
        for t in range(Cuts.periods):
            for n in Cuts.instance.scenarios.keys():
                if θ[(n, t)] < new_θ[(n, t)] + epsilon:
                    act_function = Cuts.get_activation_function(model, Y)
                    model.cbLazy(
                        model._θ[(n, t)]
                        >= (
                            new_θ[(n, t)]
                            + (new_θ[(n, t)] - Cuts.LB[(n, t)]) * act_function
                        )
                    )

                    Cuts.optimality_cuts += 1

    @staticmethod
    def get_activation_function(model, Y):
        """Get the activation function"""
        epsilon = 1e-6
        activation = (
            quicksum(
                model._Y[(s, q)]
                for s, satellite in Cuts.satellites.items()
                for q in satellite.capacity.keys()
                if Y[(s, q)] + epsilon >= 1
            )
            - quicksum(
                model._Y[(s, q)]
                for s, satellite in Cuts.satellites.items()
                for q in satellite.capacity.keys()
                if Y[(s, q)] < 0.5
            )
            - np.sum(
                [
                    1
                    for s, satellite in Cuts.satellites.items()
                    for q in satellite.capacity.keys()
                    if Y[(s, q)] + epsilon >= 1
                ]
            )
        )
        return activation

    def __create_subproblems(self, instance: Instance) -> Dict[Any, SubProblem]:
        """Create the subproblems"""
        subproblems = {}
        for t in range(instance.periods):
            for n in instance.scenarios.keys():
                scenario = instance.scenarios[n]
                subproblems[(n, t)] = SubProblem(instance, t, scenario)
        return subproblems

    @staticmethod
    def set_start_time(start_time):
        """Set start time"""
        Cuts.start_time = start_time
