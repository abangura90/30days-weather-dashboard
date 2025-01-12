import pytest
import requests
import json
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from datetime import datetime
from weather_collector_app.weather_collector import (
    verify_bucket,
    fetch_weather,
    save_to_s3,
    get_cities,
    main
)

# Bucket Verification Tests
class TestBucketVerification:
    def test_verify_bucket_success(self, mock_s3_client):
        mock_s3_client.head_bucket.return_value = {}
        assert verify_bucket('test-bucket') is True

    def test_verify_bucket_not_found(self, mock_s3_client):
        error_response = {
            'Error': {
                'Code': '404',
                'Message': 'Not Found'
            }
        }
        mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        assert verify_bucket('test-bucket') is False

    def test_verify_bucket_access_denied(self, mock_s3_client):
        error_response = {
            'Error': {
                'Code': '403',
                'Message': 'Forbidden'
            }
        }
        mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        assert verify_bucket('test-bucket') is False

# Weather API Tests
class TestWeatherAPI:
    # def test_fetch_weather_success(self, mock_requests, sample_weather_data, mock_datetime):
    #     mock_response = Mock()
    #     mock_response.ok = True
    #     mock_response.status_code = 200
    #     mock_response.text = "Success"
    #     mock_response.json.return_value = sample_weather_data
    #     mock_requests.return_value = mock_response

    #     result = fetch_weather('Japan', 'fake-api-key')
    #     assert result is not None
    #     assert result['name'] == 'Japan'
    #     assert result['main']['temp'] == 44.82
    #     assert 'timestamp' in result
    #     mock_requests.assert_called_once()

    def test_fetch_weather_city_not_found(self, mock_requests):
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "City not found"
        mock_requests.return_value = mock_response
        assert fetch_weather('NonexistentCity', 'fake-api-key') is None

    def test_fetch_weather_timeout(self, mock_requests):
        mock_requests.side_effect = requests.exceptions.Timeout
        assert fetch_weather('London', 'fake-api-key') is None

    def test_fetch_weather_connection_error(self, mock_requests):
        mock_requests.side_effect = requests.exceptions.ConnectionError
        assert fetch_weather('London', 'fake-api-key') is None

    def test_fetch_weather_invalid_json(self, mock_requests):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_requests.return_value = mock_response
        assert fetch_weather('London', 'fake-api-key') is None

# S3 Storage Tests
class TestS3Storage:
    def test_save_to_s3_success(self, mock_s3_client, sample_weather_data):
        mock_s3_client.put_object.return_value = {}
        assert save_to_s3('test-bucket', 'Japan', sample_weather_data) is True
        mock_s3_client.put_object.assert_called_once()

    def test_save_to_s3_failure(self, mock_s3_client, sample_weather_data):
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': '403', 'Message': 'Forbidden'}},
            'PutObject'
        )
        assert save_to_s3('test-bucket', 'Japan', sample_weather_data) is False

    def test_save_to_s3_no_data(self):
        assert save_to_s3('test-bucket', 'Japan', None) is False

    def test_save_to_s3_missing_timestamp(self):
        weather_data = {
            'main': {'temp': 72, 'humidity': 65},
            'name': 'Japan'
        }
        assert save_to_s3('test-bucket', 'Japan', weather_data) is False

    def test_save_to_s3_invalid_timestamp(self):
        weather_data = {
            'main': {'temp': 72, 'humidity': 65},
            'name': 'Japan',
            'timestamp': 'invalid-date'
        }
        assert save_to_s3('test-bucket', 'Japan', weather_data) is False

# City Configuration Tests
class TestCityConfiguration:
    def test_get_cities_default(self):
        with patch.dict('os.environ', {'WEATHER_CITIES': 'London,New Jersey,Japan'}, clear=True):
            cities = get_cities()
            assert len(cities) == 3
            assert all(city in cities for city in ['London', 'New Jersey', 'Japan'])

    def test_get_cities_empty(self):
        with patch.dict('os.environ', {'WEATHER_CITIES': ''}, clear=True):
            cities = get_cities()
            assert len(cities) == 0

    def test_get_cities_custom(self):
        with patch.dict('os.environ', {'WEATHER_CITIES': 'London,Paris,Tokyo'}, clear=True):
            cities = get_cities()
            assert len(cities) == 3
            assert all(city in cities for city in ['London', 'Paris', 'Tokyo'])

    def test_get_cities_whitespace(self):
        with patch.dict('os.environ', {'WEATHER_CITIES': ' London , Paris , Tokyo '}, clear=True):
            cities = get_cities()
            assert len(cities) == 3
            assert all(city in cities for city in ['London', 'Paris', 'Tokyo'])

    # def test_get_cities_duplicates(self):
    #     with patch.dict('os.environ', {'WEATHER_CITIES': 'London,London,Tokyo'}, clear=True):
    #         cities = get_cities()
    #         assert len(cities) == 2
    #         assert all(city in cities for city in ['London', 'Tokyo'])

# Main Function Tests
class TestMainFunction:
    def test_main_missing_api_key(self):
        with patch.dict('os.environ', {
            'WEATHER_S3_BUCKET': 'test-bucket',
            'WEATHER_CITIES': 'London'
        }, clear=True):
            assert main() == 1

    def test_main_missing_bucket(self):
        with patch.dict('os.environ', {
            'OPENWEATHER_API_KEY': 'test-key',
            'WEATHER_CITIES': 'London'
        }, clear=True):
            assert main() == 1

    def test_main_success(self, sample_weather_data):
        with patch.dict('os.environ', {
            'OPENWEATHER_API_KEY': 'test-key',
            'WEATHER_S3_BUCKET': 'test-bucket',
            'WEATHER_CITIES': 'Japan'
        }, clear=True):
            with patch('weather_collector_app.weather_collector.verify_bucket', return_value=True), \
                 patch('weather_collector_app.weather_collector.fetch_weather', return_value=sample_weather_data), \
                 patch('weather_collector_app.weather_collector.save_to_s3', return_value=True):
                assert main() == 0

    def test_main_unexpected_error(self):
        with patch.dict('os.environ', {
            'OPENWEATHER_API_KEY': 'test-key',
            'WEATHER_S3_BUCKET': 'test-bucket',
            'WEATHER_CITIES': 'London'
        }, clear=True):
            with patch('weather_collector_app.weather_collector.verify_bucket',
                      side_effect=Exception("Unexpected error")):
                with pytest.raises(Exception, match="Unexpected error"):
                    main()

    def test_main_bucket_verification_failed(self):
        with patch.dict('os.environ', {
            'OPENWEATHER_API_KEY': 'test-key',
            'WEATHER_S3_BUCKET': 'test-bucket',
            'WEATHER_CITIES': 'London'
        }, clear=True):
            with patch('weather_collector_app.weather_collector.verify_bucket', return_value=False):
                assert main() == 1

    def test_main_partial_failure(self, sample_weather_data):
        with patch.dict('os.environ', {
            'OPENWEATHER_API_KEY': 'test-key',
            'WEATHER_S3_BUCKET': 'test-bucket',
            'WEATHER_CITIES': 'London,Paris'
        }, clear=True):
            with patch('weather_collector_app.weather_collector.verify_bucket', return_value=True), \
                 patch('weather_collector_app.weather_collector.fetch_weather', side_effect=[sample_weather_data, None]), \
                 patch('weather_collector_app.weather_collector.save_to_s3', return_value=True):
                assert main() == 1  # Should return error due to partial failure