"""Module of instance generator."""
import json
import logging

from src.instance.instance import Instance
from src.model.deterministic_extended import FlexibilityModelExtended
from src.utils import LOGGER as logger


class Main:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path

    def solve(self, instance: Instance, run_time: int):
        self.instance: Instance = instance
        logger.info(
            f"[MAIN DETERMINISTIC EXTENDED] Experiment {self.instance.id_instance} started"
        )
        logger.info(
            f"[MAIN DETERMINISTIC EXTENDED] Instance to solve \n{self.instance}"
        )
        # (2) Create model:

        logger.disabled = True
        logging.disable(logging.CRITICAL)
        solver = FlexibilityModelExtended(self.instance)
        solver.build()
        params_config = {"TimeLimit": run_time, "MIPGap": 0.0005}
        solver.set_params(params_config)
        solver.solve()
        logger.disabled = False
        logging.disable(logging.NOTSET)

        # (3) Save results:
        Y_solution = {str(keys): value.X for keys, value in solver.model._Y.items()}
        Y_solution["objective"] = solver.objective.getValue()
        Y_solution[
            "cost_installation_satellites"
        ] = solver.cost_installation_satellites.getValue()
        Y_solution[
            "cost_operating_satellites"
        ] = solver.cost_operating_satellites.getValue()
        Y_solution[
            "cost_served_from_satellite"
        ] = solver.cost_served_from_satellite.getValue()
        Y_solution["cost_served_from_dc"] = solver.cost_served_from_dc.getValue()
        Y_solution["scenarios"] = self.instance.get_info()

        path_file_output = (
            self.folder_path + f"deterministic_{self.instance.id_instance}.json"
        )
        with open(path_file_output, "w") as file:
            file.write(json.dumps(Y_solution, indent=4))
        print(f"Results saved in {path_file_output}")

        print("-----------------------------------")
        print(json.dumps(Y_solution, indent=4))
