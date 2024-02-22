"""Module to get configuration from json file"""

SMALL_CONFIG = {
    "id_vehicle": "van",
    "type_vehicle": "small",
    "capacity": 115,
    "cost_fixed": 67,
    "time_prep": 5 / 60,
    "time_loading_per_item": 0.067 / 60,
    "time_set_up": 2 / 60,
    "time_service": 1 / 60,
    "speed_linehaul": 60,
    "speed_interstop": 35,
    "t_max": 12,
    "cost_hourly": 5.39,
    "cost_km": 2.55,
    "cost_item": 0.5,
}
LARGE_CONFIG = {
    "id_vehicle": "truck",
    "type_vehicle": "large",
    "capacity": 460,
    "cost_fixed": 268,
    "time_prep": 10 / 60,
    "time_loading_per_item": 0.05 / 60,
    "time_set_up": 2 / 60,
    "time_service": 2 / 60,
    "speed_linehaul": 45,
    "speed_interstop": 25,
    "t_max": 12,
    "cost_hourly": 5,
    "cost_km": 58,
    "cost_item": 0.5,
}
