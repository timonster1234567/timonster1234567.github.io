// Create the map
const map = L.map('map').setView([2, 20], 4);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Load GeoJSON file
fetch('data/kingdoms.geojson')
    .then(response => response.json())
    .then(data => {

        data.features.sort((a, b) => {
            // smaller areas on top (optional improvement later)
            return a.properties.polity_type.localeCompare(b.properties.polity_type);
        });

        L.geoJSON(data, {
            style: function(feature) {
                return {
                    color: feature.properties.color,
                    weight: 2,
                    fillColor: feature.properties.color,
                    fillOpacity: 0.5
                };
            },
            onEachFeature: function(feature, layer) {

                // Popup content
                const popupContent = `
                    <h2>${feature.properties.name}</h2>
                    <p><strong>Government:</strong> ${feature.properties.government}</p>
                    <p><strong>Language:</strong> ${feature.properties.language_family}</p>
                    <p><strong>Capital:</strong> ${feature.properties.capital}</p>
                    <p><strong>Years:</strong> ${feature.properties.start_year}–${feature.properties.end_year}</p>
                    <p>${feature.properties.description}</p>
                `;

                layer.bindPopup(popupContent);
                layer.on('mouseover', function () {
                    layer.bringToFront();
                });

                layer.bindPopup(feature.properties.name);
            }
            

        }).addTo(map);

    });