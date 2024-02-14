"""Module for the sub problem of the stochastic model."""
import logging
import time
from typing import Any, Dict

import gurobipy as gp
from gurobipy import GRB, quicksum

from classes import Pixel, Satellite
from src.instance.instance import Instance

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SubProblem:
    """Class for the sub problem of the stochastic model."""

    def __init__(self, instance: Instance, period: int, scenario: Dict) -> None:
        """Initialize the sub problem."""
        self.model = gp.Model(name="SubProblem")

        # Instance
        self.t: int = period
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.type_of_flexibility: str = instance.type_of_flexibility
        self.is_continuous_X: bool = instance.is_continuous_X

        # TODO - change to scenario
        self.pixels: Dict[str, Pixel] = scenario["pixels"]
        self.costs: Dict[str, Dict] = scenario["costs"]
        self.fleet_size_required: Dict[str, Any] = scenario["fleet_size_required"]

        # Create model
        self.model = self.__create_model()

    def __create_model(self):
        """Create the model."""
        return gp.Model(name="SubProblem")

    def __add_variables(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel]
    ) -> None:
        """Add variables to the model."""
        logger.info("[SUBPROBLEM] Adding variables to sub problem")
        self.X = dict(
            [
                (
                    (s, q, self.t),
                    self.model.addVar(vtype=GRB.BINARY, name=f"X_s{s}_t{self.t}"),
                )
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )
        logger.info(f"Number of variables X: {len(self.X)}")

        # 2. add variable Z: binary variable to decide if a satellite is used to serve a pixel
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
                        vtype=type_variable, name=f"Z_s{s}_k{k}_t{self.t}"
                    ),
                )
                for s in satellites.keys()
                for k in pixels.keys()
            ]
        )
        logger.info(f"Number of variables Z: {len(self.Z)}")

        # 3. add variable W: binary variable to decide if a pixel is served from dc
        logger.info("[SUBPROBLEM] Add variable W")
        self.W = dict(
            [
                (
                    (k, self.t),
                    self.model.addVar(vtype=type_variable, name=f"W_k{k}_t{self.t}"),
                )
                for k in pixels.keys()
            ]
        )
        logger.info(f"Number of variables W: {len(self.W)}")

    def __add_objective(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel], costs: Dict
    ) -> None:
        """Add objective function to the model."""
        # 1. add cost operating satellites
        self.cost_operating_satellites = quicksum(
            [
                (satellite.cost_operation[q][self.t]) * self.X[(s, q, self.t)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )

        # 2. add cost served from satellite
        self.cost_served_from_satellite = quicksum(
            [
                costs["satellite"][(s, k, self.t)]["total"] * self.Z[(s, k, self.t)]
                for s in satellites.keys()
                for k in pixels.keys()
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

    def solve_model(self, fixed_y, final_solution) -> None:
        """Solve the model."""
        self.__add_variables(self.satellites, self.pixels)
        self.__add_objective(self.satellites, self.pixels, self.costs)

        # Add Constraints
        # (1) operating satellite
        for s, satellite in self.satellites.items():
            if self.type_of_flexibility == 1:  # opera siempre con la misma capacidad
                for q in satellite.capacity.keys():
                    nameConstraint = f"R_Operating_s{s}_q{q}_t{self.t}"
                    self.model.addConstr(
                        self.X[(s, q, self.t)] == fixed_y[(s, q)],
                        name=nameConstraint,
                    )
            elif self.type_of_flexibility == 2:  # opera o no con la misma capacidad
                for q in satellite.capacity.keys():
                    nameConstraint = f"R_Operating_s{s}_q{q}_t{self.t}"
                    self.model.addConstr(
                        self.X[(s, q, self.t)] <= fixed_y[(s, q)],
                        name=nameConstraint,
                    )
            elif (
                self.type_of_flexibility == 3
            ):  # opera o no con a lo mas la capacidad de apertura
                for q, capacity in satellite.capacity.items():
                    for q_lower, capacity_lower in satellite.capacity.items():
                        if capacity >= capacity_lower:
                            nameConstraint = f"R_Operating_s{s}_q{q_lower}_t{self.t}"
                            self.model.addConstr(
                                self.X[(s, q_lower, self.t)] <= fixed_y[(s, q)],
                                name=nameConstraint,
                            )

        # (2) capacity satellite
        for s, satellite in self.satellites.items():
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
                nameConstratint = f"R_Assign_s{s}_k{k}_t{self.t}"
                self.model.addConstr(
                    self.Z[(s, k, self.t)]
                    - quicksum(
                        [self.X[(s, q, self.t)] for q in satellite.capacity.keys()]
                    )
                    <= 0,
                    name=nameConstratint,
                )

        # (4) demand satisfied
        for k in self.pixels.keys():
            nameConstraint = f"R_demand_k{k}_t{self.t}"
            self.model.addConstr(
                quicksum([self.Z[(s, k, self.t)] for s in self.satellites.keys()])
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

            self.model.dispose()  # TODO - check if it is necessary

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

            self.model.dispose()  # TODO - check if it is necessary

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
