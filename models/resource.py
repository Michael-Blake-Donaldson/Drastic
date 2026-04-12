from dataclasses import dataclass

@dataclass
class Resource:
    name: str
    quantity: int
    weight: float  # in kg
    perishability: int  # days until spoilage