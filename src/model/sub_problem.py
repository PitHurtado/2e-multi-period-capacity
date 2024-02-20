"""Module for the sub problem of the stochastic model."""
import time
from typing import Any, Dict

import gurobipy as gp
import numpy as np
from gurobipy import GRB, quicksum

from src.classes import Pixel, Satellite
from src.instance.instance import Instance
from src.instance.scenario import Scenario
from src.utils import LOGGER as logger


class SubProblem:
    """Class for the sub problem of the stochastic model."""

    def __init__(self, instance: Instance, period: int, scenario: Scenario) -> None:
        """Initialize the sub problem."""
        # params from instance
        self.t: int = period
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.type_of_flexibility: str = instance.type_of_flexibility
        self.is_continuous_x: bool = instance.is_continuous_x

        # params from scenario
        self.pixels: Dict[str, Pixel] = scenario.pixels
        self.costs_serving: Dict[str, Dict] = scenario.get_cost_serving()
        self.fleet_size_required: Dict[str, Any] = scenario.get_fleet_size_required()

        # Create model
        self.model = None

        # Variables
        self.Z = {}
        self.X = {}
        self.W = {}

        # Objective
        self.objective = None
        self.cost_operating_satellites = None
        self.cost_served_from_satellite = None
        self.cost_served_from_dc = None

    def __add_variables(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        fixed_y: Dict,
    ) -> None:
        """Add variables to the model."""
        # 1. add variable Z: binary variable to decide if a satellite is operating
        if (
            self.type_of_flexibility == 2
        ):  # only create variables for the capacity that is installed
            self.Z = dict(
                [
                    (
                        (s, q_lower, self.t),
                        self.model.addVar(
                            vtype=GRB.BINARY, name=f"Z_s{s}_q_{q_lower}_t{self.t}"
                        ),
                    )
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for q_lower in satellite.capacity.keys()
                    if fixed_y[(s, q)] > 0.5 and q >= q_lower
                ]
            )
        logger.info(f"[SP] Number of variables Z: {len(self.Z)}")

        # 2. add variable X: binary variable to decide if a satellite is used to serve a pixel # noqa
        if self.is_continuous_x:
            type_variable = GRB.CONTINUOUS
        else:
            type_variable = GRB.BINARY
        self.X = dict(
            [
                (
                    (s, k, self.t),
                    self.model.addVar(
                        vtype=type_variable,
                        name=f"X_s{s}_k{k}_t{self.t}",
                        lb=0.0,
                        ub=1.0,
                    ),
                )
                for s, satellite in satellites.items()
                for k in pixels.keys()
                if any(fixed_y[(s, q)] > 0.5 for q in satellite.capacity.keys())
            ]
        )
        logger.info(f"[SP] Number of variables X: {len(self.X)}")

        # 3. add variable W: binary variable to decide if a pixel is served from dc
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
        logger.info(f"[SP] Number of variables W: {len(self.W)}")

    def __add_objective(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        costs: Dict,
    ) -> None:
        """Add objective function to the model."""
        # 1. add cost operating satellites
        if self.type_of_flexibility == 2:
            self.cost_operating_satellites = quicksum(
                [
                    satellite.cost_operation[q][self.t] * self.Z[(s, q, self.t)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    if (s, q, self.t) in self.Z.keys()
                ]
            )

        # 2. add cost served from satellite
        self.cost_served_from_satellite = quicksum(
            [
                costs["satellite"][(s, k, self.t)]["total"] * self.X[(s, k, self.t)]
                for s in satellites.keys()
                for k in pixels.keys()
                if (s, k, self.t) in self.X.keys()
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
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def __add_constraints(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel], fixed_y: Dict
    ) -> None:
        """Add constraints to the model."""
        if self.type_of_flexibility == 1:
            # (5) capacity constraint
            for s, satellite in satellites.items():
                nameConstraint = f"R_capacity_s{s}_t{self.t}"
                for q, capacity in satellite.capacity.items():
                    if fixed_y[(s, q)] > 0.5:
                        self.model.addConstr(
                            quicksum(
                                [
                                    self.X[(s, k, self.t)]
                                    * self.fleet_size_required["satellite"][
                                        (s, k, self.t)
                                    ]["fleet_size"]
                                    for k in pixels.keys()
                                ]
                            )
                            <= capacity,
                            name=nameConstraint,
                        )
        else:
            # (5) capacity constraint
            for s, satellite in self.satellites.items():
                if any(fixed_y[(s, q)] > 0.5 for q in satellite.capacity.keys()):
                    nameConstraint = f"R_capacity_s{s}_t{self.t}"
                    self.model.addConstr(
                        quicksum(
                            [
                                self.X[(s, k, self.t)]
                                * self.fleet_size_required["satellite"][(s, k, self.t)][
                                    "fleet_size"
                                ]
                                for k in self.pixels.keys()
                            ]
                        )
                        - quicksum(
                            [
                                self.Z[(s, q, self.t)] * capacity
                                for q, capacity in satellite.capacity.items()
                                if (s, q, self.t) in self.Z.keys()
                            ]
                        )
                        <= 0,
                        name=nameConstraint,
                    )

        # (6) demand satisfied
        for k in self.pixels.keys():
            nameConstraint = f"R_demand_k{k}_t{self.t}"
            self.model.addConstr(
                quicksum(
                    [
                        self.X[(s, k, self.t)]
                        for s in self.satellites.keys()
                        if (s, k, self.t) in self.X.keys()
                    ]
                )
                + quicksum([self.W[(k, self.t)]])
                == 1,
                name=nameConstraint,
            )

    def solve_model(self, fixed_y: Dict[Any, float], final_solution: bool) -> None:
        """Solve the model of the sub problem considering the fixed y."""
        # Create model
        self.model = gp.Model(name="SubProblem")

        logger.info("[SP] Model created")
        self.__add_variables(self.satellites, self.pixels, fixed_y)
        self.__add_objective(self.satellites, self.pixels, self.costs_serving)
        self.__add_constraints(self.satellites, self.pixels, fixed_y)

        # adding operational costs only for case type of flexibility 1
        cost_operating_satellites = np.sum(
            [
                satellite.cost_operation[q][self.t]
                for s, satellite in self.satellites.items()
                for q in satellite.capacity.keys()
                if self.type_of_flexibility == 1 and fixed_y[(s, q)] > 0.5
            ]
        )

        if not final_solution:
            # update model
            self.model._total_cost = self.objective
            self.model.update()
            self.model.Params.LogToConsole = 0

            start_time = time.time()
            self.model.optimize()
            run_time = round(time.time() - start_time, 3)
            total_cost = self.model._total_cost.getValue() + cost_operating_satellites

            logger.info(
                f"[SUBPROBLEM] Sub problem solved - Run time: {run_time} - Total cost: {total_cost}"
            )
            self.model.dispose()

            return run_time, total_cost

        else:
            # update model
            self.model._x = self.X
            self.model._z = self.Z
            self.model._w = self.W
            self.model._total_cost = self.objective
            self.model.update()

            self.model.Params.LogToConsole = 0
            start_time = time.time()
            self.model.optimize()

            run_time = round(time.time() - start_time, 3)
            total_cost = self.model._total_cost.getValue() + cost_operating_satellites
            logger.info(
                f"[SUBPROBLEM] Sub problem solved - Run time: {run_time} - Total cost: {total_cost}"
            )

            # get solution
            cost_served_from_dc = self.cost_served_from_dc.getValue()
            cost_served_from_satellite = self.cost_served_from_satellite.getValue()
            cost_operating_satellites = self.cost_operating_satellites.getValue()

            # save relevant information
            x_values = {
                keys: round(self.model._x[keys].x)
                for keys in self.model._x.keys()
                if self.model._x[keys].x > 0.5
            }
            z_values = {
                keys: round(self.model._z[keys].x)
                for keys in self.model._z.keys()
                if self.model._z[keys].x > 0.5
            }
            w_values = {
                keys: round(self.model._w[keys].x)
                for keys in self.model._w.keys()
                if self.model._w[keys].x > 0.5
            }

            self.model.dispose()
            logger.info("[SP] Sub problem solved")
            logger.info(f"[SP]Run time: {run_time}")

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
