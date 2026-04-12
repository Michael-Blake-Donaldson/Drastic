from dataclasses import dataclass
from typing import List
from .resource import Resource
from .personnel import Personnel
from .transportation import Transportation

@dataclass
class Disaster:
    type: str
    location: str
    affected_population: int
    duration_days: int
    resources: List[Resource]
    personnel: List[Personnel]
    transportation: List[Transportation]