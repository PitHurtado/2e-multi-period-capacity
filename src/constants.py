"""Constants for the application."""

# Constants
FEE_COST_FROM_SATELLITE = 0.1333
FEE_COST_FROM_DC = 0.264


# Paths
PATH_DATA_SATELLITE = "./data/input_satellites.xlsx"
PATH_DATA_PIXEL = "./data/input_pixels.xlsx"
PATH_DATA_DISTANCES_FROM_SATELLITES = (
    "./data/input_matrix_distance_satellite_to_pixels.xlsx"
)
PATH_DATA_DISTANCES_FROM_DC = "./data/input_matrix_distance_dc_to_pixels.xlsx"

# Path root from scenarios
PATH_ROOT_SCENARIO = "./data/scenarios/"

PATH_SAMPLING_SCENARIO = PATH_ROOT_SCENARIO + "sampling/"
PATH_BEST_SOLUTION_SAA = PATH_ROOT_SCENARIO + "best_solution_saa/"
