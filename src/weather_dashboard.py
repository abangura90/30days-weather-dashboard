import os
import json
import boto3
import requests
from datetime import datetime
from botocore.exceptions import ClientError

def verify_bucket(bucket_name):
    """Verify S3 bucket exists and is accessible"""
    try:
        s3 = boto3.client('s3')
        s3.head_bucket(Bucket=bucket_name)
        print(f"✓ Successfully connected to bucket: {bucket_name}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == '403':
            print(f"✗ Access denied to bucket: {bucket_name}")
            print("  Please check your AWS credentials and permissions")
        elif error_code == '404':
            print(f"✗ Bucket not found: {bucket_name}")
            print("  Please verify the bucket name and region")
        else:
            print(f"✗ Error accessing bucket: {e}")
        return False

def fetch_weather(city, api_key):
    """Fetch weather data for a city"""
    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        response = requests.get(url, params={
            "q": city,
            "appid": api_key,
            "units": "imperial"
        }, timeout=10)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404:
            print(f"✗ City not found: {city}")
        elif isinstance(e, requests.exceptions.Timeout):
            print(f"✗ Request timed out for {city}")
        elif isinstance(e, requests.exceptions.ConnectionError):
            print(f"✗ Connection error while fetching data for {city}")
        else:
            print(f"✗ Error fetching weather data for {city}: {e}")
        return None

def save_to_s3(bucket_name, city, data):
    """Save weather data to S3"""
    if not data:
        return False
        
    s3 = boto3.client('s3')
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    file_path = f"weather-data/{city}-{timestamp}.json"
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=file_path,
            Body=json.dumps(data),
            ContentType='application/json'
        )
        print(f"✓ Saved to s3://{bucket_name}/{file_path}")
        return True
    except ClientError as e:
        print(f"✗ Failed to save to S3: {e}")
        print("  Please check your AWS permissions")
        return False

def get_cities():
    """Get list of cities from environment variable"""
    cities_str = os.getenv('WEATHER_CITIES', 'Philadelphia,Seattle,New York')
    # Split by comma and strip whitespace from each city
    return [city.strip() for city in cities_str.split(',') if city.strip()]

def main():
    # Get and validate environment variables
    api_key = os.getenv('OPENWEATHER_API_KEY')
    bucket_name = os.getenv('WEATHER_S3_BUCKET')
    
    if not api_key or not bucket_name:
        print("✗ Missing required environment variables:")
        if not api_key:
            print("  - OPENWEATHER_API_KEY")
        if not bucket_name:
            print("  - WEATHER_S3_BUCKET")
        return
    
    # Get cities list
    cities = get_cities()
    if not cities:
        print("✗ No cities specified in WEATHER_CITIES environment variable")
        print("  Format: WEATHER_CITIES='City1,City2,City3'")
        return
    
    print(f"\nConfig loaded:")
    print(f"• Number of cities: {len(cities)}")
    print(f"• Cities: {', '.join(cities)}")
    
    # Verify S3 bucket access
    print("\nVerifying S3 bucket access...")
    if not verify_bucket(bucket_name):
        return
    
    print("\nFetching weather data...")
    for city in cities:
        print(f"\nProcessing {city}...")
        
        # Fetch weather data
        weather_data = fetch_weather(city, api_key)
        if not weather_data:
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
            
            # Add timestamp to data
            weather_data['timestamp'] = datetime.now().isoformat()
            
            # Save to S3
            save_to_s3(bucket_name, city, weather_data)
            
        except KeyError as e:
            print(f"✗ Unexpected data format for {city}: {e}")
            print("  Weather API may have changed its response format")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise