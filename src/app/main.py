"""Main module to solve the Branch and Cut algorithm"""
import logging

from src.app.main_branch_and_cut import Main
from src.instance.instance_generator import InstanceGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    # (1) Generate instance:
    instances = InstanceGenerator().get_instances()

    # (2) Solve:
    run_time = 3600
    for instance in instances:
        logger.info(f"Solving instance {instance.id_instance}")
        main = Main(run_time)
        folder_path = "../results/branch_and_cut/"
        main.solve(instance, folder_path)
        logger.info(f"Instance {instance.id_instance} solved")
