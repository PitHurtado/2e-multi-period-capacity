"""Main module to solve the Branch and Cut algorithm"""

from src.instance.instance_generator import InstanceGenerator
from src.app.main_branch_and_cut import Main

if __name__ == "__main__":
    # (1) Generate instance:
    instances = InstanceGenerator().get_instances()

    # (2) Solve:
    run_time = 3600
    for instance in instances:
        main = Main(run_time)
        main.solve(instance)
