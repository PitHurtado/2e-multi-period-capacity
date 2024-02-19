"""Model Multiperiod Flexible Operation."""
from typing import Any, Dict

import gurobipy as gb
from gurobipy import GRB, quicksum

from src.classes import Pixel, Satellite
from src.instance.instance import Instance
from src.utils import LOGGER as logger


class FlexibilityModel:
    """Model Multiperiod Flexible Operation."""

    def __init__(self, instance: Instance, id_scenario: str = "expected"):
        self.model = gb.Model(name="Deterministic")

        # Params from instance
        self.instance: Instance = instance
        self.periods: int = instance.periods
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.pixels: Dict[str, Pixel] = instance.scenarios[id_scenario].pixels
        self.cost_serving: Dict[str, Dict] = instance.scenarios[
            id_scenario
        ].get_cost_serving()
        self.fleet_size_required: Dict[str, Dict] = instance.scenarios[
            id_scenario
        ].get_fleet_size_required()

        # variables
        self.X = {}
        self.Y = {}
        self.W = {}
        self.Z = {}

        self.objective = None
        self.constraints = {}

    def build(self) -> None:
        """Build the model."""
        logger.info("[DETERMINISTIC] Build model")

        # 1.  add variables
        self.__add_variables(self.satellites, self.pixels)

        # 2. add objective
        self.__add_objective(self.satellites, self.pixels, self.cost_serving)

        # 3. add constraints
        self.__add_constraints(
            self.satellites,
            self.pixels,
            self.fleet_size_required,
        )

        # 4. update model
        self.model.update()
        logger.info("[DETERMINISTIC] Model built")

    def __add_variables(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel]
    ) -> None:
        """Add variables to model."""
        # 1. add variable X: binary variable to decide if a satellite is operating in a period
        logger.info("[DETERMINISTIC] Add variable X")
        self.X = dict(
            [
                (
                    (s, q, t),
                    self.model.addVar(vtype=GRB.BINARY, name=f"X_s{s}_t{t}"),
                )
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
                for t in range(self.periods)
            ]
        )
        logger.info(f"Number of variables X: {len(self.X)}")

        # 2. add variable Z: binary variable to decide if a satellite is used to serve a pixel
        logger.info("[DETERMINISTIC] Add variable Z")
        self.Z = dict(
            [
                (
                    (s, k, t),
                    self.model.addVar(vtype=GRB.BINARY, name=f"Z_s{s}_k{k}_t{t}"),
                )
                for s in satellites.keys()
                for k in pixels.keys()
                for t in range(self.periods)
            ]
        )
        logger.info(f"Number of variables Z: {len(self.Z)}")

        # 3. add variable W: binary variable to decide if a pixel is served from dc
        logger.info("[DETERMINISTIC] Add variable W")
        self.W = dict(
            [
                ((k, t), self.model.addVar(vtype=GRB.BINARY, name=f"W_k{k}_t{t}"))
                for k in pixels.keys()
                for t in range(self.periods)
            ]
        )
        logger.info(f"Number of variables W: {len(self.W)}")

        # 4. add variable Y: binary variable to decide if a satellite is open or not
        logger.info("[DETERMINISTIC] Add variable Y")
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

        self.model._X = self.X
        self.model._Y = self.Y
        self.model._W = self.W
        self.model._Z = self.Z

    def __add_objective(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        costs: Dict[str, Any],
    ) -> None:
        """Add objective to model."""
        # 1. add cost allocation satellites
        logger.info("[DETERMINISTIC] Add objective")
        self.cost_allocation_satellites = quicksum(
            [
                (satellite.cost_fixed[q] / 20) * self.Y[(s, q)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )

        # 2. add cost operating satellites
        self.cost_operating_satellites = quicksum(
            [
                (satellite.cost_operation[q][t] / 8) * self.X[(s, q, t)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
                for t in range(self.periods)
            ]
        )

        # 3. add cost served from satellite
        self.cost_served_from_satellite = quicksum(
            [
                costs["satellite"][(s, k, t)]["total"] * self.Z[(s, k, t)]
                for s in satellites.keys()
                for k in pixels.keys()
                for t in range(self.periods)
            ]
        )

        # 4. add cost served from dc
        self.cost_served_from_dc = quicksum(
            [
                costs["dc"][(k, t)]["total"] * self.W[(k, t)]
                for k in pixels.keys()
                for t in range(self.periods)
            ]
        )

        self.objective = (
            self.cost_allocation_satellites
            + self.cost_served_from_dc
            + self.cost_served_from_satellite
            + self.cost_operating_satellites
        )
        # logger.info(f"[DETERMINISTIC] Objective: \n{self.objective}")
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def __add_constraints(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        fleet_size_required: Dict[str, Any],
    ) -> None:
        """Add constraints to model."""
        self.__add_constr_allocation_satellite(satellites)
        self.__add_constr_operating_satellite(satellites)
        self.__add_constr_capacity_satellite(satellites, pixels, fleet_size_required)
        self.__add_constr_assign_pixel_sallite(satellites, pixels)
        self.__add_constr_demand_satified(satellites, pixels)

        # dumming constraints
        # self.__add_constr_dumming(satellites)

    def __add_constr_dumming(self, satellites: Dict[str, Satellite]) -> None:
        """Add constraint dumming."""
        logger.info("[DETERMINISTIC] Add constraint dumming")
        nameConstraint = f"R_Dumming"
        self.model.addConstr(
            quicksum(
                [
                    self.Y[(s, q)]
                    for s in satellites.keys()
                    for q in satellites[s].capacity.keys()
                ]
            )
            >= 1,
            name=nameConstraint,
        )

    def __add_constr_allocation_satellite(
        self, satellites: Dict[str, Satellite]
    ) -> None:
        """Add constraint allocation satellite."""
        logger.info("[DETERMINISTIC] Add constraint allocation satellite")
        for s, satellite in satellites.items():
            nameConstraint = f"R_Open_s{s}"
            self.model.addConstr(
                quicksum([self.Y[(s, q)] for q in satellite.capacity.keys()]) <= 1,
                name=nameConstraint,
            )

    def __add_constr_operating_satellite(
        self, satellites: Dict[str, Satellite]
    ) -> None:
        """Add constraint operating satellite."""
        logger.info("[DETERMINISTIC] Add constraint operating satellite")
        for t in range(self.periods):
            for s, satellite in satellites.items():
                for q in satellite.capacity.keys():
                    for q_lower in satellite.capacity.keys():
                        if q_lower <= q:
                            nameConstraint = f"R_Operating_s{s}_q{q_lower}_t{t}"
                            self.model.addConstr(
                                self.X[(s, q, t)] <= self.Y[(s, q)],
                                name=nameConstraint,
                            )

    def __add_constr_capacity_satellite(
        self,
        satellites: Dict[str, Satellite],
        pixels: Dict[str, Pixel],
        fleet_size_required: Dict[str, Any],
    ) -> None:
        """Add constraint capacity satellite."""
        logger.info("[DETERMINISTIC] Add constraint capacity satellite")
        for t in range(self.periods):
            for s, satellite in satellites.items():
                nameConstraint = f"R_capacity_s{s}_t{t}"
                # logger.info(f"[DETERMINISTIC] Add constraint: {nameConstraint}")
                self.model.addConstr(
                    quicksum(
                        [
                            self.Z[(s, k, t)]
                            * fleet_size_required["satellite"][(s, k, t)]["fleet_size"]
                            for k in pixels.keys()
                        ]
                    )
                    - quicksum(
                        [
                            self.X[(s, q, t)] * capacity
                            for q, capacity in satellite.capacity.items()
                        ]
                    )
                    <= 0,
                    name=nameConstraint,
                )

    def __add_constr_assign_pixel_sallite(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel]
    ) -> None:
        """Add constraint assign pixel to satellite."""
        logger.info("[DETERMINISTIC] Add constraint assign pixel to satellite")
        for t in range(self.periods):
            for k in pixels.keys():
                for s, satellite in satellites.items():
                    nameConstratint = f"R_Assign_s{s}_k{k}_t{t}"
                    self.model.addConstr(
                        self.Z[(s, k, t)]
                        - quicksum(
                            [self.X[(s, q, t)] for q in satellite.capacity.keys()]
                        )
                        <= 0,
                        name=nameConstratint,
                    )

    def __add_constr_demand_satified(
        self, satellites: Dict[str, Satellite], pixels: Dict[str, Pixel]
    ):
        """Add constraint demand satisfied."""
        logger.info("[DETERMINISTIC] Add constraint demand satisfied")
        for t in range(self.periods):
            for k in pixels.keys():
                nameConstraint = f"R_demand_k{k}_t{t}"
                self.model.addConstr(
                    quicksum([self.Z[(s, k, t)] for s in satellites.keys()])
                    + quicksum([self.W[(k, t)]])
                    == 1,
                    name=nameConstraint,
                )

    def solve(self):
        """Solve the model."""
        logger.info("[DETERMINISTIC] Solve model")
        self.model.optimize()
        logger.info("[DETERMINISTIC] Model solved")


# class DeterministicWithMutipleInstances(ModelMultiperiod):
#     """Model Deterministic with mutiple instances."""

#     def __init__(self, instance: Instance, reporter: Reporter):
#         super().__init__(name="DeterministicMultiScenario", reporter=reporter)
#         self.instance = instance
#         self.periods = instance.periods

#         # variables
#         self.X = {}
#         self.Y = {}
#         self.W = {}
#         self.Z = {}

#         self.objective = None
#         self.constraints = {}

#     def build(self) -> None:
#         """Build the model."""
#         logger.info("[DETERMINISTIC-Full] Build model")

#         # 1.  add variables
#         self.__add_variables(
#             self.instance.satellites, self.instance.pixels, self.instance.scenarios
#         )

#         # 2. add objective
#         self.__add_objective(
#             self.instance.satellites, self.instance.pixels, self.instance.scenarios
#         )

#         # 3. add constraints
#         self.__add_constraints(
#             self.instance.satellites, self.instance.pixels, self.instance.scenarios
#         )

#         # 4. update model
#         self.model.update()
#         logger.info("[DETERMINISTIC-Full] Model built")

#     def __add_variables(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Any],
#     ) -> None:
#         """Add variables to model."""
#         # 1. add variable X: binary variable to decide if a satellite is operating in a period in a scenario
#         logger.info("[DETERMINISTIC-Full] Add variable X")
#         self.X = dict(
#             [
#                 (
#                     (s, q, t, n),
#                     self.model.addVar(vtype=GRB.BINARY, name=f"X_s{s}_t{t}_n{n}"),
#                 )
#                 for s, satellite in satellites.items()
#                 for q in satellite.capacity.keys()
#                 for t in range(self.periods)
#                 for n in scenarios.keys()
#             ]
#         )
#         logger.info(f"Number of variables X: {len(self.X)}")

#         # 2. add variable Z: binary variable to decide if a satellite is used to serve a pixel in a scenario
#         logger.info("[DETERMINISTIC-Full] Add variable Z")
#         self.Z = dict(
#             [
#                 (
#                     (s, k, t, n),
#                     self.model.addVar(vtype=GRB.BINARY, name=f"Z_s{s}_k{k}_t{t}_n{n}"),
#                 )
#                 for s in satellites.keys()
#                 for k in pixels.keys()
#                 for t in range(self.periods)
#                 for n in scenarios.keys()
#             ]
#         )
#         logger.info(f"Number of variables Z: {len(self.Z)}")

#         # 3. add variable W: binary variable to decide if a pixel is served from dc in a scenario
#         logger.info("[DETERMINISTIC-Full] Add variable W")
#         self.W = dict(
#             [
#                 (
#                     (k, t, n),
#                     self.model.addVar(vtype=GRB.BINARY, name=f"W_k{k}_t{t}_n{n}"),
#                 )
#                 for k in pixels.keys()
#                 for t in range(self.periods)
#                 for n in scenarios.keys()
#             ]
#         )
#         logger.info(f"Number of variables W: {len(self.W)}")

#         # 4. add variable Y: binary variable to decide if a satellite is open or not
#         logger.info("[DETERMINISTIC-Full] Add variable Y")
#         self.Y = dict(
#             [
#                 (
#                     (s, q),
#                     self.model.addVar(vtype=GRB.BINARY, name=f"Y_s{s}_q{q}"),
#                 )
#                 for s, satellite in satellites.items()
#                 for q in satellite.capacity.keys()
#             ]
#         )
#         logger.info(f"Number of variables Y: {len(self.Y)}")

#     def __add_objective(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Scenario],
#     ) -> None:
#         """Add objective to model."""
#         # 1. add cost allocation satellites
#         logger.info("[DETERMINISTIC-Full] Add objective")
#         self.cost_allocation_satellites = quicksum(
#             [
#                 (satellite.cost_fixed[q]) * self.Y[(s, q)]
#                 for s, satellite in satellites.items()
#                 for q in satellite.capacity.keys()
#             ]
#         )

#         # 2. add cost operating satellites in a scenario
#         self.cost_operating_satellites = quicksum(
#             [
#                 (satellite.cost_operation[q][t]) * self.X[(s, q, t, n)]
#                 for s, satellite in satellites.items()
#                 for q in satellite.capacity.keys()
#                 for t in range(self.periods)
#                 for n in scenarios.keys()
#             ]
#         )

#         # 3. add cost served from satellite in a scenario
#         self.cost_served_from_satellite = quicksum(
#             [
#                 scenario.costs["satellite"][(s, k, t)]["total"] * self.Z[(s, k, t, n)]
#                 for s in satellites.keys()
#                 for k in pixels.keys()
#                 for t in range(self.periods)
#                 for n, scenario in scenarios.items()
#             ]
#         )

#         # 4. add cost served from dc in a scenario
#         self.cost_served_from_dc = quicksum(
#             [
#                 scenario.costs["dc"][(k, t)]["total"] * self.W[(k, t, n)]
#                 for k in pixels.keys()
#                 for t in range(self.periods)
#                 for n, scenario in scenarios.items()
#             ]
#         )

#         self.objective = self.cost_allocation_satellites + 1 / len(scenarios) * (
#             self.cost_served_from_dc
#             + self.cost_served_from_satellite
#             + self.cost_operating_satellites
#         )
#         logger.info(f"[DETERMINISTIC-Full] Objective: \n{self.objective}")
#         self.model.setObjective(self.objective, GRB.MINIMIZE)

#     def __add_constraints(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Scenario],
#     ) -> None:
#         """Add constraints to model."""
#         self.__add_constr_allocation_satellite(satellites)
#         self.__add_constr_operating_satellite(satellites, scenarios)
#         self.__add_constr_capacity_satellite(satellites, pixels, scenarios)
#         self.__add_constr_assign_pixel_sallite(satellites, pixels, scenarios)
#         self.__add_constr_demand_satified(satellites, pixels, scenarios)

#     def __add_constr_allocation_satellite(
#         self, satellites: Dict[str, Satellite]
#     ) -> None:
#         """Add constraint allocation satellite."""
#         logger.info("[DETERMINISTIC-Full] Add constraint allocation satellite")
#         for s, satellite in satellites.items():
#             nameConstraint = f"R_Open_s{s}"
#             # logger.info(f"[DETERMINISTIC-Full] Add constraint: {nameConstraint}")
#             self.model.addConstr(
#                 quicksum([self.Y[(s, q)] for q in satellite.capacity.keys()]) <= 1,
#                 name=nameConstraint,
#             )

#     def __add_constr_operating_satellite(
#         self, satellites: Dict[str, Satellite], scenarios: Dict[str, Scenario]
#     ) -> None:
#         """Add constraint operating satellite."""
#         logger.info("[DETERMINISTIC-Full] Add constraint operating satellite")
#         for t in range(self.periods):
#             for s, satellite in satellites.items():
#                 for q in satellite.capacity.keys():
#                     for n in scenarios.keys():
#                         nameConstraint = f"R_Operating_s{s}_q{q}_t{t}_n{n}"
#                         # logger.info(f"[DETERMINISTIC-Full] Add constraint: {nameConstraint}")
#                         self.model.addConstr(
#                             self.X[(s, q, t, n)] <= self.Y[(s, q)],
#                             name=nameConstraint,
#                         )

#     def __add_constr_capacity_satellite(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Scenario],
#     ) -> None:
#         """Add constraint capacity satellite."""
#         logger.info("[DETERMINISTIC-Full] Add constraint capacity satellite")
#         for t in range(self.periods):
#             for s, satellite in satellites.items():
#                 for n, scenario in scenarios.items():
#                     nameConstraint = f"R_capacity_s{s}_t{t}_n{n}"
#                     # logger.info(f"[DETERMINISTIC-Full] Add constraint: {nameConstraint}")
#                     self.model.addConstr(
#                         quicksum(
#                             [
#                                 self.Z[(s, k, t, n)]
#                                 * scenario.fleet_size["small"][(s, k, t)]["fleet_size"]
#                                 for k in pixels.keys()
#                             ]
#                         )
#                         - quicksum(
#                             [
#                                 self.Y[(s, q)] * capacity
#                                 for q, capacity in satellite.capacity.items()
#                             ]
#                         )
#                         <= 0,
#                         name=nameConstraint,
#                     )

#     def __add_constr_assign_pixel_sallite(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Scenario],
#     ) -> None:
#         """Add constraint assign pixel to satellite."""
#         logger.info("[DETERMINISTIC-Full] Add constraint assign pixel to satellite")
#         for t in range(self.periods):
#             for k in pixels.keys():
#                 for s, satellite in satellites.items():
#                     for n in scenarios.keys():
#                         nameConstratint = f"R_Assign_s{s}_k{k}_t{t}_n{n}"
#                         # logger.info(f"[DETERMINISTIC-Full] Add constraint: {nameConstratint}")
#                         self.model.addConstr(
#                             self.Z[(s, k, t, n)]
#                             - quicksum(
#                                 [
#                                     self.X[(s, q, t, n)]
#                                     for q in satellite.capacity.keys()
#                                 ]
#                             )
#                             <= 0,
#                             name=nameConstratint,
#                         )

#     def __add_constr_demand_satified(
#         self,
#         satellites: Dict[str, Satellite],
#         pixels: Dict[str, Pixel],
#         scenarios: Dict[str, Scenario],
#     ):
#         """Add constraint demand satisfied."""
#         logger.info("[DETERMINISTIC-Full] Add constraint demand satisfied")
#         for t in range(self.periods):
#             for k in pixels.keys():
#                 for n in scenarios.keys():
#                     nameConstraint = f"R_demand_k{k}_t{t}_n{n}"
#                     # logger.info(f"[DETERMINISTIC-Full] Add constraint: {nameConstraint}")
#                     self.model.addConstr(
#                         quicksum([self.Z[(s, k, t, n)] for s in satellites.keys()])
#                         + quicksum([self.W[(k, t, n)]])
#                         == 1,
#                         name=nameConstraint,
#                     )