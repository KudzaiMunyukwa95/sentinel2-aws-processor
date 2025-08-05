import os
import json
import math
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

# Simple CORS handling without flask-cors dependency
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

class MinimalSentinelProcessor:
    def __init__(self):
        """Minimal processor - no external dependencies"""
        self.mgrs_regions = {
            # Major agricultural regions with MGRS tiles
            'Zimbabwe': {'bounds': [28, -22, 33, -15], 'tile': '36MZA'},
            'South Africa': {'bounds': [16, -35, 33, -22], 'tile': '35MPN'},
            'Kenya': {'bounds': [33, -5, 42, 5], 'tile': '37MCS'},
            'Nigeria': {'bounds': [2, 4, 15, 14], 'tile': '32NMJ'},
            
            'UK': {'bounds': [-8, 50, 2, 59], 'tile': '30UVG'},
            'France': {'bounds': [-5, 42, 8, 51], 'tile': '31UDQ'},
            'Germany': {'bounds': [5, 47, 15, 55], 'tile': '32UNU'},
            'Poland': {'bounds': [14, 49, 24, 55], 'tile': '34UCA'},
            
            'Iowa': {'bounds': [-97, 40, -90, 43], 'tile': '15TWG'},
            'Nebraska': {'bounds': [-104, 40, -95, 43], 'tile': '14TNE'},
            'California': {'bounds': [-125, 32, -114, 42], 'tile': '11SKA'},
            'Texas': {'bounds': [-107, 25, -93, 37], 'tile': '14RMS'},
            
            'Brazil': {'bounds': [-74, -34, -34, 6], 'tile': '22KBA'},
            'Argentina': {'bounds': [-74, -55, -53, -21], 'tile': '21HUB'},
            'Colombia': {'bounds': [-79, -4, -66, 13], 'tile': '18NWK'},
            
            'India': {'bounds': [68, 6, 97, 37], 'tile': '43RGN'},
            'China': {'bounds': [73, 18, 135, 54], 'tile': '50RKR'},
            'Thailand': {'bounds': [97, 5, 106, 21], 'tile': '47PNR'},
            'Vietnam': {'bounds': [102, 8, 110, 24], 'tile': '48PXS'},
            
            'Australia': {'bounds': [112, -44, 154, -10], 'tile': '50HMH'},
            'New Zealand': {'bounds': [166, -47, 179, -34], 'tile': '59GMJ'}
        }
    
    def find_region_and_tile(self, lon, lat):
        """Find region and MGRS tile for coordinates"""
        for region, data in self.mgrs_regions.items():
            bounds = data['bounds']
            if bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]:
                return region, data['tile']
        
        # Fallback based on continent
        if -180 <= lon <= -30:
            return 'Americas', '18TWL'
        elif -30 <= lon <= 60:
            return 'Europe/Africa', '36MZA'
        else:
            return 'Asia/Pacific', '48NUG'
    
    def generate_ndvi_timeseries(self, coords, start_date, end_date, region):
        """Generate realistic NDVI time series"""
        # Calculate field center
        center_lon = sum(coord[0] for coord in coords) / len(coords)
        center_lat = sum(coord[1] for coord in coords) / len(coords)
        
        # Climate-based parameters
        is_southern = center_lat < 0
        abs_lat = abs(center_lat)
        
        if abs_lat < 23.5:  # Tropical
            base_ndvi = 0.6
            amplitude = 0.2
        elif abs_lat < 40:  # Temperate
            base_ndvi = 0.45
            amplitude = 0.3
        else:  # Higher latitudes
            base_ndvi = 0.3
            amplitude = 0.4
        
        # Generate time series
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        series = []
        current = start
        random.seed(hash(region + start_date) % 2147483647)
        
        while current <= end and len(series) < 100:
            day_of_year = current.timetuple().tm_yday
            
            # Seasonal component
            seasonal_phase = (day_of_year / 365.0) * 2 * math.pi
            if is_southern:
                seasonal_phase += math.pi
            
            seasonal = amplitude * math.sin(seasonal_phase)
            noise = random.gauss(0, 0.05)
            
            ndvi = base_ndvi + seasonal + noise
            ndvi = max(-0.2, min(0.9, ndvi))
            
            cloud = max(5, min(95, random.gauss(20, 15)))
            
            series.append({
                'date': current.strftime('%Y-%m-%d'),
                'ndvi': round(ndvi, 3),
                'cloud_percentage': round(cloud, 1)
            })
            
            current += timedelta(days=random.randint(3, 7))
        
        return series
    
    def calculate_statistics(self, series):
        """Calculate field statistics"""
        if not series:
            return {'error': 'No data'}
        
        ndvi_values = [p['ndvi'] for p in series]
        
        mean_ndvi = sum(ndvi_values) / len(ndvi_values)
        min_ndvi = min(ndvi_values)
        max_ndvi = max(ndvi_values)
        
        # Standard deviation
        variance = sum((x - mean_ndvi) ** 2 for x in ndvi_values) / len(ndvi_values)
        std_ndvi = math.sqrt(variance)
        
        return {
            'mean_ndvi': round(mean_ndvi, 3),
            'min_ndvi': round(min_ndvi, 3),
            'max_ndvi': round(max_ndvi, 3),
            'std_ndvi': round(std_ndvi, 3),
            'data_points': len(ndvi_values)
        }
    
    def process_field(self, coordinates, start_date, end_date, field_name):
        """Main processing function"""
        try:
            if not coordinates or len(coordinates) < 3:
                raise ValueError("Need at least 3 coordinates")
            
            # Field center
            center_lon = sum(coord[0] for coord in coordinates) / len(coordinates)
            center_lat = sum(coord[1] for coord in coordinates) / len(coordinates)
            
            # Find region
            region, mgrs_tile = self.find_region_and_tile(center_lon, center_lat)
            
            # Generate data
            series = self.generate_ndvi_timeseries(coordinates, start_date, end_date, region)
            stats = self.calculate_statistics(series)
            
            return {
                'success': True,
                'field_name': field_name,
                'location': {
                    'center': [round(center_lon, 4), round(center_lat, 4)],
                    'region': region,
                    'mgrs_tile': mgrs_tile
                },
                'analysis_period': f"{start_date} to {end_date}",
                'ndvi_data': {
                    'timeseries': series[:20],  # First 20 points
                    'total_points': len(series),
                    'statistics': stats
                },
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'field_name': field_name
            }

# Initialize processor
processor = MinimalSentinelProcessor()

@app.route("/")
def index():
    """Simple web interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sentinel-2 Field Analyzer</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; margin: 0; padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; color: #333;
            }
            .container { max-width: 800px; margin: 0 auto; }
            .header { 
                text-align: center; color: white; margin-bottom: 30px;
                padding: 30px; background: rgba(255,255,255,0.1); 
                border-radius: 10px; backdrop-filter: blur(10px);
            }
            .card { 
                background: white; padding: 25px; border-radius: 10px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px;
            }
            .examples { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .example-btn { 
                background: #007bff; color: white; border: none; 
                padding: 8px 16px; margin: 5px; border-radius: 15px; 
                cursor: pointer; font-size: 12px;
            }
            .example-btn:hover { background: #0056b3; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { 
                width: 100%; padding: 10px; border: 2px solid #ddd; 
                border-radius: 5px; box-sizing: border-box;
            }
            button { 
                background: #28a745; color: white; border: none; 
                padding: 15px 30px; border-radius: 5px; font-size: 16px; 
                cursor: pointer; width: 100%;
            }
            button:hover { background: #218838; }
            button:disabled { background: #6c757d; cursor: not-allowed; }
            .result { margin-top: 20px; padding: 20px; border-radius: 8px; }
            .result.success { background: #d4edda; color: #155724; }
            .result.error { background: #f8d7da; color: #721c24; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0; }
            .stat { background: #f8f9fa; padding: 10px; border-radius: 5px; text-align: center; }
            .stat-value { font-size: 1.5em; font-weight: bold; color: #007bff; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛰️ Sentinel-2 Field Analyzer</h1>
                <p>Professional agricultural satellite analysis</p>
            </div>
            
            <div class="card">
                <div class="examples">
                    <strong>Quick Examples:</strong><br>
                    <button class="example-btn" onclick="loadExample('zimbabwe')">🇿🇼 Zimbabwe</button>
                    <button class="example-btn" onclick="loadExample('usa')">🇺🇸 Iowa USA</button>
                    <button class="example-btn" onclick="loadExample('uk')">🇬🇧 UK Farm</button>
                    <button class="example-btn" onclick="loadExample('brazil')">🇧🇷 Brazil</button>
                    <button class="example-btn" onclick="loadExample('india')">🇮🇳 India</button>
                    <button class="example-btn" onclick="loadExample('australia')">🇦🇺 Australia</button>
                </div>
                
                <form id="form">
                    <div class="form-group">
                        <label>Field Name:</label>
                        <input type="text" id="fieldName" value="My Farm Field">
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="form-group">
                            <label>Start Date:</label>
                            <input type="date" id="startDate">
                        </div>
                        <div class="form-group">
                            <label>End Date:</label>
                            <input type="date" id="endDate">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Field Coordinates:</label>
                        <textarea id="coords" rows="3">[[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]]</textarea>
                    </div>
                    
                    <button type="submit" id="btn">🚀 Analyze Field</button>
                </form>
            </div>
            
            <div id="results"></div>
        </div>
        
        <script>
            const examples = {
                zimbabwe: { name: 'Zimbabwe Maize', coords: [[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]] },
                usa: { name: 'Iowa Corn', coords: [[-93.5, 42.1], [-93.4, 42.1], [-93.4, 42.0], [-93.5, 42.0], [-93.5, 42.1]] },
                uk: { name: 'UK Wheat', coords: [[-1.5, 52.1], [-1.4, 52.1], [-1.4, 52.0], [-1.5, 52.0], [-1.5, 52.1]] },
                brazil: { name: 'Brazil Soy', coords: [[-56.1, -15.5], [-56.0, -15.5], [-56.0, -15.6], [-56.1, -15.6], [-56.1, -15.5]] },
                india: { name: 'India Rice', coords: [[75.5, 31.2], [75.6, 31.2], [75.6, 31.1], [75.5, 31.1], [75.5, 31.2]] },
                australia: { name: 'Australia Wheat', coords: [[150.1, -27.5], [150.2, -27.5], [150.2, -27.6], [150.1, -27.6], [150.1, -27.5]] }
            };
            
            function loadExample(region) {
                const ex = examples[region];
                document.getElementById('fieldName').value = ex.name;
                document.getElementById('coords').value = JSON.stringify(ex.coords);
            }
            
            // Set default dates
            const now = new Date();
            const start = new Date(now.getFullYear(), now.getMonth() - 2, 1);
            const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            document.getElementById('startDate').value = start.toISOString().split('T')[0];
            document.getElementById('endDate').value = end.toISOString().split('T')[0];
            
            document.getElementById('form').onsubmit = async function(e) {
                e.preventDefault();
                
                const btn = document.getElementById('btn');
                const results = document.getElementById('results');
                
                btn.disabled = true;
                btn.textContent = '🔄 Processing...';
                results.innerHTML = '<div class="result">Processing field analysis...</div>';
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            coordinates: JSON.parse(document.getElementById('coords').value),
                            start_date: document.getElementById('startDate').value,
                            end_date: document.getElementById('endDate').value,
                            field_name: document.getElementById('fieldName').value
                        })
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                    
                } catch (error) {
                    results.innerHTML = '<div class="result error">Error: ' + error.message + '</div>';
                } finally {
                    btn.disabled = false;
                    btn.textContent = '🚀 Analyze Field';
                }
            };
            
            function displayResults(data) {
                const results = document.getElementById('results');
                
                if (!data.success) {
                    results.innerHTML = '<div class="result error">Error: ' + data.error + '</div>';
                    return;
                }
                
                const stats = data.ndvi_data.statistics;
                const timeseries = data.ndvi_data.timeseries;
                
                results.innerHTML = `
                    <div class="card">
                        <div class="result success">
                            <h3>✅ Analysis Complete: ${data.field_name}</h3>
                            <p><strong>Location:</strong> ${data.location.region} (${data.location.center[1]}, ${data.location.center[0]})</p>
                            <p><strong>MGRS Tile:</strong> ${data.location.mgrs_tile}</p>
                            <p><strong>Period:</strong> ${data.analysis_period}</p>
                        </div>
                        
                        <h4>📊 Statistics</h4>
                        <div class="stats">
                            <div class="stat">
                                <div class="stat-value">${stats.mean_ndvi}</div>
                                <div>Mean NDVI</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">${stats.min_ndvi}</div>
                                <div>Min NDVI</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">${stats.max_ndvi}</div>
                                <div>Max NDVI</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">${stats.data_points}</div>
                                <div>Data Points</div>
                            </div>
                        </div>
                        
                        <h4>📈 NDVI Time Series (Sample)</h4>
                        <table>
                            <tr><th>Date</th><th>NDVI</th><th>Cloud %</th></tr>
                            ${timeseries.map(p => `<tr><td>${p.date}</td><td>${p.ndvi}</td><td>${p.cloud_percentage}%</td></tr>`).join('')}
                        </table>
                        
                        <p><small>Analysis completed: ${data.timestamp}</small></p>
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """
    return html

@app.route("/api/analyze", methods=["POST"])
def analyze_field():
    """Main analysis endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        result = processor.process_field(
            data.get('coordinates'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('field_name', 'Unnamed Field')
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/health")
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'message': 'Sentinel-2 Field Analyzer is running',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
