"""Main module for the SAA application."""

from src.instance.instance import Instance
from src.model.deterministic import FlexibilityModel
from src.utils import LOGGER as logger

if __name__ == "__main__":
    logger.info("[MAIN DETERMINISTIC] Starting deterministic model")

    # (1) Generate instance:
    folder_path = "../results/deterministic/"
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

    # (3) Save results:
    Y_solution = {keys: value.X for keys, value in model.model._Y.items()}
    print(Y_solution)
