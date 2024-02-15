"""Module of instance generator."""
import itertools
import logging
from typing import List

from src.instance.instance import Instance

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class InstanceGenerator:
    """Class to generate instances."""

    def __init__(self, N_testing: int, M: int, folder_path: str):
        self.N_testing = N_testing
        self.M = M
        self.folder_path = folder_path

    def get_instances(self) -> List[Instance]:
        """Return a list of instances"""

        # Params
        N = [10, 20, 30, 40, 50]
        capacity_satellites = [[2, 6, 12], [2, 4, 6, 8], [2, 4, 6, 8, 12]]
        is_continuous_X = [True, False]
        alpha = [0.1, 0.5]
        beta = [0.1, 0.5]
        type_of_flexibility = [1, 2]

        # Generate instances
        instances_list = []
        combinations = itertools.product(
            N, capacity_satellites, is_continuous_X, alpha, beta, type_of_flexibility
        )
        for combination in combinations:
            instances_list.append(
                Instance(
                    id_instance=f"{combination[0]}_{combination[1]}_{combination[2]}_{combination[3]}_{combination[4]}_{combination[5]}",
                    N=combination[0],
                    M=self.M,
                    capacity_satellites=combination[1],
                    is_continuous_X=combination[2],
                    alpha=combination[3],
                    beta=combination[4],
                    type_of_flexibility=combination[5],
                    folder_path=self.folder_path,
                    id_scenarios=self.__get_scenarios(combination[0]),
                )
            )
        logger.info(f"[Scenarios Generation] Generated {len(instances_list)} instances")
        # logger.info(f"[Scenarios Generation] Generated instances: {instances_list}")
        return instances_list

    def __get_scenarios(self, N: int) -> List[int]:
        """Return a list of scenarios"""
        scenarios_hardcoded = {
            "10": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "20": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
            ],
            "30": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
            ],
            "40": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
                33,
                34,
                35,
                36,
                37,
                38,
                39,
                40,
            ],
            "50": [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                28,
                29,
                30,
                31,
                32,
                33,
                34,
                35,
                36,
                37,
                38,
                39,
                40,
                41,
                42,
                43,
                44,
                45,
                46,
                47,
                48,
                49,
                50,
            ],
        }
        return scenarios_hardcoded[str(N)]
