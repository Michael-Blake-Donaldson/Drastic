from dataclasses import dataclass

@dataclass
class Transportation:
    type: str
    capacity: float  # in kg
    cost_per_km: float
    availability: int  # number of vehicles