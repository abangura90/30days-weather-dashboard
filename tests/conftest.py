import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture
def mock_s3_client():
    with patch('boto3.client') as mock_boto3:
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_get.return_value = mock_response
        yield mock_get

@pytest.fixture
def sample_weather_data():
    return {
        'base': 'stations',
        'clouds': {
            'all': 75
        },
        'cod': 200,
        'coord': {
            'lat': 35.6854,
            'lon': 139.7531
        },
        'dt': 1736656076,
        'id': 1861060,
        'main': {
            'feels_like': 41.65,
            'grnd_level': 1016,
            'humidity': 52,
            'pressure': 1018,
            'sea_level': 1018,
            'temp': 44.82,
            'temp_max': 45.81,
            'temp_min': 43.88
        },
        'name': 'Japan',
        'rain': {
            '1h': 0.25
        },
        'sys': {
            'country': 'JP',
            'id': 268395,
            'sunrise': 1736632243,
            'sunset': 1736668031,
            'type': 2
        },
        'timestamp': '2025-01-12T04:28:00.375974',
        'timezone': 32400,
        'visibility': 10000,
        'weather': [
            {
                'description': 'light rain',
                'icon': '10d',
                'id': 500,
                'main': 'Rain'
            }
        ],
        'wind': {
            'deg': 10,
            'speed': 5.75
        }
    }

@pytest.fixture
def sample_s3_response():
    """Mock S3 list_objects_v2 response"""
    return {
        'Contents': [
            {
                'Key': 'weather-data/japan/2025/01/12/042800.json',
                'LastModified': datetime(2025, 1, 12, 4, 28, 0),
                'Size': 1234,
                'StorageClass': 'STANDARD'
            }
        ],
        'KeyCount': 1,
        'MaxKeys': 1000,
        'Name': 'test-bucket',
        'Prefix': 'weather-data/'
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for testing"""
    monkeypatch.setenv('OPENWEATHER_API_KEY', 'test-api-key')
    monkeypatch.setenv('WEATHER_S3_BUCKET', 'test-bucket')
    monkeypatch.setenv('WEATHER_CITIES', 'London,New Jersey,Japan')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')

@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing-key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing-secret')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')

@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime for consistent timestamps"""
    class MockDateTime:
        @staticmethod
        def now():
            return datetime(2025, 1, 12, 4, 28, 0, 375974)
        
        @staticmethod
        def fromisoformat(date_string):
            return datetime.fromisoformat(date_string)

    monkeypatch.setattr('weather_collector.datetime', MockDateTime)