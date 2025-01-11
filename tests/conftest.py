import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_s3_client():
    with patch('boto3.client') as mock_boto3:
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_requests():
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def sample_weather_data():
    return {
        'main': {
            'temp': 72,
            'feels_like': 70,
            'humidity': 65
        },
        'weather': [
            {'description': 'clear sky'}
        ]
    }