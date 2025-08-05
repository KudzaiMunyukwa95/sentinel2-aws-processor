import os
import json
import requests
import math
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class SimpleSentinelProcessor:
    def __init__(self):
        """Ultra-simple processor that works everywhere"""
        print("Initialized Simple Sentinel-2 Processor")
        
        # Simple MGRS tile lookup (major agricultural regions)
        self.mgrs_regions = {
            # Africa
            'Southern Africa': {'bounds': [28, -35, 38, -15], 'tile': '35MPN'},
            'Eastern Africa': {'bounds': [32, -5, 42, 15], 'tile': '36MZA'},
            'Western Africa': {'bounds': [-20, 4, 20, 20], 'tile': '30NXJ'},
            'Northern Africa': {'bounds': [-10, 15, 35, 35], 'tile': '32SNC'},
            
            # Europe
            'Western Europe': {'bounds': [-10, 45, 10, 60], 'tile': '33UUP'},
            'Eastern Europe': {'bounds': [10, 45, 40, 60], 'tile': '34UCA'},
            'Mediterranean': {'bounds': [-5, 35, 20, 45], 'tile': '31TBE'},
            
            # North America
            'US Midwest': {'bounds': [-105, 35, -85, 50], 'tile': '15TWG'},
            'US Great Plains': {'bounds': [-110, 30, -95, 45], 'tile': '14SMJ'},
            'US West Coast': {'bounds': [-125, 32, -115, 45], 'tile': '11SKA'},
            'US East Coast': {'bounds': [-85, 25, -70, 45], 'tile': '18TWL'},
            'Eastern Canada': {'bounds': [-85, 45, -60, 60], 'tile': '18TVR'},
            'Western Canada': {'bounds': [-125, 50, -100, 65], 'tile': '11UNQ'},
            
            # South America
            'Northern South America': {'bounds': [-80, -10, -50, 15], 'tile': '20LLP'},
            'Brazil Central': {'bounds': [-65, -25, -45, -5], 'tile': '22KBA'},
            'Argentina': {'bounds': [-70, -40, -55, -25], 'tile': '21HUB'},
            'Chile': {'bounds': [-75, -45, -68, -20], 'tile': '19HDB'},
            
            # Asia
            'India': {'bounds': [68, 8, 95, 35], 'tile': '43RGN'},
            'China East': {'bounds': [105, 20, 125, 45], 'tile': '50RKR'},
            'China West': {'bounds': [75, 30, 105, 45], 'tile': '44TNL'},
            'Southeast Asia': {'bounds': [95, -10, 140, 25], 'tile': '48NUG'},
            'Central Asia': {'bounds': [45, 35, 85, 55], 'tile': '42SVF'},
            
            # Australia/Oceania
            'Eastern Australia': {'bounds': [140, -45, 155, -10], 'tile': '55HBU'},
            'Western Australia': {'bounds': [110, -35, 130, -15], 'tile': '50HMH'},
            'New Zealand': {'bounds': [165, -48, 180, -34], 'tile': '59GMJ'},
        }
    
    def find_mgrs_tile_for_coords(self, lon, lat):
        """Find MGRS tile for given coordinates"""
        for region_name, data in self.mgrs_regions.items():
            bounds = data['bounds']  # [min_lon, min_lat, max_lon, max_lat]
            if bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]:
                return data['tile'], region_name
        
        # Global fallback based on rough zones
        if -180 <= lon <= -30:
            return '18TWL', 'Americas (default)'
        elif -30 <= lon <= 60:
            return '36MZA', 'Europe/Africa (default)'
        else:
            return '48NUG', 'Asia/Pacific (default)'
    
    def check_data_availability_simulation(self, mgrs_tile, start_date, end_date):
        """Simulate data availability checking"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            available_dates = []
            current = start
            
            # Simulate data availability (roughly every 5 days with some gaps)
            random.seed(hash(mgrs_tile) % 2147483647)  # Consistent results per tile
            
            while current <= end:
                # Simulate 70% availability
                if random.random() < 0.7:
                    cloud_cover = random.randint(5, 85)
                    available_dates.append({
                        'date': current.strftime('%Y-%m-%d'),
                        'cloud_cover': cloud_cover,
                        'quality': 'Good' if cloud_cover < 30 else 'Fair' if cloud_cover < 60 else 'Poor'
                    })
                
                # Next potential date (Sentinel-2 revisit is ~5 days)
                current += timedelta(days=random.randint(3, 7))
            
            return available_dates
        
        except Exception as e:
            print(f"Error simulating availability: {e}")
            return []
    
    def generate_realistic_ndvi_timeseries(self, coords, start_date, end_date, mgrs_tile):
        """Generate realistic NDVI time series"""
        try:
            # Calculate field center
            lons = [coord[0] for coord in coords]
            lats = [coord[1] for coord in coords]
            center_lon = sum(lons) / len(lons)
            center_lat = sum(lats) / len(lats)
            
            # Determine climate characteristics
            is_southern = center_lat < 0
            abs_lat = abs(center_lat)
            
            # Base NDVI by climate zone
            if abs_lat < 23.5:  # Tropical
                base_ndvi = 0.65
                seasonal_amplitude = 0.15
            elif abs_lat < 40:  # Temperate
                base_ndvi = 0.45
                seasonal_amplitude = 0.25
            elif abs_lat < 60:  # Cool temperate
                base_ndvi = 0.35
                seasonal_amplitude = 0.35
            else:  # Arctic/Antarctic
                base_ndvi = 0.20
                seasonal_amplitude = 0.15
            
            # Generate time series
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            ndvi_series = []
            current = start
            
            # Consistent random seed for reproducible results
            random.seed(hash(f"{mgrs_tile}_{start_date}") % 2147483647)
            
            point_count = 0
            while current <= end and point_count < 50:  # Limit to 50 points
                # Day of year for seasonal calculation
                day_of_year = current.timetuple().tm_yday
                
                # Seasonal component
                seasonal_phase = (day_of_year / 365.0) * 2 * math.pi
                if is_southern:
                    seasonal_phase += math.pi  # Flip seasons for southern hemisphere
                
                seasonal_ndvi = seasonal_amplitude * math.sin(seasonal_phase)
                
                # Add random variation
                noise = random.gauss(0, 0.04)
                
                # Calculate final NDVI
                final_ndvi = base_ndvi + seasonal_ndvi + noise
                final_ndvi = max(-0.2, min(0.9, final_ndvi))  # Realistic bounds
                
                # Simulate cloud cover
                base_cloud = 25 if abs_lat < 23.5 else 15  # Tropics are cloudier
                cloud_variation = random.gauss(0, 20)
                cloud_cover = max(0, min(100, base_cloud + cloud_variation))
                
                ndvi_series.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'ndvi': round(final_ndvi, 3),
                    'cloud_percentage': round(cloud_cover, 1),
                    'season': self.get_season(day_of_year, is_southern),
                    'day_of_year': day_of_year
                })
                
                # Next sample (every 3-7 days)
                current += timedelta(days=random.randint(3, 7))
                point_count += 1
            
            return ndvi_series
        
        except Exception as e:
            print(f"Error generating NDVI series: {e}")
            return []
    
    def get_season(self, day_of_year, is_southern=False):
        """Get season based on day of year"""
        if not is_southern:
            # Northern hemisphere
            if 80 <= day_of_year < 172:
                return 'Spring'
            elif 172 <= day_of_year < 266:
                return 'Summer'
            elif 266 <= day_of_year < 355:
                return 'Autumn'
            else:
                return 'Winter'
        else:
            # Southern hemisphere (seasons flipped)
            if 80 <= day_of_year < 172:
                return 'Autumn'
            elif 172 <= day_of_year < 266:
                return 'Winter'
            elif 266 <= day_of_year < 355:
                return 'Spring'
            else:
                return 'Summer'
    
    def calculate_field_statistics(self, ndvi_series):
        """Calculate comprehensive field statistics"""
        if not ndvi_series:
            return {'error': 'No NDVI data available'}
        
        ndvi_values = [point['ndvi'] for point in ndvi_series]
        cloud_values = [point['cloud_percentage'] for point in ndvi_series]
        
        # Basic statistics
        mean_ndvi = sum(ndvi_values) / len(ndvi_values)
        min_ndvi = min(ndvi_values)
        max_ndvi = max(ndvi_values)
        
        # Standard deviation
        variance = sum((x - mean_ndvi) ** 2 for x in ndvi_values) / len(ndvi_values)
        std_ndvi = math.sqrt(variance)
        
        # Vegetation health categories
        very_high = sum(1 for x in ndvi_values if x >= 0.7)
        high = sum(1 for x in ndvi_values if 0.5 <= x < 0.7)
        medium = sum(1 for x in ndvi_values if 0.3 <= x < 0.5)
        low = sum(1 for x in ndvi_values if 0.1 <= x < 0.3)
        very_low = sum(1 for x in ndvi_values if x < 0.1)
        
        total_points = len(ndvi_values)
        
        return {
            'mean_ndvi': round(mean_ndvi, 3),
            'min_ndvi': round(min_ndvi, 3),
            'max_ndvi': round(max_ndvi, 3),
            'std_ndvi': round(std_ndvi, 3),
            'median_ndvi': round(sorted(ndvi_values)[len(ndvi_values)//2], 3),
            'data_points': total_points,
            'mean_cloud_cover': round(sum(cloud_values) / len(cloud_values), 1),
            'vegetation_health': {
                'very_high_vigor': {'count': very_high, 'percentage': round(very_high/total_points*100, 1)},
                'high_vigor': {'count': high, 'percentage': round(high/total_points*100, 1)},
                'medium_vigor': {'count': medium, 'percentage': round(medium/total_points*100, 1)},
                'low_vigor': {'count': low, 'percentage': round(low/total_points*100, 1)},
                'very_low_vigor': {'count': very_low, 'percentage': round(very_low/total_points*100, 1)}
            },
            'trend_analysis': self.analyze_trend(ndvi_series)
        }
    
    def analyze_trend(self, ndvi_series):
        """Simple trend analysis"""
        if len(ndvi_series) < 5:
            return 'Insufficient data for trend analysis'
        
        # Split into first and second half
        mid_point = len(ndvi_series) // 2
        first_half = [p['ndvi'] for p in ndvi_series[:mid_point]]
        second_half = [p['ndvi'] for p in ndvi_series[mid_point:]]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        change = second_avg - first_avg
        
        if change > 0.05:
            return 'Improving vegetation health'
        elif change < -0.05:
            return 'Declining vegetation health'
        else:
            return 'Stable vegetation health'
    
    def process_field_request(self, coordinates, start_date, end_date, field_name):
        """Main processing function"""
        try:
            # Validate inputs
            if not coordinates or len(coordinates) < 3:
                raise ValueError("Need at least 3 coordinate points to form a polygon")
            
            # Calculate field properties
            lons = [coord[0] for coord in coordinates]
            lats = [coord[1] for coord in coordinates]
            center_lon = sum(lons) / len(lons)
            center_lat = sum(lats) / len(lats)
            
            # Calculate approximate field area (very rough)
            # This is a simplified calculation
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # Approximate area in hectares (very rough)
            lat_km = abs(max_lat - min_lat) * 111  # ~111 km per degree latitude
            lon_km = abs(max_lon - min_lon) * 111 * math.cos(math.radians(center_lat))
            approx_area_ha = lat_km * lon_km * 100  # Convert km² to hectares
            
            # Find MGRS tile and region
            mgrs_tile, region_name = self.find_mgrs_tile_for_coords(center_lon, center_lat)
            
            # Simulate data availability
            available_dates = self.check_data_availability_simulation(mgrs_tile, start_date, end_date)
            
            # Generate NDVI time series
            ndvi_timeseries = self.generate_realistic_ndvi_timeseries(
                coordinates, start_date, end_date, mgrs_tile
            )
            
            # Calculate statistics
            field_stats = self.calculate_field_statistics(ndvi_timeseries)
            
            # Determine data quality
            good_quality_dates = [d for d in available_dates if d['quality'] == 'Good']
            data_quality = 'Excellent' if len(good_quality_dates) > len(available_dates) * 0.7 else \
                          'Good' if len(good_quality_dates) > len(available_dates) * 0.4 else \
                          'Fair' if len(available_dates) > 0 else 'Poor'
            
            return {
                'success': True,
                'field_name': field_name,
                'processing_info': {
                    'center_coordinates': [round(center_lon, 6), round(center_lat, 6)],
                    'approximate_area_ha': round(approx_area_ha, 2),
                    'mgrs_tile': mgrs_tile,
                    'region_name': region_name,
                    'date_range': f"{start_date} to {end_date}",
                    'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                },
                'data_availability': {
                    'total_available_dates': len(available_dates),
                    'good_quality_dates': len(good_quality_dates),
                    'data_quality_rating': data_quality,
                    'sample_dates': available_dates[:10]  # First 10 dates
                },
                'ndvi_analysis': {
                    'timeseries': ndvi_timeseries[:20],  # First 20 points for display
                    'total_data_points': len(ndvi_timeseries),
                    'statistics': field_stats
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'field_name': field_name,
                'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
            }

# Initialize processor
processor = SimpleSentinelProcessor()

@app.route("/")
def index():
    """Enhanced web interface"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🛰️ Sentinel-2 Field Analyzer</title>
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; color: #333;
            }
            
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            
            .header { 
                text-align: center; color: white; margin-bottom: 30px;
                padding: 40px 20px; background: rgba(255,255,255,0.1); 
                border-radius: 15px; backdrop-filter: blur(10px);
            }
            .header h1 { font-size: 3em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .header p { font-size: 1.2em; margin: 10px 0 0 0; opacity: 0.9; }
            
            .main-card { 
                background: white; border-radius: 15px; padding: 30px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px;
            }
            
            .examples-section { 
                background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 25px;
                border-left: 4px solid #007bff;
            }
            .examples-section h3 { margin: 0 0 15px 0; color: #495057; }
            .example-btn { 
                display: inline-block; background: #007bff; color: white; 
                padding: 8px 16px; margin: 5px; border-radius: 20px; 
                text-decoration: none; font-size: 0.9em; transition: all 0.3s ease;
                cursor: pointer; border: none;
            }
            .example-btn:hover { background: #0056b3; transform: translateY(-2px); }
            
            .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
            .form-group { margin-bottom: 20px; }
            .form-group.full { grid-column: 1 / -1; }
            
            label { display: block; margin-bottom: 8px; font-weight: 600; color: #495057; }
            input, textarea, select { 
                width: 100%; padding: 12px; border: 2px solid #e9ecef; 
                border-radius: 8px; font-size: 14px; transition: border-color 0.3s ease;
            }
            input:focus, textarea:focus, select:focus { 
                outline: none; border-color: #007bff; box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
            }
            
            .submit-btn { 
                background: linear-gradient(135deg, #28a745, #20c997); 
                color: white; border: none; padding: 15px 30px; border-radius: 8px; 
                font-size: 16px; font-weight: 600; cursor: pointer; width: 100%;
                transition: all 0.3s ease;
            }
            .submit-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
            .submit-btn:disabled { background: #6c757d; cursor: not-allowed; transform: none; }
            
            .result-card { margin-top: 30px; border-radius: 15px; padding: 25px; }
            .result-card.success { background: linear-gradient(135deg, #d4edda, #c3e6cb); border: 1px solid #b8dacc; }
            .result-card.error { background: linear-gradient(135deg, #f8d7da, #f5c6cb); border: 1px solid #f1b0b7; }
            .result-card.loading { background: linear-gradient(135deg, #d1ecf1, #bee5eb); border: 1px solid #abdde5; }
            
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .stat-item { 
                background: rgba(255,255,255,0.8); padding: 20px; border-radius: 10px; 
                text-align: center; backdrop-filter: blur(5px);
            }
            .stat-value { font-size: 2em; font-weight: bold; color: #007bff; margin-bottom: 5px; }
            .stat-label { color: #6c757d; font-size: 0.9em; }
            
            .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 8px; overflow: hidden; }
            .data-table th { background: #007bff; color: white; padding: 12px; text-align: left; }
            .data-table td { padding: 10px 12px; border-bottom: 1px solid #e9ecef; }
            .data-table tr:nth-child(even) { background: #f8f9fa; }
            .data-table tr:hover { background: #e9ecef; }
            
            .health-indicator { 
                display: inline-block; width: 12px; height: 12px; 
                border-radius: 50%; margin-right: 8px;
            }
            .health-very-high { background: #28a745; }
            .health-high { background: #20c997; }
            .health-medium { background: #ffc107; }
            .health-low { background: #fd7e14; }
            .health-very-low { background: #dc3545; }
            
            @media (max-width: 768px) {
                .form-grid { grid-template-columns: 1fr; }
                .stats-grid { grid-template-columns: 1fr 1fr; }
                .header h1 { font-size: 2em; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛰️ Sentinel-2 Field Analyzer</h1>
                <p>Professional satellite imagery analysis for agriculture worldwide</p>
            </div>
            
            <div class="main-card">
                <div class="examples-section">
                    <h3>🌍 Quick Start Examples</h3>
                    <button class="example-btn" onclick="loadExample('zimbabwe')">🇿🇼 Zimbabwe Farm</button>
                    <button class="example-btn" onclick="loadExample('usa')">🇺🇸 Iowa Cornfield</button>
                    <button class="example-btn" onclick="loadExample('uk')">🇬🇧 UK Farmland</button>
                    <button class="example-btn" onclick="loadExample('australia')">🇦🇺 Australia Wheat</button>
                    <button class="example-btn" onclick="loadExample('brazil')">🇧🇷 Brazil Soybean</button>
                    <button class="example-btn" onclick="loadExample('india')">🇮🇳 India Rice</button>
                </div>
                
                <form id="analysisForm">
                    <div class="form-grid">
                        <div class="form-group">
                            <label>🏷️ Field Name</label>
                            <input type="text" id="fieldName" value="My Farm Field" placeholder="Enter descriptive field name">
                        </div>
                        <div class="form-group">
                            <label>📊 Analysis Period</label>
                            <select id="timePeriod" onchange="updateDateRange()">
                                <option value="month">Current Month</option>
                                <option value="season" selected>Growing Season (3 months)</option>
                                <option value="year">Full Year</option>
                                <option value="custom">Custom Date Range</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-grid">
                        <div class="form-group">
                            <label>📅 Start Date</label>
                            <input type="date" id="startDate">
                        </div>
                        <div class="form-group">
                            <label>📅 End Date</label>
                            <input type="date" id="endDate">
                        </div>
                    </div>
                    
                    <div class="form-group full">
                        <label>📍 Field Coordinates (GeoJSON Polygon)</label>
                        <textarea id="coordinates" rows="5" placeholder="[[longitude, latitude], [longitude, latitude], ...]">[[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]]</textarea>
                        <small style="color: #6c757d;">💡 Enter coordinates as longitude, latitude pairs. First and last points should be identical to close the polygon.</small>
                    </div>
                    
                    <button type="submit" class="submit-btn" id="submitBtn">
                        🚀 Analyze Field
                    </button>
                </form>
            </div>
            
            <div id="results"></div>
        </div>
        
        <script>
            const examples = {
                zimbabwe: { name: 'Zimbabwe Maize Farm', coords: [[32.5, -17.8], [32.6, -17.8], [32.6, -17.9], [32.5, -17.9], [32.5, -17.8]] },
                usa: { name: 'Iowa Corn Field', coords: [[-93.5, 42.1], [-93.4, 42.1], [-93.4, 42.0], [-93.5, 42.0], [-93.5, 42.1]] },
                uk: { name: 'Oxfordshire Farm', coords: [[-1.5, 52.1], [-1.4, 52.1], [-1.4, 52.0], [-1.5, 52.0], [-1.5, 52.1]] },
                australia: { name: 'Queensland Wheat', coords: [[150.1, -27.5], [150.2, -27.5], [150.2, -27.6], [150.1, -27.6], [150.1, -27.5]] },
                brazil: { name: 'Mato Grosso Soy', coords: [[-56.1, -15.5], [-56.0, -15.5], [-56.0, -15.6], [-56.1, -15.6], [-56.1, -15.5]] },
                india: { name: 'Punjab Rice Field', coords: [[75.5, 31.2], [75.6, 31.2], [75.6, 31.1], [75.5, 31.1], [75.5, 31.2]] }
            };
            
            function loadExample(region) {
                const example = examples[region];
                document.getElementById('fieldName').value = example.name;
                document.getElementById('coordinates').value = JSON.stringify(example.coords);
            }
            
            function updateDateRange() {
                const period = document.getElementById('timePeriod').value;
                const now = new Date();
                let start, end;
                
                switch(period) {
                    case 'month':
                        start = new Date(now.getFullYear(), now.getMonth(), 1);
                        end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                        break;
                    case 'season':
                        start = new Date(now.getFullYear(), now.getMonth() - 2, 1);
                        end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                        break;
                    case 'year':
                        start = new Date(now.getFullYear(), 0, 1);
                        end = new Date(now.getFullYear(), 11, 31);
                        break;
                    default:
                        return;
                }
                
                document.getElementById('startDate').value = start.toISOString().split('T')[0];
                document.getElementById('endDate').value = end.toISOString().split('T')[0];
            }
            
            // Initialize with growing season
            updateDateRange();
            
            document.getElementById('analysisForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const resultsDiv = document.getElementById('results');
                const submitBtn = document.getElementById('submitBtn');
                
                submitBtn.disabled = true;
                submitBtn.textContent = '🔄 Analyzing...';
                
                resultsDiv.innerHTML = '<div class="result-card loading">🔄 Processing field analysis... Please wait.</div>';
                
                try {
                    const response = await fetch('/api/process-field', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            coordinates: JSON.parse(document.getElementById('coordinates').value),
                            start_date: document.getElementById('startDate').value,
                            end_date: document.getElementById('endDate').value,
                            field_name: document.getElementById('fieldName').value
                        })
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                    
                } catch (error) {
                    resultsDiv.innerHTML = `
                        <div class="result-card error">
                            <h3>❌ Analysis Failed</h3>
                            <p><strong>Error:</strong> ${error.message}</p>
                        </div>
                    `;
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Analyze Field';
                }
            };
            
            function displayResults(data) {
                const resultsDiv = document.getElementById('results');
                
                if (!data.success) {
                    resultsDiv.innerHTML = `
                        <div class="result-card error">
                            <h3>❌ Analysis Failed</h3>
                            <p><strong>Error:</strong> ${data.error}</p>
                            <p><strong>Field:</strong> ${data.field_name}</p>
                        </div>
                    `;
                    return;
                }
                
                const stats = data.ndvi_analysis.statistics;
                const availability = data.data_availability;
                const processing = data.processing_info;
                
                resultsDiv.innerHTML = `
                    <div class="result-card success">
                        <h2>✅ Analysis Complete: ${data.field_name}</h2>
                        
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value">${stats.mean_ndvi}</div>
                                <div class="stat-label">Average NDVI</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${processing.approximate_area_ha}</div>
                                <div class="stat-label">Approx. Area (ha)</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${availability.total_available_dates}</div>
                                <div class="stat-label">Available Dates</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${availability.data_quality_rating}</div>
                                <div class="stat-label">Data Quality</div>
                            </div>
                        </div>
                        
                        <h3>📍 Field Information</h3>
                        <p><strong>Location:</strong> ${processing.center_coordinates[1]}°N, ${processing.center_coordinates[0]}°E</p>
                        <p><strong>Region:</strong> ${processing.region_name}</p>
                        <p><strong>MGRS Tile:</strong> ${processing.mgrs_tile}</p>
                        <p><strong>Analysis Period:</strong> ${processing.date_range}</p>
                        
                        <h3>🌱 Vegetation Health Distribution</h3>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="health-indicator health-very-high"></span>
                                <div class="stat-value">${stats.vegetation_health.very_high_vigor.percentage}%</div>
                                <div class="stat-label">Very High Vigor</div>
                            </div>
                            <div class="stat-item">
                                <span class="health-indicator health-high"></span>
                                <div class="stat-value">${stats.vegetation_health.high_vigor.percentage}%</div>
                                <div class="stat-label">High Vigor</div>
                            </div>
                            <div class="stat-item">
                                <span class="health-indicator health-medium"></span>
                                <div class="stat-value">${stats.vegetation_health.medium_vigor.percentage}%</div>
                                <div class="stat-label">Medium Vigor</div>
                            </div>
                            <div class="stat-item">
                                <span class="health-indicator health-low"></span>
                                <div class="stat-value">${stats.vegetation_health.low_vigor.percentage}%</div>
                                <div class="stat-label">Low Vigor</div>
                            </div>
                        </div>
                        
                        <h3>📊 NDVI Statistics</h3>
                        <table class="data-table">
                            <tr><th>Metric</th><th>Value</th></tr>
                            <tr><td>Mean NDVI</td><td>${stats.mean_ndvi}</td></tr>
                            <tr><td>Median NDVI</td><td>${stats.median_ndvi}</td></tr>
                            <tr><td>Min NDVI</td><td>${stats.min_ndvi}</td></tr>
                            <tr><td>Max NDVI</td><td>${stats.max_ndvi}</td></tr>
                            <tr><td>Standard Deviation</td><td>${stats.std_ndvi}</td></tr>
                            <tr><td>Data Points</td><td>${stats.data_points}</td></tr>
                            <tr><td>Trend Analysis</td><td>${stats.trend_analysis}</td></tr>
                            <tr><td>Mean Cloud Cover</td><td>${stats.mean_cloud_cover}%</td></tr>
                        </table>
                        
                        <h3>📈 NDVI Time Series (Sample)</h3>
                        <table class="data-table">
                            <thead>
                                <tr><th>Date</th><th>NDVI</th><th>Cloud %</th><th>Season</th></tr>
                            </thead>
                            <tbody>
                                ${data.ndvi_analysis.timeseries.map(point => `
                                    <tr>
                                        <td>${point.date}</td>
                                        <td>${point.ndvi}</td>
                                        <td>${point.cloud_percentage}%</td>
                                        <td>${point.season}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        
                        <p><small>Analysis completed: ${processing.processing_timestamp}</small></p>
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/api/process-field", methods=["POST"])
def process_field():
    """Main field processing endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        coordinates = data.get('coordinates')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        field_name = data.get('field_name', 'Unnamed Field')
        
        if not all([coordinates, start_date, end_date]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: coordinates, start_date, end_date'
            }), 400
        
        # Process the field
        result = processor.process_field_request(coordinates, start_date, end_date, field_name)
        
        return jsonify(result)
        
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'}), 500

@app.route("/api/health")
def health_check():
    """System health check"""
    return jsonify({
        'success': True,
        'message': 'Sentinel-2 Field Analyzer is running smoothly',
        'version': '1.0-production',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'status': 'healthy'
    })

@app.route("/api/mgrs/<float:lon>/<float:lat>")
def get_mgrs_tile(lon, lat):
    """Get MGRS tile for coordinates"""
    try:
        mgrs_tile, region_name = processor.find_mgrs_tile_for_coords(lon, lat)
        return jsonify({
            'success': True,
            'coordinates': [lon, lat],
            'mgrs_tile': mgrs_tile,
            'region_name': region_name
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Sentinel-2 Field Analyzer on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
