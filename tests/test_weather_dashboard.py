import pytest
import requests
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from weather_dashboard import (
    verify_bucket,
    fetch_weather,
    save_to_s3,
    get_cities,
    main
)

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

def test_verify_bucket_success(mock_s3_client):
    mock_s3_client.head_bucket.return_value = {}
    assert verify_bucket('test-bucket') is True

def test_verify_bucket_not_found(mock_s3_client):
    error_response = {
        'Error': {
            'Code': '404',
            'Message': 'Not Found'
        }
    }
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
    assert verify_bucket('test-bucket') is False

def test_verify_bucket_access_denied(mock_s3_client):
    error_response = {
        'Error': {
            'Code': '403',
            'Message': 'Forbidden'
        }
    }
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
    assert verify_bucket('test-bucket') is False

def test_fetch_weather_success(mock_requests, sample_weather_data):
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = sample_weather_data
    mock_requests.return_value = mock_response

    result = fetch_weather('London', 'fake-api-key')
    assert result is not None
    assert result['main']['temp'] == 72

def test_fetch_weather_city_not_found(mock_requests):
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=Mock(status_code=404)
    )
    mock_requests.return_value = mock_response
    assert fetch_weather('NonexistentCity', 'fake-api-key') is None

def test_fetch_weather_timeout(mock_requests):
    mock_requests.side_effect = requests.exceptions.Timeout
    assert fetch_weather('London', 'fake-api-key') is None

def test_fetch_weather_connection_error(mock_requests):
    mock_requests.side_effect = requests.exceptions.ConnectionError
    assert fetch_weather('London', 'fake-api-key') is None

def test_save_to_s3_success(mock_s3_client):
    mock_s3_client.put_object.return_value = {}
    weather_data = {'temp': 72, 'humidity': 65}
    assert save_to_s3('test-bucket', 'London', weather_data) is True

def test_save_to_s3_failure(mock_s3_client):
    mock_s3_client.put_object.side_effect = ClientError(
        {'Error': {'Code': '403', 'Message': 'Forbidden'}},
        'PutObject'
    )
    weather_data = {'temp': 72, 'humidity': 65}
    assert save_to_s3('test-bucket', 'London', weather_data) is False

def test_save_to_s3_no_data():
    assert save_to_s3('test-bucket', 'London', None) is False

def test_get_cities_default():
    with patch.dict('os.environ', {}, clear=True):
        cities = get_cities()
        assert len(cities) == 3
        assert 'Philadelphia' in cities

def test_get_cities_custom():
    with patch.dict('os.environ', {'WEATHER_CITIES': 'London,Paris,Tokyo'}, clear=True):
        cities = get_cities()
        assert len(cities) == 3
        assert 'London' in cities

def test_main_missing_api_key():
    with patch.dict('os.environ', {'WEATHER_S3_BUCKET': 'test-bucket'}, clear=True):
        main()

def test_main_missing_bucket():
    with patch.dict('os.environ', {'OPENWEATHER_API_KEY': 'test-key'}, clear=True):
        main()

def test_main_success():
    with patch.dict('os.environ', {
        'OPENWEATHER_API_KEY': 'test-key',
        'WEATHER_S3_BUCKET': 'test-bucket',
        'WEATHER_CITIES': 'London'
    }, clear=True):
        with patch('weather_dashboard.verify_bucket', return_value=True):
            with patch('weather_dashboard.fetch_weather') as mock_fetch:
                with patch('weather_dashboard.save_to_s3', return_value=True):
                    mock_fetch.return_value = {
                        'main': {'temp': 72, 'feels_like': 70, 'humidity': 65},
                        'weather': [{'description': 'clear sky'}]
                    }
                    main()

def test_main_bucket_verification_failed():
    with patch.dict('os.environ', {
        'OPENWEATHER_API_KEY': 'test-key',
        'WEATHER_S3_BUCKET': 'test-bucket'
    }, clear=True):
        with patch('weather_dashboard.verify_bucket', return_value=False):
            main()

def test_main_unexpected_error():
    with patch.dict('os.environ', {
        'OPENWEATHER_API_KEY': 'test-key',
        'WEATHER_S3_BUCKET': 'test-bucket'
    }, clear=True):
        with patch('weather_dashboard.verify_bucket', 
                  side_effect=Exception("Unexpected error")):
            with pytest.raises(Exception):
                main()