document.getElementById('add-resource').addEventListener('click', function() {
    const resourceDiv = document.createElement('div');
    resourceDiv.classList.add('resource');
    resourceDiv.innerHTML = `
        <label for="resource_name">Name:</label>
        <input type="text" name="resource_name" required>
        
        <label for="resource_quantity">Quantity:</label>
        <input type="number" name="resource_quantity" required>
        
        <label for="resource_weight">Weight (kg):</label>
        <input type="number" name="resource_weight" required>
        
        <label for="resource_perishability">Perishability (days):</label>
        <input type="number" name="resource_perishability" required><br>
    `;
    document.getElementById('resources').appendChild(resourceDiv);
});

document.getElementById('add-personnel').addEventListener('click', function() {
    const personnelDiv = document.createElement('div');
    personnelDiv.classList.add('person');
    personnelDiv.innerHTML = `
        <label for="personnel_role">Role:</label>
        <input type="text" name="personnel_role" required>
        
        <label for="personnel_number">Number:</label>
        <input type="number" name="personnel_number" required>
        
        <label for="personnel_pay_rate">Pay Rate:</label>
        <input type="number" name="personnel_pay_rate" required>
        
        <label for="personnel_volunteer">Volunteer:</label>
        <input type="checkbox" name="personnel_volunteer"><br>
    `;
    document.getElementById('personnel').appendChild(personnelDiv);
});

document.getElementById('add-transportation').addEventListener('click', function() {
    const transportDiv = document.createElement('div');
    transportDiv.classList.add('transport');
    transportDiv.innerHTML = `
        <label for="transport_type">Type:</label>
        <input type="text" name="transport_type" required>
        
        <label for="transport_capacity">Capacity (kg):</label>
        <input type="number" name="transport_capacity" required>
        
        <label for="transport_cost_per_km">Cost per km:</label>
        <input type="number" name="transport_cost_per_km" required>
        
        <label for="transport_availability">Availability:</label>
        <input type="number" name="transport_availability" required><br>
    `;
    document.getElementById('transportation').appendChild(transportDiv);
});

document.getElementById('disaster-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const data = {
        type: document.getElementById('type').value,
        location: document.getElementById('location').value,
        affected_population: parseInt(document.getElementById('affected_population').value),
        duration_days: parseInt(document.getElementById('duration_days').value),
        resources: [],
        personnel: [],
        transportation: []
    };

    document.querySelectorAll('.resource').forEach(function(resource) {
        data.resources.push({
            name: resource.querySelector('input[name="resource_name"]').value,
            quantity: parseInt(resource.querySelector('input[name="resource_quantity"]').value),
            weight: parseFloat(resource.querySelector('input[name="resource_weight"]').value),
            perishability: parseInt(resource.querySelector('input[name="resource_perishability"]').value)
        });
    });

    document.querySelectorAll('.person').forEach(function(person) {
        data.personnel.push({
            role: person.querySelector('input[name="personnel_role"]').value,
            number: parseInt(person.querySelector('input[name="personnel_number"]').value),
            pay_rate: parseFloat(person.querySelector('input[name="personnel_pay_rate"]').value),
            volunteer: person.querySelector('input[name="personnel_volunteer"]').checked
        });
    });

    document.querySelectorAll('.transport').forEach(function(transport) {
        data.transportation.push({
            type: transport.querySelector('input[name="transport_type"]').value,
            capacity: parseFloat(transport.querySelector('input[name="transport_capacity"]').value),
            cost_per_km: parseFloat(transport.querySelector('input[name="transport_cost_per_km"]').value),
            availability: parseInt(transport.querySelector('input[name="transport_availability"]').value)
        });
    });

    console.log("Data to send:", data);  // Log the collected data

    fetch('/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(result => {
        console.log("Received result:", result);  // Log the result
        document.getElementById('result').innerHTML = `
            <h2>Calculation Results</h2>
            <p>Total Resources: Quantity = ${result.total_resources.quantity}, Weight = ${result.total_resources.weight} kg</p>
            <p>Personnel Costs: Cost = $${result.personnel_costs.cost}, Volunteers = ${result.personnel_costs.volunteers}</p>
            <p>Transportation: Cost = $${result.transportation.cost}, Success = ${result.transportation.success}</p>
            <p>Total Cost: $${result.total_cost}</p>
            <p>Overall Success: ${result.overall_success}</p>
        `;
        document.getElementById('save-form').style.display = 'block';  // Show save form
    })
    .catch(error => {
        document.getElementById('result').innerHTML = `<p>Error: ${error.message}</p>`;
        console.error('Error:', error);
    });
});

document.getElementById('save-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const calculationName = document.getElementById('calculation_name').value;
    const calculation = {
        type: document.getElementById('type').value,
        location: document.getElementById('location').value,
        affected_population: document.getElementById('affected_population').value,
        duration_days: document.getElementById('duration_days').value,
        resources: [],
        personnel: [],
        transportation: []
    };

    document.querySelectorAll('.resource').forEach(function(resource) {
        calculation.resources.push({
            name: resource.querySelector('input[name="resource_name"]').value,
            quantity: resource.querySelector('input[name="resource_quantity"]').value,
            weight: resource.querySelector('input[name="resource_weight"]').value,
            perishability: resource.querySelector('input[name="resource_perishability"]').value
        });
    });

    document.querySelectorAll('.person').forEach(function(person) {
        calculation.personnel.push({
            role: person.querySelector('input[name="personnel_role"]').value,
            number: person.querySelector('input[name="personnel_number"]').value,
            pay_rate: person.querySelector('input[name="personnel_pay_rate"]').value,
            volunteer: person.querySelector('input[name="personnel_volunteer"]').checked
        });
    });

    document.querySelectorAll('.transport').forEach(function(transport) {
        calculation.transportation.push({
            type: transport.querySelector('input[name="transport_type"]').value,
            capacity: transport.querySelector('input[name="transport_capacity"]').value,
            cost_per_km: transport.querySelector('input[name="transport_cost_per_km"]').value,
            availability: transport.querySelector('input[name="transport_availability"]').value
        });
    });

    fetch('/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: calculationName, calculation: calculation })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(result => {
        if (result.status === 'success') {
            alert('Calculation saved successfully');
            loadCalculations();  // Reload saved calculations
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

function loadCalculations() {
    fetch('/load')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(calculations => {
        const savedCalculationsDiv = document.getElementById('saved-calculations');
        savedCalculationsDiv.innerHTML = '';
        for (const name in calculations) {
            const calc = calculations[name];
            const calcDiv = document.createElement('div');
            calcDiv.classList.add('saved-calculation');
            calcDiv.innerHTML = `
                <h3>${name}</h3>
                <p>Type: ${calc.type}</p>
                <p>Location: ${calc.location}</p>
                <p>Affected Population: ${calc.affected_population}</p>
                <p>Duration (days): ${calc.duration_days}</p>
                <h4>Resources</h4>
                ${calc.resources.map(res => `
                    <p>Name: ${res.name}, Quantity: ${res.quantity}, Weight: ${res.weight}, Perishability: ${res.perishability}</p>
                `).join('')}
                <h4>Personnel</h4>
                ${calc.personnel.map(pers => `
                    <p>Role: ${pers.role}, Number: ${pers.number}, Pay Rate: ${pers.pay_rate}, Volunteer: ${pers.volunteer}</p>
                `).join('')}
                <h4>Transportation</h4>
                ${calc.transportation.map(trans => `
                    <p>Type: ${trans.type}, Capacity: ${trans.capacity}, Cost per km: ${trans.cost_per_km}, Availability: ${trans.availability}</p>
                `).join('')}
            `;
            savedCalculationsDiv.appendChild(calcDiv);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Initial load of saved calculations
loadCalculations();

// Initialize Google Places Autocomplete for location input
function initAutocomplete() {
    const locationInput = document.getElementById('location');
    const autocomplete = new google.maps.places.Autocomplete(locationInput, {
        types: ['(cities)'],
        componentRestrictions: { country: "us" }
    });

    autocomplete.addListener('place_changed', function() {
        const place = autocomplete.getPlace();
        locationInput.value = place.formatted_address;
    });
}

// Load Google Maps API script and initialize autocomplete
function loadScript(url, callback) {
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = url;
    script.onload = callback;
    document.head.appendChild(script);
}

loadScript('https://maps.googleapis.com/maps/api/js?key=AIzaSyA1CcS8ZCABwElqxyOSp5po_69-aE6zX-I&libraries=places', initAutocomplete);