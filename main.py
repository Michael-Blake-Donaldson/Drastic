from models.resource import Resource
from models.personnel import Personnel
from models.transportation import Transportation
from models.disaster import Disaster

# Example usage
resources = [
    Resource(name="Food", quantity=1000, weight=0.5, perishability=30),
    Resource(name="Water", quantity=2000, weight=1.0, perishability=365),
]

personnel = [
    Personnel(role="Medical", number=50, pay_rate=20.0, volunteer=False),
    Personnel(role="Logistical", number=30, pay_rate=15.0, volunteer=True),
]

transportation = [
    Transportation(type="Truck", capacity=10000, cost_per_km=2.0, availability=10),
    Transportation(type="Plane", capacity=50000, cost_per_km=10.0, availability=2),
]

disaster = Disaster(
    type="Earthquake",
    location="Country X",
    affected_population=10000,
    duration_days=30,
    resources=resources,
    personnel=personnel,
    transportation=transportation,
)

print(disaster)