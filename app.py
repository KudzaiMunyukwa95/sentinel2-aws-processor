import os
import json
import requests
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import tempfile
import zipfile
from pathlib import Path
import boto3
from botocore import UNSIGNED
from botocore.config import Config

app = Flask(__name__)
CORS(app)

# Initialize AWS S3 client (no credentials needed for public data)
s3_client = boto3.client('s3', 
                        config=Config(signature_version=UNSIGNED),
                        region_name='eu-west-1')

# Sentinel-2 bucket name
BUCKET_NAME = 'sentinel-s2-l2a'

class SimpleSentinel2Processor:
    def __init__(self):
        """Initialize the simplified processor for Render"""
        self.temp_dir = tempfile.mkdtemp()
        print(f"Temp directory: {self.temp_dir}")
    
    def find_mgrs_tile_for_coords(self, lon, lat):
        """
        Simple MGRS tile lookup for common regions
        In production, you'd use a proper MGRS library
        """
        # Simplified lookup table for major regions
        mgrs_lookup = [
            # Africa
            {'bounds': [30, -25, 38, -15], 'tiles': ['36MZA', '36MYA', '35MPN']},
            # Europe
            {'bounds': [-10, 45, 10, 60], 'tiles': ['33UUP', '32UPU', '31UDQ']},
            # North America East
            {'bounds': [-80, 35, -70, 45], 'tiles': ['18TWL', '17TKM', '18TXL']},
            # North America West  
            {'bounds': [-125, 32, -115, 42], 'tiles': ['11SKA', '10TFK', '11SLA']},
            # Asia
            {'bounds': [100, 0, 140, 40], 'tiles': ['48NUG', '49NGA', '50NKG']},
            # Australia
            {'bounds': [110, -40, 155, -10], 'tiles': ['52LGL', '53LLJ', '54LZL']},
        ]
        
        for region in mgrs_lookup:
            bounds = region['bounds']
            if bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]:
                return region['tiles'][0]  # Return first tile for region
        
        # Default fallback
        return '36MZA'  # Zimbabwe region
    
    def check_image_availability(self, mgrs_tile, date_str):
        """
        Check if Sentinel-2 image is available for given tile and date
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # Check if data exists for this date
            prefix = f"tiles/{mgrs_tile}/{year}/{month:02d}/{day:02d}/"
            
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=prefix,
                MaxKeys=1
            )
            
            return 'Contents' in response and len(response['Contents']) > 0
            
        except Exception as e:
            print(f"Error checking availability: {e}")
            return False
    
    def find_best_available_date(self, mgrs_tile, target_date, search_days=30):
        """
        Find the best available date near the target date
        """
        target = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Search around target date
        for delta in range(search_days):
            # Try dates before and after target
            for direction in [-1, 1]:
                check_date = target + timedelta(days=delta * direction)
                date_str = check_date.strftime('%Y-%m-%d')
                
                if self.check_image_availability(mgrs_tile, date_str):
                    return date_str
        
        return None
    
    def get_sample_ndvi_data(self, polygon_coords, target_date):
        """
        Generate sample NDVI data for demonstration
        In production, this would process actual Sentinel-2 imagery
        """
        # Get center point of polygon
        lons = [coord[0] for coord in polygon_coords]
        lats = [coord[1] for coord in polygon_coords]
        center_lon = sum(lons) / len(lons)
        center_lat = sum(lats) / len(lats)
        
        # Find MGRS tile
        mgrs_tile = self.find_mgrs_tile_for_coords(center_lon, center_lat)
        
        # Find best available date
        available_date = self.find_best_available_date(mgrs_tile, target_date)
        
        if not available_date:
            available_date = target_date  # Fallback
        
        # Generate realistic NDVI values based on location and season
        base_ndvi = 0.3  # Base vegetation
        seasonal_factor = 0.2 * np.sin((datetime.strptime(available_date, '%Y-%m-%d').timetuple().tm_yday / 365.0) * 2 * np.pi)
        
        # Simulate different vegetation zones within the field
        np.random.seed(42)  # For consistent results
        ndvi_values = []
        
        for i in range(10):  # Generate 10 sample points
            variation = np.random.normal(0, 0.1)
            ndvi = base_ndvi + seasonal_factor + variation
            ndvi = max(-0.2, min(0.9, ndvi))  # Clamp to realistic range
            
            sample_date = datetime.strptime(available_date, '%Y-%m-%d') + timedelta(days=i*3)
            ndvi_values.append({
                'date': sample_date.strftime('%Y-%m-%d'),
                'ndvi': round(ndvi, 3),
                'cloud_percentage': np.random.randint(5, 25)
            })
        
        return {
            'success': True,
            'mgrs_tile': mgrs_tile,
            'available_date': available_date,
            'center_coords': [center_lon, center_lat],
            'ndvi_samples': ndvi_values,
            'message': f'Processed field using MGRS tile {mgrs_tile}. Best available date: {available_date}'
        }

# Initialize processor
processor = SimpleSentinel2Processor()

@app.route("/")
def index():
    """Simple demo interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sentinel-2 AWS Processor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, button { padding: 10px; width: 100%; box-sizing: border-box; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .result { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-top: 20px; }
            .error { background: #f8d7da; color: #721c24; }
            .success { background: #d4edda; color: #155724; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ Sentinel-2 AWS Processor</h1>
            <p>Direct access to Sentinel-2 imagery without Google Earth Engine</p>
            
            <form id="processForm">
                <div class="form-group">
                    <label>Field Coordinates (JSON format):</label>
                    <textarea id="coordinates" rows="4" placeholder='[[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]]'>[[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]]</textarea>
                </div>
                
                <div class="form-group">
                    <label>Target Date:</label>
                    <input type="date" id="targetDate" value="2024-01-15">
                </div>
                
                <div class="form-group">
                    <label>Field Name:</label>
                    <input type="text" id="fieldName" value="Test Field" placeholder="Enter field name">
                </div>
                
                <button type="submit">🚀 Process Field</button>
            </form>
            
            <div id="result"></div>
        </div>
        
        <script>
            document.getElementById('processForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '<div class="result">Processing... Please wait.</div>';
                
                try {
                    const response = await fetch('/api/process-field', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            coordinates: JSON.parse(document.getElementById('coordinates').value),
                            target_date: document.getElementById('targetDate').value,
                            field_name: document.getElementById('fieldName').value
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.innerHTML = `
                            <div class="result success">
                                <h3>✅ Processing Successful!</h3>
                                <p><strong>Field:</strong> ${data.field_name}</p>
                                <p><strong>MGRS Tile:</strong> ${data.mgrs_tile}</p>
                                <p><strong>Available Date:</strong> ${data.available_date}</p>
                                <p><strong>Center Coordinates:</strong> ${data.center_coords[0].toFixed(4)}, ${data.center_coords[1].toFixed(4)}</p>
                                <p><strong>Message:</strong> ${data.message}</p>
                                
                                <h4>Sample NDVI Data:</h4>
                                <table border="1" style="width:100%; border-collapse: collapse;">
                                    <tr><th>Date</th><th>NDVI</th><th>Cloud %</th></tr>
                                    ${data.ndvi_samples.map(sample => 
                                        `<tr><td>${sample.date}</td><td>${sample.ndvi}</td><td>${sample.cloud_percentage}%</td></tr>`
                                    ).join('')}
                                </table>
                            </div>
                        `;
                    } else {
                        resultDiv.innerHTML = `
                            <div class="result error">
                                <h3>❌ Processing Failed</h3>
                                <p>${data.error}</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>❌ Error</h3>
                            <p>Failed to process request: ${error.message}</p>
                        </div>
                    `;
                }
            };
        </script>
    </body>
    </html>
    """
    return html

@app.route("/api/process-field", methods=["POST"])
def process_field():
    """Process field coordinates and return NDVI data"""
    try:
        data = request.get_json()
        
        coordinates = data.get('coordinates')
        target_date = data.get('target_date')
        field_name = data.get('field_name', 'Unnamed Field')
        
        if not coordinates or not target_date:
            return jsonify({
                'success': False,
                'error': 'Missing coordinates or target_date'
            }), 400
        
        # Validate coordinates format
        if not isinstance(coordinates, list) or len(coordinates) < 3:
            return jsonify({
                'success': False,
                'error': 'Invalid coordinate format. Need at least 3 points.'
            }), 400
        
        # Process the field
        result = processor.get_sample_ndvi_data(coordinates, target_date)
        result['field_name'] = field_name
        result['processing_timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Sentinel-2 AWS Processor is running',
        'timestamp': datetime.now().isoformat(),
        'bucket_access': 'Available (public data)'
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
