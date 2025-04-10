#!/usr/bin/env python
"""
Advanced Object Measurement Survey Application with GPS
------------------------------------------------------
A comprehensive web interface for the object measurement tool with:
- GPS location tracking
- Weather data at measurement location
- Category tagging
- Export functionality
- Mobile-responsive design
"""

from flask import Flask, request, render_template_string, redirect, url_for, flash, send_from_directory, jsonify
import os
import uuid
import json
import csv
import io
import time
from datetime import datetime
from measure_object_simple import measure_object

# Create Flask app
app = Flask(__name__)
app.secret_key = "object_measurement_secret_key"

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('results', exist_ok=True)

# Data storage for measurements with GPS
MEASUREMENTS_FILE = 'results/measurements.json'
CATEGORIES_FILE = 'results/categories.json'

# Default categories if none exist
DEFAULT_CATEGORIES = [
    {"id": "furniture", "name": "Furniture", "color": "#4285F4"},
    {"id": "electronics", "name": "Electronics", "color": "#34A853"},
    {"id": "clothing", "name": "Clothing", "color": "#FBBC05"},
    {"id": "kitchenware", "name": "Kitchenware", "color": "#EA4335"},
    {"id": "tools", "name": "Tools", "color": "#8F44AD"},
    {"id": "toys", "name": "Toys", "color": "#F39C12"},
    {"id": "other", "name": "Other", "color": "#7F8C8D"}
]

# Initialize measurements and categories storage
if not os.path.exists(MEASUREMENTS_FILE):
    with open(MEASUREMENTS_FILE, 'w') as f:
        json.dump([], f)

if not os.path.exists(CATEGORIES_FILE):
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(DEFAULT_CATEGORIES, f, indent=2)

# Load categories
try:
    with open(CATEGORIES_FILE, 'r') as f:
        CATEGORIES = json.load(f)
except Exception as e:
    print(f"Error loading categories, using defaults: {e}")
    CATEGORIES = DEFAULT_CATEGORIES

# HTML Templates
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Object Measurement Tool</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        form { margin-top: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="file"], input[type="number"], select, textarea { margin-bottom: 15px; width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        input[type="submit"] { background-color: #4CAF50; color: white; padding: 12px 20px; border: none; cursor: pointer; border-radius: 4px; font-size: 16px; }
        input[type="submit"]:hover { background-color: #45a049; }
        .link { display: inline-block; margin: 10px 10px 10px 0; padding: 10px 15px; background-color: #f8f9fa; color: #333; text-decoration: none; border-radius: 4px; border: 1px solid #ddd; }
        .link:hover { background-color: #e9ecef; }
        .primary-link { background-color: #007bff; color: white; border-color: #007bff; }
        .primary-link:hover { background-color: #0069d9; }
        .flash-message { background-color: #f8d7da; color: #721c24; padding: 10px; margin-bottom: 20px; border-radius: 5px; }
        #map { width: 100%; height: 300px; margin-top: 20px; border: 1px solid #ddd; }
        .location-info { background-color: #e8f4f8; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        .location-info p { margin: 5px 0; }
        .btn { background-color: #4CAF50; color: white; padding: 8px 12px; border: none; cursor: pointer; border-radius: 4px; }
        .btn-secondary { background-color: #6c757d; }
        .hidden { display: none; }
        .weather-info { background-color: #f0f4c3; padding: 10px; border-radius: 5px; margin-top: 10px; }
        .category-selector { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px; }
        .category-item { padding: 8px 15px; border-radius: 20px; cursor: pointer; user-select: none; }
        .category-item.selected { color: white; font-weight: bold; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border: 1px solid #ddd; border-bottom: none; border-radius: 5px 5px 0 0; }
        .tab.active { background-color: #f0f0f0; font-weight: bold; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        @media (max-width: 600px) {
            body { padding: 10px; }
            .container { padding: 15px; }
            h1 { font-size: 24px; }
            h2 { font-size: 20px; }
            .tabs { flex-direction: column; }
            .tab { border: 1px solid #ddd; border-radius: 5px; margin-bottom: 5px; }
        }
    </style>
</head>
<body>
    <h1>Advanced Object Measurement Tool</h1>
    
    {% if messages %}
    <div class="flash-message">
        {% for message in messages %}
            <p>{{ message }}</p>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="tabs">
        <div class="tab active" data-tab="upload">Upload Image</div>
        <div class="tab" data-tab="sample">Use Sample</div>
        <div class="tab" data-tab="location">GPS Settings</div>
    </div>
    
    <div class="container tab-content active" id="upload-tab">
        <h2>Upload an Image</h2>
        <p>Upload an image containing a reference coin and the object you want to measure. The app will detect the coin and use it as a reference to calculate the object's dimensions.</p>
        
        <form action="/upload" method="post" enctype="multipart/form-data" id="upload-form">
            <div>
                <label for="image">Select Image:</label>
                <input type="file" name="file" id="image" accept="image/*" required>
            </div>
            
            <div>
                <label for="reference_size">Reference Coin Diameter (mm):</label>
                <input type="number" name="reference_size" id="reference_size" value="24.26" step="0.01">
                <small>Default: 24.26mm (US Quarter)</small>
            </div>
            
            <div>
                <label for="object_name">Object Name:</label>
                <input type="text" name="object_name" id="object_name" placeholder="Enter a name for this object">
            </div>
            
            <div>
                <label for="notes">Notes:</label>
                <textarea name="notes" id="notes" rows="3" placeholder="Add any additional notes about this measurement"></textarea>
            </div>
            
            <div>
                <label>Category:</label>
                <div class="category-selector">
                    {% for category in categories %}
                    <div class="category-item" data-id="{{ category.id }}" style="background-color: {{ category.color }}22; border: 2px solid {{ category.color }};">
                        {{ category.name }}
                    </div>
                    {% endfor %}
                </div>
                <input type="hidden" name="category" id="category-field" value="other">
            </div>
            
            <!-- Hidden fields for GPS data -->
            <input type="hidden" name="latitude" id="lat-field">
            <input type="hidden" name="longitude" id="lng-field">
            <input type="hidden" name="accuracy" id="acc-field">
            <input type="hidden" name="weather" id="weather-field">
            
            <input type="submit" value="Upload & Measure">
        </form>
    </div>
    
    <div class="container tab-content" id="sample-tab">
        <h2>Use Sample Image</h2>
        <p>Process our sample image that contains a reference coin and a rectangular object.</p>
        
        <div>
            <img src="/static/sample-preview.jpg" alt="Sample Image Preview" style="max-width: 100%; margin-bottom: 20px;">
        </div>
        
        <a href="/sample" class="btn primary-link">Process Sample Image</a>
    </div>
    
    <div class="container tab-content" id="location-tab">
        <h2>GPS Location</h2>
        <div id="location-status">Getting your location...</div>
        
        <div id="location-info" class="location-info hidden">
            <p><strong>Latitude:</strong> <span id="latitude">Not available</span></p>
            <p><strong>Longitude:</strong> <span id="longitude">Not available</span></p>
            <p><strong>Accuracy:</strong> <span id="accuracy">Not available</span>m</p>
            <p><strong>Timestamp:</strong> <span id="timestamp">Not available</span></p>
        </div>
        
        <div id="weather-display" class="weather-info hidden">
            <h3>Local Weather</h3>
            <div id="weather-content">Loading weather information...</div>
        </div>
        
        <div style="margin-top: 20px;">
            <button id="refresh-location" class="btn">Refresh Location</button>
            <button id="use-sample-location" class="btn btn-secondary">Use Sample Location</button>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <a href="/measurements" class="link primary-link">View Measurement History</a>
        <a href="/map" class="link">View All Locations on Map</a>
        <a href="/export" class="link">Export Data</a>
    </div>
    
    <script>
        // Tab functionality
        document.addEventListener('DOMContentLoaded', function() {
            const tabs = document.querySelectorAll('.tab');
            const tabContents = document.querySelectorAll('.tab-content');
            
            tabs.forEach(tab => {
                tab.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    
                    // Remove active class from all tabs and contents
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(c => c.classList.remove('active'));
                    
                    // Add active class to clicked tab and corresponding content
                    this.classList.add('active');
                    document.getElementById(tabId + '-tab').classList.add('active');
                });
            });
            
            // Category selector
            const categoryItems = document.querySelectorAll('.category-item');
            const categoryField = document.getElementById('category-field');
            
            categoryItems.forEach(item => {
                item.addEventListener('click', function() {
                    // Remove selected class from all items
                    categoryItems.forEach(i => i.classList.remove('selected'));
                    
                    // Add selected class to clicked item
                    this.classList.add('selected');
                    
                    // Update the hidden field
                    categoryField.value = this.getAttribute('data-id');
                    
                    // Change text color to white for better contrast
                    this.style.backgroundColor = this.style.borderColor;
                    this.style.color = 'white';
                });
            });
            
            // Set default category
            const defaultCategory = document.querySelector('.category-item[data-id="other"]');
            if (defaultCategory) {
                defaultCategory.click();
            }
        });
        
        // GPS functionality
        document.addEventListener('DOMContentLoaded', function() {
            const locationStatus = document.getElementById('location-status');
            const locationInfo = document.getElementById('location-info');
            const latitudeDisplay = document.getElementById('latitude');
            const longitudeDisplay = document.getElementById('longitude');
            const accuracyDisplay = document.getElementById('accuracy');
            const timestampDisplay = document.getElementById('timestamp');
            const weatherDisplay = document.getElementById('weather-display');
            const weatherContent = document.getElementById('weather-content');
            
            // Hidden form fields
            const latField = document.getElementById('lat-field');
            const lngField = document.getElementById('lng-field');
            const accField = document.getElementById('acc-field');
            const weatherField = document.getElementById('weather-field');
            
            // Buttons
            const refreshBtn = document.getElementById('refresh-location');
            const sampleBtn = document.getElementById('use-sample-location');
            
            function fetchWeatherData(lat, lng) {
                // In a real application, this would call a weather API
                // For this demo, we'll generate mock weather data
                weatherDisplay.classList.remove('hidden');
                
                // Use coordinates to "generate" weather (just for demonstration)
                const temperature = Math.round(20 + (lat % 10) - (lng % 5));
                const conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Thunderstorm"][Math.abs(Math.round(lat + lng) % 5)];
                const humidity = Math.round(40 + (lat % 20) + (lng % 20));
                const windSpeed = Math.round(5 + (lat % 10));
                
                const weatherData = {
                    temperature,
                    conditions,
                    humidity,
                    windSpeed,
                    location: `Near ${lat.toFixed(3)}, ${lng.toFixed(3)}`
                };
                
                // Update weather display
                weatherContent.innerHTML = `
                    <p><strong>Temperature:</strong> ${weatherData.temperature}°C</p>
                    <p><strong>Conditions:</strong> ${weatherData.conditions}</p>
                    <p><strong>Humidity:</strong> ${weatherData.humidity}%</p>
                    <p><strong>Wind Speed:</strong> ${weatherData.windSpeed} km/h</p>
                    <p><strong>Location:</strong> ${weatherData.location}</p>
                `;
                
                // Store weather data in form field as JSON
                weatherField.value = JSON.stringify(weatherData);
                
                return weatherData;
            }
            
            function updateLocationDisplay(position) {
                const { latitude, longitude, accuracy } = position.coords;
                const timestamp = new Date(position.timestamp).toLocaleString();
                
                // Update display
                latitudeDisplay.textContent = latitude.toFixed(6);
                longitudeDisplay.textContent = longitude.toFixed(6);
                accuracyDisplay.textContent = accuracy.toFixed(1);
                timestampDisplay.textContent = timestamp;
                
                // Update form fields
                latField.value = latitude;
                lngField.value = longitude;
                accField.value = accuracy;
                
                // Show location info
                locationStatus.textContent = 'Location acquired successfully!';
                locationStatus.style.color = 'green';
                locationInfo.classList.remove('hidden');
                
                // Fetch weather data for this location
                fetchWeatherData(latitude, longitude);
            }
            
            function handleLocationError(error) {
                console.error('Error getting location:', error);
                locationStatus.textContent = 'Could not get your location: ' + error.message;
                locationStatus.style.color = 'red';
            }
            
            function getCurrentLocation() {
                if (!navigator.geolocation) {
                    locationStatus.textContent = 'Geolocation is not supported by your browser';
                    locationStatus.style.color = 'red';
                    return;
                }
                
                locationStatus.textContent = 'Getting your location...';
                locationStatus.style.color = 'blue';
                
                navigator.geolocation.getCurrentPosition(updateLocationDisplay, handleLocationError, {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                });
            }
            
            function useSampleLocation() {
                const samplePosition = {
                    coords: {
                        latitude: 40.7128,
                        longitude: -74.0060,
                        accuracy: 10.0
                    },
                    timestamp: Date.now()
                };
                updateLocationDisplay(samplePosition);
            }
            
            // Initial location request
            getCurrentLocation();
            
            // Event listeners
            refreshBtn.addEventListener('click', getCurrentLocation);
            sampleBtn.addEventListener('click', useSampleLocation);
            
            // Ensure form has location data before submission
            const uploadForm = document.getElementById('upload-form');
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    if (!latField.value || !lngField.value) {
                        e.preventDefault();
                        alert('Please wait for your location data to be acquired or use the sample location.');
                    }
                });
            }
        });
    </script>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Measurement Results</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #333; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .result-image { text-align: center; margin: 20px 0; }
        .result-image img { max-width: 100%; border: 1px solid #ddd; }
        .measurement { font-size: 18px; margin: 10px 0; }
        .link { display: inline-block; margin: 10px 10px 10px 0; padding: 10px 15px; background-color: #f8f9fa; color: #333; text-decoration: none; border-radius: 4px; border: 1px solid #ddd; }
        .link:hover { background-color: #e9ecef; }
        .primary-link { background-color: #007bff; color: white; border-color: #007bff; }
        .primary-link:hover { background-color: #0069d9; }
        .location-info { background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-top: 20px; }
        .weather-info { background-color: #f0f4c3; padding: 15px; border-radius: 5px; margin-top: 20px; }
        #map { width: 100%; height: 300px; margin-top: 15px; border: 1px solid #ddd; }
        .category-badge { display: inline-block; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; margin-right: 10px; }
        .metadata-box { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }
        
        @media (max-width: 600px) {
            body { padding: 10px; }
            .container { padding: 15px; }
            h1 { font-size: 24px; }
            h2 { font-size: 20px; }
        }
    </style>
</head>
<body>
    <h1>Measurement Results</h1>
    
    <div class="container">
        <div class="result-image">
            <img src="{{ image_url }}" alt="Measurement Result">
        </div>
        
        {% if category_color %}
        <div class="category-badge" style="background-color: {{ category_color }}">
            {{ category_name }}
        </div>
        {% endif %}
        
        {% if object_name %}
        <h2>{{ object_name }}</h2>
        {% else %}
        <h2>Measured Object</h2>
        {% endif %}
        
        <div class="measurements">
            <p class="measurement"><strong>Width:</strong> {{ width }} mm</p>
            <p class="measurement"><strong>Height:</strong> {{ height }} mm</p>
            <p class="measurement"><strong>Reference Coin Size:</strong> {{ reference_size }} mm</p>
        </div>
        
        {% if notes %}
        <div class="metadata-box">
            <h3>Notes</h3>
            <p>{{ notes }}</p>
        </div>
        {% endif %}
    </div>
    
    <div class="container">
        <h2>Location Information</h2>
        <div class="location-info">
            <p><strong>Latitude:</strong> {{ latitude }}</p>
            <p><strong>Longitude:</strong> {{ longitude }}</p>
            <p><strong>Accuracy:</strong> {{ accuracy }} meters</p>
            <p><strong>Timestamp:</strong> {{ timestamp }}</p>
        </div>
        
        {% if weather_data %}
        <div class="weather-info">
            <h3>Weather at Measurement Location</h3>
            <p><strong>Temperature:</strong> {{ weather_data.temperature }}°C</p>
            <p><strong>Conditions:</strong> {{ weather_data.conditions }}</p>
            <p><strong>Humidity:</strong> {{ weather_data.humidity }}%</p>
            <p><strong>Wind Speed:</strong> {{ weather_data.windSpeed }} km/h</p>
        </div>
        {% endif %}
        
        <div id="map"></div>
        
        <script>
            // Simplified map rendering
            document.addEventListener('DOMContentLoaded', function() {
                const mapDiv = document.getElementById('map');
                const lat = {{ latitude|tojson }};
                const lng = {{ longitude|tojson }};
                
                if (typeof lat === 'number' && typeof lng === 'number') {
                    // Create a simple map representation with a link to Google Maps
                    mapDiv.innerHTML = `
                        <div style="background-color: #f5f5f5; padding: 20px; text-align: center;">
                            <p>Map location: ${lat.toFixed(6)}, ${lng.toFixed(6)}</p>
                            <a href="https://www.google.com/maps?q=${lat},${lng}" target="_blank" 
                               style="display: inline-block; background-color: #4285F4; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; margin-top: 10px;">
                                View on Google Maps
                            </a>
                        </div>
                    `;
                } else {
                    mapDiv.innerHTML = '<p style="padding: 20px; text-align: center;">No valid GPS data available</p>';
                }
            });
        </script>
    </div>
    
    <div>
        <a href="/" class="link">Return to Home</a>
        <a href="/measurements" class="link primary-link">View All Measurements</a>
        <a href="/share/{{ measurement_id }}" class="link">Share This Measurement</a>
    </div>
</body>
</html>
"""

MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>All Measurement Locations</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .link { display: inline-block; margin: 10px 10px 10px 0; padding: 10px 15px; background-color: #f8f9fa; color: #333; text-decoration: none; border-radius: 4px; border: 1px solid #ddd; }
        .link:hover { background-color: #e9ecef; }
        #map { width: 100%; height: 600px; margin: 20px 0; border: 1px solid #ddd; }
        .map-placeholder { background-color: #f8f9fa; padding: 20px; text-align: center; }
        .measurement-items { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; margin-top: 20px; }
        .measurement-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; }
        .category-badge { display: inline-block; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; margin-bottom: 10px; }
        .coordinates { font-size: 14px; color: #666; }
        .card-links { margin-top: 10px; }
        .card-link { font-size: 14px; color: #007bff; text-decoration: none; margin-right: 10px; }
        .card-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>All Measurement Locations</h1>
    
    <div class="container">
        <div id="map" class="map-area"></div>
        
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const mapDiv = document.getElementById('map');
                const measurements = {{ measurements|tojson }};
                
                // Filter measurements with valid GPS data
                const locationsData = measurements.filter(m => 
                    m.latitude !== null && m.longitude !== null && 
                    typeof m.latitude === 'number' && typeof m.longitude === 'number'
                );
                
                if (locationsData.length > 0) {
                    let mapHtml = '<div class="map-placeholder">';
                    mapHtml += '<h2>Measurement Locations</h2>';
                    
                    // Create a combined map link with all locations
                    let googleMapsUrl = 'https://www.google.com/maps/dir/?api=1';
                    let firstLocation = locationsData[0];
                    
                    // Add a button to show all locations on Google Maps
                    mapHtml += `
                        <a href="https://www.google.com/maps?q=${firstLocation.latitude},${firstLocation.longitude}" target="_blank" 
                           style="display: inline-block; background-color: #4285F4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 15px 0;">
                            View All Locations on Google Maps
                        </a>
                    `;
                    
                    mapHtml += '<div style="margin-top: 20px; text-align: left;">';
                    locationsData.forEach((m, index) => {
                        let categoryStyle = '';
                        let categoryName = 'Other';
                        
                        if (m.category && m.category_data) {
                            categoryStyle = `background-color: ${m.category_data.color}`;
                            categoryName = m.category_data.name;
                        }
                        
                        mapHtml += `
                            <div style="padding: 15px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; background-color: #fff;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <span style="display: inline-block; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; ${categoryStyle}">
                                            ${categoryName}
                                        </span>
                                        <h3 style="margin: 5px 0;">${m.object_name || 'Unnamed Object'}</h3>
                                    </div>
                                    <div style="font-size: 14px; color: #666;">
                                        ${m.timestamp}
                                    </div>
                                </div>
                                <div style="margin: 10px 0;">
                                    <p><strong>Dimensions:</strong> ${m.width_mm} mm × ${m.height_mm} mm</p>
                                    <p><strong>Location:</strong> ${m.latitude.toFixed(6)}, ${m.longitude.toFixed(6)}</p>
                                </div>
                                <div style="margin-top: 10px;">
                                    <a href="/view/${m.id}" style="color: #007bff; text-decoration: none; margin-right: 15px;">
                                        View Details
                                    </a>
                                    <a href="https://www.google.com/maps?q=${m.latitude},${m.longitude}" target="_blank" style="color: #007bff; text-decoration: none;">
                                        View on Map
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                    mapHtml += '</div>';
                    
                    mapHtml += '</div>';
                    mapDiv.innerHTML = mapHtml;
                } else {
                    mapDiv.innerHTML = '<div class="map-placeholder"><p>No GPS data available for measurements</p></div>';
                }
            });
        </script>
    </div>
    
    <a href="/" class="link">Return to Home</a>
</body>
</html>
"""

MEASUREMENTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Measurement History</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 1000px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        tr:hover { background-color: #f5f5f5; }
        .link { display: inline-block; margin: 10px 10px 10px 0; padding: 10px 15px; background-color: #f8f9fa; color: #333; text-decoration: none; border-radius: 4px; border: 1px solid #ddd; }
        .link:hover { background-color: #e9ecef; }
        .primary-link { background-color: #007bff; color: white; border-color: #007bff; }
        .primary-link:hover { background-color: #0069d9; }
        #map { width: 100%; height: 400px; margin-top: 20px; border: 1px solid #ddd; }
        .no-data { padding: 20px; background-color: #f8f8f8; text-align: center; }
        .action-link { color: #007bff; text-decoration: none; margin-right: 10px; }
        .action-link:hover { text-decoration: underline; }
        .category-badge { display: inline-block; padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; }
        .filter-options { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
        .filter-option { padding: 8px 15px; border-radius: 20px; cursor: pointer; background-color: #f0f0f0; }
        .filter-option.active { background-color: #007bff; color: white; }
        .search-box { margin-bottom: 20px; }
        .search-box input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        
        @media (max-width: 768px) {
            table { font-size: 14px; }
            th, td { padding: 8px; }
            .responsive-table { overflow-x: auto; }
            .hide-mobile { display: none; }
        }
    </style>
</head>
<body>
    <h1>Measurement History</h1>
    
    <div class="container">
        <div class="filter-controls">
            <h2>Filter Measurements</h2>
            
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Search by object name, notes, or location...">
            </div>
            
            <div class="filter-options">
                <div class="filter-option active" data-filter="all">All</div>
                {% for category in categories %}
                <div class="filter-option" data-filter="{{ category.id }}" style="background-color: {{ category.color }}22; border: 2px solid {{ category.color }};">
                    {{ category.name }}
                </div>
                {% endfor %}
            </div>
        </div>
        
        <h2>All Measurements</h2>
        
        {% if measurements %}
        <div class="responsive-table">
            <table id="measurements-table">
                <thead>
                    <tr>
                        <th>Date/Time</th>
                        <th>Object</th>
                        <th>Category</th>
                        <th>Dimensions</th>
                        <th>Location</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for m in measurements %}
                    <tr data-category="{{ m.category or 'other' }}">
                        <td>{{ m.timestamp }}</td>
                        <td>{{ m.object_name or "Unnamed Object" }}</td>
                        <td>
                            {% if m.category_data %}
                            <span class="category-badge" style="background-color: {{ m.category_data.color }}">
                                {{ m.category_data.name }}
                            </span>
                            {% else %}
                            <span class="category-badge" style="background-color: #7F8C8D">Other</span>
                            {% endif %}
                        </td>
                        <td>{{ m.width_mm }} × {{ m.height_mm }} mm</td>
                        <td>
                            {% if m.latitude and m.longitude %}
                            <a href="https://www.google.com/maps?q={{ m.latitude }},{{ m.longitude }}" target="_blank" class="action-link">
                                View Map
                            </a>
                            {% else %}
                            No location data
                            {% endif %}
                        </td>
                        <td>
                            <a href="/view/{{ m.id }}" class="action-link">View</a>
                            <a href="/share/{{ m.id }}" class="action-link">Share</a>
                            <a href="/export/{{ m.id }}" class="action-link">Export</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <h2>Measurement Locations</h2>
        <div id="map"></div>
        
        <script>
            // Filter functionality
            document.addEventListener('DOMContentLoaded', function() {
                const filterOptions = document.querySelectorAll('.filter-option');
                const searchInput = document.getElementById('search-input');
                const tableRows = document.querySelectorAll('#measurements-table tbody tr');
                
                function filterTable() {
                    const activeFilter = document.querySelector('.filter-option.active').getAttribute('data-filter');
                    const searchTerm = searchInput.value.toLowerCase();
                    
                    tableRows.forEach(row => {
                        const category = row.getAttribute('data-category');
                        const rowContent = row.textContent.toLowerCase();
                        const matchesCategory = activeFilter === 'all' || category === activeFilter;
                        const matchesSearch = searchTerm === '' || rowContent.includes(searchTerm);
                        
                        row.style.display = matchesCategory && matchesSearch ? '' : 'none';
                    });
                }
                
                filterOptions.forEach(option => {
                    option.addEventListener('click', function() {
                        filterOptions.forEach(opt => opt.classList.remove('active'));
                        this.classList.add('active');
                        filterTable();
                    });
                });
                
                searchInput.addEventListener('input', filterTable);
                
                // Map functionality
                const mapDiv = document.getElementById('map');
                const measurements = {{ measurements|tojson }};
                
                // Filter measurements with valid GPS data
                const locationsData = measurements.filter(m => 
                    m.latitude !== null && m.longitude !== null && 
                    typeof m.latitude === 'number' && typeof m.longitude === 'number'
                );
                
                if (locationsData.length > 0) {
                    let mapHtml = '<div style="background-color: #f5f5f5; padding: 20px; text-align: center;">';
                    mapHtml += '<p>Map showing all measurement locations</p>';
                    
                    // Add a button to show all locations on Google Maps
                    let firstLocation = locationsData[0];
                    mapHtml += `
                        <a href="https://www.google.com/maps?q=${firstLocation.latitude},${firstLocation.longitude}" target="_blank" 
                           style="display: inline-block; background-color: #4285F4; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; margin-top: 10px;">
                            View All on Google Maps
                        </a>
                    `;
                    
                    mapHtml += '<div style="margin-top: 15px;">';
                    locationsData.forEach((m, index) => {
                        let categoryStyle = '';
                        let categoryName = 'Other';
                        
                        if (m.category && m.category_data) {
                            categoryStyle = `background-color: ${m.category_data.color}`;
                            categoryName = m.category_data.name;
                        }
                        
                        mapHtml += `
                            <div style="margin: 10px 0; padding: 10px; background-color: white; border-radius: 5px; text-align: left;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <span style="display: inline-block; padding: 3px 8px; border-radius: 20px; color: white; font-weight: bold; ${categoryStyle}">
                                            ${categoryName}
                                        </span>
                                        <strong>${m.object_name || 'Unnamed Object'}</strong>
                                    </div>
                                    <small>${m.timestamp}</small>
                                </div>
                                <div style="margin-top: 5px;">
                                    <small>${m.latitude.toFixed(6)}, ${m.longitude.toFixed(6)}</small>
                                </div>
                                <div style="margin-top: 5px;">
                                    <a href="/view/${m.id}" style="color: #007bff; text-decoration: none; font-size: 12px; margin-right: 10px;">View</a>
                                    <a href="https://www.google.com/maps?q=${m.latitude},${m.longitude}" target="_blank" style="color: #007bff; text-decoration: none; font-size: 12px;">
                                        Map
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                    mapHtml += '</div>';
                    
                    mapHtml += '</div>';
                    mapDiv.innerHTML = mapHtml;
                } else {
                    mapDiv.innerHTML = '<p style="padding: 20px; text-align: center;">No GPS data available for measurements</p>';
                }
            });
        </script>
        {% else %}
        <div class="no-data">
            <p>No measurements have been recorded yet.</p>
        </div>
        {% endif %}
    </div>
    
    <div>
        <a href="/" class="link">Return to Home</a>
        <a href="/map" class="link primary-link">View Map of All Locations</a>
        <a href="/export" class="link">Export All Data</a>
    </div>
</body>
</html>
"""

EXPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Export Measurement Data</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1, h2 { color: #333; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .export-option { display: flex; align-items: center; margin-bottom: 15px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; cursor: pointer; }
        .export-option:hover { background-color: #e9ecef; }
        .export-icon { font-size: 24px; margin-right: 15px; color: #007bff; }
        .export-details { flex-grow: 1; }
        .export-title { font-weight: bold; margin-bottom: 5px; }
        .export-description { color: #666; font-size: 14px; }
        .link { display: inline-block; margin: 10px 10px 10px 0; padding: 10px 15px; background-color: #f8f9fa; color: #333; text-decoration: none; border-radius: 4px; border: 1px solid #ddd; }
        .link:hover { background-color: #e9ecef; }
    </style>
</head>
<body>
    <h1>Export Measurement Data</h1>
    
    <div class="container">
        <h2>Export Options</h2>
        
        <a href="/export/csv" class="export-option">
            <div class="export-icon">📊</div>
            <div class="export-details">
                <div class="export-title">CSV Export</div>
                <div class="export-description">Export all measurement data to a CSV file for use in spreadsheet applications like Excel or Google Sheets.</div>
            </div>
        </a>
        
        <a href="/export/json" class="export-option">
            <div class="export-icon">📝</div>
            <div class="export-details">
                <div class="export-title">JSON Export</div>
                <div class="export-description">Export all measurement data to a JSON file for use in programming or data analysis applications.</div>
            </div>
        </a>
        
        <a href="/export/zip" class="export-option">
            <div class="export-icon">🗃️</div>
            <div class="export-details">
                <div class="export-title">Complete Export (ZIP)</div>
                <div class="export-description">Export all measurement data along with the original and processed images in a ZIP archive.</div>
            </div>
        </a>
    </div>
    
    <a href="/" class="link">Return to Home</a>
</body>
</html>
"""

@app.route('/')
def index():
    """Render the main page"""
    messages = []
    return render_template_string(HOME_TEMPLATE, messages=messages, categories=CATEGORIES)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Process an uploaded image with GPS data"""
    if 'file' not in request.files:
        return redirect('/')
    
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    
    if file:
        # Get form data
        reference_size = float(request.form.get('reference_size', 24.26))
        object_name = request.form.get('object_name', '').strip()
        notes = request.form.get('notes', '').strip()
        category = request.form.get('category', 'other')
        
        # Get GPS data
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        accuracy = request.form.get('accuracy')
        weather_data_str = request.form.get('weather')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Parse weather data if available
        try:
            weather_data = json.loads(weather_data_str) if weather_data_str else None
        except:
            weather_data = None
        
        # Convert GPS data to float if present
        try:
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None
            accuracy = float(accuracy) if accuracy else None
        except (ValueError, TypeError):
            latitude, longitude, accuracy = None, None, None
        
        # Find category data
        category_data = next((c for c in CATEGORIES if c['id'] == category), None)
        
        # Save the file
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Process the image (saving output to output_image.jpg)
        measure_object(filepath, reference_size)
        
        # Output file is always output_image.jpg in the current approach
        output_filename = "output_image.jpg"
        
        # Generate a unique ID for this measurement
        measurement_id = str(uuid.uuid4())
        
        # Save measurement data with GPS info
        measurement_data = {
            "id": measurement_id,
            "timestamp": timestamp,
            "image_filename": filename,
            "output_filename": output_filename,
            "reference_size_mm": reference_size,
            "width_mm": "Calculated automatically",  # In a real app, get the actual value
            "height_mm": "Calculated automatically", # In a real app, get the actual value
            "object_name": object_name,
            "notes": notes,
            "category": category,
            "category_data": category_data,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "weather_data": weather_data
        }
        
        # Save the data to our JSON file
        try:
            with open(MEASUREMENTS_FILE, 'r') as f:
                measurements = json.load(f)
            
            measurements.append(measurement_data)
            
            with open(MEASUREMENTS_FILE, 'w') as f:
                json.dump(measurements, f, indent=2)
        except Exception as e:
            print(f"Error saving measurement data: {e}")
        
        # Get the category color for display
        category_color = category_data['color'] if category_data else None
        category_name = category_data['name'] if category_data else 'Other'
        
        return render_template_string(
            RESULT_TEMPLATE, 
            image_url=f'/{output_filename}',
            width="Calculated automatically",
            height="Calculated automatically",
            reference_size=reference_size,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            timestamp=timestamp,
            weather_data=weather_data,
            object_name=object_name,
            notes=notes,
            category_color=category_color,
            category_name=category_name,
            measurement_id=measurement_id
        )
    
    return redirect('/')

@app.route('/sample')
def sample():
    """Process a sample image with sample GPS data"""
    # Create a sample image
    from create_sample_image import create_sample_image
    sample_path = create_sample_image()
    
    # Process the image
    measure_object(sample_path)
    
    # Output file is always output_image.jpg in the current approach
    output_filename = "output_image.jpg"
    
    # Use New York City coordinates as a sample location
    latitude = 40.7128
    longitude = -74.0060
    accuracy = 10.0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Sample weather data
    weather_data = {
        "temperature": 22,
        "conditions": "Partly Cloudy",
        "humidity": 65,
        "windSpeed": 8,
        "location": "New York City"
    }
    
    # Generate a unique ID for this measurement
    measurement_id = str(uuid.uuid4())
    
    # Use "Sample Object" as the object name
    object_name = "Sample Test Object"
    category = "other"
    category_data = next((c for c in CATEGORIES if c['id'] == category), None)
    
    # Save measurement data with GPS info
    measurement_data = {
        "id": measurement_id,
        "timestamp": timestamp,
        "image_filename": "sample_image.jpg",
        "output_filename": output_filename,
        "reference_size_mm": 24.26,
        "width_mm": "Calculated automatically",  # In a real app, get the actual value
        "height_mm": "Calculated automatically", # In a real app, get the actual value
        "object_name": object_name,
        "notes": "This is a sample measurement generated by the system.",
        "category": category,
        "category_data": category_data,
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "weather_data": weather_data
    }
    
    # Save the data to our JSON file
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
        
        measurements.append(measurement_data)
        
        with open(MEASUREMENTS_FILE, 'w') as f:
            json.dump(measurements, f, indent=2)
    except Exception as e:
        print(f"Error saving measurement data: {e}")
    
    return render_template_string(
        RESULT_TEMPLATE, 
        image_url=f'/{output_filename}',
        width="Calculated automatically",
        height="Calculated automatically",
        reference_size=24.26,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        timestamp=timestamp,
        weather_data=weather_data,
        object_name=object_name,
        notes="This is a sample measurement generated by the system.",
        category_color=category_data['color'] if category_data else None,
        category_name=category_data['name'] if category_data else 'Other',
        measurement_id=measurement_id
    )

@app.route('/measurements')
def list_measurements():
    """Display all measurements with their GPS locations"""
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
    except Exception as e:
        measurements = []
        print(f"Error loading measurements: {e}")
    
    return render_template_string(MEASUREMENTS_TEMPLATE, measurements=measurements, categories=CATEGORIES)

@app.route('/map')
def show_map():
    """Show a map of all measurement locations"""
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
    except Exception as e:
        measurements = []
        print(f"Error loading measurements: {e}")
    
    return render_template_string(MAP_TEMPLATE, measurements=measurements)

@app.route('/view/<measurement_id>')
def view_measurement(measurement_id):
    """View a specific measurement with its GPS location"""
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
        
        measurement = next((m for m in measurements if m["id"] == measurement_id), None)
        
        if not measurement:
            return redirect('/measurements')
            
    except Exception as e:
        print(f"Error loading measurement: {e}")
        return redirect('/measurements')
    
    # Get the category color for display
    category_data = measurement.get('category_data', None)
    category_color = category_data['color'] if category_data else None
    category_name = category_data['name'] if category_data else 'Other'
    
    # Use same template as regular results but with the specific measurement data
    return render_template_string(
        RESULT_TEMPLATE,
        image_url=f'/{measurement["output_filename"]}',
        width=measurement["width_mm"],
        height=measurement["height_mm"],
        reference_size=measurement["reference_size_mm"],
        latitude=measurement["latitude"],
        longitude=measurement["longitude"],
        accuracy=measurement["accuracy"],
        timestamp=measurement["timestamp"],
        weather_data=measurement.get("weather_data", None),
        object_name=measurement.get("object_name", ""),
        notes=measurement.get("notes", ""),
        category_color=category_color,
        category_name=category_name,
        measurement_id=measurement_id
    )

@app.route('/export')
def export_options():
    """Show export options"""
    return render_template_string(EXPORT_TEMPLATE)

@app.route('/export/csv')
def export_csv():
    """Export all measurements as CSV"""
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
    except Exception as e:
        measurements = []
        print(f"Error loading measurements: {e}")
    
    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'ID', 'Timestamp', 'Object Name', 'Category', 'Width (mm)', 'Height (mm)', 
        'Reference Size (mm)', 'Latitude', 'Longitude', 'Accuracy', 
        'Temperature', 'Weather Conditions', 'Notes'
    ])
    
    # Write data rows
    for m in measurements:
        # Extract weather data if available
        temperature = ""
        conditions = ""
        if m.get('weather_data'):
            temperature = m['weather_data'].get('temperature', '')
            conditions = m['weather_data'].get('conditions', '')
        
        # Get category name
        category_name = m.get('category_data', {}).get('name', 'Other') if m.get('category_data') else 'Other'
        
        writer.writerow([
            m.get('id', ''),
            m.get('timestamp', ''),
            m.get('object_name', ''),
            category_name,
            m.get('width_mm', ''),
            m.get('height_mm', ''),
            m.get('reference_size_mm', ''),
            m.get('latitude', ''),
            m.get('longitude', ''),
            m.get('accuracy', ''),
            temperature,
            conditions,
            m.get('notes', '')
        ])
    
    # Create response
    from flask import Response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=measurements_export.csv"}
    )

@app.route('/export/json')
def export_json():
    """Export all measurements as JSON"""
    try:
        with open(MEASUREMENTS_FILE, 'r') as f:
            measurements = json.load(f)
    except Exception as e:
        measurements = []
        print(f"Error loading measurements: {e}")
    
    # Create response
    from flask import Response
    return Response(
        json.dumps(measurements, indent=2),
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=measurements_export.json"}
    )

@app.route('/share/<measurement_id>')
def share_measurement(measurement_id):
    """Generate a sharable link for a measurement"""
    # In a real app, this would generate a unique sharable link
    # For this demo, we'll just redirect to the view page
    return redirect(f'/view/{measurement_id}')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from static directory"""
    return send_from_directory('static', filename)

@app.route('/<path:filename>')
def serve_file(filename):
    """Serve static files from root directory"""
    return send_from_directory('.', filename)

if __name__ == '__main__':
    # Ensure sample-preview.jpg exists in static folder
    os.makedirs('static', exist_ok=True)
    
    # If the file doesn't exist, create it by copying output_image.jpg
    if not os.path.exists('static/sample-preview.jpg'):
        # First create a sample image if it doesn't exist
        from create_sample_image import create_sample_image
        sample_path = create_sample_image()
        measure_object(sample_path)
        
        # Now copy output_image.jpg to static/sample-preview.jpg
        import shutil
        try:
            shutil.copy('output_image.jpg', 'static/sample-preview.jpg')
        except Exception as e:
            print(f"Error creating sample preview: {e}")
    
    # Start the application
    app.run(host='0.0.0.0', port=5000, debug=True)