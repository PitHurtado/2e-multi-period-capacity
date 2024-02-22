"""Main module for the SAA application."""
import sys

from src.app.main_local import Main
from src.instance.experiment import Experiment
from src.utils import LOGGER as logger

if __name__ == "__main__":
    # (1) Generate instance:
    FOLDER_PATH = "./data/results/deterministic_extended/"

    logger.info("[MAIN DETERMINISTIC EXTENDED] Starting deterministic model")
    logger.info("[MAIN DETERMINISTIC EXTENDED] Generating instances")

    # (1.1) Generate instance:
    instance_list = Experiment(
        N_evaluation=0, M=10, folder_path=FOLDER_PATH
    ).generate_instances(include_expected=True)

    # (2) select cluster into supercloud
    main = Main(FOLDER_PATH)

    # (3) Get the pointers to the subset of instances to solve
    my_task_id = int(sys.argv[1])
    num_tasks = int(sys.argv[2])

    # (4) Get subset of instances to be solved:
    instances_to_solve = instance_list[my_task_id : len(instance_list) : num_tasks]

    # (4) Solve the instances:
    for experiment in instances_to_solve:
        for instance_train in experiment["instances_train"].values():
            try:
                main.solve(instance_train, run_time=3600)
            except:
                print("Error")

    # # (3) Get subset of instances to be solved:
    # instances_to_solve = instance_list
    # print(f"Total experiments: {len(instances_to_solve)}")

    # # (4) Solve the instances:
    # for experiment in instances_to_solve:
    #     for instance in experiment["instances_train"].values():
    #         try:
    #             print(instance.get_info())
    #             #main.solve(instance, run_time=3600)
    #         except:
    #             print("Error")
