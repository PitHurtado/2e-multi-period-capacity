"""Module for the master problem of the stochastic model."""
import logging
from typing import Any, Dict

import gurobipy as gp
from gurobipy import GRB, quicksum

from classes import Satellite
from src.instance.instance import Instance

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MasterProblem:
    """Class for the master problem of the stochastic model."""

    def __init__(self, instance: Instance) -> None:
        """Initialize the master problem."""
        self.model = gp.Model(name="MasterProblem")

        # Instance
        self.periods: int = instance.periods
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.scenarios: Dict[str, Any] = instance.get_scenarios()

        # Variables
        self.Y = {}
        self.θ = {}

        # Parameters
        self.LB = {}

    def build(self) -> None:
        """Build the master problem."""
        logger.info("[MODEL] Building master problem")
        self.__add_variables(self.satellites, self.scenarios)
        self.__add_objective(self.satellites, self.scenarios)
        self.__add_constraints(self.satellites)

        self.model._start_time = 0
        self.model.update()

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
                    (t, n),
                    self.model.addVar(
                        vtype=GRB.CONTINUOUS, lb=0.0, name=f"θ_t{t}_n{n}"
                    ),
                )
                for t in range(self.periods)
                for n in scenarios.keys()
            ]
        )
        logger.info(f"Number of variables θ: {len(self.θ)}")
        self.model._Y = self.Y
        self.model._θ = self.θ

        self.LB = dict(
            [
                (
                    (t, n),
                    0,
                )
                for t in range(self.periods)
                for n in scenarios.keys()
            ]
        )

    def __add_objective(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Dict[str, Any]]
    ) -> None:
        """Add objective function to the model."""
        logger.info("[MODEL] Adding objective function to master problem")

        cost_allocation_satellites = quicksum(
            [
                (satellite.cost_fixed[q]) * self.Y[(s, q)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )
        cost_second_stage = (
            1
            / len(scenarios)
            * quicksum(
                [self.θ[(t, n)] for t in range(self.periods) for n in scenarios.keys()]
            )
        )

        total_cost = cost_allocation_satellites + cost_second_stage
        self.model.setObjective(total_cost, GRB.MINIMIZE)
        self.model._total_cost = total_cost
        self.model._cost_allocation_satellites = cost_allocation_satellites
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
        for t in range(self.periods):
            for n in self.scenarios.keys():
                if self.LB[(t, n)] > 0:
                    self.model.addConstr(self.θ[(t, n)] >= self.LB[(t, n)])

    def get_objective_value(self):
        """Get the objective value of the model."""
        return self.model._total_cost.getValue()

    def get_best_bound_value(self):
        """Get the best bound value of the model."""
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
