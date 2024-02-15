"""Module for the sub problem of the stochastic model."""
import logging
import time
from typing import Any, Dict

import gurobipy as gp
from gurobipy import GRB, quicksum

from src.classes import Pixel, Satellite
from src.instance.instance import Instance

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SubProblem:
    """Class for the sub problem of the stochastic model."""

    def __init__(self, instance: Instance, period: int, scenario: Dict) -> None:
        """Initialize the sub problem."""
        # Instance
        self.t: int = period
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.type_of_flexibility: str = instance.type_of_flexibility
        self.is_continuous_X: bool = instance.is_continuous_X

        self.pixels: Dict[str, Pixel] = scenario["pixels"]
        self.costs: Dict[str, Dict] = scenario["costs"]
        self.fleet_size_required: Dict[str, Any] = scenario["fleet_size_required"]

        # Create model
        self.model = self.__create_model()

        # Variables
        self.X = {}
        self.Z = {}
        self.W = {}

        # Objective
        self.objective = None
        self.cost_operating_satellites = None
        self.cost_served_from_satellite = None
        self.cost_served_from_dc = None

    def __create_model(self):
        """Create the model."""
        logger.info("[SUBPROBLEM] Creating sub problem model")
        return gp.Model(name="SubProblem")

    def __add_variables(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        fixed_y: Dict,
    ) -> None:
        """Add variables to the model."""
        # 1. add variable X: binary variable to decide if a satellite is operating
        logger.info("[SUBPROBLEM] Adding variables to sub problem")
        if self.type_of_flexibility == 1:  # only one capacity per satellite
            self.X = dict(
                [
                    (
                        (s, q, self.t),
                        self.model.addVar(vtype=GRB.BINARY, name=f"X_s{s}_t{self.t}"),
                    )
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    if fixed_y[(s, q)] > 0.5
                ]
            )
        else:
            self.X = dict(
                [
                    (
                        (s, q_lower, self.t),
                        self.model.addVar(vtype=GRB.BINARY, name=f"X_s{s}_t{self.t}"),
                    )
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for q_lower in satellite.capacity.keys()
                    if fixed_y[(s, q)] > 0.5
                    and q
                    >= q_lower  # only if the satellite is installed with higher capacity
                ]
            )
        logger.info(f"Number of variables X: {len(self.X)}")

        # 2. add variable Z: binary variable to decide if a satellite is used to serve a pixel # noqa
        logger.info("[SUBPROBLEM] Add variable Z")
        if not self.is_continuous_X:
            type_variable = GRB.BINARY
        else:
            type_variable = GRB.CONTINUOUS
        self.Z = dict(
            [
                (
                    (s, k, self.t),
                    self.model.addVar(
                        vtype=type_variable,
                        name=f"Z_s{s}_k{k}_t{self.t}",
                        lb=0.0,
                        ub=1.0,
                    ),
                )
                for s in satellites.keys()
                for k in pixels.keys()
                if len(
                    [
                        fixed_y[(s, q)]
                        for q in satellites.capacity.keys()
                        if fixed_y[(s, q)] > 0.5
                    ]
                )
                > 0  # only if the satellite is installed
            ]
        )
        logger.info(f"Number of variables Z: {len(self.Z)}")

        # 3. add variable W: binary variable to decide if a pixel is served from dc
        logger.info("[SUBPROBLEM] Add variable W")
        self.W = dict(
            [
                (
                    (k, self.t),
                    self.model.addVar(
                        vtype=type_variable, name=f"W_k{k}_t{self.t}", lb=0.0, ub=1.0
                    ),
                )
                for k in pixels.keys()
            ]
        )
        logger.info(f"Number of variables W: {len(self.W)}")

    def __add_objective(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        costs: Dict,
        fixed_y: Dict,
    ) -> None:
        """Add objective function to the model."""
        # 1. add cost operating satellites
        if self.type_of_flexibility == 1:
            self.cost_operating_satellites = quicksum(
                [
                    (satellite.cost_operation[q][self.t]) * self.X[(s, q, self.t)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    if fixed_y[(s, q)] > 0.5
                ]
            )
        else:
            self.cost_operating_satellites = quicksum(
                [
                    (satellite.cost_operation[q_lower][self.t])
                    * self.X[(s, q_lower, self.t)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for q_lower in satellite.capacity.keys()
                    if fixed_y[(s, q)] > 0.5 and q >= q_lower
                ]
            )

        # 2. add cost served from satellite
        self.cost_served_from_satellite = quicksum(
            [
                costs["satellite"][(s, k, self.t)]["total"] * self.Z[(s, k, self.t)]
                for s in satellites.keys()
                for k in pixels.keys()
                if len(
                    [
                        fixed_y[(s, q)]
                        for q in satellites.capacity.keys()
                        if fixed_y[(s, q)] > 0.5
                    ]
                )
                > 0  # only if the satellite is installed
            ]
        )

        # 3. add cost served from dc
        self.cost_served_from_dc = quicksum(
            [
                costs["dc"][(k, self.t)]["total"] * self.W[(k, self.t)]
                for k in pixels.keys()
            ]
        )

        self.objective = (
            self.cost_served_from_dc
            + self.cost_served_from_satellite
            + self.cost_operating_satellites
        )
        logger.info("[SUBPROBLEM] Adding objective function to sub problem")
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def solve_model(self, fixed_y, final_solution) -> None:
        """Solve the model."""
        self.__add_variables(self.satellites, self.pixels, fixed_y)
        self.__add_objective(self.satellites, self.pixels, self.costs, fixed_y)

        # Add Constraints
        # (1) operating satellite
        if self.type_of_flexibility == 1:
            for s, satellite in self.satellites.items():
                for q in satellite.capacity.keys():
                    if fixed_y[(s, q)] > 0.5:
                        nameConstraint = f"R_Operating_s{s}_q{q}_t{self.t}"
                        self.model.addConstr(
                            self.X[(s, q, self.t)] == 1,
                            name=nameConstraint,
                        )

        for s, satellite in self.satellites.items():
            if (
                len(
                    [
                        fixed_y[(s, q)]
                        for q in satellite.capacity.keys()
                        if fixed_y[(s, q)] > 0.5
                    ]
                )
                > 0
            ):
                nameConstraint = f"R_capacity_s{s}_t{self.t}"
                self.model.addConstr(
                    quicksum(
                        [
                            self.Z[(s, k, self.t)]
                            * self.fleet_size_required["small"][(s, k, self.t)][
                                "fleet_size"
                            ]
                            for k in self.pixels.keys()
                        ]
                    )
                    - quicksum(
                        [
                            fixed_y[(s, q)] * capacity
                            for q, capacity in satellite.capacity.items()
                        ]
                    )
                    <= 0,
                    name=nameConstraint,
                )

        # (3) assign pixel to satellite
        for k in self.pixels.keys():
            for s, satellite in self.satellites.items():
                if (
                    len(
                        [
                            fixed_y[(s, q)]
                            for q in satellite.capacity.keys()
                            if fixed_y[(s, q)] > 0.5
                        ]
                    )
                    > 0
                ):
                    nameConstratint = f"R_Assign_s{s}_k{k}_t{self.t}"
                    self.model.addConstr(
                        self.Z[(s, k, self.t)]
                        - quicksum(
                            [
                                self.X[(s, q_lower, self.t)]
                                for q in satellite.capacity.keys()
                                for q_lower in satellite.capacity.keys()
                                if (
                                    self.type_of_flexibility != 1
                                    and fixed_y[(s, q)] > 0.5
                                    and q >= q_lower
                                )
                                or (
                                    self.type_of_flexibility == 1
                                    and fixed_y[(s, q)] > 0.5
                                    and q == q_lower
                                )
                            ]
                        )
                        <= 0,
                        name=nameConstratint,
                    )

        # (4) demand satisfied
        for k in self.pixels.keys():
            nameConstraint = f"R_demand_k{k}_t{self.t}"
            self.model.addConstr(
                quicksum(
                    [
                        self.Z[(s, k, self.t)]
                        for s, satellite in self.satellites.items()
                        if len(
                            [
                                fixed_y[(s, q)]
                                for q in satellite.capacity.keys()
                                if fixed_y[(s, q)] > 0.5
                            ]
                        )
                        > 0
                    ]
                )
                + quicksum([self.W[(k, self.t)]])
                == 1,
                name=nameConstraint,
            )

        if not final_solution:
            # update model
            self.model._total_cost = self.objective
            self.model.update()
            self.model.Params.LogToConsole = 0
            start_time = time.time()
            self.model.optimize()

            run_time = round(time.time() - start_time, 3)
            total_cost = self.model._total_cost.getValue()

            self.model.dispose()
            logger.info("[SUBPROBLEM] Sub problem solved")
            logger.info(f"Run time: {run_time}")

            return run_time, total_cost

        else:
            # update model
            self.model._z = self.Z
            self.model._x = self.X
            self.model._w = self.W
            self.model._total_cost = self.objective
            self.model.update()

            self.model.Params.LogToConsole = 0
            start_time = time.time()
            self.model.optimize()

            run_time = round(time.time() - start_time, 3)
            total_cost = self.model._total_cost.getValue()

            # get solution
            cost_served_from_dc = self.cost_served_from_dc.getValue()
            cost_served_from_satellite = self.cost_served_from_satellite.getValue()
            cost_operating_satellites = self.cost_operating_satellites.getValue()

            # save relevant information
            x_values = {
                (s, q, self.t): round(self.model._x[(s, q, self.t)].x)
                for s, satellite in self.satellites.items()
                for q in satellite.capacity.keys()
                if self.model._x[(s, q, self.t)].x > 0
            }
            z_values = {
                (s, k, self.t): round(self.model._z[(s, k, self.t)].x)
                for s in self.satellites.keys()
                for k in self.pixels.keys()
                if self.model._z[(s, k, self.t)].x > 0
            }
            w_values = {
                (k, self.t): round(self.model._w[(k, self.t)].x)
                for k in self.pixels.keys()
                if self.model._w[(k, self.t)].x > 0
            }

            self.model.dispose()
            logger.info("[SUBPROBLEM] Sub problem solved")
            logger.info(f"Run time: {run_time}")

            total_cost = {
                "sp_total_cost": total_cost,
                "sp_cost_served_from_dc": cost_served_from_dc,
                "sp_cost_served_from_satellite": cost_served_from_satellite,
                "sp_cost_operating_satellites": cost_operating_satellites,
            }
            solution = {
                "sp_x": x_values,
                "sp_z": z_values,
                "sp_w": w_values,
            }
            return run_time, total_cost, solution
