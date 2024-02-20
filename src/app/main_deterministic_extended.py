"""Main module for the SAA application."""
import json

from src.instance.experiment import Experiment
from src.instance.instance import Instance # type: ignore
from src.model.deterministic_extended import FlexibilityModelExtended
from src.utils import LOGGER as logger

if __name__ == "__main__":
    # (1) Generate instance:
    folder_path = "./data/results/deterministic_extended/"

    logger.info("[MAIN DETERMINISTIC EXTENDED] Starting deterministic model")
    logger.info("[MAIN DETERMINISTIC EXTENDED] Generating instances")

    # (1.1) Generate instance:
    instance_generated = Experiment(
        N_evaluation=1, M=1, folder_path=folder_path
    ).generate_instances()
    # (1.2) Select instance to solve:
    for i, experiment in enumerate(instance_generated):
        id_experiment = (1 + i) * 100
        logger.info(f"[MAIN DETERMINISTIC EXTENDED] Experiment {id_experiment} started")
        for id_instance, instance in experiment["instances_train"].items():
            logger.info(f"[MAIN DETERMINISTIC EXTENDED] Instance to solve {instance}")
            # (2) Create model:
            solver = FlexibilityModelExtended(instance)
            solver.build()
            solver.solve()

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
            Y_solution["scenarios"] = instance.get_info()

            path_file_output = (
                folder_path + f"deterministic_{instance.id_instance}.json"
            )
            with open(path_file_output, "w") as file:
                file.write(json.dumps(Y_solution, indent=4))
            print(f"Results saved in {path_file_output}")

            print("-----------------------------------")
            print(json.dumps(Y_solution, indent=4))
