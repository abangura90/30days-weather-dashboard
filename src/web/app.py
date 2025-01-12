from flask import Flask, render_template, jsonify, request
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import os
import boto3
import json
import requests
import traceback
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weather_collector_app.weather_collector import verify_bucket, fetch_weather, save_to_s3, get_cities

# Create Flask app with correct template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

# Configure default settings
app.config.update(
    JSON_SORT_KEYS=False,
    TEMPLATES_AUTO_RELOAD=True
)
# # Add the src directory to the Python path so we can import weather_dashboard
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from weather_collector.weather_collector import verify_bucket, fetch_weather, save_to_s3, get_cities

# app = Flask(__name__)


def get_weather_data(bucket_name, hours=24):
    """Retrieve weather data from OpenWeather API if S3 data is not available"""
    weather_data = []
    cities = ['London', 'New Jersey', 'Japan']
    api_key = os.environ.get('OPENWEATHER_API_KEY')

    # Try S3 first if credentials are available
    if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
        try:
            if not os.environ.get('AWS_DEFAULT_REGION'):
                os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
            
            s3 = boto3.client('s3')
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix='weather-data/'
            )
            
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    file_response = s3.get_object(
                        Bucket=bucket_name,
                        Key=obj['Key']
                    )
                    data = json.loads(file_response['Body'].read())
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if timestamp > datetime.now() - timedelta(hours=hours):
                        weather_data.append(data)
            
            if weather_data:
                return sorted(weather_data, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            app.logger.error(f"S3 error: {str(e)}")
            # Continue to API fallback if S3 fails

    # Fallback to direct API calls if no S3 data
    if not weather_data and api_key:
        for city in cities:
            try:
                data = fetch_weather(city, api_key)
                if data:
                    data['timestamp'] = datetime.now().isoformat()
                    weather_data.append(data)
            except Exception as e:
                app.logger.error(f"API error for {city}: {str(e)}")
                continue

    return sorted(weather_data, key=lambda x: x['timestamp'], reverse=True) if weather_data else []

def create_temperature_gauge(data):
    """Create animated temperature gauge"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=data['main']['temp'],
        delta={'reference': data['main']['feels_like'],
               'position': "top"},
        gauge={
            'axis': {'range': [data['main']['temp_min'], data['main']['temp_max']],
                    'tickwidth': 1,
                    'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [data['main']['temp_min'], data['main']['feels_like']], 'color': 'royalblue'},
                {'range': [data['main']['feels_like'], data['main']['temp_max']], 'color': 'lightblue'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': data['main']['feels_like']
            }
        },
        title={'text': f"Temperature in {data['name']}"}
    ))
    
    # Add animation
    fig.update_layout(
        updatemenus=[{
            'type': "buttons",
            'showactive': False,
            'buttons': [{
                'label': "Refresh",
                'method': "animate",
                'args': [None, {"frame": {"duration": 500, "redraw": True},
                                "fromcurrent": True}]
            }]
        }]
    )
    return fig

def create_wind_compass(data):
    """Create interactive wind direction compass"""
    fig = go.Figure(go.Scatterpolar(
        r=[data['wind']['speed']],
        theta=[data['wind']['deg']],
        mode='markers+text',
        marker=dict(
            size=40,
            symbol='arrow',
            angle=data['wind']['deg'],
            color='royalblue'
        ),
        text=[f"{data['wind']['speed']} mph"],
        textposition="top center"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, max(20, data['wind']['speed'] + 5)]),
            angularaxis=dict(
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
            )
        ),
        title="Wind Direction and Speed"
    )
    return fig

def create_weather_dashboard(data):
    """Create a comprehensive weather dashboard"""
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "indicator"}, {"type": "polar"}]],
        subplot_titles=("Temperature", "Humidity", "Pressure", "Wind")
    )

    # Temperature indicator
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=data['main']['temp'],
            delta={'reference': data['main']['feels_like']},
            title={'text': "Temperature (°F)"},
            domain={'x': [0, 0.5], 'y': [0.5, 1]}
        ),
        row=1, col=1
    )

    # Humidity gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=data['main']['humidity'],
            gauge={
                'axis': {'range': [0, 100]},
                'steps': [
                    {'range': [0, 20], 'color': "lightgray"},
                    {'range': [20, 40], 'color': "gray"},
                    {'range': [40, 60], 'color': "lightblue"},
                    {'range': [60, 80], 'color': "royalblue"},
                    {'range': [80, 100], 'color': "darkblue"}
                ],
                'bar': {'color': "#3498db"}
            },
            title={'text': "Humidity (%)"}
        ),
        row=1, col=2
    )

    # Pressure indicator
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=data['main']['pressure'],
            delta={'reference': 1013.25},  # Standard atmospheric pressure
            title={'text': "Pressure (hPa)"}
        ),
        row=2, col=1
    )

    # Wind rose
    fig.add_trace(
        go.Scatterpolar(
            r=[data['wind']['speed']],
            theta=[data['wind']['deg']],
            mode='markers',
            marker=dict(
                size=20,
                symbol='arrow',
                angle=data['wind']['deg'],
                color="#3498db"
            )
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_layout(
        height=600,
        showlegend=False,
        title=dict(
            text=f"Weather Conditions for {data['name']}",
            y=0.95
        ),
        polar=dict(
            radialaxis=dict(range=[0, max(20, data['wind']['speed'] + 5)]),
            angularaxis=dict(
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
            )
        ),
        margin=dict(t=100, b=20, l=20, r=20)
    )

    return fig

def create_forecast_chart(forecast_data):
    """Create a 5-day forecast chart"""
    # Process forecast data
    dates = []
    temps = []
    humidity = []
    descriptions = []
    icons = []

    for item in forecast_data['list']:
        dt = datetime.fromtimestamp(item['dt'])
        if dt.hour == 12:  # Get only noon forecasts for each day
            dates.append(dt.strftime('%Y-%m-%d'))
            temps.append(item['main']['temp'])
            humidity.append(item['main']['humidity'])
            descriptions.append(item['weather'][0]['description'])
            icons.append(item['weather'][0]['icon'])

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add temperature line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=temps,
            name="Temperature (°F)",
            line=dict(color='red', width=2),
            hovertemplate="Temperature: %{y:.1f}°F<br>Date: %{x}<extra></extra>"
        ),
        secondary_y=False
    )

    # Add humidity line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=humidity,
            name="Humidity (%)",
            line=dict(color='blue', width=2, dash='dot'),
            hovertemplate="Humidity: %{y}%<br>Date: %{x}<extra></extra>"
        ),
        secondary_y=True
    )

    # Add weather descriptions as annotations
    for i, (date, desc) in enumerate(zip(dates, descriptions)):
        fig.add_annotation(
            x=date,
            y=temps[i],
            text=desc,
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#636363",
            ax=0,
            ay=-40
        )

    # Update layout
    fig.update_layout(
        title=f"5-Day Weather Forecast for {forecast_data['city']['name']}",
        xaxis_title="Date",
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Update yaxis titles
    fig.update_yaxes(title_text="Temperature (°F)", secondary_y=False)
    fig.update_yaxes(title_text="Humidity (%)", secondary_y=True)

    return fig

def get_forecast_data(city):
    """Fetch 5-day forecast from OpenWeather API"""
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY not set")

    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    
    try:
        response = requests.get(
            base_url,
            params={
                'q': city,
                'appid': api_key,
                'units': 'imperial'  # Use Fahrenheit
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API request failed for {city}: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error fetching forecast data for {city}: {e}")
        return None

def create_modern_temp_gauge(data):
    """Create a modern temperature gauge visualization"""
    
    # Calculate temperature percentage
    temp_min = data['main']['temp_min']
    temp_max = data['main']['temp_max']
    current_temp = data['main']['temp']
    
    # Create modern gauge
    fig = go.Figure()

    # Add main temperature gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=current_temp,
        delta={
            'reference': data['main']['feels_like'],
            'position': "bottom",
            'valueformat': ".1f",
            'suffix': "°F",
            'font': {'size': 16}
        },
        number={
            'suffix': "°F",
            'font': {'size': 48, 'family': "Inter, sans-serif", 'color': "#1e293b"}
        },
        gauge={
            'axis': {
                'range': [temp_min - 5, temp_max + 5],
                'tickwidth': 2,
                'tickcolor': "#94a3b8",
                'tickfont': {'family': "Inter, sans-serif"},
                'ticksuffix': "°F"
            },
            'bar': {'color': "rgba(0,0,0,0)"},  # Transparent bar
            'bgcolor': "rgba(0,0,0,0)",  # Transparent background
            'borderwidth': 0,
            'steps': [
                {'range': [temp_min - 5, temp_max + 5], 'color': "rgba(241, 245, 249, 0.5)"},  # Background
                {'range': [temp_min - 5, current_temp], 'color': "rgba(59, 130, 246, 0.8)"}   # Progress
            ],
            'threshold': {
                'line': {'color': "#ef4444", 'width': 2},
                'thickness': 0.75,
                'value': data['main']['feels_like']
            }
        },
        title={
            'text': f"Current Weather<br><span style='font-size:0.9em'>{data['weather'][0]['description'].title()}</span>",
            'font': {'size': 20, 'family': "Inter, sans-serif", 'color': "#1e293b"}
        }
    ))

    # Add additional info annotation
    fig.add_annotation(
        text=f"H: {temp_max}°F • L: {temp_min}°F",
        x=0.5,
        y=0.1,
        showarrow=False,
        font={
            'size': 14,
            'family': "Inter, sans-serif",
            'color': "#64748b"
        }
    )

    # Update layout for modern look
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",   # Transparent plot
        height=300,
        margin=dict(t=80, b=40, l=40, r=40)
    )

    return fig

def create_weather_matrix(data):
    """Create weather data matrix visualization with optional fields"""
    
    # Get weather conditions
    conditions = data['weather'][0]['description'].title()
    
    # Base metrics
    metrics = [
        ['Temperature', f"{data['main']['temp']:.1f}°F"],
        ['Feels Like', f"{data['main']['feels_like']:.1f}°F"],
        ['Min/Max', f"{data['main']['temp_min']:.1f}°F / {data['main']['temp_max']:.1f}°F"],
        ['Humidity', f"{data['main']['humidity']}%"],
        ['Pressure', f"{data['main']['pressure']} hPa"],
        ['Visibility', f"{round(data['visibility'] / 1000, 1)} km"],
        ['Wind Speed', f"{data['wind'].get('speed', 0):.1f} mph"],
        ['Wind Direction', f"{data['wind'].get('deg', 0)}°"],
        ['Cloud Cover', f"{data['clouds']['all']}%"],
        ['Conditions', conditions]
    ]
    
    # Add rain data if available
    if 'rain' in data:
        rain_1h = data['rain'].get('1h', 0)
        metrics.append(['Rain (1h)', f"{rain_1h:.2f} mm"])
    
    # Add sea level and ground level pressure if available
    if 'sea_level' in data['main']:
        metrics.append(['Sea Level Pressure', f"{data['main']['sea_level']} hPa"])
    if 'grnd_level' in data['main']:
        metrics.append(['Ground Level Pressure', f"{data['main']['grnd_level']} hPa"])
    
    # Create table figure
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['Metric', 'Value'],
            fill_color='#3498db',
            align='left',
            font=dict(color='white', size=14),
            height=40
        ),
        cells=dict(
            values=list(zip(*metrics)),
            fill_color=[[
                '#f8f9fa' if i % 2 == 0 else 'white' for i in range(len(metrics))
            ]],
            align='left',
            font=dict(color=['#444', '#000'], size=14),
            height=30
        )
    )])

    # Update layout
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=len(metrics) * 35 + 40,
        showlegend=False
    )

    return fig

def create_temp_distribution(data):
    """Create temperature distribution visualization"""
    
    # Create temperature gauge with gradient
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=data['main']['temp'],
        delta={
            'reference': data['main']['feels_like'],
            'position': "top",
            'valueformat': ".1f"
        },
        number={
            'font': {'size': 40, 'color': '#2c3e50'},
            'valueformat': ".1f",
            'suffix': "°F"
        },
        gauge={
            'axis': {
                'range': [None, data['main']['temp_max'] + 5],
                'tickwidth': 1,
                'tickcolor': "#2c3e50"
            },
            'bar': {'color': "#3498db"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, data['main']['temp_min']], 'color': "#ebf5fa"},
                {'range': [data['main']['temp_min'], data['main']['temp']], 'color': "#3498db"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': data['main']['feels_like']
            }
        },
        title={
            'text': "Temperature Distribution",
            'font': {'size': 24, 'color': '#2c3e50'}
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='white',
        font={'color': "#2c3e50"}
    )

    return fig

def create_air_quality_gauge(data):
    """Create air quality visualization"""
    # Calculate air quality index based on available metrics
    visibility_score = min(100, (data['visibility'] / 100))
    cloud_score = 100 - data['clouds']['all']
    aqi = (visibility_score + cloud_score) / 2

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=aqi,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, 100],
                    'tickwidth': 1,
                    'tickcolor': "white"},
            'bar': {'color': "#4CAF50"},
            'steps': [
                {'range': [0, 30], 'color': "#ff5252"},
                {'range': [30, 70], 'color': "#ffab40"},
                {'range': [70, 100], 'color': "#69f0ae"}
            ],
        },
        title={'text': "Air Quality Index",
               'font': {'size': 24, 'color': 'white'}}
    ))

    fig.update_layout(
        paper_bgcolor='#2d2d2d',
        plot_bgcolor='#2d2d2d',
        height=300,
        margin=dict(t=60, b=20, l=20, r=20),
        font={'color': 'white'}
    )

    return fig

def create_wind_analysis(data):
    """Create wind analysis visualization"""
    fig = go.Figure()

    # Add wind rose
    fig.add_trace(go.Scatterpolar(
        r=[data['wind']['speed']],
        theta=[data['wind']['deg']],
        mode='markers+text',
        marker=dict(
            size=40,
            symbol='arrow',
            angle=data['wind']['deg'],
            color='#4CAF50'
        ),
        text=[f"{data['wind']['speed']} mph"],
        textposition="top center",
        textfont={'color': 'white'}
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, max(20, data['wind']['speed'] + 5)],
                           visible=True,
                           gridcolor='rgba(255, 255, 255, 0.2)'),
            angularaxis=dict(
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                gridcolor='rgba(255, 255, 255, 0.2)'
            ),
            bgcolor='#2d2d2d'
        ),
        paper_bgcolor='#2d2d2d',
        plot_bgcolor='#2d2d2d',
        title=dict(
            text='Wind Analysis',
            font=dict(color='white', size=24)
        ),
        height=300,
        margin=dict(t=60, b=20, l=20, r=20)
    )

    return fig

def create_environmental_trends(data):
    """Create environmental trends visualization"""
    fig = make_subplots(rows=1, cols=1)

    # Add pressure trend
    fig.add_trace(
        go.Scatter(
            x=['6h ago', '4h ago', '2h ago', 'now'],
            y=[data['main']['pressure'] - 2, data['main']['pressure'] - 1, 
               data['main']['pressure'] - 0.5, data['main']['pressure']],
            name='Pressure',
            line=dict(color='#4CAF50', width=2)
        )
    )

    # Update layout
    fig.update_layout(
        paper_bgcolor='#2d2d2d',
        plot_bgcolor='#2d2d2d',
        title=dict(
            text='Environmental Trends',
            font=dict(color='white', size=24)
        ),
        height=300,
        margin=dict(t=60, b=20, l=20, r=20),
        showlegend=True,
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(0,0,0,0)'
        ),
        xaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            color='white'
        ),
        yaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            color='white'
        )
    )

    return fig

@app.route('/')
def dashboard():
    try:
        # Get weather data
        bucket_name = os.environ.get('S3_BUCKET_NAME', '')
        weather_data = get_weather_data(bucket_name)
        if not weather_data:
            return render_template('error.html', 
                                error="No weather data available"), 404

        # Process cities data
        cities_data = []
        
        for data in weather_data:
            # Create visualization components for each city
            city_visualizations = {
                'name': data['name'],
                'temp_gauge': create_temperature_gauge(data).to_html(
                    full_html=False, 
                    div_id=f"temp-gauge-{data['name']}"
                ),
                'wind_compass': create_wind_compass(data).to_html(
                    full_html=False,
                    div_id=f"wind-compass-{data['name']}"
                ),
                'temp_distribution': create_temp_distribution(data).to_html(
                    full_html=False,
                    div_id=f"temp-dist-{data['name']}"
                ),
                'modern_gauge': create_modern_temp_gauge(data).to_html(
                    full_html=False,
                    div_id=f"modern-gauge-{data['name']}"
                ),
                'dashboard': create_weather_dashboard(data).to_html(
                    full_html=False,
                    div_id=f"dashboard-{data['name']}"
                ),
                'weather_matrix': create_weather_matrix(data).to_html(
                    full_html=False,
                    div_id=f"matrix-{data['name']}"
                ),
                'metrics': {
                    'temp_max': data['main']['temp_max'],
                    'temp_min': data['main']['temp_min'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'visibility': round(data['visibility'] / 1000, 1),
                    'clouds': data['clouds']['all'],
                    'grnd_level': data['main'].get('grnd_level', data['main']['pressure']),
                    'sea_level': data['main'].get('sea_level', data['main']['pressure'])
                }
            }
            
            # Try to fetch forecast data
            try:
                forecast_data = get_forecast_data(data['name'])
                if forecast_data:
                    city_visualizations['forecast'] = create_forecast_chart(forecast_data).to_html(
                        full_html=False,
                        div_id=f"forecast-{data['name']}"
                    )
            except Exception as e:
                app.logger.error(f"Error fetching forecast for {data['name']}: {e}")

            cities_data.append(city_visualizations)

        # Determine active city
        active_city = request.args.get('city', cities_data[0]['name']) if cities_data else None
        
        # Get dashboard style
        style = request.args.get('style', 'classic')
        template_name = {
            'classic': 'dashboard_classic.html',
            'environmental': 'dashboard_environmental.html',
            'modern': 'dashboard_modern.html'
        }.get(style, 'dashboard_classic.html')

        return render_template(
            template_name,
            cities_data=cities_data,
            cities=[city['name'] for city in cities_data],
            active_city=active_city,
            current_style=style,
            last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template(
            'error.html',
            error=f"Error loading dashboard: {str(e)}",
            debug_info=traceback.format_exc() if app.debug else None
        ), 500

@app.route('/update_data')
def update_data():
    """Endpoint for AJAX updates"""
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        return jsonify({'error': 'S3_BUCKET_NAME not set'}), 500
        
    try:
        data = get_weather_data(bucket_name)
        if not data:
            return jsonify({'error': 'No weather data available'}), 404
            
        unique_cities = {item['name']: item for item in data}  # Get latest data for each city
        return jsonify(list(unique_cities.values()))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('Server Error: %s', str(error))
    app.logger.error('Traceback: \n%s', traceback.format_exc())
    return render_template('error.html',
                         error=f"Internal Server Error: {str(error)}",
                         debug_info=traceback.format_exc() if app.debug else None)

@app.route('/debug')
def debug():
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    try:
        weather_data = get_weather_data(bucket_name)
        return jsonify({
            'bucket_name': bucket_name,
            'weather_data': weather_data,
            'env_vars': {
                'aws_region': os.environ.get('AWS_DEFAULT_REGION'),
                'has_aws_key': bool(os.environ.get('AWS_ACCESS_KEY_ID')),
                'has_aws_secret': bool(os.environ.get('AWS_SECRET_ACCESS_KEY')),
                'has_openweather_key': bool(os.environ.get('OPENWEATHER_API_KEY'))
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)