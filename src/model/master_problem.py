"""Module for the master problem of the stochastic model."""
from typing import Any, Dict, Tuple

import gurobipy as gp
import numpy as np
from gurobipy import GRB, quicksum

from src.classes import Satellite
from src.instance.instance import Instance
from src.instance.scenario import Scenario
from src.utils import LOGGER as logger


class MasterProblem:
    """Class for the master problem of the stochastic model."""

    def __init__(self, instance: Instance) -> None:
        """Initialize the master problem."""
        # Instance
        self.periods: int = instance.periods
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.scenarios: Dict[str, Scenario] = instance.scenarios

        # Variables
        self.Y = {}
        self.θ = {}

        # Parameters Lower Bound
        self.LB: Dict[Tuple[str, int], float] = self.__compute_lower_bound()

        # objective
        self.objective = None
        self.cost_installation_satellites = None
        self.cost_second_stage = None

    def build(self) -> None:
        """Build the master problem."""
        logger.info("[MODEL] Building master problem")
        # create Model
        self.model: gp.Model = gp.Model(name="MasterProblem")

        # Add variables, objective and constraints
        self.__add_variables(self.satellites, self.scenarios)
        self.__add_objective(self.satellites, self.scenarios)
        self.__add_constraints(self.satellites)

        # self.model.update()
        self.model._start_time = 0

    def __add_variables(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add variables to the model."""
        logger.info("[MODEL] Adding variables to master problem")
        self.Y = dict(
            [
                (
                    (s, q),
                    self.model.addVar(vtype=GRB.BINARY, name=f"Y_s{s}_q{q}"),
                )
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )
        logger.info(f"Number of variables Y: {len(self.Y)}")

        self.θ = dict(
            [
                (
                    n,
                    self.model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"θ_n{n}"),
                )
                for n in scenarios.keys()
            ]
        )
        logger.info(f"Number of variables θ: {len(self.θ)}")
        self.model._Y = self.Y
        self.model._θ = self.θ

    def __compute_lower_bound(self):
        """Compute the lower bound for the second stage cost."""
        LB = {}
        logger.info("[MODEL] Computing lower bounds for the second stage cost")
        for n, scenario in self.scenarios.items():
            LB[n] = np.sum(
                [
                    np.min(
                        [
                            scenario.get_cost_serving("satellite")[(s, k, t)]["total"]
                            for s in self.satellites.keys()
                        ]
                        + [scenario.get_cost_serving("dc")[(k, t)]["total"]]
                    )
                    for k in scenario.pixels.keys()
                    for t in range(self.periods)
                ]
            )
            # LB[n] = 0
        logger.info(f"[MODEL] Lower bounds: {LB}")
        return LB

    def __add_objective(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add objective function to the model."""
        logger.info("[MODEL] Adding objective function to master problem")

        cost_installation_satellites = quicksum(
            [
                (satellite.cost_fixed[q]) * self.Y[(s, q)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )
        cost_second_stage = (
            1 / (len(scenarios)) * quicksum([self.θ[n] for n in scenarios.keys()])
        )

        total_cost = cost_installation_satellites + cost_second_stage
        self.model.setObjective(total_cost, GRB.MINIMIZE)

        self.objective = total_cost
        self.cost_installation_satellites = cost_installation_satellites
        self.cost_second_stage = cost_second_stage

        self.model._total_cost = total_cost
        self.model._cost_installation_satellites = cost_installation_satellites
        self.model._cost_second_stage = cost_second_stage

    def __add_constraints(self, satellites: Dict[str, Satellite]) -> None:
        """Add constraints to the model."""
        logger.info("[MODEL] Adding constraints to master problem")

        # Constraint (1)
        for s, satellite in satellites.items():
            nameConstraint = f"R_Open_s{s}"
            self.model.addConstr(
                quicksum([self.Y[(s, q)] for q in satellite.capacity.keys()]) <= 1,
                name=nameConstraint,
            )

        # Lower bounds on the second-stage cost:
        for n in self.scenarios.keys():
            if self.LB[n] > 0:
                self.model.addConstr(self.θ[n] >= self.LB[n])

        # dummy constraint
        # this constraint is added to avoid the following error:
        # self.model.addConstr(
        #     quicksum(
        #         [
        #             self.Y[(s, q)]
        #             for s in satellites.keys()
        #             for q in satellites[s].capacity.keys()
        #         ]
        #     )
        #     == 1
        # )

    def get_objective_value(self):
        """Get the objective value of the model."""
        logger.info("[MODEL] Getting objective value")
        return self.model._total_cost.getValue()

    def get_best_bound_value(self):
        """Get the best bound value of the model."""
        logger.info("[MODEL] Getting best bound value")
        return self.model.ObjBound

    def set_start_time(self, start_time):
        """Set start time to model."""
        self.model._start_time = start_time

    def set_params(self, params: Dict[str, int]):
        """Set params to model."""
        logger.info(f"[MODEL] Set params to model {params}")
        for key, item in params.items():
            self.model.setParam(key, item)

    def warm_start(
        self, solution: Dict[str, int]
    ):  # TODO check if it is the right type
        """Warm start the model."""
        logger.info(f"[MODEL] Warm start the model with solution {solution}")
        for key, item in solution.items():
            self.model.getVarByName(key).start = item

    def get_y_solution(self):
        """Get the Y solution of the model."""
        logger.info("[MODEL] Getting Y solution")
        return {str(keys): value.X for keys, value in self.Y.items()}
