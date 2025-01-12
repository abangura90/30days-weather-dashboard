# src/weather_collector/__init__.py
import os
import boto3
import requests
from datetime import datetime
import json

def get_cities():
    """Get list of cities from environment variable"""
    cities_str = os.getenv('WEATHER_CITIES')
    
    # If environment variable exists but is empty, return empty list
    if cities_str is not None and not cities_str.strip():
        return []
    
    # If environment variable doesn't exist, return default cities
    if cities_str is None:
        return ['London', 'New Jersey', 'Japan']
        
    # Return parsed cities from environment variable
    return [city.strip() for city in cities_str.split(',') if city.strip()]

def verify_bucket(bucket_name):
    """Verify S3 bucket exists and is accessible"""
    try:
        s3 = boto3.client('s3')
        s3.head_bucket(Bucket=bucket_name)
        print("✓ S3 bucket verified")
        return True
    except Exception as e:
        print(f"✗ S3 bucket verification failed: {e}")
        return False

def fetch_weather(city, api_key):
    """Fetch weather data from OpenWeather API"""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    
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
            data = response.json()
            # Add timestamp to the data
            data['timestamp'] = datetime.now().isoformat()
            return data
        else:
            print(f"✗ API request failed for {city}: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error fetching weather data for {city}: {e}")
        return None

def save_to_s3(bucket_name, city, data):
    """Save weather data to S3"""
    if not data:
        print("✗ Error saving data to S3: No data provided")
        return False

    try:
        # Verify timestamp exists
        if 'timestamp' not in data:
            print("✗ Error saving data to S3: timestamp missing")
            return False

        s3 = boto3.client('s3')
        timestamp = datetime.fromisoformat(data['timestamp'])
        filename = f"weather-data/{city.lower()}/{timestamp.strftime('%Y/%m/%d/%H%M%S')}.json"
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        print(f"✓ Data saved to s3://{bucket_name}/{filename}")
        return True
        
    except Exception as e:
        print(f"✗ Error saving data to S3: {e}")
        return False

# src/weather_collector/collect.py (NEW FILE)
def main():
    try:
        # Get and validate environment variables
        api_key = os.getenv('OPENWEATHER_API_KEY')
        bucket_name = os.getenv('WEATHER_S3_BUCKET')
        
        if not api_key or not bucket_name:
            print("✗ Missing required environment variables:")
            if not api_key:
                print("  - OPENWEATHER_API_KEY")
            if not bucket_name:
                print("  - WEATHER_S3_BUCKET")
            return 1
        
        # Get cities list
        cities = get_cities()
        if not cities:
            print("✗ No cities specified in WEATHER_CITIES environment variable")
            print("  Format: WEATHER_CITIES='City1,City2,City3'")
            return 1
        
        print(f"\nConfig loaded:")
        print(f"• Number of cities: {len(cities)}")
        print(f"• Cities: {', '.join(cities)}")
        
        # Verify S3 bucket access
        print("\nVerifying S3 bucket access...")
        if not verify_bucket(bucket_name):
            return 1
        
        errors = 0
        print("\nFetching weather data...")
        for city in cities:
            print(f"\nProcessing {city}...")
            
            # Fetch weather data
            weather_data = fetch_weather(city, api_key)
            if not weather_data:
                errors += 1
                continue
                
            # Print weather information
            try:
                temp = weather_data['main']['temp']
                feels_like = weather_data['main']['feels_like']
                humidity = weather_data['main']['humidity']
                conditions = weather_data['weather'][0]['description']
                
                print(f"• Temperature: {temp}°F")
                print(f"• Feels like: {feels_like}°F")
                print(f"• Humidity: {humidity}%")
                print(f"• Conditions: {conditions}")
                
                # Save to S3
                if not save_to_s3(bucket_name, city, weather_data):
                    errors += 1
                
            except KeyError as e:
                print(f"✗ Unexpected data format for {city}: {e}")
                print("  Weather API may have changed its response format")
                errors += 1

        return 1 if errors > 0 else 0
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise  # Re-raise the exception for test to catch

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise

# src/run_collector.py (NEW FILE)
#!/usr/bin/env python3
from weather_collector_app.weather_collector import main

if __name__ == "__main__":
    exit(main())