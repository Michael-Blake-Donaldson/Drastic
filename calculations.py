from models.resource import Resource
from models.personnel import Personnel
from models.transportation import Transportation
from models.disaster import Disaster

def calculate_total_resources(resources):
    print("Calculating total resources...")
    for resource in resources:
        print(f"Resource: {resource}")
    total_quantity = sum(resource.quantity for resource in resources)
    total_weight = sum(resource.quantity * resource.weight for resource in resources)
    return total_quantity, total_weight

def calculate_personnel_costs(personnel):
    total_cost = sum(person.number * person.pay_rate for person in personnel if not person.volunteer)
    total_volunteers = sum(person.number for person in personnel if person.volunteer)
    return total_cost, total_volunteers

def calculate_transportation_needs(resources, transportation):
    total_weight = sum(resource.quantity * resource.weight for resource in resources)
    total_cost = 0
    print(f"Total weight to be transported: {total_weight} kg")
    
    for transport in transportation:
        if total_weight <= 0:
            break
        capacity_used = min(total_weight, transport.capacity * transport.availability)
        total_cost += (capacity_used / transport.capacity) * transport.cost_per_km
        total_weight -= capacity_used
        print(f"Using transport: {transport.type}, capacity used: {capacity_used} kg, remaining weight: {total_weight} kg")
    
    success = total_weight <= 0
    print(f"Transportation success: {success}, total cost: {total_cost}")
    return total_cost, success

def calculate_aid_effort_success(resources, personnel, transportation):
    total_quantity, total_weight = calculate_total_resources(resources)
    personnel_cost, total_volunteers = calculate_personnel_costs(personnel)
    transportation_cost, transport_success = calculate_transportation_needs(resources, transportation)
    
    total_cost = personnel_cost + transportation_cost
    overall_success = transport_success
    
    return {
        'total_resources': {
            'quantity': total_quantity,
            'weight': total_weight
        },
        'personnel_costs': {
            'cost': personnel_cost,
            'volunteers': total_volunteers
        },
        'transportation': {
            'cost': transportation_cost,
            'success': transport_success
        },
        'total_cost': total_cost,
        'overall_success': overall_success
    }