import json
from flask import Flask, request, jsonify, send_from_directory
from models.resource import Resource
from models.personnel import Personnel
from models.transportation import Transportation
from models.disaster import Disaster
from calculations import calculate_aid_effort_success

app = Flask(__name__, static_url_path='', static_folder='static')

CALCULATIONS_FILE = 'calculations.json'

def load_calculations():
    try:
        with open(CALCULATIONS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_calculations(calculations):
    with open(CALCULATIONS_FILE, 'w') as file:
        json.dump(calculations, file)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        print("Received data:", data)  # Log received data
        
        # Validate received data
        if not data:
            raise ValueError("No data received")

        # Validate resources
        resources_data = data.get('resources', [])
        if not isinstance(resources_data, list):
            raise ValueError("Resources data is not a list")

        personnel_data = data.get('personnel', [])
        if not isinstance(personnel_data, list):
            raise ValueError("Personnel data is not a list")

        transportation_data = data.get('transportation', [])
        if not isinstance(transportation_data, list):
            raise ValueError("Transportation data is not a list")

        # Parse resources
        resources = []
        for res in resources_data:
            print(f"Parsing resource: {res}")
            resource = Resource(
                name=res['name'],
                quantity=int(res['quantity']),
                weight=float(res['weight']),
                perishability=int(res['perishability'])
            )
            print(f"Parsed resource: {resource}")
            resources.append(resource)

        # Parse personnel
        personnel = []
        for pers in personnel_data:
            print(f"Parsing personnel: {pers}")
            person = Personnel(
                role=pers['role'],
                number=int(pers['number']),
                pay_rate=float(pers['pay_rate']),
                volunteer=pers['volunteer']
            )
            print(f"Parsed personnel: {person}")
            personnel.append(person)

        # Parse transportation
        transportation = []
        for trans in transportation_data:
            print(f"Parsing transportation: {trans}")
            transport = Transportation(
                type=trans['type'],
                capacity=float(trans['capacity']),
                cost_per_km=float(trans['cost_per_km']),
                availability=int(trans['availability'])
            )
            print(f"Parsed transportation: {transport}")
            transportation.append(transport)

        # Calculate aid effort success
        result = calculate_aid_effort_success(resources, personnel, transportation)

        return jsonify(result)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.json
        print("Received save data:", data)  # Log received data
        
        calculations = load_calculations()
        
        calculations[data['name']] = data['calculation']
        
        save_calculations(calculations)
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/load', methods=['GET'])
def load():
    try:
        calculations = load_calculations()
        return jsonify(calculations)
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)