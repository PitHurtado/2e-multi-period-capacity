"""Main module for the SAA application."""
import json

from src.instance.instance import Instance
from src.model.deterministic import FlexibilityModel
from src.utils import LOGGER as logger

if __name__ == "__main__":
    logger.info("[MAIN DETERMINISTIC] Starting deterministic model")

    # (1) Generate instance:
    folder_path = "./data/results/deterministic/"
    logger.info("[MAIN DETERMINISTIC] Generating instances")
    instance_to_solve: Instance = Instance(
        id_instance="expected",
        capacity_satellites={"2": 2, "4": 4, "6": 6, "8": 8},
        is_continuous_x=False,
        alpha=0.5,
        beta=0.5,
        type_of_flexibility=2,
        periods=12,
        N=1,
        is_evaluation=False,
    )
    scenario = instance_to_solve.get_scenario_expected()
    instance_to_solve.scenarios = {"expected": scenario}

    # (2) Create model:
    logger.info(
        f"[MAIN DETERMINISTIC] Instance generated - instance_to_solve {instance_to_solve}"
    )
    model = FlexibilityModel(instance_to_solve)
    model.build()
    model.solve()

    # print("Objective function value: ", model.objective.getValue())
    # print(
    #     "cost_allocation_satellites value: ",
    #     model.cost_allocation_satellites.getValue(),
    # )
    # print(
    #     "cost_operating_satellitesn value: ", model.cost_operating_satellites.getValue()
    # )
    # print(
    #     "cost_served_from_satellite value: ",
    #     model.cost_served_from_satellite.getValue(),
    # )
    # print("cost_served_from_dc value: ", model.cost_served_from_dc.getValue())

    # (3) Save results:
    Y_solution = {str(keys): value.X for keys, value in model.model._Y.items()}
    Y_solution["objective"] = model.objective.getValue()
    Y_solution[
        "cost_installation_satellites"
    ] = model.cost_installation_satellites.getValue()
    Y_solution["cost_operating_satellites"] = model.cost_operating_satellites.getValue()
    Y_solution[
        "cost_served_from_satellite"
    ] = model.cost_served_from_satellite.getValue()
    Y_solution["cost_served_from_dc"] = model.cost_served_from_dc.getValue()
    Y_solution["scenarios"] = instance_to_solve.get_info()

    path_file_output = (
        folder_path + f"deterministic_{instance_to_solve.id_instance}.json"
    )
    with open(path_file_output, "w") as file:
        file.write(json.dumps(Y_solution, indent=4))
    print(f"Results saved in {path_file_output}")

    print("-----------------------------------")
    print(json.dumps(Y_solution, indent=4))
