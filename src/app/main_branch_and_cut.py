"""Module of main branch and cut."""
import json
from typing import Any, Dict, List

from src.instance.instance import Instance
from src.instance.scenario import Scenario
from src.model.branch_and_cut import Branch_and_Cut
from src.utils import LOGGER as logger

if __name__ == "__main__":
    # (1) Generate instance
    folder_path = "../results/byc/"
    logger.info("[MAIN BRANCH AND CUT] Generating instances")
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

    # (2) Create model
    logger.info(
        f"[MAIN BRANCH AND CUT] Instance generated - instance_to_solve {instance_to_solve}"
    )
    solver = Branch_and_Cut(instance_to_solve)
    solver.solve(max_run_time=3600, warm_start=False)

    # (3) Save results:
    Y_solution = {str(keys): value.X for keys, value in solver.MP.model._Y.items()}
    # Y_solution["objective"] = solver.MP.model._total_cost.getValue()
    # Y_solution[
    #     "cost_installation_satellites"
    # ] = solver.MP.model._cost_installation_satellites.getValue()

    # path_file_output = (
    #     folder_path + f"deterministic_{instance_to_solve.id_instance}.json"
    # )
    # with open(path_file_output, "w") as file:
    #     file.write(json.dumps(Y_solution, indent=4))
    # print(f"Results saved in {path_file_output}")

    print("-----------------------------------")
    print(json.dumps(Y_solution, indent=4))
