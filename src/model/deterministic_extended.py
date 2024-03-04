"""Model Multiperiod Flexible Operation."""
from typing import Dict

import gurobipy as gb
from gurobipy import GRB, quicksum

from src.classes import Satellite
from src.instance.instance import Instance
from src.instance.scenario import Scenario
from src.utils import LOGGER as logger


class FlexibilityModelExtended:
    """Model Multiperiod Flexible Operation."""

    def __init__(self, instance: Instance):
        self.model = gb.Model(name="Deterministic")

        # Params from instance and one scenario
        self.instance: Instance = instance
        self.periods: int = instance.periods
        self.satellites: Dict[str, Satellite] = instance.satellites
        self.scenarios: Dict[str, Scenario] = instance.scenarios

        # Params from instance
        self.type_of_flexibility: int = instance.type_of_flexibility
        self.is_continuous_x: bool = instance.is_continuous_x

        # variables
        self.Z = {}
        self.Y = {}
        self.W = {}
        self.X = {}

        # objective
        self.objective = None
        self.cost_installation_satellites = None
        self.cost_served_from_dc = None
        self.cost_served_from_satellite = None
        self.cost_operating_satellites = None

    def build(self) -> None:
        """Build the model."""
        logger.info("[DETERMINISTIC] Build model")
        self.__add_variables(self.satellites, self.scenarios)
        self.__add_objective(self.satellites, self.scenarios)
        self.__add_constraints(self.satellites, self.scenarios)

        self.model.update()
        logger.info("[DETERMINISTIC] Model built")

    def __add_variables(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Scenario]
    ) -> None:
        """Add variables to model."""
        type_variable = GRB.CONTINUOUS if self.is_continuous_x else GRB.BINARY

        # 1. add variable Z: binary variable to decide if a satellite is operating in a period with a capacity
        if self.type_of_flexibility == 2:
            self.Z = dict(
                [
                    (
                        (s, q, n, t),
                        self.model.addVar(
                            vtype=GRB.BINARY, name=f"Z_s{s}_q{q}_n{n}_t{t}"
                        ),
                    )
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for t in range(self.periods)
                    for n in scenarios.keys()
                ]
            )
        logger.info(f"[DETERMINISTIC] Number of variables Z: {len(self.Z)}")

        # 2. add variable X: binary variable to decide if a satellite is used to serve a pixel
        self.X = dict(
            [
                (
                    (s, k, n, t),
                    self.model.addVar(
                        vtype=type_variable, name=f"X_s{s}_k{k}_n{n}_t{t}", lb=0, ub=1
                    ),
                )
                for s in satellites.keys()
                for n, scenario in scenarios.items()
                for k in scenario.pixels.keys()
                for t in range(self.periods)
            ]
        )
        logger.info(f"[DETERMINISTIC] Number of variables X: {len(self.X)}")

        # 3. add variable W: binary variable to decide if a pixel is served from dc
        self.W = dict(
            [
                (
                    (k, n, t),
                    self.model.addVar(
                        vtype=type_variable, name=f"W_k{k}_n{n}_t{t}", lb=0, ub=1
                    ),
                )
                for n, scenario in scenarios.items()
                for k in scenario.pixels.keys()
                for t in range(self.periods)
            ]
        )
        logger.info(f"[DETERMINISTIC] Number of variables W: {len(self.W)}")

        # 4. add variable Y: binary variable to decide if a satellite is open or not
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
        logger.info(f"[DETERMINISTIC] Number of variables Y: {len(self.Y)}")

        self.model._X = self.Z
        self.model._Y = self.Y
        self.model._W = self.W
        self.model._Z = self.X

    def __add_objective(
        self,
        satellites: Dict[str, Satellite],
        scenarios: Dict[str, Scenario],
    ) -> None:
        """Add objective to model."""
        # 1. add cost installation satellites
        logger.info("[DETERMINISTIC] Add objective")
        self.cost_installation_satellites = quicksum(
            [
                satellite.cost_fixed[q] * self.Y[(s, q)]
                for s, satellite in satellites.items()
                for q in satellite.capacity.keys()
            ]
        )

        # 2. add cost operating satellites
        if self.type_of_flexibility == 1:
            self.cost_operating_satellites = quicksum(
                [
                    satellite.cost_operation[q][t] * self.Y[(s, q)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for t in range(self.periods)
                    for n in scenarios.keys()
                ]
            )
        else:
            self.cost_operating_satellites = quicksum(
                [
                    satellite.cost_operation[q][t] * self.Z[(s, q, n, t)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                    for t in range(self.periods)
                    for n in scenarios.keys()
                ]
            )

        # 3. add cost served from satellite
        self.cost_served_from_satellite = quicksum(
            [
                scenario.get_cost_serving("satellite")[(s, k, t)]["total"]
                * self.X[(s, k, n, t)]
                for s in satellites.keys()
                for n, scenario in scenarios.items()
                for k in scenario.pixels.keys()
                for t in range(self.periods)
            ]
        )

        # 4. add cost served from dc
        self.cost_served_from_dc = quicksum(
            [
                scenario.get_cost_serving("dc")[(k, t)]["total"] * self.W[(k, n, t)]
                for n, scenario in scenarios.items()
                for k in scenario.pixels.keys()
                for t in range(self.periods)
            ]
        )

        self.objective = self.cost_installation_satellites + (1 / len(scenarios)) * (
            self.cost_operating_satellites
            + self.cost_served_from_dc
            + self.cost_served_from_satellite
        )
        self.model.setObjective(self.objective, GRB.MINIMIZE)

    def __add_constraints(
        self,
        satellites: Dict[str, Satellite],
        scenarios: Dict[str, Scenario],
    ) -> None:
        """Add constraints to model."""

        if self.type_of_flexibility == 2:
            self.__add_constr_activation_satellite(satellites, scenarios)
            self.__add_constr_operating_capacity_satellite(satellites, scenarios)

        self.__add_constr_installation_satellite(satellites)
        self.__add_constr_capacity_satellite(satellites, scenarios)
        self.__add_constr_demand_satified(satellites, scenarios)

        # dummi constraints
        # self.__add_constr_dummi(satellites)

    def __add_constr_installation_satellite(
        self, satellites: Dict[str, Satellite]
    ) -> None:
        """Add constraint installation satellite."""
        logger.info("[DETERMINISTIC] Add constraint installation satellite")
        for s, satellite in satellites.items():
            nameConstraint = f"R_Open_s{s}"
            self.model.addConstr(
                quicksum([self.Y[(s, q)] for q in satellite.capacity.keys()]) <= 1,
                name=nameConstraint,
            )

    def __add_constr_activation_satellite(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Scenario]
    ) -> None:
        """Add constraint activation satellite."""
        logger.info("[DETERMINISTIC] Add constraint activation satellite")
        for s, satellite in satellites.items():
            for n in scenarios.keys():
                for t in range(self.periods):
                    nameConstraint = f"R_activation_s{s}_n{n}_t{t}"
                    self.model.addConstr(
                        quicksum(
                            [self.Z[(s, q, n, t)] for q in satellite.capacity.keys()]
                        )
                        <= quicksum(
                            [self.Y[(s, q)] for q in satellite.capacity.keys()]
                        ),
                        name=nameConstraint,
                    )

    def __add_constr_operating_capacity_satellite(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Scenario]
    ) -> None:
        """Add constraint operating satellite."""
        logger.info("[DETERMINISTIC] Add constraint operating satellite")
        for t in range(self.periods):
            for n in scenarios.keys():
                for s, satellite in satellites.items():
                    max_capacity = max(satellite.capacity.values())
                    for q, q_value in satellite.capacity.items():
                        if q_value < max_capacity:
                            nameConstraint = f"R_Operating_s{s}_q{q}_n{n}_t{t}"
                            q_higher_values = [
                                q_higher
                                for q_higher, q_higher_value in satellite.capacity.items()
                                if q_higher_value > q_value
                            ]
                            self.model.addConstr(
                                quicksum(
                                    [
                                        self.Z[(s, q_higher, n, t)]
                                        for q_higher in q_higher_values
                                    ]
                                )
                                <= 1 - self.Y[(s, q)],
                                name=nameConstraint,
                            )

    def __add_constr_capacity_satellite(
        self,
        satellites: Dict[str, Satellite],
        scenarios: Dict[str, Scenario],
    ) -> None:
        """Add constraint capacity satellite."""
        logger.info("[DETERMINISTIC] Add constraint capacity satellite")
        for t in range(self.periods):
            for s, satellite in satellites.items():
                for n, scenario in scenarios.items():
                    pixels = scenario.pixels
                    fleet_size_required = scenario.get_fleet_size_required("satellite")
                    nameConstraint = f"R_capacity_s{s}_n{n}_t{t}"
                    if self.type_of_flexibility == 2:
                        self.model.addConstr(
                            quicksum(
                                [
                                    self.X[(s, k, n, t)]
                                    * fleet_size_required[(s, k, t)]["fleet_size"]
                                    for k in pixels.keys()
                                ]
                            )
                            - quicksum(
                                [
                                    self.Z[(s, q, n, t)] * capacity
                                    for q, capacity in satellite.capacity.items()
                                ]
                            )
                            <= 0,
                            name=nameConstraint,
                        )
                    else:
                        self.model.addConstr(
                            quicksum(
                                [
                                    self.X[(s, k, n, t)]
                                    * fleet_size_required[(s, k, t)]["fleet_size"]
                                    for k in pixels.keys()
                                ]
                            )
                            - quicksum(
                                [
                                    self.Y[(s, q)] * capacity
                                    for q, capacity in satellite.capacity.items()
                                ]
                            )
                            <= 0,
                            name=nameConstraint,
                        )

    def __add_constr_demand_satified(
        self, satellites: Dict[str, Satellite], scenarios: Dict[str, Scenario]
    ):
        """Add constraint demand satisfied."""
        logger.info("[DETERMINISTIC] Add constraint demand satisfied")
        for n, scenario in scenarios.items():
            for t in range(self.periods):
                for k in scenario.pixels.keys():
                    nameConstraint = f"R_demand_k{k}_n{n}_t{t}"
                    self.model.addConstr(
                        quicksum([self.X[(s, k, n, t)] for s in satellites.keys()])
                        + quicksum([self.W[(k, n, t)]])
                        == 1,
                        name=nameConstraint,
                    )

    def __add_constr_dummi(self, satellites: Dict[str, Satellite]) -> None:
        """Add constraint dumming."""
        logger.info("[DETERMINISTIC] Add constraint dummi")
        nameConstraint = f"R_Dumming"
        self.model.addConstr(
            quicksum(
                [
                    self.Y[(s, q)]
                    for s, satellite in satellites.items()
                    for q in satellite.capacity.keys()
                ]
            )
            == 0,
            name=nameConstraint,
        )

    def solve(self):
        """Solve the model."""
        logger.info("[DETERMINISTIC] Solve model")
        self.model.optimize()
        logger.info("[DETERMINISTIC] Model solved")

    def set_params(self, params: Dict[str, int]) -> None:
        """Set parameters to model."""
        for key, item in params.items():
            self.model.setParam(key, item)
