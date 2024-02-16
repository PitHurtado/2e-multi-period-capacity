"""Module of instance generator."""
import itertools
import logging
from typing import Any, Dict, List

from src.instance.instance import Instance

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Experiment:
    """Class to generate instances."""

    def __init__(self, N_evaluation: int, M: int, folder_path: str):
        self.N_evaluation = N_evaluation
        self.M = M
        self.folder_path = folder_path

    def __get_combinations(self) -> itertools.product:
        """Return a list of combinations"""
        N = [1, 1]
        capacity_satellites = [[2, 6, 12]]
        is_continuous_x = [True, False]
        type_of_flexibility = [1, 2]
        alpha = [0.1]
        beta = [0.1]
        # TODO add more combinations
        # N = [10, 20, 30, 40, 50]
        # capacity_satellites = [[2, 6, 12], [2, 4, 6, 8], [2, 4, 6, 8, 12]]
        # is_continuous_x = [True, False]
        # type_of_flexibility = [1, 2]
        # alpha = [0.1, 0.5]
        # beta = [0.1, 0.5]
        return itertools.product(
            N, capacity_satellites, is_continuous_x, type_of_flexibility, alpha, beta
        )

    def get_info_combinations(self) -> List[Dict[str, Any]]:
        """Return a list of combinations"""
        combinations = self.__get_combinations()
        info_combinations = []
        for combination in combinations:
            (
                N,
                capacity_satellites,
                is_continuous_x,
                type_of_flexibility,
                alpha,
                beta,
            ) = combination
            info_combinations.append(
                {
                    "N": N,
                    "capacity_satellites": capacity_satellites,
                    "is_continuous_x": is_continuous_x,
                    "type_of_flexibility": type_of_flexibility,
                    "alpha": alpha,
                    "beta": beta,
                    "periods": 12,
                    "N_evaluation": self.N_evaluation,
                    "M": self.M,
                }
            )
        return info_combinations

    def generate_instances(self, debug: bool = False) -> List[Dict[str, Any]]:
        """Generate instances for training and evaluation. Return a list of instances."""
        combinations = self.__get_combinations()
        experiments = []
        index = 0
        for combination in combinations:
            # training instances
            instances_train = {}
            (
                N,
                capacity_satellites,
                is_continuous_x,
                type_of_flexibility,
                alpha,
                beta,
            ) = combination
            for m in range(self.M):
                id_instance = f"id_{index}_M_{m}_train"
                logger.info(
                    f"[EXPERIMENT] Generating instance {id_instance} - combination {combination}"
                )
                instance = Instance(
                    id_instance=id_instance,
                    capacity_satellites=capacity_satellites,
                    is_continuous_x=is_continuous_x,
                    alpha=alpha,
                    beta=beta,
                    type_of_flexibility=type_of_flexibility,
                    periods=12,
                    N=N,
                    is_evaluation=False,
                )
                if debug:
                    logger.info(
                        f"[EXPERIMENT] Instance training {id_instance} \n {instance}"
                    )
                instances_train[id_instance] = instance
            logger.info(
                f"[EXPERIMENT] Generated {len(instances_train)} instances for training"
            )

            # evaluation instances
            id_instance = f"id_{index}_testing"
            instance_evaluation = Instance(
                id_instance=id_instance,
                capacity_satellites=capacity_satellites,
                is_continuous_x=is_continuous_x,
                alpha=alpha,
                beta=beta,
                type_of_flexibility=type_of_flexibility,
                periods=12,
                N=self.N_evaluation,
                is_evaluation=True,
            )
            if debug:
                logger.info(
                    f"[EXPERIMENT] Instance testing {id_instance} \n {instance_evaluation}"
                )

            experiments.append(
                {
                    "instances_train": instances_train,
                    "instance_evaluation": instance_evaluation,
                }
            )
            index += 1
        logger.info(f"[EXPERIMENT] Generated {len(experiments)} experiments")
        return experiments


# if __name__ == "__main__":
#     experiment = Experiment(N_evaluation=2, M=2, folder_path="data")
#     experiment.generate_instances(debug=True)
