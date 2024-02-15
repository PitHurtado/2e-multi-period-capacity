"""Module to solve the Branch and Cut algorithm"""
import json
import logging

from src.instance.instance import Instance
from src.model.branch_and_cut import Branch_and_Cut

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Main:
    """Class to define the main runner"""

    def __init__(self, run_time):
        self.run_time = run_time

    def solve(self, instance: Instance, folder_path: str):
        """Solve the instance"""
        # (1) Create Branch and Cut:
        BC = Branch_and_Cut(instance)

        # (2) Solve:
        BC.solve(self.run_time, False)

        # (3) Save metrics:
        run_time = BC.run_time
        optimality_gap = BC.optimality_gap
        objective_value = BC.objective_value
        best_bound_value = BC.best_bound_value
        initial_upper_bound = BC.initial_upper_bound

        # (4) Save results:
        results = {
            "run_time": run_time,
            "optimality_gap": optimality_gap,
            "objective_value": objective_value,
            "best_bound_value": best_bound_value,
            "initial_upper_bound": initial_upper_bound,
            "id_instance": instance.id_instance,
        }
        logger.info(f"[Main] Results: {results}")
        results.update(BC.get_metrics_from_fixed_solution(folder_path))

        file_name = f"{folder_path}/id_instance_{instance.id_instance}_results.json"
        with open(file_name, "w") as f:
            json.dump(results, f)
        logger.info(f"[Main] Results saved in results.json")
        return results
